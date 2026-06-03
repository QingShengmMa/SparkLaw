"""Lightweight supervisor debate agent.

This module intentionally avoids eager RAG/vector initialization so the app can
start on small servers. When a vector store is available it enriches the debate
with retrieved references; otherwise it falls back to direct LLM analysis.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Optional

from app.core.logger import app_logger
from app.models.response import AgentArgument, DebateResponse
from app.services.llm_factory import LLMFactory


class SupervisorDebateAgent:
    """Small-footprint multi-perspective debate agent."""

    def __init__(self):
        self.llm = LLMFactory.create_llm()
        self.rag_service = None
        app_logger.info("SupervisorDebateAgent initialized in lightweight mode")

    def _get_rag_service(self):
        if self.rag_service is None:
            from app.services.rag_service import get_rag_service

            self.rag_service = get_rag_service()
        return self.rag_service

    async def _retrieve_legal_basis(self, case_description: str) -> List[str]:
        try:
            rag = self._get_rag_service()
            results = await rag.retrieve_law(query=case_description, top_k=5)
            if not results:
                results = await rag.retrieve_clauses(query=case_description, top_k=5)
            return [
                str(item.get("text") or "").strip()[:320]
                for item in results
                if str(item.get("text") or "").strip()
            ][:5]
        except Exception as exc:
            app_logger.warning(f"Debate RAG unavailable, continuing without local references: {exc}")
            return []

    @staticmethod
    def _extract_points(text: str, fallback: str) -> List[str]:
        points: List[str] = []
        for line in (text or "").splitlines():
            cleaned = line.strip().lstrip("-*0123456789.、 ")
            if 8 <= len(cleaned) <= 90:
                points.append(cleaned)
            if len(points) >= 3:
                break
        return points or [fallback]

    async def _ask_role(self, role: str, case_description: str, legal_basis: List[str], strategy: str) -> str:
        basis_text = "\n".join(f"{idx}. {item}" for idx, item in enumerate(legal_basis, 1))
        if not basis_text:
            basis_text = "未接入本地知识库，请基于一般中国法律知识谨慎分析，并避免编造具体法条编号。"

        prompt = (
            f"你是{role}。请围绕以下案情进行专业、克制的法律分析。\n"
            f"辩论策略：{strategy or 'aggressive'}\n\n"
            f"案情：\n{case_description}\n\n"
            f"参考资料：\n{basis_text}\n\n"
            "输出要求：使用中文，列出3个核心观点，每个观点给出简短理由。"
        )
        response = await self.llm.ainvoke(prompt)
        return response.content if hasattr(response, "content") else str(response)

    async def simulate_debate(self, case_description: str, strategy: str = "aggressive") -> DebateResponse:
        if not case_description or len(case_description.strip()) < 20:
            raise ValueError("案情描述过短或为空，请提供更完整的事实。")

        legal_basis = await self._retrieve_legal_basis(case_description)
        plaintiff_text = await self._ask_role("原告律师", case_description, legal_basis, strategy)
        defendant_text = await self._ask_role("被告律师", case_description, legal_basis, strategy)
        judge_text = await self._ask_role("主审法官", case_description, legal_basis, "neutral")

        return DebateResponse(
            case_description=case_description,
            plaintiff_argument=AgentArgument(
                agent_role="LegalResearcher",
                argument=plaintiff_text,
                legal_basis=legal_basis,
                key_points=self._extract_points(plaintiff_text, "原告主张需要进一步补充证据支持"),
            ),
            defendant_argument=AgentArgument(
                agent_role="ContractAnalyzer",
                argument=defendant_text,
                legal_basis=legal_basis,
                key_points=self._extract_points(defendant_text, "被告抗辩需要进一步补充事实依据"),
            ),
            judge_opinion=AgentArgument(
                agent_role="Supervisor",
                argument=judge_text,
                legal_basis=legal_basis,
                key_points=self._extract_points(judge_text, "裁判逻辑需结合完整证据进一步审查"),
            ),
            win_probability={"plaintiff": 0.5, "defendant": 0.5},
        )

    async def execute(self, case_description: str, strategy: str = "aggressive") -> DebateResponse:
        return await self.simulate_debate(case_description=case_description, strategy=strategy)

    async def execute_stream(
        self,
        case_description: str,
        strategy: str = "aggressive",
        custom_config: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        original_llm = self.llm
        if custom_config and custom_config.get("api_key"):
            self.llm = LLMFactory.create_llm(
                api_key=custom_config.get("api_key"),
                base_url=custom_config.get("base_url"),
                model=custom_config.get("model"),
                temperature=custom_config.get("temperature"),
                max_tokens=custom_config.get("max_tokens"),
            )

        try:
            result = await self.simulate_debate(case_description=case_description, strategy=strategy)
            yield {"type": "result", "result": result.model_dump(mode="json")}
        finally:
            self.llm = original_llm

    async def simulate_debate_stream(
        self,
        case_description: str,
        strategy: str = "aggressive",
        custom_config: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        async for payload in self.execute_stream(case_description, strategy, custom_config):
            yield payload

    async def resume_debate_stream(self, thread_id: str, human_question: str):
        payload = {
            "type": "error",
            "message": "轻量部署模式暂不支持中断后恢复庭审线程，请重新发起一次辩论。",
            "thread_id": thread_id,
        }
        yield payload


_supervisor_agent_instance: Optional[SupervisorDebateAgent] = None


def get_supervisor_agent() -> SupervisorDebateAgent:
    global _supervisor_agent_instance
    if _supervisor_agent_instance is None:
        _supervisor_agent_instance = SupervisorDebateAgent()
    return _supervisor_agent_instance
