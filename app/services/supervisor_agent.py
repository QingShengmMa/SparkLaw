"""
Supervisor 多智能体架构（主管-打工人）
- Supervisor: 任务路由与验收
- LegalResearcher: 法条检索与法理分析
- ContractAnalyzer: 合同文本风险识别
- LitigationStrategist: 诉讼策略与文书草案
"""

from __future__ import annotations

import asyncio
from operator import add
from typing import Annotated, Any, AsyncIterator, Dict, List, Literal, Optional, TypedDict
import json
import re
import uuid

from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field

from app.core.logger import app_logger
from app.core.config import settings
from app.services.llm_factory import LLMFactory
from app.services.rag_service import get_rag_service
from app.models.response import DebateResponse, AgentArgument


class SupervisorState(TypedDict):
    case_description: str
    strategy: str
    human_question: str
    evidence_list: List[Dict[str, str]]
    legal_basis: str
    messages: Annotated[List[Dict], add]
    supervisor_note: str
    next_worker: Literal[
        "LegalResearcher",
        "ContractAnalyzer",
        "LitigationStrategist",
        "Verification_Node",
        "HumanJudgeIntervention",
        "END",
    ]
    last_worker: str
    last_worker_result: str
    verification_status: Literal["pending", "pass", "rework"]
    verification_feedback: str
    verification_target_worker: Literal["LegalResearcher", "ContractAnalyzer", "LitigationStrategist"]
    legal_research_result: str
    contract_analysis_result: str
    litigation_strategy_result: str
    plaintiff_key_points: List[str]
    defendant_key_points: List[str]
    current_turn: int
    max_turns: int
    retries: int
    max_verification_retries: int
    final_answer: str
    verdict_result: Dict[str, Any]
    plaintiff_win_rate: int
    defendant_win_rate: int


class VerdictResult(BaseModel):
    plaintiff_win_rate: int = Field(..., ge=0, le=100, description="原告胜诉概率，0到100的整数")
    defendant_win_rate: int = Field(..., ge=0, le=100, description="被告胜诉概率，0到100的整数，必须与原告相加为100")
    verdict_text: str = Field(
        ...,
        description="详细的判决书正文，必须使用 Markdown 格式排版（包含案由、争议焦点、判决逻辑）",
    )


class DebateSummary(BaseModel):
    plaintiff_winning_factors: List[str] = Field(default_factory=list)
    defendant_winning_factors: List[str] = Field(default_factory=list)
    judge_summary: str = ""


class DebateStreamInit(BaseModel):
    thread_id: str
    evidence_list: List[Dict[str, str]]


class DebateStreamResult(BaseModel):
    result: Dict[str, Any]


STRATEGY_INSTRUCTION_MAP: Dict[str, str] = {
    "aggressive": "你现在的辩论策略是【激进施压】。请主动寻找被告的逻辑漏洞，语言风格锋利、具有压迫感，强调攻势与节奏。",
    "conservative": "你现在的辩论策略是【死磕法条】。请以保守防御方式作答，严格咬文嚼字，强调程序正义与法条精准适配。",
    "mediator": "你现在的辩论策略是【商业调解】。请强调合作背景与现实利益，优先提出减少损失、推动共赢和解的方案。",
}


def normalize_strategy(strategy: str | None) -> str:
    value = (strategy or "").strip().lower()
    if value in STRATEGY_INSTRUCTION_MAP:
        return value
    return "aggressive"


def _text_fingerprint(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip())


