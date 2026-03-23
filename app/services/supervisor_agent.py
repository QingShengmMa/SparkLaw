"""
Supervisor 多智能体架构（主管-打工人）
- Supervisor: 任务路由与验收
- LegalResearcher: 法条检索与法理分析
- ContractAnalyzer: 合同文本风险识别
- LitigationStrategist: 诉讼策略与文书草案
"""

from __future__ import annotations

import re
from operator import add
from typing import Annotated, Dict, List, Literal, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph

from app.core.logger import app_logger
from app.services.llm_factory import LLMFactory
from app.services.rag_service import get_rag_service
from app.services.multimodal_contract_reviewer import get_multimodal_reviewer
from app.models.response import DebateResponse, AgentArgument


class SupervisorState(TypedDict):
    case_description: str
    messages: Annotated[List[Dict], add]
    supervisor_note: str
    next_worker: Literal["LegalResearcher", "ContractAnalyzer", "LitigationStrategist", "END"]
    last_worker: str
    last_worker_result: str
    legal_research_result: str
    contract_analysis_result: str
    litigation_strategy_result: str
    retries: int
    final_answer: str


class SupervisorDebateAgent:
    """基于 LangGraph Conditional Edges 的 Supervisor 多智能体。"""

    def __init__(self):
        self.llm = LLMFactory.create_llm()
        self.rag_service = get_rag_service()
        self.contract_reviewer = get_multimodal_reviewer()
        self.graph = self._build_graph()
        app_logger.info("🧠 SupervisorDebateAgent 初始化完成")

    def _build_graph(self):
        workflow = StateGraph(SupervisorState)

        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("LegalResearcher", self._legal_researcher_node)
        workflow.add_node("ContractAnalyzer", self._contract_analyzer_node)
        workflow.add_node("LitigationStrategist", self._litigation_strategist_node)

        workflow.set_entry_point("supervisor")

        workflow.add_conditional_edges(
            "supervisor",
            self._route_by_supervisor,
            {
                "LegalResearcher": "LegalResearcher",
                "ContractAnalyzer": "ContractAnalyzer",
                "LitigationStrategist": "LitigationStrategist",
                "END": END,
            },
        )

        workflow.add_edge("LegalResearcher", "supervisor")
        workflow.add_edge("ContractAnalyzer", "supervisor")
        workflow.add_edge("LitigationStrategist", "supervisor")

        return workflow.compile()

    def _route_by_supervisor(self, state: SupervisorState) -> str:
        return state.get("next_worker", "END")

    def _initial_worker(self, case_description: str) -> str:
        text = case_description
        if any(k in text for k in ["合同", "条款", "甲方", "乙方"]):
            return "ContractAnalyzer"
        if any(k in text for k in ["起诉", "诉状", "答辩", "抗辩", "庭审"]):
            return "LitigationStrategist"
        return "LegalResearcher"

    def _is_result_satisfactory(self, result: str) -> bool:
        if not result:
            return False
        return len(result.strip()) >= 120

    async def _supervisor_node(self, state: SupervisorState) -> Dict:
        case_description = state["case_description"]
        last_worker_result = state.get("last_worker_result", "")
        retries = state.get("retries", 0)

        # 首次派工
        if not state.get("last_worker"):
            worker = self._initial_worker(case_description)
            note = f"Supervisor 决定调用 {worker} 处理当前问题。"
            return {
                "next_worker": worker,
                "supervisor_note": note,
                "messages": [{"role": "supervisor", "content": note}],
            }

        # 二次验收：不满意则返工/改派，满意则结束
        if self._is_result_satisfactory(last_worker_result):
            final_answer = (
                "# Agent 团队协作结论\n\n"
                f"## Supervisor 结论\n{last_worker_result}\n\n"
                "---\n"
                f"- 来源 Worker: {state.get('last_worker')}"
            )
            note = "Supervisor 验收通过，输出最终结论。"
            return {
                "next_worker": "END",
                "final_answer": final_answer,
                "supervisor_note": note,
                "messages": [{"role": "supervisor", "content": note}],
            }

        if retries >= 1:
            # 一次返工后仍不满意，改派诉讼策略师做整合兜底
            note = "Supervisor 对结果不满意，改派 LitigationStrategist 做整合。"
            return {
                "next_worker": "LitigationStrategist",
                "retries": retries + 1,
                "supervisor_note": note,
                "messages": [{"role": "supervisor", "content": note}],
            }

        note = f"Supervisor 认为 {state.get('last_worker')} 结果不充分，打回重做。"
        return {
            "next_worker": state.get("last_worker", "LegalResearcher"),
            "retries": retries + 1,
            "supervisor_note": note,
            "messages": [{"role": "supervisor", "content": note}],
        }

    async def _legal_researcher_node(self, state: SupervisorState) -> Dict:
        question = state["case_description"]
        rag_results = await self.rag_service.retrieve_clauses(question, top_k=3)
        context = "\n".join([f"[{i+1}] {r.get('text', '')[:260]}" for i, r in enumerate(rag_results)])

        prompt = (
            "你是 LegalResearcher。请仅基于给定法条片段回答：\n"
            f"问题：{question}\n\n"
            f"法条片段：\n{context or '（未检索到法条）'}\n\n"
            "输出：1) 核心法条 2) 适用要点 3) 风险提示。"
        )
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content if hasattr(response, "content") else str(response)

        return {
            "last_worker": "LegalResearcher",
            "last_worker_result": content,
            "legal_research_result": content,
            "messages": [{"role": "LegalResearcher", "content": content}],
        }

    async def _contract_analyzer_node(self, state: SupervisorState) -> Dict:
        # 这里直接把用户输入视为待审合同文本片段
        text = state["case_description"]
        result = await self.contract_reviewer.review_from_text(text, contract_id="adhoc_session")

        formatted = "\n".join(
            [f"- [{r.risk_level}] {r.risk_explanation}（建议：{r.revise_suggestion}）" for r in result.risks[:5]]
        )
        content = f"合同风险审查结论：\n{formatted or result.overall_summary}\n\n总体：{result.overall_summary}"

        return {
            "last_worker": "ContractAnalyzer",
            "last_worker_result": content,
            "contract_analysis_result": content,
            "messages": [{"role": "ContractAnalyzer", "content": content}],
        }

    async def _litigation_strategist_node(self, state: SupervisorState) -> Dict:
        question = state["case_description"]
        hints = "\n\n".join(
            [
                state.get("legal_research_result", ""),
                state.get("contract_analysis_result", ""),
                state.get("last_worker_result", ""),
            ]
        ).strip()

        prompt = (
            "你是 LitigationStrategist，请给出诉状/答辩/举证策略草案。\n"
            f"案情：{question}\n\n"
            f"可用线索：{hints or '无'}\n\n"
            "输出结构：\n"
            "1. 诉讼请求建议\n2. 事实与法律依据\n3. 证据清单\n4. 庭审攻防要点\n5. 执行建议"
        )
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content if hasattr(response, "content") else str(response)

        return {
            "last_worker": "LitigationStrategist",
            "last_worker_result": content,
            "litigation_strategy_result": content,
            "messages": [{"role": "LitigationStrategist", "content": content}],
        }

    async def simulate_debate(self, case_description: str) -> DebateResponse:
        if not case_description or len(case_description.strip()) < 20:
            raise ValueError("案情描述过短或为空，请提供详细案情")

        initial_state: SupervisorState = {
            "case_description": case_description,
            "messages": [],
            "supervisor_note": "",
            "next_worker": "LegalResearcher",
            "last_worker": "",
            "last_worker_result": "",
            "legal_research_result": "",
            "contract_analysis_result": "",
            "litigation_strategy_result": "",
            "retries": 0,
            "final_answer": "",
        }

        final_state = await self.graph.ainvoke(initial_state)

        plaintiff_text = final_state.get("legal_research_result", "")
        defendant_text = final_state.get("contract_analysis_result", "")
        judge_text = final_state.get("final_answer") or final_state.get("litigation_strategy_result", "")

        # 简单概率提取
        match = re.search(r"(\d{1,2})%", judge_text)
        plaintiff_prob = 0.5
        if match:
            plaintiff_prob = max(0.0, min(1.0, int(match.group(1)) / 100.0))

        return DebateResponse(
            case_description=case_description,
            plaintiff_argument=AgentArgument(
                agent_role="LegalResearcher",
                argument=plaintiff_text,
                legal_basis=[],
                key_points=[],
            ),
            defendant_argument=AgentArgument(
                agent_role="ContractAnalyzer",
                argument=defendant_text,
                legal_basis=[],
                key_points=[],
            ),
            judge_opinion=AgentArgument(
                agent_role="Supervisor",
                argument=judge_text,
                legal_basis=[],
                key_points=[],
            ),
            win_probability={"plaintiff": plaintiff_prob, "defendant": 1 - plaintiff_prob},
        )

    async def simulate_debate_stream(self, case_description: str, custom_config: Dict = None):
        if not case_description or len(case_description.strip()) < 20:
            raise ValueError("案情描述过短或为空")

        original_llm = None
        if custom_config and custom_config.get("api_key"):
            original_llm = self.llm
            self.llm = LLMFactory.create_llm(
                api_key=custom_config.get("api_key"),
                base_url=custom_config.get("base_url"),
                model=custom_config.get("model"),
                temperature=custom_config.get("temperature"),
                max_tokens=custom_config.get("max_tokens"),
            )
            self.graph = self._build_graph()

        try:
            initial_state: SupervisorState = {
                "case_description": case_description,
                "messages": [],
                "supervisor_note": "",
                "next_worker": "LegalResearcher",
                "last_worker": "",
                "last_worker_result": "",
                "legal_research_result": "",
                "contract_analysis_result": "",
                "litigation_strategy_result": "",
                "retries": 0,
                "final_answer": "",
            }

            async for event in self.graph.astream(initial_state):
                for node_name, node_output in event.items():
                    messages = node_output.get("messages", []) if isinstance(node_output, dict) else []
                    if not messages:
                        continue

                    for msg in messages:
                        role = msg.get("role", node_name)
                        content = msg.get("content", "")

                        yield {"role": role, "event": "start"}
                        yield {"role": role, "event": "content", "content": content}
                        yield {"role": role, "event": "end"}

            # 最终结果事件
            final_state = await self.graph.ainvoke(initial_state)
            yield {
                "role": "supervisor",
                "event": "result",
                "result": {
                    "plaintiff_win_rate": int(final_state.get("win_probability", {}).get("plaintiff", 0.5) * 100),
                    "plaintiff_winning_factors": ["已完成多 Agent 协作分析"],
                    "defendant_winning_factors": ["需结合证据和程序进一步核验"],
                    "judge_summary": final_state.get("final_answer", final_state.get("last_worker_result", "")),
                },
            }
        finally:
            if original_llm is not None:
                self.llm = original_llm
                self.graph = self._build_graph()


_supervisor_agent_instance = None


def get_supervisor_agent() -> SupervisorDebateAgent:
    global _supervisor_agent_instance
    if _supervisor_agent_instance is None:
        _supervisor_agent_instance = SupervisorDebateAgent()
    return _supervisor_agent_instance
