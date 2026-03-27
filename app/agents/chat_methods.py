"""
法律 Agent 服务 - Part 2: 消息构建、流式输出、chat 接口
"""

from __future__ import annotations
import json
import re
from typing import Dict, List, Optional, Any, AsyncIterator, Tuple
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.agents.legal_agent import (
    LegalAgentService,
    LegalAgentGraphState,
    PersonalityType,
    normalize_personality,
    PERSONALITY_PROMPTS,
    DEEP_THINK_SYSTEM_PROMPT,
)
from app.llm.factory import LLMFactory
from app.core.memory_manager import memory_manager
from app.core.logger import app_logger
from app.guardrails.hallucination_guard import HallucinationGuard, GuardrailViolationError
from app.guardrails.output_validator import OutputValidator


def _build_messages(
    self: LegalAgentService,
    session_id: str,
    user_input: str,
    personality: PersonalityType = "empathy",
    summary_memory: str = "",
    semantic_memories: Optional[List[str]] = None,
    legal_context: str = "",
    enable_deep_think: bool = False,
) -> List:
    normalized = normalize_personality(personality)
    memory_block = []
    if summary_memory:
        memory_block.append(f"[User Profile & Context Summary]\n{summary_memory}")
    if semantic_memories:
        memory_block.append("[User Semantic Profile Snippets]\n" + "\n".join(f"- {m}" for m in semantic_memories))
    if legal_context:
        memory_block.append(f"[Relevant Legal References]\n{legal_context}")

    system_content = self._get_system_prompt(normalized, deep_think=enable_deep_think)
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


def _extract_urls_from_output(output: Any) -> List[str]:
    """从工具输出中提取 URL 列表（最多5个）。"""
    text = str(output.content) if hasattr(output, "content") else str(output)
    urls = re.findall(r'https?://[^\s"<>]+', text)
    seen: set = set()
    result: List[str] = []
    for u in urls:
        u = u.rstrip('.,;)')
        if u not in seen:
            seen.add(u)
            result.append(u)
        if len(result) >= 5:
            break
    return result


def _extract_search_items_from_output(output: Any) -> List[Dict[str, str]]:
    """从搜索工具输出中提取结构化条目（标题/链接/摘要）。"""
    text = str(output.content) if hasattr(output, "content") else str(output)
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    items: List[Dict[str, str]] = []

    for block in blocks:
        title = ""
        url = ""
        snippet = ""
        for ln in block.splitlines():
            line = ln.strip()
            if line.startswith("标题："):
                title = line.replace("标题：", "", 1).strip()
            elif line.startswith("链接："):
                url = line.replace("链接：", "", 1).strip()
            elif line.startswith("摘要："):
                snippet = line.replace("摘要：", "", 1).strip()
        if url:
            items.append({"title": title, "url": url, "snippet": snippet})
        if len(items) >= 8:
            break

    return items


def _parse_law_list_from_legal_context(legal_context: str) -> List[Dict[str, str]]:
    """从 legal_context 文本中解析 law_x 引用 ID，供 guardrail 校验使用。"""
    if not legal_context:
        return []

    law_ids = re.findall(r"\[(\d+)\]", legal_context)
    # legal_context 当前格式为 [1] xxx，[2] xxx，映射到 law_1/law_2
    return [{"id": f"law_{idx}"} for idx in law_ids]


def _split_think_fragments(buffer: str, in_thinking: bool) -> Tuple[List[Tuple[str, str]], str, bool]:
    """Split stream text into normal/thinking fragments with boundary-safe buffer.

    Returns: (segments[(kind,text)], remained_buffer, new_in_thinking)
    """
    segments: List[Tuple[str, str]] = []
    i = 0
    n = len(buffer)

    while i < n:
        if in_thinking:
            close_idx = buffer.find("</think>", i)
            if close_idx == -1:
                tail = buffer[i:]
                # keep possible truncated close tag in remainder
                keep = min(len("</think>") - 1, len(tail))
                split_at = len(tail) - keep
                if split_at > 0:
                    segments.append(("thinking", tail[:split_at]))
                return segments, tail[split_at:], True

            chunk = buffer[i:close_idx]
            if chunk:
                segments.append(("thinking", chunk))
            i = close_idx + len("</think>")
            in_thinking = False
            continue

        open_idx = buffer.find("<think>", i)
        if open_idx == -1:
            tail = buffer[i:]
            keep = min(len("<think>") - 1, len(tail))
            split_at = len(tail) - keep
            if split_at > 0:
                segments.append(("text", tail[:split_at]))
            return segments, tail[split_at:], False

        if open_idx > i:
            segments.append(("text", buffer[i:open_idx]))
        i = open_idx + len("<think>")
        in_thinking = True

    return segments, "", in_thinking


