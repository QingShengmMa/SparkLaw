"""
法律 Agent 服务 - Part 1: 初始化与核心方法
"""

import asyncio
from typing import Dict, List, Optional, Literal, Any, AsyncIterator
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict, Annotated
from app.llm.factory import LLMFactory
from app.tools.legal_tools import get_tools
from app.knowledge.rag_service import get_rag_service
from app.core.memory_manager import memory_manager
from app.core.config import settings
from app.core.logger import app_logger


class LLMConnectionError(Exception):
    pass


PersonalityType = Literal["machine", "empathy", "cost", "cost_expert", "aggressive", "educator"]

PERSONALITY_PROMPTS = {
    "machine": """【冰冷机器】\n你是纯粹理性的法律分析机器，只提供法条和判例，不带情感色彩，回答简洁精准。""",
    "empathy": """【共情守护】\n你是温暖体贴的法律顾问，理解用户处境，用温和鼓励的语气，兼顾法律与人性化因素。""",
    "cost_expert": """【成本专家】\n你是精打细算的法律成本分析师，关注每个决策的经济成本和收益，用数字和对比说话。""",
    "aggressive": """【激进斗士】\n你是寸土必争的法律战士，帮用户找到所有反击点和进攻策略，不放过任何法律漏洞。""",
    "educator": """【普法导师】\n你是耐心的法律教育者，用通俗易懂的语言解释法律概念，举例说明，鼓励提问。""",
}


def normalize_personality(personality: PersonalityType) -> str:
    return "cost_expert" if personality == "cost" else personality


class LegalAgentGraphState(TypedDict):
    messages: Annotated[List[Any], add_messages]


class LegalAgentService:
    """法律 Agent 服务，支持多轮对话与 ReAct 工具调用。"""

    def __init__(self):
        try:
            self.llm = LLMFactory.create_llm()
            self.tools = get_tools(enable_search=settings.ENABLE_WEB_SEARCH, enable_calculator=True)
            self.rag_service = get_rag_service()
            self.sessions: Dict[str, List[Dict]] = {}
            self.system_prompt = self._get_system_prompt()
            self.llm_with_tools = self.llm.bind_tools(self.tools)
            self.tool_node = ToolNode(self.tools)
            self.checkpointer = self._create_checkpointer()
            self.graph = self._build_react_graph(self.llm_with_tools)
            app_logger.info("✅ 法律 Agent 服务初始化完成")
        except Exception as e:
            app_logger.error(f"❌ 法律 Agent 服务初始化失败: {str(e)}")
            raise

    def _get_system_prompt(self, personality: PersonalityType = "machine") -> str:
        base = f"""你是一个专业的法律咨询助手，专注于{settings.DEFAULT_JURISDICTION}法律体系。

**重要原则：**
1. 使用通俗易懂的语言，避免复杂法律术语
2. 你提供的是一般性法律信息，不是专业法律建议
3. 始终建议用户在重要事项上咨询专业律师
4. 保持友好、耐心的态度
5. 严禁把未提供的合同/证据说成用户已提供
6. 若用户未提供合同原文，只能给通用审查框架并明确标注

**输出约束：**
- 用户未提供合同原文/截图/文件时，禁止输出"条款一/条款二"这类具体条文分析。
- 需要分析合同时，先向用户索取合同文本。

"""
        return base + PERSONALITY_PROMPTS.get(personality, PERSONALITY_PROMPTS["machine"])

    def _get_session_history(self, session_id: str) -> List[Dict]:
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]

    async def _retrieve_legal_context(self, question: str, top_k: int = 3) -> str:
        try:
            results = await self.rag_service.retrieve_clauses(query=question, top_k=top_k)
            if not results:
                return ""
            return "\n".join(f"[{i}] {item.get('text','')[:300]}" for i, item in enumerate(results, 1) if item.get("text"))
        except Exception as e:
            app_logger.warning(f"法律上下文检索失败: {str(e)}")
            return ""

    def _create_checkpointer(self):
        try:
            from langgraph.checkpoint.base import BaseCheckpointSaver
            from langgraph.checkpoint.memory import MemorySaver
            try:
                from langgraph.checkpoint.redis.aio import AsyncRedisSaver

                candidate = AsyncRedisSaver.from_conn_string(settings.REDIS_URL)
                if not isinstance(candidate, BaseCheckpointSaver):
                    raise TypeError(f"Invalid redis checkpointer type: {type(candidate).__name__}")

                app_logger.info(f"✅ LangGraph Checkpointer 使用 Redis: {settings.REDIS_URL}")
                return candidate
            except Exception as redis_err:
                app_logger.warning(f"⚠️ Redis Checkpointer 不可用，回退 MemorySaver: {str(redis_err)}")
                return MemorySaver()
        except Exception as err:
            app_logger.error(f"❌ Checkpointer 初始化失败: {str(err)}")
            return None

    async def _setup_async_checkpointer(self, saver) -> None:
        setup = getattr(saver, "setup", None)
        if callable(setup):
            await setup()

    def _build_react_graph(self, llm_with_tools) -> Any:
        workflow = StateGraph(LegalAgentGraphState)

        async def agent_node(state: LegalAgentGraphState) -> Dict[str, Any]:
            return await self._agent_node(state, llm_with_tools)

        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", self._safe_tools_node)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", self._should_continue, {"tools": "tools", "end": END})
        workflow.add_edge("tools", "agent")
        return workflow.compile(checkpointer=self.checkpointer) if self.checkpointer else workflow.compile()

    async def _agent_node(self, state: LegalAgentGraphState, llm_with_tools) -> Dict[str, Any]:
        try:
            return {"messages": [await llm_with_tools.ainvoke(state["messages"])]}
        except Exception as e:
            s = str(e).lower()
            if any(k in s for k in ["timeout", "timed out", "connecttimeout", "read timeout"]):
                raise LLMConnectionError(f"LLM API 请求超时: {e}") from e
            if any(k in s for k in ["401", "403", "authentication", "invalid api key", "unauthorized"]):
                raise LLMConnectionError(f"LLM API 鉴权失败: {e}") from e
            if any(k in s for k in ["429", "rate limit", "rate_limit"]):
                raise LLMConnectionError(f"LLM API 速率限制: {e}") from e
            raise

    def _should_continue(self, state: LegalAgentGraphState) -> str:
        return "tools" if bool(getattr(state["messages"][-1], "tool_calls", None)) else "end"

    async def _safe_tools_node(self, state: LegalAgentGraphState) -> Dict[str, Any]:
        try:
            return await self.tool_node.ainvoke(state)
        except Exception as e:
            app_logger.warning(f"工具执行失败: {str(e)}")
            tool_calls = getattr(state["messages"][-1], "tool_calls", []) or []
            return {"messages": [ToolMessage(content=f"工具执行失败: {str(e)}", tool_call_id=tc.get("id", "tool_error")) for tc in tool_calls]}
