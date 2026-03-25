"""
法律 Agent 服务 - Part 2: 消息构建、流式输出、chat 接口
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, AsyncIterator
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.agents.legal_agent import (
    LegalAgentService,
    LegalAgentGraphState,
    PersonalityType,
    normalize_personality,
    PERSONALITY_PROMPTS,
)
from app.llm.factory import LLMFactory
from app.core.memory_manager import memory_manager
from app.core.logger import app_logger


def _build_messages(
    self: LegalAgentService,
    session_id: str,
    user_input: str,
    personality: PersonalityType = "empathy",
    summary_memory: str = "",
    semantic_memories: Optional[List[str]] = None,
    legal_context: str = "",
) -> List:
    normalized = normalize_personality(personality)
    memory_block = []
    if summary_memory:
        memory_block.append(f"[User Profile & Context Summary]\n{summary_memory}")
    if semantic_memories:
        memory_block.append("[User Semantic Profile Snippets]\n" + "\n".join(f"- {m}" for m in semantic_memories))
    if legal_context:
        memory_block.append(f"[Relevant Legal References]\n{legal_context}")

    system_content = self._get_system_prompt(normalized)
    if memory_block:
        system_content += "\n\n" + "\n\n".join(memory_block)

    messages = [SystemMessage(content=system_content)]
    history = self._get_session_history(session_id)
    for msg in memory_manager.get_short_term_messages(history):
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=user_input))
    return messages


def _extract_text_from_chunk(self: LegalAgentService, chunk: Any) -> str:
    if chunk is None:
        return ""
    content = getattr(chunk, "content", chunk)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return ""


async def run_react_event_stream(
    self: LegalAgentService,
    messages: List[Any],
    graph_to_use=None,
    thread_id: Optional[str] = None,
) -> AsyncIterator[Dict[str, Any]]:
    graph = graph_to_use or self.graph
    initial_state: LegalAgentGraphState = {"messages": messages}
    final_chunks: List[str] = []
    config = {"configurable": {"thread_id": thread_id}} if thread_id else None

    event_stream = (
        graph.astream_events(initial_state, config=config, version="v2")
        if config
        else graph.astream_events(initial_state, version="v2")
    )

    async for evt in event_stream:
        event_type = evt.get("event")
        if event_type == "on_chat_model_stream":
            text = self._extract_text_from_chunk(evt.get("data", {}).get("chunk"))
            if text:
                final_chunks.append(text)
                yield {"type": "text_chunk", "content": text}
        elif event_type == "on_tool_start":
            yield {
                "type": "tool_start",
                "tool_name": evt.get("name") or evt.get("data", {}).get("name") or "unknown_tool",
                "input": evt.get("data", {}).get("input"),
            }
        elif event_type in ("on_tool_end", "on_tool_error"):
            yield {"type": "tool_end", "tool_name": evt.get("name") or "unknown_tool"}

    yield {"type": "final", "answer": "".join(final_chunks)}


async def run_react_stream(
    self: LegalAgentService,
    messages: List[Any],
    graph_to_use=None,
    thread_id: Optional[str] = None,
) -> AsyncIterator[Dict[str, Any]]:
    async for evt in self.run_react_event_stream(messages, graph_to_use=graph_to_use, thread_id=thread_id):
        if evt.get("type") == "tool_start":
            yield {"role": "agent", "event": "tool_call", "tool_name": evt.get("tool_name", "unknown_tool"), "tool_args": evt.get("input", {})}
        elif evt.get("type") == "tool_end":
            yield {"role": "tools", "event": "tool_result", "content": f"工具 {evt.get('tool_name', 'unknown_tool')} 执行完成"}
        elif evt.get("type") == "final":
            yield {"role": "agent", "event": "final", "content": evt.get("answer", "")}


async def chat(
    self: LegalAgentService,
    question: str,
    session_id: str = "default",
    personality: PersonalityType = "empathy",
    custom_config: Optional[Dict] = None,
    thread_id: Optional[str] = None,
) -> Dict:
    if not question or not question.strip():
        return {"answer": "请输入您的法律问题。", "session_id": session_id, "sources": [], "error": "Empty question"}

    try:
        app_logger.info(f"📝 处理问题 [session={session_id}]: {question[:50]}...")
        graph_to_use = self.graph
        if custom_config and custom_config.get("api_key"):
            custom_llm = LLMFactory.create_llm(
                api_key=custom_config.get("api_key"),
                base_url=custom_config.get("base_url"),
                model=custom_config.get("model"),
                temperature=custom_config.get("temperature"),
                max_tokens=custom_config.get("max_tokens"),
            )
            graph_to_use = self._build_react_graph(custom_llm.bind_tools(self.tools))

        history = self._get_session_history(session_id)
        await memory_manager.maybe_update_summary(session_id, history)
        summary_memory = memory_manager.get_summary(session_id)
        semantic_memories = memory_manager.search_semantic_memory(session_id=session_id, query=question, top_k=3)
        legal_context = await self._retrieve_legal_context(question, top_k=3)

        messages = self._build_messages(
            session_id=session_id,
            user_input=question,
            personality=personality,
            summary_memory=summary_memory,
            semantic_memories=semantic_memories,
            legal_context=legal_context,
        )

        initial_state: LegalAgentGraphState = {"messages": messages}
        config = {"configurable": {"thread_id": thread_id}} if thread_id else None
        final_state = await (graph_to_use.ainvoke(initial_state, config=config) if config else graph_to_use.ainvoke(initial_state))
        final_msg = final_state["messages"][-1]
        answer = final_msg.content if hasattr(final_msg, "content") else str(final_msg)

        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})
        memory_manager.schedule_semantic_memory_write(session_id=session_id, user_question=question, assistant_answer=answer)

        app_logger.info(f"✅ 回答生成成功 [session={session_id}]")
        return {"answer": answer, "session_id": session_id, "sources": ["summary_memory", "semantic_memory", "legal_rag"]}

    except Exception as e:
        app_logger.error(f"❌ 处理问题时出错 [session={session_id}]: {str(e)}")
        return {"answer": "抱歉，处理您的问题时出现错误。请稍后重试。", "session_id": session_id, "sources": [], "error": str(e)}


def reset_session(self: LegalAgentService, session_id: str) -> bool:
    try:
        if session_id in self.sessions:
            self.sessions[session_id] = []
        return True
    except Exception as e:
        app_logger.error(f"重置会话失败: {str(e)}")
        return False


def get_session_history(self: LegalAgentService, session_id: str) -> List[Dict]:
    return self._get_session_history(session_id)


# Monkey-patch methods onto LegalAgentService
LegalAgentService._build_messages = _build_messages
LegalAgentService._extract_text_from_chunk = _extract_text_from_chunk
LegalAgentService.run_react_event_stream = run_react_event_stream
LegalAgentService.run_react_stream = run_react_stream
LegalAgentService.chat = chat
LegalAgentService.reset_session = reset_session
LegalAgentService.get_session_history = get_session_history

# Re-export singleton
from app.agents.legal_agent import LegalAgentService as _Svc  # noqa: E402
_legal_agent_instance: Optional[_Svc] = None


def get_legal_agent() -> _Svc:
    global _legal_agent_instance
    if _legal_agent_instance is None:
        _legal_agent_instance = _Svc()
    return _legal_agent_instance


legal_agent = get_legal_agent()