async def run_react_event_stream(
    self: LegalAgentService,
    messages: List[Any],
    graph_to_use=None,
    thread_id: Optional[str] = None,
    enable_deep_think: bool = False,
    enable_web_search: bool = False,
    legal_context: str = "",
) -> AsyncIterator[Dict[str, Any]]:
    graph = graph_to_use or self.graph
    initial_state: LegalAgentGraphState = {"messages": messages}
    final_chunks: List[str] = []
    think_chunks: List[str] = []
    in_thinking = False
    think_buffer = ""
    config = {"configurable": {"thread_id": thread_id}} if thread_id else None

    if enable_deep_think:
        yield {"type": "thinking_start"}

    event_stream = (
        graph.astream_events(initial_state, config=config, version="v2")
        if config
        else graph.astream_events(initial_state, version="v2")
    )

    async for evt in event_stream:
        event_type = evt.get("event")

        if event_type == "on_chat_model_stream":
            chunk = evt.get("data", {}).get("chunk")
            # 支持 DeepSeek-R1 等带 reasoning_content 的模型
            reasoning = getattr(chunk, "additional_kwargs", {}).get("reasoning_content") or ""
            if reasoning and enable_deep_think:
                in_thinking = True
                think_chunks.append(reasoning)
                yield {"type": "thinking", "content": reasoning}
                continue

            text = self._extract_text_from_chunk(chunk)
            if not text:
                continue

            think_buffer += text
            segments, think_buffer, in_thinking = _split_think_fragments(think_buffer, in_thinking)
            for kind, content in segments:
                if not content:
                    continue
                if kind == "thinking":
                    think_chunks.append(content)
                    yield {"type": "thinking", "content": content}
                else:
                    final_chunks.append(content)
                    yield {"type": "text", "content": content}

        elif event_type == "on_tool_start":
            tool_name = evt.get("name") or evt.get("data", {}).get("name") or "unknown_tool"
            tool_input = evt.get("data", {}).get("input") or {}
            if enable_web_search and "search" in tool_name.lower():
                query = ""
                if isinstance(tool_input, dict):
                    query = tool_input.get("query") or tool_input.get("__arg1") or str(tool_input)
                else:
                    query = str(tool_input)
                yield {"type": "search_start", "tool_name": tool_name, "query": query, "input": tool_input}
            else:
                yield {"type": "tool_start", "tool_name": tool_name, "input": tool_input}

        elif event_type in ("on_tool_end", "on_tool_error"):
            tool_name = evt.get("name") or "unknown_tool"
            output = evt.get("data", {}).get("output") or ""
            if enable_web_search and "search" in tool_name.lower():
                urls = _extract_urls_from_output(output)
                items = _extract_search_items_from_output(output)
                yield {
                    "type": "search_end",
                    "tool_name": tool_name,
                    "urls": urls,
                    "items": items,
                    "snippet": str(output)[:400] if output else "",
                }
            else:
                yield {"type": "tool_end", "tool_name": tool_name}

    if think_buffer:
        tail_segments, think_buffer, in_thinking = _split_think_fragments(think_buffer, in_thinking)
        for kind, content in tail_segments:
            if not content:
                continue
            if kind == "thinking":
                think_chunks.append(content)
                yield {"type": "thinking", "content": content}
            else:
                final_chunks.append(content)
                yield {"type": "text", "content": content}

        if think_buffer:
            # 仍残留截断标签或未闭合 think 内容，按当前状态并入可见文本以避免丢字
            if in_thinking:
                think_chunks.append(think_buffer)
                yield {"type": "thinking", "content": think_buffer}
            else:
                final_chunks.append(think_buffer)
                yield {"type": "text", "content": think_buffer}
            think_buffer = ""

    if in_thinking or (enable_deep_think and think_chunks):
        yield {"type": "thinking_end", "thinking": "".join(think_chunks)}

    final_answer = "".join(final_chunks)
    guard = HallucinationGuard()
    validator = OutputValidator()

    try:
        retrieved_law_list = _parse_law_list_from_legal_context(legal_context)
        guard_result = guard.check_hallucination(
            generated_text=final_answer,
            retrieved_law_list=retrieved_law_list,
            raise_on_violation=True,
        )
        _ = guard_result

        if "[法条:" in final_answer:
            normalized = {
                "plaintiff_win_rate": 50,
                "defendant_win_rate": 50,
                "verdict_text": final_answer,
            }
            if not validator.validate_verdict(normalized):
                raise GuardrailViolationError("输出结构化校验未通过", violations=["OUTPUT_VALIDATION_FAILED"])
    except GuardrailViolationError as e:
        app_logger.warning(f"⚠️ Guardrail 拦截（降级继续）: {str(e)}")
        final_answer += "\n\n> ⚠️ **系统提示**：以上部分法条引用未能与本地知识库完全匹配，请审慎参考。"
    except Exception as e:
        app_logger.warning(f"⚠️ Guardrail 校验异常（降级继续）: {str(e)}")
        final_answer += "\n\n> ⚠️ **系统提示**：以上内容暂未完成完整合规校验，请审慎参考。"

    if not final_answer.strip():
        raise RuntimeError("GUARDRAIL_BLOCKED: 无法生成有效合规回复")

    yield {"type": "final", "answer": final_answer}


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
