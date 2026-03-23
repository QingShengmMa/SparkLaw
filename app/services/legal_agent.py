"""
法律 Agent 服务
基于 LangChain 实现智能法律助手
"""

from typing import Dict, List, Optional, Literal, Any, AsyncIterator
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict, Annotated
from app.services.llm_factory import LLMFactory
from app.services.tools import get_tools
from app.services.rag_service import get_rag_service
from app.core.memory_manager import memory_manager
from app.core.config import settings
from app.core.logger import app_logger

# 五大律师人格定义
PersonalityType = Literal["machine", "empathy", "cost", "cost_expert", "aggressive", "educator"]

PERSONALITY_PROMPTS = {
    "machine": """【冰冷机器】
你是一个纯粹理性的法律分析机器。你的特点：
- 只提供法条和判例，不带任何情感色彩
- 用数据和逻辑说话，避免主观判断
- 直接指出法律风险，不做安慰
- 回答简洁、精准、无冗余
- 如果问题超出法律范围，直接拒绝""",
    
    "empathy": """【共情守护】
你是一个温暖体贴的法律顾问。你的特点：
- 理解用户的处境和情感，提供同情和支持
- 在法律建议的基础上，考虑人性化因素
- 用温和、鼓励的语气交流
- 不仅解释法律，还帮助用户理解权利和保护
- 建议用户寻求心理或社会支持（如需要）""",
    
    "cost_expert": """【成本专家】
你是一个精打细算的法律成本分析师。你的特点：
- 关注每一个决策的经济成本和收益
- 提供成本-收益分析，帮助用户做出经济理性的选择
- 指出隐藏成本和长期影响
- 提供最具成本效益的解决方案
- 用数字和对比说话""",
    
    "aggressive": """【激进斗士】
你是一个寸土必争的法律战士。你的特点：
- 帮助用户找到所有可能的反击点和进攻策略
- 不放过任何法律漏洞或对方的错误
- 用强硬、坚定的语气
- 提供最激进的法律主张
- 鼓励用户维护自己的权利，不要退缩""",
    
    "educator": """【普法导师】
你是一个耐心的法律教育者。你的特点：
- 用通俗易懂的语言解释复杂的法律概念
- 提供背景知识和法律原理的深度讲解
- 举例说明，帮助用户理解
- 鼓励提问，耐心回答
- 目标是让用户真正理解法律，而不仅仅是获得答案"""
}


def normalize_personality(personality: PersonalityType) -> str:
    """统一前后端人格字段，兼容 cost/cost_expert"""
    if personality == "cost":
        return "cost_expert"
    return personality


class LegalAgentGraphState(TypedDict):
    """Legal Agent ReAct 图状态。"""
    messages: Annotated[List[Any], add_messages]