class SupervisorDebateAgent:
    """基于 LangGraph Conditional Edges 的 Supervisor 多智能体。"""

    def __init__(self):
        self.llm = LLMFactory.create_llm()
        self.rag_service = get_rag_service()
        self.checkpointer = self._create_checkpointer()
        self.graph = self._build_graph()
        app_logger.info("🧠 SupervisorDebateAgent 初始化完成")

    def _create_checkpointer(self):
        try:
            from langgraph.checkpoint.redis.aio import AsyncRedisSaver
            saver = AsyncRedisSaver.from_conn_string(settings.REDIS_URL)
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._setup_async_checkpointer(saver))
            except RuntimeError:
                asyncio.run(self._setup_async_checkpointer(saver))
            return saver
        except Exception as e:
            app_logger.warning(f"SupervisorAgent Redis Checkpointer 不可用，回退 MemorySaver: {str(e)}")
            return MemorySaver()

    async def _setup_async_checkpointer(self, saver) -> None:
        setup = getattr(saver, "setup", None)
        if callable(setup):
            await setup()

    def _build_graph(self):
        workflow = StateGraph(SupervisorState)

        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("LegalResearcher", self._legal_researcher_node)
        workflow.add_node("ContractAnalyzer", self._contract_analyzer_node)
        workflow.add_node("LitigationStrategist", self._litigation_strategist_node)
        workflow.add_node("Verification_Node", self._verification_node)
        workflow.add_node("HumanJudgeIntervention", self._human_judge_intervention_node)

        workflow.set_entry_point("supervisor")

        workflow.add_conditional_edges(
            "supervisor",
            self._route_by_supervisor,
            {
                "LegalResearcher": "LegalResearcher",
                "ContractAnalyzer": "ContractAnalyzer",
                "LitigationStrategist": "LitigationStrategist",
                "Verification_Node": "Verification_Node",
                "HumanJudgeIntervention": "HumanJudgeIntervention",
                "END": END,
            },
        )

        workflow.add_edge("LegalResearcher", "Verification_Node")
        workflow.add_edge("ContractAnalyzer", "Verification_Node")
        workflow.add_edge("LitigationStrategist", "Verification_Node")
        workflow.add_conditional_edges(
            "Verification_Node",
            self._route_by_verification,
            {
                "supervisor": "supervisor",
                "LegalResearcher": "LegalResearcher",
                "ContractAnalyzer": "ContractAnalyzer",
                "LitigationStrategist": "LitigationStrategist",
            },
        )
        workflow.add_edge("HumanJudgeIntervention", "LitigationStrategist")

        return workflow.compile(checkpointer=self.checkpointer)

    def _route_by_supervisor(self, state: SupervisorState) -> str:
        """Return next worker selected by supervisor node."""
        return state.get("next_worker", "END")

    def _route_by_verification(self, state: SupervisorState) -> str:
        verification_status = state.get("verification_status", "pending")
        retries = int(state.get("retries", 0))
        max_retries = int(state.get("max_verification_retries", 2))

        if verification_status == "rework" and retries < max_retries:
            return state.get("verification_target_worker", "LegalResearcher")
        return "supervisor"

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

    def _extract_key_points(self, text: str, fallback: str) -> List[str]:
        """从模型输出中提取最多 3 条可读要点。"""
        if not text:
            return [fallback]

        points: List[str] = []
        for line in text.splitlines():
            cleaned = line.strip().lstrip("-•1234567890.、 ")
            if len(cleaned) >= 8 and len(cleaned) <= 80:
                points.append(cleaned)
            if len(points) >= 3:
                break

        return points or [fallback]

    def _normalize_verdict_result(self, verdict_result: VerdictResult) -> VerdictResult:
        """Normalize verdict probabilities and fallback text."""
        plaintiff = max(0, min(100, int(verdict_result.plaintiff_win_rate)))
        defendant = max(0, min(100, int(verdict_result.defendant_win_rate)))
        if plaintiff + defendant != 100:
            defendant = 100 - plaintiff

        verdict_text = (verdict_result.verdict_text or "").strip()
        if not verdict_text:
            verdict_text = "# 法官综合意见\n\n本院将基于现有证据与法条进行裁判评议。"

        return VerdictResult(
            plaintiff_win_rate=plaintiff,
            defendant_win_rate=defendant,
            verdict_text=verdict_text,
        )

    async def _build_structured_debate_summary(
        self,
        plaintiff_text: str,
        defendant_text: str,
        judge_text: str,
    ) -> DebateSummary:
        """使用结构化 JSON 约束输出双方有利点与法官总结。"""
        prompt = (
            "你是法律辩论总结器。请严格输出 JSON 对象，不要输出任何多余文字。"
            "JSON Schema: {"
            "\"plaintiff_winning_factors\": [\"...\"],"
            "\"defendant_winning_factors\": [\"...\"],"
            "\"judge_summary\": \"...\""
            "}\n"
            "要求：每个数组给出 3 条完整句子，不得输出半截句。\n\n"
            f"原告发言：\n{plaintiff_text}\n\n"
            f"被告发言：\n{defendant_text}\n\n"
            f"法官意见：\n{judge_text}\n"
        )

        try:
            llm_for_json = self.llm
            try:
                llm_for_json = self.llm.bind(response_format={"type": "json_object"})
            except Exception:
                pass

            response = await llm_for_json.ainvoke(prompt)
            raw = response.content if hasattr(response, "content") else str(response)
            if isinstance(raw, list):
                raw = "".join([str(x.get("text", x)) if isinstance(x, dict) else str(x) for x in raw])

            start = str(raw).find("{")
            end = str(raw).rfind("}")
            if start == -1 or end == -1:
                raise ValueError("未返回 JSON 对象")

            payload = json.loads(str(raw)[start:end + 1])
            return DebateSummary.model_validate(payload)
        except Exception as e:
            app_logger.warning(f"结构化总结失败，回退启发式抽取: {str(e)}")
            return DebateSummary(
                plaintiff_winning_factors=self._extract_key_points(plaintiff_text, "原告的核心主张仍需补充证据支持"),
                defendant_winning_factors=self._extract_key_points(defendant_text, "被告的抗辩理由仍需补充事实依据"),
                judge_summary=judge_text,
            )

    async def _ensure_legal_basis(self, state: SupervisorState) -> str:
        """在流程初始阶段强制检索真实法条并写入 State。"""
        existing = (state.get("legal_basis") or "").strip()
        if existing:
            return existing

        query = state["case_description"]
        rag_results = await self.rag_service.retrieve_clauses(query, top_k=5)

        legal_lines: List[str] = []
        for idx, item in enumerate(rag_results, start=1):
            text = (item.get("text") or "").strip()
            if not text:
                continue
            metadata = item.get("metadata") or {}
            article = metadata.get("article") or metadata.get("chapter") or f"参考条文{idx}"
            legal_lines.append(f"【{article}】{text[:320]}")

        if not legal_lines:
            legal_lines.append("【未检索到条文】请明确说明证据不足，禁止编造法律条款。")

        return "\n".join(legal_lines)

    async def _ensure_evidence_list(self, state: SupervisorState) -> List[Dict[str, str]]:
        existing = state.get("evidence_list") or []
        if existing:
            return existing

        query = state["case_description"]
        rag_results = await self.rag_service.retrieve_clauses(query, top_k=6)
        evidence_list: List[Dict[str, str]] = []

        for idx, item in enumerate(rag_results, start=1):
            text = (item.get("text") or "").strip()
            if not text:
                continue
            evidence_id = f"evidence_{idx}"
            metadata = item.get("metadata") or {}
            title = metadata.get("article") or metadata.get("chapter") or f"参考证据 {idx}"
            evidence_list.append(
                {
                    "id": evidence_id,
                    "title": str(title),
                    "content": text[:380],
                    "source": str(metadata.get("source") or metadata.get("law_name") or "RAG检索结果"),
                }
            )

        if not evidence_list:
            evidence_list.append(
                {
                    "id": "evidence_1",
                    "title": "证据不足提示",
                    "content": "未检索到可用法条或合同条款，请在发言中明确证据不足。",
                    "source": "系统提示",
                }
            )

        return self._dedup_evidence_list(evidence_list)

    def _build_evidence_instructions(self, evidence_list: List[Dict[str, str]]) -> str:
        lines: List[str] = []
        for item in evidence_list:
            lines.append(f"- {item['id']}: {item.get('title', '')} | {item.get('content', '')}")

        return (
            "【证据链列表】\n"
            + "\n".join(lines)
            + "\n\n"
            + "【强制引用格式】当你引用特定法条或证据时，必须在对应句子后追加锚点，格式严格为 [引用:evidence_x]。"
        )

    def _extract_evidence_mentions(self, text: str) -> List[str]:
        if not text:
            return []
        return re.findall(r"\[引用:(evidence_\d+)\]", text)

    def _dedup_evidence_list(self, evidence_list: List[Dict[str, str]]) -> List[Dict[str, str]]:
        deduped: List[Dict[str, str]] = []
        seen_fp: set[str] = set()
        for item in evidence_list:
            content = (item.get("content") or "").strip()
            title = (item.get("title") or "").strip()
            fp = _text_fingerprint(content or title)
            if not fp or fp in seen_fp:
                continue
            seen_fp.add(fp)
            deduped.append(item)
        return deduped

    def _strip_evidence_anchors(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r"\[引用:evidence_\d+\]", "", text)

    def _build_role_prompt(
        self,
        role_key: Literal["plaintiff", "defendant", "judge"],
        case_description: str,
        legal_basis: str,
        opponent_points: List[str],
        current_turn: int,
        max_turns: int,
        strategy: str,
        evidence_list: List[Dict[str, str]],
        human_question: str,
    ) -> List:
        opponent_text = "\n".join([f"- {p}" for p in (opponent_points or [])]) or "- 暂无"
        evidence_instruction = self._build_evidence_instructions(evidence_list)
        human_question_context = (
            f"\n\n【法官（人类）补充追问】\n{human_question}\n请你直接回应该追问，并与已有论证保持一致。"
            if human_question else ""
        )

        if role_key == "plaintiff":
            strategy_instruction = STRATEGY_INSTRUCTION_MAP.get(normalize_strategy(strategy), STRATEGY_INSTRUCTION_MAP["aggressive"])
            system_prompt = (
                "你现在的身份是【原告律师】。你必须且只能从原告的利益出发进行主张。"
                "请使用第一人称（如‘我方认为...’）进行表述。"
                "严禁以被告或法官口吻发言，严禁替法官下最终判决。\n\n"
                "【重要】你所有的抗辩理由必须严格基于以下提供的参考法律条文。"
                "严禁自行捏造、背诵未提供的法律条款。引用时请明确指出依据的是哪一条。\n\n"
                f"【策略指令】{strategy_instruction}\n\n"
                f"{evidence_instruction}"
            )
            output_rule = "请输出：1) 原告诉请主张 2) 法条依据（逐条引用） 3) 针对被告上一轮观点的反驳。"
        elif role_key == "defendant":
            system_prompt = (
                "你现在的身份是【被告律师】。你必须且只能从被告的利益出发进行抗辩。"
                "请使用第一人称（如‘我方认为...’）进行表述。"
                "严禁以原告或法官的口吻发言，严禁替法官做出裁判结论。\n\n"
                "【重要】你所有的抗辩理由必须严格基于以下提供的参考法律条文。"
                "严禁自行捏造、背诵未提供的法律条款。引用时请明确指出依据的是哪一条。\n\n"
                f"{evidence_instruction}"
            )
            output_rule = "请输出：1) 被告抗辩主张 2) 法条依据（逐条引用） 3) 针对原告上一轮观点的反驳。"
        else:
            system_prompt = (
                "你是本案的【主审法官】。你的职责是归纳双方争议焦点，并基于事实和法律给出最终裁判逻辑。"
                "请使用法官的客观、庄重语气。严禁代入原告或被告立场，严禁情绪化表达。\n\n"
                "【重要】你的判决逻辑必须严格基于以下提供的参考法律条文。"
                "严禁自行捏造、背诵未提供的法律条款。引用时请明确指出依据的是哪一条。\n\n"
                f"{evidence_instruction}"
            )
            output_rule = "请输出：1) 争议焦点归纳 2) 法条适用分析 3) 裁判逻辑结论。"

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "{system_prompt}"),
                (
                    "human",
                    "当前辩论轮次：第 {current_turn} / {max_turns} 轮。\n"
                    "案情描述：\n{case_description}\n\n"
                    "参考法律条文：\n{legal_basis}\n\n"
                    "对方上一轮核心论点：\n{opponent_points}{human_question_context}\n\n"
                    "{output_rule}",
                ),
            ]
        )

        return prompt.format_messages(
            system_prompt=system_prompt,
            current_turn=current_turn + 1,
            max_turns=max_turns,
            case_description=case_description,
            legal_basis=legal_basis,
            opponent_points=opponent_text,
            human_question_context=human_question_context,
            output_rule=output_rule,
        )

    async def _supervisor_node(self, state: SupervisorState) -> Dict:
        # 流程初始阶段强制注入真实法条，供所有角色共享
        legal_basis = await self._ensure_legal_basis(state)
        current_turn = int(state.get("current_turn", 0))
        max_turns = int(state.get("max_turns", 2))

        # 第一轮一定先由原告发言
        if not state.get("legal_research_result"):
            note = f"第 {current_turn + 1} 轮：原告律师先行陈述。"
            return {
                "legal_basis": legal_basis,
                "next_worker": "LegalResearcher",
                "supervisor_note": note,
                "messages": [{"role": "supervisor", "content": note}],
            }

        # 原告发言后，轮到被告
        if not state.get("contract_analysis_result"):
            note = f"第 {current_turn + 1} 轮：被告律师进行抗辩。"
            return {
                "legal_basis": legal_basis,
                "next_worker": "ContractAnalyzer",
                "supervisor_note": note,
                "messages": [{"role": "supervisor", "content": note}],
            }

        # 已完成一轮原被告攻防
        if current_turn + 1 < max_turns:
            next_turn = current_turn + 1
            note = f"第 {next_turn + 1} 轮反驳开始：原告律师继续围绕上一轮观点反驳。"
            return {
                "legal_basis": legal_basis,
                "current_turn": next_turn,
                "next_worker": "LegalResearcher",
                "supervisor_note": note,
                # 清空本轮临时槽位，保留双方关键要点用于下一轮互相反驳
                "legal_research_result": "",
                "contract_analysis_result": "",
                "messages": [{"role": "supervisor", "content": note}],
            }

        # 轮次达到上限，触发人类法官介入
        if not state.get("human_question"):
            note = "辩论轮次已满，等待法官（人类）追问。"
            return {
                "legal_basis": legal_basis,
                "next_worker": "HumanJudgeIntervention",
                "supervisor_note": note,
                "messages": [{"role": "supervisor", "content": note}],
            }

        # 人类追问后，交由 AI 法官终局裁判
        if not state.get("litigation_strategy_result"):
            note = "已收到法官追问，进入最终评议。"
            return {
                "legal_basis": legal_basis,
                "next_worker": "LitigationStrategist",
                "supervisor_note": note,
                "messages": [{"role": "supervisor", "content": note}],
            }

        final_answer = (
            "# 法官综合意见\n\n"
            f"{state.get('litigation_strategy_result', '')}\n\n"
            "---\n"
            "以上结论基于当前案情与已提供信息，仅供诉前分析参考。"
        )
        note = "综合评议完成，生成最终结论。"
        return {
            "legal_basis": legal_basis,
            "next_worker": "END",
            "final_answer": final_answer,
            "supervisor_note": note,
            "messages": [{"role": "supervisor", "content": note}],
        }

    async def _verification_node(self, state: SupervisorState) -> Dict:
        """
        法务合规稽查节点：核验上一发言 Agent 的观点是否与 laws/evidences 一致。

        规则：
        1) 若发现捏造法条编号或事实错误，返回 status=rework，并给出明确整改意见。
        2) 若核验通过，返回 status=pass。
        3) 为避免死循环，重写最多允许 2 次（由 route 层与 retries 控制）。
        """
        legal_basis = state.get("legal_basis") or await self._ensure_legal_basis(state)
        evidence_list = state.get("evidence_list") or await self._ensure_evidence_list(state)
        last_worker = state.get("last_worker") or "LegalResearcher"
        worker_output = state.get("last_worker_result") or ""

        evidence_text = "\n".join(
            [f"- {item.get('id', '')}: {item.get('title', '')} | {item.get('content', '')}" for item in evidence_list]
        )

        verify_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一个严苛的【法务合规稽查员】。请严格对比前面 Agent 生成的法律观点与系统中存储的 laws（法条）和 evidences（证据）。"
                    "检查是否存在：1. 捏造法条编号；2. 事实错误。"
                    "如果无误，输出 {\"status\":\"pass\"}；"
                    "如果有误，指出具体错误并输出 {\"status\":\"rework\",\"errors\":[...],\"rewrite_advice\":\"...\"}。"
                    "只允许输出 JSON，不得输出其他文字。"
                ),
                (
                    "human",
                    "【被稽查发言角色】\n{last_worker}\n\n"
                    "【待核验文本】\n{worker_output}\n\n"
                    "【laws】\n{legal_basis}\n\n"
                    "【evidences】\n{evidence_text}"
                ),
            ]
        )

        messages = verify_prompt.format_messages(
            last_worker=last_worker,
            worker_output=worker_output,
            legal_basis=legal_basis,
            evidence_text=evidence_text,
        )

        retries = int(state.get("retries", 0))
        max_retries = int(state.get("max_verification_retries", 2))

        try:
            llm_for_json = self.llm
            try:
                llm_for_json = self.llm.bind(response_format={"type": "json_object"})
            except Exception:
                pass

            response = await llm_for_json.ainvoke(messages)
            raw = response.content if hasattr(response, "content") else str(response)
            if isinstance(raw, list):
                raw = "".join([str(x.get("text", x)) if isinstance(x, dict) else str(x) for x in raw])

            start = str(raw).find("{")
            end = str(raw).rfind("}")
            payload: Dict[str, Any] = {"status": "pass"}
            if start != -1 and end != -1 and end > start:
                payload = json.loads(str(raw)[start:end + 1])

            status = str(payload.get("status") or "pass").lower()
            if status not in {"pass", "rework"}:
                status = "pass"

            if status == "rework" and retries < max_retries:
                errors = payload.get("errors") or []
                advice = str(payload.get("rewrite_advice") or "请严格依据已给法条与证据重写，禁止新增未给定事实与法条编号。")
                feedback_lines = ["稽查未通过，请按以下意见重写："]
                if isinstance(errors, list) and errors:
                    feedback_lines.extend([f"- {str(e)}" for e in errors])
                feedback_lines.append(f"整改要求：{advice}")
                feedback = "\n".join(feedback_lines)
                return {
                    "verification_status": "rework",
                    "verification_feedback": feedback,
                    "verification_target_worker": last_worker,
                    "retries": retries + 1,
                    "messages": [{"role": "Verification_Node", "content": feedback}],
                }

            pass_note = "法务合规稽查通过。"
            if status == "rework" and retries >= max_retries:
                pass_note = "法务稽查达到最大重试次数，按当前版本继续流转。"
            return {
                "verification_status": "pass",
                "verification_feedback": pass_note,
                "verification_target_worker": last_worker,
                "messages": [{"role": "Verification_Node", "content": pass_note}],
            }
        except Exception as e:
            fallback_note = f"稽查节点异常，默认放行以保障流程连续性：{str(e)}"
            return {
                "verification_status": "pass",
                "verification_feedback": fallback_note,
                "verification_target_worker": last_worker,
                "messages": [{"role": "Verification_Node", "content": fallback_note}],
            }

    async def _human_judge_intervention_node(self, state: SupervisorState) -> Dict:
        payload = {
            "type": "waiting_for_judge",
            "message": "请法官（人类）输入追问后继续庭审",
        }
        resume_value = interrupt(payload)
        question = ""
        if isinstance(resume_value, str):
            question = resume_value.strip()
        elif isinstance(resume_value, dict):
            question = str(resume_value.get("human_question") or "").strip()

        return {
            "human_question": question,
            "messages": [{"role": "human_judge", "content": question}],
            "supervisor_note": "法官（人类）已提交追问，继续审理。",
        }

    async def _legal_researcher_node(self, state: SupervisorState) -> Dict:
        case_description = state["case_description"]
        legal_basis = state.get("legal_basis") or await self._ensure_legal_basis(state)
        evidence_list = state.get("evidence_list") or await self._ensure_evidence_list(state)
        opponent_points = state.get("defendant_key_points") or []

        current_turn = int(state.get("current_turn", 0))
        max_turns = int(state.get("max_turns", 2))
        messages = self._build_role_prompt(
            role_key="plaintiff",
            case_description=case_description,
            legal_basis=legal_basis,
            opponent_points=opponent_points,
            current_turn=current_turn,
            max_turns=max_turns,
            strategy=state.get("strategy", "aggressive"),
            evidence_list=evidence_list,
            human_question=state.get("human_question", ""),
        )

        response = await self.llm.ainvoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        plaintiff_points = self._extract_key_points(content, "我方主张需要进一步补充证据")

        return {
            "legal_basis": legal_basis,
            "evidence_list": evidence_list,
            "last_worker": "LegalResearcher",
            "last_worker_result": content,
            "legal_research_result": content,
            "plaintiff_key_points": plaintiff_points,
            "messages": [{"role": "LegalResearcher", "content": content}],
        }

    async def _contract_analyzer_node(self, state: SupervisorState) -> Dict:
        case_description = state["case_description"]
        legal_basis = state.get("legal_basis") or await self._ensure_legal_basis(state)
        evidence_list = state.get("evidence_list") or await self._ensure_evidence_list(state)
        opponent_points = state.get("plaintiff_key_points") or []

        current_turn = int(state.get("current_turn", 0))
        max_turns = int(state.get("max_turns", 2))
        messages = self._build_role_prompt(
            role_key="defendant",
            case_description=case_description,
            legal_basis=legal_basis,
            opponent_points=opponent_points,
            current_turn=current_turn,
            max_turns=max_turns,
            strategy=state.get("strategy", "aggressive"),
            evidence_list=evidence_list,
            human_question=state.get("human_question", ""),
        )

        response = await self.llm.ainvoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        defendant_points = self._extract_key_points(content, "我方抗辩需要进一步补充证据")

        return {
            "legal_basis": legal_basis,
            "evidence_list": evidence_list,
            "last_worker": "ContractAnalyzer",
            "last_worker_result": content,
            "contract_analysis_result": content,
            "defendant_key_points": defendant_points,
            "messages": [{"role": "ContractAnalyzer", "content": content}],
        }

    async def _litigation_strategist_node(self, state: SupervisorState) -> Dict:
        case_description = state["case_description"]
        legal_basis = state.get("legal_basis") or await self._ensure_legal_basis(state)
        evidence_list = state.get("evidence_list") or await self._ensure_evidence_list(state)

        opponent_points = []
        opponent_points.extend(state.get("plaintiff_key_points") or [])
        opponent_points.extend(state.get("defendant_key_points") or [])

        current_turn = int(state.get("current_turn", 0))
        max_turns = int(state.get("max_turns", 2))
        messages = self._build_role_prompt(
            role_key="judge",
            case_description=case_description,
            legal_basis=legal_basis,
            opponent_points=opponent_points,
            current_turn=current_turn,
            max_turns=max_turns,
            strategy=state.get("strategy", "aggressive"),
            evidence_list=evidence_list,
            human_question=state.get("human_question", ""),
        )

        response = await self.llm.ainvoke(messages)
        content = response.content if hasattr(response, "content") else str(response)

        return {
            "legal_basis": legal_basis,
            "evidence_list": evidence_list,
            "last_worker": "LitigationStrategist",
            "last_worker_result": content,
            "litigation_strategy_result": content,
            "messages": [{"role": "LitigationStrategist", "content": content}],
        }

    async def execute(self, case_description: str, strategy: str = "aggressive") -> DebateResponse:
        """Unified non-stream execution entry for supervisor debate."""
        return await self.simulate_debate(case_description=case_description, strategy=strategy)

    async def execute_stream(
        self,
        case_description: str,
        strategy: str = "aggressive",
        custom_config: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Unified streaming execution entry for supervisor debate."""
        async for payload in self.simulate_debate_stream(
            case_description=case_description,
            strategy=strategy,
            custom_config=custom_config,
        ):
            yield payload

    async def simulate_debate(self, case_description: str, strategy: str = "aggressive") -> DebateResponse:
        """Run full debate and return final structured response."""
        if not case_description or len(case_description.strip()) < 20:
            raise ValueError("案情描述过短或为空，请提供详细案情")

        initial_state: SupervisorState = {
            "case_description": case_description,
            "strategy": normalize_strategy(strategy),
            "human_question": "请在无额外追问前提下直接进入最终评议。",
            "evidence_list": [],
            "legal_basis": "",
            "messages": [],
            "supervisor_note": "",
            "next_worker": "LegalResearcher",
            "last_worker": "",
            "last_worker_result": "",
            "legal_research_result": "",
            "contract_analysis_result": "",
            "litigation_strategy_result": "",
            "plaintiff_key_points": [],
            "defendant_key_points": [],
            "current_turn": 0,
            "max_turns": 2,
            "retries": 0,
            "final_answer": "",
        }

        final_state = await self.graph.ainvoke(initial_state)

        plaintiff_text = final_state.get("legal_research_result", "")
        defendant_text = final_state.get("contract_analysis_result", "")
        judge_text = final_state.get("final_answer") or final_state.get("litigation_strategy_result", "")

        # 胜诉概率（简化为默认均衡，可在后续版本接入结构化评分）
        plaintiff_prob = 0.5

        legal_basis_text = final_state.get("legal_basis", "")
        legal_basis_items = [line for line in legal_basis_text.splitlines() if line.strip()][:5]
        plaintiff_points = final_state.get("plaintiff_key_points") or self._extract_key_points(plaintiff_text, "我方主张需要进一步补充证据")
        defendant_points = final_state.get("defendant_key_points") or self._extract_key_points(defendant_text, "我方抗辩需要进一步补充证据")

        return DebateResponse(
            case_description=case_description,
            plaintiff_argument=AgentArgument(
                agent_role="LegalResearcher",
                argument=plaintiff_text,
                legal_basis=legal_basis_items,
                key_points=plaintiff_points,
            ),
            defendant_argument=AgentArgument(
                agent_role="ContractAnalyzer",
                argument=defendant_text,
                legal_basis=legal_basis_items,
                key_points=defendant_points,
            ),
            judge_opinion=AgentArgument(
                agent_role="Supervisor",
                argument=judge_text,
                legal_basis=legal_basis_items,
                key_points=self._extract_key_points(judge_text, "裁判逻辑需结合完整证据进一步审查"),
            ),
            win_probability={"plaintiff": plaintiff_prob, "defendant": 1 - plaintiff_prob},
        )

    def _node_to_role(self, node_name: str) -> Dict[str, str]:
        mapping = {
            "LegalResearcher": {"role": "原告律师", "role_key": "plaintiff"},
            "ContractAnalyzer": {"role": "被告律师", "role_key": "defendant"},
            "LitigationStrategist": {"role": "法官", "role_key": "judge"},
            "HumanJudgeIntervention": {"role": "法官", "role_key": "judge"},
            "supervisor": {"role": "法官", "role_key": "judge"},
            "Supervisor": {"role": "法官", "role_key": "judge"},
        }
        return mapping.get(node_name, {"role": node_name or "未知角色", "role_key": "judge"})

    def _extract_chunk_text(self, chunk: object) -> str:
        """兼容不同 message chunk 结构，提取可展示文本。"""
        if chunk is None:
            return ""

        content = getattr(chunk, "content", chunk)
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            texts: List[str] = []
            for part in content:
                if isinstance(part, str):
                    texts.append(part)
                elif isinstance(part, dict):
                    text = part.get("text") or part.get("content") or ""
                    if text:
                        texts.append(str(text))
            return "".join(texts)

        return str(content)

    async def _collect_final_result(self, config: Dict[str, Any]) -> Dict[str, Any]:
        final_state = await self.graph.aget_state(config)
        values = final_state.values or {}
        plaintiff_text = values.get("legal_research_result", "")
        defendant_text = values.get("contract_analysis_result", "")
        judge_text = values.get("final_answer", values.get("litigation_strategy_result", ""))

        summary = await self._build_structured_debate_summary(
            plaintiff_text=plaintiff_text,
            defendant_text=defendant_text,
            judge_text=judge_text,
        )

        return {
            "plaintiff_win_rate": 50,
            "plaintiff_winning_factors": summary.plaintiff_winning_factors,
            "defendant_winning_factors": summary.defendant_winning_factors,
            "judge_summary": summary.judge_summary,
            "legal_basis": [line for line in (values.get("legal_basis", "").splitlines()) if line.strip()][:8],
            "evidence_list": values.get("evidence_list", []),
        }

    async def _stream_with_state(self, stream_input: Any, config: Dict[str, Any]):
        evidence_emitted = False
        interrupted = False

        async for event in self.graph.astream_events(stream_input, config=config, version="v2"):
            event_type = event.get("event")

            if event_type == "on_chain_start":
                data = event.get("data") or {}
                interrupt_payload = data.get("input")
                if isinstance(interrupt_payload, dict) and interrupt_payload.get("type") == "waiting_for_judge":
                    interrupted = True
                    break

            metadata = event.get("metadata", {}) or {}
            node_name = metadata.get("langgraph_node")
            if not node_name:
                continue

            role_info = self._node_to_role(node_name)

            if event_type == "on_chat_model_stream":
                chunk = ((event.get("data") or {}).get("chunk"))
                text = self._extract_chunk_text(chunk)
                if text:
                    yield {
                        "type": "chunk",
                        "node": node_name,
                        "role": role_info["role"],
                        "role_key": role_info["role_key"],
                        "content": text,
                    }

                    for evidence_id in self._extract_evidence_mentions(text):
                        yield {
                            "type": "evidence_reference",
                            "evidence_id": evidence_id,
                            "role": role_info["role"],
                        }

            elif event_type == "on_chat_model_end":
                if node_name in {"LegalResearcher", "ContractAnalyzer", "LitigationStrategist"}:
                    yield {
                        "type": "node_end",
                        "node": node_name,
                        "role": role_info["role"],
                        "role_key": role_info["role_key"],
                    }

            if not evidence_emitted:
                snapshot = await self.graph.aget_state(config)
                values = snapshot.values or {}
                evidence_list = values.get("evidence_list") or []
                if evidence_list:
                    evidence_emitted = True
                    yield {"type": "evidence_list", "evidence_list": evidence_list}

        snapshot = await self.graph.aget_state(config)
        task_list = getattr(snapshot, "tasks", []) or []
        for task in task_list:
            interrupts = getattr(task, "interrupts", None) or []
            if interrupts:
                interrupted = True
                break

        if interrupted:
            yield {"type": "status", "content": "waiting_for_judge"}
            return

        final_result = await self._collect_final_result(config)
        yield {"type": "result", "result": final_result}

    async def simulate_debate_stream(
        self,
        case_description: str,
        strategy: str = "aggressive",
        custom_config: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Run debate in streaming mode and yield SSE-friendly payloads."""
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

        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        try:
            initial_state: SupervisorState = {
                "case_description": case_description,
                "strategy": normalize_strategy(strategy),
                "human_question": "",
                "evidence_list": [],
                "legal_basis": "",
                "messages": [],
                "supervisor_note": "",
                "next_worker": "LegalResearcher",
                "last_worker": "",
                "last_worker_result": "",
                "legal_research_result": "",
                "contract_analysis_result": "",
                "litigation_strategy_result": "",
                "plaintiff_key_points": [],
                "defendant_key_points": [],
                "current_turn": 0,
                "max_turns": 2,
                "retries": 0,
                "final_answer": "",
            }

            yield {"type": "thread", "thread_id": thread_id}

            async for payload in self._stream_with_state(initial_state, config):
                yield payload
        finally:
            if original_llm is not None:
                self.llm = original_llm
                self.graph = self._build_graph()

    async def resume_debate_stream(self, thread_id: str, human_question: str):
        if not thread_id:
            raise ValueError("thread_id 不能为空")
        if not human_question or len(human_question.strip()) < 2:
            raise ValueError("human_question 不能为空")

        config = {"configurable": {"thread_id": thread_id}}
        async for payload in self._stream_with_state(Command(resume={"human_question": human_question.strip()}), config):
            yield payload


_supervisor_agent_instance = None


def get_supervisor_agent() -> SupervisorDebateAgent:
    global _supervisor_agent_instance
    if _supervisor_agent_instance is None:
        _supervisor_agent_instance = SupervisorDebateAgent()
    return _supervisor_agent_instance