class LegalAgentService:
    """
    法律 Agent 服务类

    提供智能法律咨询功能，支持多轮对话和会话管理。
    基于 LangChain 框架，可配置使用不同的 LLM 后端。

    Attributes:
        llm: LLM 实例（ChatOllama 或 ChatOpenAI）
        tools: 可用的工具列表（搜索、计算器等）
        sessions: 会话历史存储（session_id -> 消息列表）
        system_prompt: 系统提示词
    """
    
    def __init__(self):
        """
        初始化法律 Agent 服务
        
        创建 LLM 实例、加载工具、初始化会话存储。
        
        Raises:
            Exception: 当 LLM 初始化失败时抛出异常
        """
        try:
            self.llm = LLMFactory.create_llm()
            self.tools = get_tools(
                enable_search=settings.ENABLE_WEB_SEARCH,
                enable_calculator=True
            )
            self.rag_service = get_rag_service()
            self.sessions: Dict[str, List[Dict]] = {}
            self.system_prompt = self._get_system_prompt()
            self.llm_with_tools = self.llm.bind_tools(self.tools)
            self.tool_node = ToolNode(self.tools)
            self.graph = self._build_react_graph(self.llm_with_tools)
            
            app_logger.info("✅ 法律 Agent 服务初始化完成")
        except Exception as e:
            app_logger.error(f"❌ 法律 Agent 服务初始化失败: {str(e)}")
            raise
    
    def _get_system_prompt(self, personality: PersonalityType = "machine") -> str:
        """
        获取系统提示词
        
        根据选定的律师人格构建系统提示词，定义其角色、能力和行为准则。
        
        Args:
            personality: 律师人格类型（machine, empathy, cost_expert, aggressive, educator）
        
        Returns:
            str: 系统提示词文本
        """
        base_prompt = f"""你是一个专业的法律咨询助手，专注于{settings.DEFAULT_JURISDICTION}法律体系。

**重要原则：**
1. 使用通俗易懂的语言，避免复杂的法律术语，或在使用时提供清晰解释
2. 你提供的是一般性法律信息，不是专业法律建议
3. 始终建议用户在重要事项上咨询专业律师
4. 保持友好、耐心的态度
5. 如果不确定，诚实地说明，不要编造信息

**你的能力：**
- 解释常见法律概念和条款
- 回答基本的法律问题
- 分析简单合同的关键条款
- 提供法律程序的基本指导

**免责声明：**
⚠️ 本助手提供的信息仅供参考，不构成专业法律建议。如遇具体法律问题，请咨询持牌律师。

"""
        
        # 添加人格特定的提示词
        personality_prompt = PERSONALITY_PROMPTS.get(personality, PERSONALITY_PROMPTS["machine"])
        
        return base_prompt + personality_prompt
    
    def _get_session_history(self, session_id: str) -> List[Dict]:
        """
        获取指定会话的历史记录
        
        如果会话不存在，会自动创建一个空的会话。
        
        Args:
            session_id: 会话唯一标识
            
        Returns:
            List[Dict]: 会话历史消息列表
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = []
            app_logger.debug(f"创建新会话: {session_id}")
        return self.sessions[session_id]
    
    async def _retrieve_legal_context(self, question: str, top_k: int = 3) -> str:
        """从法律知识库检索与问题相关的条文片段。"""
        try:
            results = await self.rag_service.retrieve_clauses(query=question, top_k=top_k)
            if not results:
                return ""

            snippets = []
            for idx, item in enumerate(results, start=1):
                text = item.get("text", "")
                if text:
                    snippets.append(f"[{idx}] {text[:300]}")
            return "\n".join(snippets)
        except Exception as e:
            app_logger.warning(f"法律上下文检索失败: {str(e)}")
            return ""

    def _build_react_graph(self, llm_with_tools) -> Any:
        """构建标准 ReAct 图：agent -> tools -> agent。"""
        workflow = StateGraph(LegalAgentGraphState)
        workflow.add_node("agent", lambda state: self._agent_node(state, llm_with_tools))
        workflow.add_node("tools", self._safe_tools_node)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", self._should_continue, {"tools": "tools", "end": END})
        workflow.add_edge("tools", "agent")
        return workflow.compile()

    async def _agent_node(self, state: LegalAgentGraphState, llm_with_tools) -> Dict[str, Any]:
        """Agent 节点：思考并可能生成 tool_calls。"""
        response = await llm_with_tools.ainvoke(state["messages"])
        return {"messages": [response]}

    def _should_continue(self, state: LegalAgentGraphState) -> str:
        """判断是否继续工具调用循环。"""
        last_msg = state["messages"][-1]
        has_tool_calls = bool(getattr(last_msg, "tool_calls", None))
        return "tools" if has_tool_calls else "end"

    async def _safe_tools_node(self, state: LegalAgentGraphState) -> Dict[str, Any]:
        """工具节点：执行工具并在异常时回填错误 ToolMessage。"""
        try:
            return await self.tool_node.ainvoke(state)
        except Exception as e:
            app_logger.warning(f"工具执行失败: {str(e)}")
            last_msg = state["messages"][-1]
            tool_calls = getattr(last_msg, "tool_calls", []) or []
            fallback_messages = []
            for tool_call in tool_calls:
                fallback_messages.append(
                    ToolMessage(
                        content=f"工具执行失败，请检查参数后重试。错误详情: {str(e)}",
                        tool_call_id=tool_call.get("id", "tool_error"),
                    )
                )
            return {"messages": fallback_messages}

    def _build_messages(
        self,
        session_id: str,
        user_input: str,
        personality: PersonalityType = "empathy",
        summary_memory: str = "",
        semantic_memories: Optional[List[str]] = None,
        legal_context: str = "",
    ) -> List:
        """
        构建 LLM 输入消息：系统提示词 + 长期记忆 + 短期窗口 + 当前问题。
        """
        normalized_personality = normalize_personality(personality)

        memory_block = []
        if summary_memory:
            memory_block.append(f"[User Profile & Context Summary]\n{summary_memory}")

        if semantic_memories:
            memory_block.append("[User Semantic Profile Snippets]\n" + "\n".join([f"- {m}" for m in semantic_memories]))

        if legal_context:
            memory_block.append("[Relevant Legal References]\n" + legal_context)

        enhanced_system_prompt = self._get_system_prompt(normalized_personality)
        if memory_block:
            enhanced_system_prompt += "\n\n" + "\n\n".join(memory_block)

        messages = [SystemMessage(content=enhanced_system_prompt)]

        history = self._get_session_history(session_id)
        short_term_history = memory_manager.get_short_term_messages(history)
        for msg in short_term_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=user_input))

        return messages
    
    async def run_react_stream(
        self,
        messages: List[Any],
        graph_to_use=None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """流式执行 ReAct 图，输出工具调用事件供 SSE 使用。"""
        graph = graph_to_use or self.graph
        initial_state: LegalAgentGraphState = {"messages": messages}

        final_content = ""

        async for event in graph.astream(initial_state):
            for node_name, node_output in event.items():
                if node_name == "agent" and isinstance(node_output, dict):
                    msg_list = node_output.get("messages", [])
                    if msg_list:
                        msg = msg_list[-1]
                        content = getattr(msg, "content", "")
                        tool_calls = getattr(msg, "tool_calls", None) or []
                        if tool_calls:
                            for call in tool_calls:
                                yield {
                                    "role": "agent",
                                    "event": "tool_call",
                                    "tool_name": call.get("name", "unknown_tool"),
                                    "tool_args": call.get("args", {}),
                                }
                        else:
                            final_content = content

                if node_name == "tools" and isinstance(node_output, dict):
                    msg_list = node_output.get("messages", [])
                    for tool_msg in msg_list:
                        yield {
                            "role": "tools",
                            "event": "tool_result",
                            "content": getattr(tool_msg, "content", str(tool_msg)),
                        }

        yield {
            "role": "agent",
            "event": "final",
            "content": final_content,
        }

    async def chat(
        self,
        question: str,
        session_id: str = "default",
        personality: PersonalityType = "empathy",
        custom_config: Optional[Dict] = None
    ) -> Dict:
        """
        处理用户法律咨询问题（集成 Hybrid Memory）。
        """
        if not question or not question.strip():
            return {
                "answer": "请输入您的法律问题。",
                "session_id": session_id,
                "sources": [],
                "error": "Empty question"
            }

        try:
            app_logger.info(f"📝 处理问题 [session={session_id}]: {question[:50]}...")

            graph_to_use = self.graph
            if custom_config and custom_config.get("api_key"):
                app_logger.info("🔧 使用自定义 LLM 配置")
                custom_llm = LLMFactory.create_llm(
                    api_key=custom_config.get("api_key"),
                    base_url=custom_config.get("base_url"),
                    model=custom_config.get("model"),
                    temperature=custom_config.get("temperature"),
                    max_tokens=custom_config.get("max_tokens")
                )
                graph_to_use = self._build_react_graph(custom_llm.bind_tools(self.tools))

            history = self._get_session_history(session_id)

            # 1) 维护摘要记忆（当历史超阈值时自动压缩）
            await memory_manager.maybe_update_summary(session_id, history)
            summary_memory = memory_manager.get_summary(session_id)

            # 2) 语义记忆检索（用户画像档案）
            semantic_memories = memory_manager.search_semantic_memory(
                session_id=session_id,
                query=question,
                top_k=3,
            )

            # 3) 法律条文检索上下文
            legal_context = await self._retrieve_legal_context(question, top_k=3)

            # 4) 构建上下文消息（短期窗口 + 长期摘要 + 语义记忆 + 法条）
            messages = self._build_messages(
                session_id=session_id,
                user_input=question,
                personality=personality,
                summary_memory=summary_memory,
                semantic_memories=semantic_memories,
                legal_context=legal_context,
            )

            # 5) ReAct 图执行（agent <-> tools 闭环）
            initial_state: LegalAgentGraphState = {"messages": messages}
            final_state = await graph_to_use.ainvoke(initial_state)
            final_msg = final_state["messages"][-1]
            answer = final_msg.content if hasattr(final_msg, "content") else str(final_msg)

            # 6) 更新短期会话
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer})

            # 7) 后台异步写入语义记忆（不阻塞响应）
            memory_manager.schedule_semantic_memory_write(
                session_id=session_id,
                user_question=question,
                assistant_answer=answer,
            )

            app_logger.info(f"✅ 回答生成成功 [session={session_id}]")

            return {
                "answer": answer,
                "session_id": session_id,
                "sources": ["summary_memory", "semantic_memory", "legal_rag"]
            }

        except Exception as e:
            app_logger.error(f"❌ 处理问题时出错 [session={session_id}]: {str(e)}")
            error_msg = "抱歉，处理您的问题时出现错误。请稍后重试，或咨询专业律师。"

            return {
                "answer": error_msg,
                "session_id": session_id,
                "sources": [],
                "error": str(e)
            }
    
    def reset_session(self, session_id: str) -> bool:
        """
        重置会话历史
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功
        """
        try:
            if session_id in self.sessions:
                self.sessions[session_id] = []
                app_logger.info(f"会话已重置 [session={session_id}]")
            return True
        except Exception as e:
            app_logger.error(f"重置会话失败 [session={session_id}]: {str(e)}")
            return False
    
    def get_session_history(self, session_id: str) -> List[Dict]:
        """
        获取会话历史
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话历史列表
        """
        return self._get_session_history(session_id)


# 创建全局 Agent 实例
legal_agent = LegalAgentService()
