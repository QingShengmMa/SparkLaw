"""
中国民事庭审多智能体模拟引擎
严格按照【宣布开庭 → 法庭调查 → 法庭辩论 → 最后陈述 → 宣判】流程设计
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from operator import add
from typing import Annotated, Any, Dict, List, TypedDict, Optional, AsyncIterator

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.core.logger import app_logger
from app.core.config import settings
from app.services.llm_factory import LLMFactory
from app.services.rag_service import get_rag_service
from app.guardrails.hallucination_guard import HallucinationGuard


def _text_fingerprint(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip())


# ─────────────────────────── State ───────────────────────────

class TranscriptMessage(TypedDict):
    id: str
    role: str
    role_key: str
    phase: str
    content: str


class CourtState(TypedDict):
    case_description: str
    strategy: str
    current_phase: str
    debate_turn: int
    max_debate_turns: int
    legal_basis: str
    law_list: List[Dict[str, str]]
    evidence_list: List[Dict[str, str]]
    plaintiff_evidence: List[Dict[str, str]]
    defendant_evidence: List[Dict[str, str]]
    transcript: Annotated[List[TranscriptMessage], add]
    plaintiff_points: List[str]
    defendant_points: List[str]
    verdict: str
    verdict_result: Dict[str, Any]


class VerdictResult(BaseModel):
    plaintiff_win_rate: int = Field(..., ge=0, le=100, description="原告胜诉概率，0-100 的整数")
    defendant_win_rate: int = Field(..., ge=0, le=100, description="被告胜诉概率，0-100 的整数，与原告相加为100")
    verdict_text: str = Field(..., description="包含案情简介、争议焦点和裁判逻辑的详细判决书（Markdown格式）")


class MockEvidenceItem(BaseModel):
    party: str
    name: str
    desc: str


class MockEvidenceList(BaseModel):
    plaintiff_evidence: List[MockEvidenceItem] = Field(default_factory=list)
    defendant_evidence: List[MockEvidenceItem] = Field(default_factory=list)


# ─────────────────────────── 常量 ───────────────────────────

PHASE_OPENING  = "宣布开庭"
PHASE_INVEST_P = "法庭调查·原告"
PHASE_INVEST_D = "法庭调查·被告"
PHASE_DEBATE_P = "法庭辩论·原告"
PHASE_DEBATE_D = "法庭辩论·被告"
PHASE_FINAL_P  = "最后陈述·原告"
PHASE_FINAL_D  = "最后陈述·被告"
PHASE_VERDICT  = "宣判"

STRATEGY_MAP: Dict[str, str] = {
    "aggressive":   "【激进施压策略】主动寻找被告逻辑漏洞，语言锋利，强调攻势与节奏。",
    "conservative": "【死磕法条策略】保守防御，严格咬文嚼字，强调程序正义与法条精准适配。",
    "mediator":     "【商业调解策略】强调合作背景与现实利益，推动减损与共赢和解。",
}


def normalize_strategy(s: str | None) -> str:
    v = (s or "").strip().lower()
    return v if v in STRATEGY_MAP else "aggressive"


# ─────────────────────────── Agent ───────────────────────────

class CourtDebateAgent:
    """严格遵循中国民事庭审程序的 LangGraph 多智能体。"""

    def __init__(self) -> None:
        self.llm = LLMFactory.create_llm()
        self.rag = get_rag_service()
        self.hallucination_guard = HallucinationGuard()
        self.checkpointer = self._create_checkpointer()
        self.graph = self._build_graph()
        app_logger.info("⚖️  CourtDebateAgent 初始化完成")

    def _create_checkpointer(self):
        try:
            from langgraph.checkpoint.base import BaseCheckpointSaver
            from langgraph.checkpoint.redis.aio import AsyncRedisSaver

            candidate = AsyncRedisSaver.from_conn_string(settings.REDIS_URL)
            if not isinstance(candidate, BaseCheckpointSaver):
                raise TypeError(f"Invalid redis checkpointer type: {type(candidate).__name__}")

            setup = getattr(candidate, "setup", None)
            if callable(setup):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(setup())
                except RuntimeError:
                    asyncio.run(setup())

            app_logger.info(f"✅ CourtDebateAgent Checkpointer 使用 Redis: {settings.REDIS_URL}")
            return candidate
        except Exception as e:
            app_logger.warning(f"CourtDebateAgent Redis Checkpointer 不可用，回退 MemorySaver: {str(e)}")
            return MemorySaver()

    async def _setup_async_checkpointer(self, saver) -> None:
        setup = getattr(saver, "setup", None)
        if callable(setup):
            await setup()

    # ────── Graph ──────

    def _build_graph(self):
        g = StateGraph(CourtState)
        g.add_node("simulate_evidence", self._node_simulate_evidence)
        g.add_node("evidence_prepare", self._node_evidence_preparation)
        g.add_node("opening",  self._node_opening)
        g.add_node("invest_p", self._node_invest_plaintiff)
        g.add_node("invest_d", self._node_invest_defendant)
        g.add_node("debate_p", self._node_debate_plaintiff)
        g.add_node("debate_d", self._node_debate_defendant)
        g.add_node("final_p",  self._node_final_plaintiff)
        g.add_node("final_d",  self._node_final_defendant)
        g.add_node("verdict",  self._node_verdict)

        g.set_entry_point("simulate_evidence")
        g.add_edge("simulate_evidence", "evidence_prepare")
        g.add_edge("evidence_prepare", "opening")
        g.add_edge("opening",  "invest_p")
        g.add_edge("invest_p", "invest_d")
        g.add_edge("invest_d", "debate_p")
        g.add_edge("debate_p", "debate_d")
        g.add_conditional_edges(
            "debate_d",
            self._should_continue_debate,
            {"continue": "debate_p", "finish": "final_p"},
        )
        g.add_edge("final_p", "final_d")
        g.add_edge("final_d", "verdict")
        g.add_edge("verdict",  END)
        return g.compile(checkpointer=self.checkpointer)

    def _should_continue_debate(self, state: CourtState) -> str:
        if state["debate_turn"] < state["max_debate_turns"] - 1:
            return "continue"
        return "finish"

    # ────── RAG ──────

    async def _ensure_legal_basis(self, state: CourtState) -> str:
        existing = (state.get("legal_basis") or "").strip()
        if existing:
            return existing

        law_list = await self._ensure_law_list(state)
        lines: List[str] = []
        for law in law_list:
            title = (law.get("title") or "").strip() or law.get("id", "法条")
            content = (law.get("content") or "").strip()
            if content:
                lines.append(f"【{title}】{content[:320]}")

        if not lines:
            lines.append("【未检索到条文】请明确说明证据不足，禁止编造法律条款。")
        return "\n".join(lines)

    async def _ensure_law_list(self, state: CourtState) -> List[Dict[str, str]]:
        existing = state.get("law_list") or []
        if existing:
            return existing

        # 优先从法律条文库（legal_corpus）检索，若法条库为空则回退到合同库
        results = await self.rag.retrieve_law(
            query=state["case_description"], top_k=8, recall_top_k=20
        ) if hasattr(self.rag, "retrieve_law") else []

        if not results:
            raw = await self.rag.retrieve_clauses(
                state["case_description"], top_k=8, recall_top_k=20
            )
            classified = self.rag.classify_retrieved_candidates(raw)
            results = classified.get("laws") or []
            # 如果合同库也没有法条，就把 evidences 也当作備选
            if not results:
                results = classified.get("evidences") or []

        laws: List[Dict[str, str]] = []
        for idx, item in enumerate(results, 1):
            text = (item.get("text") or "").strip()
            if not text:
                continue
            meta = item.get("metadata") or {}
            title = str(
                meta.get("article") or meta.get("chapter")
                or meta.get("law_name") or f"参考法条 {idx}"
            )
            laws.append({
                "id": f"law_{idx}",
                "title": title,
                "content": text[:900],
                "source": str(meta.get("source") or meta.get("law_name") or "RAG检索法条"),
            })

        if not laws:
            laws.append({
                "id": "law_1",
                "title": "法律依据不足提示",
                "content": "未检索到可用法条，请在发言中明确法条依据不足，禁止编造法律规则。",
                "source": "系统提示",
            })

        return self._dedup_evidence_list(laws)

    async def _ensure_evidence_list(self, state: CourtState) -> List[Dict[str, str]]:
        existing = state.get("evidence_list") or []
        if existing:
            return existing
        # 庭审事实证据不从用户上传的合同向量库检索，避免早期测试数据污染庭审。
        # 证据由 _node_simulate_evidence 节点用 LLM 根据案情生成。
        return []

    # ────── Prompt helpers ──────

    def _citation_instruction(
        self,
        evidence_list: List[Dict[str, str]],
        law_list: List[Dict[str, str]],
    ) -> str:
        evidence_lines = [f"- {e['id']}: {e.get('title','')} | {e.get('content','')}" for e in evidence_list]
        law_lines = [f"- {l['id']}: {l.get('title','')} | {l.get('content','')}" for l in law_list]
        return (
            "【事实证据列表】\n" + "\n".join(evidence_lines) + "\n\n"
            "【法律规则列表】\n" + "\n".join(law_lines) + "\n\n"
            "【强制引用格式】\n"
            "- 引用事实材料时，必须使用 [证据:evidence_x]\n"
            "- 引用法律规则时，必须使用 [法条:law_x]"
        )

    def _extract_key_points(self, text: str, fallback: str) -> List[str]:
        pts: List[str] = []
        for line in text.splitlines():
            c = line.strip().lstrip("-•1234567890.、 ")
            if 8 <= len(c) <= 100:
                pts.append(c)
            if len(pts) >= 3:
                break
        return pts or [fallback]

    def _extract_evidence_ids(self, text: str) -> List[str]:
        ids = re.findall(r"\[(?:证据|引用):(evidence_\d+)\]", text or "")
        return list(dict.fromkeys(ids))

    def _extract_law_ids(self, text: str) -> List[str]:
        ids = re.findall(r"\[法条:(law_\d+)\]", text or "")
        return list(dict.fromkeys(ids))

    def _apply_guardrail_warning(self, content: str, law_list: List[Dict[str, str]]) -> str:
        """Append warning when cited law ids are outside retrieved law list."""
        check = self.hallucination_guard.check_hallucination(
            generated_text=content,
            retrieved_law_list=law_list or [],
            raise_on_violation=False,
        )
        if check.passed:
            return content

        app_logger.warning(f"⚠️ Court guardrail warning, invalid laws: {check.violations}")
        return content + "\n\n> ⚠️ **合规提示**：本段存在未在本地法条列表命中的引用，请审慎参考。"

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

    def _dedup_party_evidence_list(self, evidence_list: List[Dict[str, str]]) -> List[Dict[str, str]]:
        deduped: List[Dict[str, str]] = []
        seen_fp: set[str] = set()
        for item in evidence_list:
            content = (item.get("desc") or "").strip()
            title = (item.get("name") or "").strip()
            fp = _text_fingerprint(content or title)
            if not fp or fp in seen_fp:
                continue
            seen_fp.add(fp)
            deduped.append(item)
        return deduped

    def _dedup_transcript(self, transcript: List[TranscriptMessage]) -> List[TranscriptMessage]:
        deduped: List[TranscriptMessage] = []
        seen_ids: set[str] = set()
        seen_fp: set[str] = set()
        for msg in transcript:
            msg_id = msg.get("id", "")
            fp = _text_fingerprint(f"{msg.get('phase','')}|{msg.get('role_key','')}|{msg.get('content','')}")
            if (msg_id and msg_id in seen_ids) or (fp and fp in seen_fp):
                continue
            if msg_id:
                seen_ids.add(msg_id)
            if fp:
                seen_fp.add(fp)
            deduped.append(msg)
        return deduped

    async def _call_llm(self, system: str, human: str) -> str:
        resp = await self.llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content=human),
        ])
        raw = resp.content if hasattr(resp, "content") else str(resp)
        if isinstance(raw, list):
            raw = "".join([
                p.get("text", "") if isinstance(p, dict) else str(p) for p in raw
            ])
        return str(raw)

    async def _call_structured_verdict(self, system: str, human: str, fallback_verdict_text: str) -> VerdictResult:
        try:
            structured_llm = self.llm.with_structured_output(VerdictResult)
            result = await structured_llm.ainvoke([
                SystemMessage(content=system),
                HumanMessage(content=human),
            ])
            parsed = result if isinstance(result, VerdictResult) else VerdictResult.model_validate(result)
            if parsed.plaintiff_win_rate + parsed.defendant_win_rate != 100:
                parsed = VerdictResult(
                    plaintiff_win_rate=max(0, min(100, parsed.plaintiff_win_rate)),
                    defendant_win_rate=max(0, min(100, 100 - max(0, min(100, parsed.plaintiff_win_rate)))),
                    verdict_text=parsed.verdict_text or fallback_verdict_text,
                )
            if not parsed.verdict_text.strip():
                parsed = VerdictResult(
                    plaintiff_win_rate=parsed.plaintiff_win_rate,
                    defendant_win_rate=parsed.defendant_win_rate,
                    verdict_text=fallback_verdict_text,
                )
            return parsed
        except Exception:
            text = await self._call_llm(system, human)
            parsed = self._extract_json_block(text)
            plaintiff_win_rate = int(parsed.get("plaintiff_win_rate") or self._estimate_win_rate(fallback_verdict_text))
            plaintiff_win_rate = max(0, min(100, plaintiff_win_rate))
            defendant_win_rate = max(0, min(100, int(parsed.get("defendant_win_rate") or (100 - plaintiff_win_rate))))
            if plaintiff_win_rate + defendant_win_rate != 100:
                defendant_win_rate = 100 - plaintiff_win_rate
            verdict_text = str(parsed.get("verdict_text") or fallback_verdict_text)
            return VerdictResult(
                plaintiff_win_rate=plaintiff_win_rate,
                defendant_win_rate=defendant_win_rate,
                verdict_text=verdict_text,
            )

    def _estimate_win_rate(self, verdict_text: str) -> int:
        m = re.search(r"(\d{1,3})\s*%", verdict_text or "")
        if m:
            val = max(0, min(100, int(m.group(1))))
            return val

        txt = verdict_text or ""
        if "原告" in txt and "支持" in txt:
            return 70
        if "驳回" in txt and "原告" in txt:
            return 30
        return 50

    def _extract_json_block(self, text: str) -> Dict[str, Any]:
        raw = (text or "").strip()
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            pass

        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return {}
        try:
            return json.loads(m.group())
        except Exception:
            return {}

    def _normalize_party_evidence(
        self,
        evidence_items: List[Dict[str, Any]],
        party_prefix: str,
        party_label: str,
    ) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        for idx, item in enumerate(evidence_items or [], 1):
            out.append({
                "id": str(item.get("id") or f"ev_{party_prefix}_{idx}"),
                "name": str(item.get("name") or f"{party_label}证据{idx}"),
                "desc": str(item.get("desc") or ""),
            })
        return out

    def _make_msg(
        self,
        msg_id: str,
        role: str,
        role_key: str,
        phase: str,
        content: str,
    ) -> TranscriptMessage:
        return {
            "id": msg_id or f"msg_{uuid.uuid4().hex[:8]}",
            "role": role,
            "role_key": role_key,
            "phase": phase,
            "content": content,
        }

    async def _node_simulate_evidence(self, state: CourtState) -> Dict:
        existing = state.get("evidence_list") or []
        if existing:
            return {}

        try:
            structured_llm = self.llm.with_structured_output(MockEvidenceList)
            prompt = (
                "作为一个资深律师，请根据案情，分别为原告和被告合理推演 2-3 份模拟证据，"
                "用于后续模拟庭审辩论。证据类型可包括聊天记录、转账凭证、考勤记录、制度通知等。"
            )
            mock_data = await structured_llm.ainvoke([
                SystemMessage(content="你是庭审证据合成助手，必须输出严格结构化数据。"),
                HumanMessage(content=f"案情描述：\n{state['case_description']}\n\n{prompt}"),
            ])
            parsed = mock_data if isinstance(mock_data, MockEvidenceList) else MockEvidenceList.model_validate(mock_data)
        except Exception:
            parsed = MockEvidenceList(
                plaintiff_evidence=[
                    MockEvidenceItem(party="plaintiff", name="微信聊天记录", desc="显示原告曾多次就争议事项向被告提出异议并保留证据。"),
                    MockEvidenceItem(party="plaintiff", name="银行转账记录", desc="显示原告主张款项的支付时间与金额明细。"),
                ],
                defendant_evidence=[
                    MockEvidenceItem(party="defendant", name="考勤系统导出表", desc="显示被告主张工作安排与实际考勤对应关系。"),
                    MockEvidenceItem(party="defendant", name="公司规章制度公告", desc="显示被告主张相关制度已公示并执行。"),
                ],
            )

        merged_evidence = []
        plaintiff_party = []
        defendant_party = []

        for idx, item in enumerate(parsed.plaintiff_evidence, 1):
            ev_id = f"evidence_{idx}"
            merged_evidence.append({
                "id": ev_id,
                "title": item.name,
                "content": item.desc,
                "source": "AI模拟合成",
            })
            plaintiff_party.append({"id": ev_id, "name": item.name, "desc": item.desc})

        offset = len(merged_evidence)
        for idx, item in enumerate(parsed.defendant_evidence, 1):
            ev_id = f"evidence_{offset + idx}"
            merged_evidence.append({
                "id": ev_id,
                "title": item.name,
                "content": item.desc,
                "source": "AI模拟合成",
            })
            defendant_party.append({"id": ev_id, "name": item.name, "desc": item.desc})

        return {
            "evidence_list": self._dedup_evidence_list(merged_evidence),
            "plaintiff_evidence": self._dedup_party_evidence_list(plaintiff_party),
            "defendant_evidence": self._dedup_party_evidence_list(defendant_party),
        }

    async def _node_evidence_preparation(self, state: CourtState) -> Dict:
        law_list = await self._ensure_law_list(state)
        evidence_list = await self._ensure_evidence_list(state)
        legal_basis = await self._ensure_legal_basis({**state, "law_list": law_list})

        evidence_hint = "\n".join(
            f"- {item.get('id')}: {item.get('title')} | {item.get('content')}"
            for item in evidence_list
        )
        law_hint = "\n".join(
            f"- {item.get('id')}: {item.get('title')} | {item.get('content')}"
            for item in law_list
        )

        system = (
            "你是中国民事诉讼庭审准备助手。请基于案情与材料，生成结构化模拟证据清单。"
            "你必须且只能输出 JSON，不得输出任何解释。"
            "JSON 必须严格为："
            "{\"plaintiff_evidence\":[{\"id\":\"ev_p_1\",\"name\":\"原证1：...\",\"desc\":\"...\"}],"
            "\"defendant_evidence\":[{\"id\":\"ev_d_1\",\"name\":\"被证1：...\",\"desc\":\"...\"}]}。"
            "每方至少 2 条，描述简洁、可用于庭审质证。"
        )
        human = (
            f"案情描述：\n{state['case_description']}\n\n"
            f"RAG事实材料：\n{evidence_hint or '暂无'}\n\n"
            f"RAG法律规则：\n{law_hint or '暂无'}\n\n"
            f"参考法律条文：\n{legal_basis}"
        )

        model_output = await self._call_llm(system, human)
        parsed = self._extract_json_block(model_output)

        plaintiff_evidence = self._normalize_party_evidence(
            parsed.get("plaintiff_evidence") or [],
            party_prefix="p",
            party_label="原证",
        )
        defendant_evidence = self._normalize_party_evidence(
            parsed.get("defendant_evidence") or [],
            party_prefix="d",
            party_label="被证",
        )

        if not plaintiff_evidence:
            plaintiff_evidence = [
                {"id": "ev_p_1", "name": "原证1：劳动合同", "desc": "证明双方存在劳动关系及主要权利义务。"},
                {"id": "ev_p_2", "name": "原证2：沟通记录", "desc": "证明原告主张事项曾向被告明确提出。"},
            ]
        if not defendant_evidence:
            defendant_evidence = [
                {"id": "ev_d_1", "name": "被证1：考勤或履约记录", "desc": "证明被告对争议事实的抗辩基础。"},
                {"id": "ev_d_2", "name": "被证2：制度或通知文件", "desc": "证明被告已履行告知或管理义务。"},
            ]

        return {
            "legal_basis": legal_basis,
            "law_list": law_list,
            "evidence_list": evidence_list,
            "plaintiff_evidence": plaintiff_evidence,
            "defendant_evidence": defendant_evidence,
        }

    # ────── Nodes ──────

    async def _node_opening(self, state: CourtState) -> Dict:
        legal_basis = await self._ensure_legal_basis(state)
        law_list = await self._ensure_law_list(state)
        evidence_list = await self._ensure_evidence_list(state)
        system = (
            "你是本案的【主审法官】。现在是【宣布开庭】阶段。"
            "你必须严格遵守以下排版规则，且只能输出一个 Markdown 结果，不得添加任何额外说明。\n\n"
            "请强制使用以下 Markdown 模板进行输出，严禁将关键词和正文混排，严禁输出重复的内容：\n\n"
            "**【案件案由】**\n"
            "（此处提取 3-5 个核心关键词，使用 | 分隔，例如：违法辞退 | 加班费争议 | 经济补偿金）\n\n"
            "**【案件简介】**\n"
            "（此处用一两句话简述原被告身份及起诉缘由）\n\n"
            "**【争议焦点】**\n"
            "（此处使用有序列表列出本案的 2-3 个核心争议焦点）\n"
            "1. 争议焦点一...\n"
            "2. 争议焦点二...\n\n"
            "**【宣布开庭】**\n"
            "本庭将严格依法办案，公正裁定。现在，宣布开庭！\n\n"
            "硬性约束：\n"
            "1) 不得重复任何词组或句子，不得输出关键词连写。\n"
            "2) 每个模块之间必须空一行。\n"
            "3) 不得输出模板外标题，不得输出 JSON，不得输出代码块围栏。\n"
            "4) 保持语言庄重、简洁、可读。"
        )
        human = (
            f"案情描述：\n{state['case_description']}\n\n"
            f"参考法律条文（仅供庭审参考）：\n{legal_basis}\n\n"
            f"可引用材料：\n{self._citation_instruction(evidence_list, law_list)}"
        )
        content = await self._call_llm(system, human)
        msg = self._make_msg("msg_opening", "法官", "judge", PHASE_OPENING, content)
        return {
            "current_phase": PHASE_OPENING,
            "legal_basis": legal_basis,
            "law_list": law_list,
            "evidence_list": evidence_list,
            "transcript": [msg],
        }

    async def _node_invest_plaintiff(self, state: CourtState) -> Dict:
        evidence_list = state.get("evidence_list") or []
        law_list = state.get("law_list") or []
        strategy_hint = STRATEGY_MAP.get(normalize_strategy(state.get("strategy")), "")
        system = (
            "你是本案【原告律师】，现在进入【法庭调查阶段】原告陈述环节。"
            "请依次阐述：①诉讼请求 ②事实与理由 ③核心证据。"
            "使用第一人称（如'我方认为...'）。严禁以法官或被告口吻发言。"
            "庭审已经为你准备好了事实证据材料。你必须引用分配给你的证据（使用 [引用:evidence_x] 或 [证据:evidence_x] 格式）进行强有力的辩护，绝对不允许以‘证据不足’或‘未检索到证据’为由推脱。\n\n"
            f"{strategy_hint}\n\n"
            f"{self._citation_instruction(evidence_list, law_list)}"
        )
        human = (
            f"案情描述：\n{state['case_description']}\n\n"
            f"参考法律条文：\n{state.get('legal_basis', '')}"
        )
        content = await self._call_llm(system, human)
        pts = self._extract_key_points(content, "原告诉请需进一步补充证据")
        msg = self._make_msg("msg_invest_p", "原告律师", "plaintiff", PHASE_INVEST_P, content)
        return {"current_phase": PHASE_INVEST_P, "plaintiff_points": pts, "transcript": [msg]}

    async def _node_invest_defendant(self, state: CourtState) -> Dict:
        evidence_list = state.get("evidence_list") or []
        law_list = state.get("law_list") or []
        plaintiff_summary = "\n".join(f"- {p}" for p in (state.get("plaintiff_points") or []))
        system = (
            "你是本案【被告律师】，现在进入【法庭调查阶段】被告答辩环节。"
            "请依次阐述：①答辩意见 ②反驳原告陈述的具体理由 ③被告方核心证据。"
            "使用第一人称。严禁以法官或原告口吻发言。"
            "庭审已经为你准备好了事实证据材料。你必须引用分配给你的证据（使用 [引用:evidence_x] 或 [证据:evidence_x] 格式）进行强有力的辩护，绝对不允许以‘证据不足’或‘未检索到证据’为由推脱。\n\n"
            f"{self._citation_instruction(evidence_list, law_list)}"
        )
        human = (
            f"案情描述：\n{state['case_description']}\n\n"
            f"参考法律条文：\n{state.get('legal_basis', '')}\n\n"
            f"原告方核心主张：\n{plaintiff_summary or '暂无'}"
        )
        content = await self._call_llm(system, human)
        pts = self._extract_key_points(content, "被告抗辩需进一步补充证据")
        msg = self._make_msg("msg_invest_d", "被告律师", "defendant", PHASE_INVEST_D, content)
        return {"current_phase": PHASE_INVEST_D, "defendant_points": pts, "transcript": [msg]}

    async def _node_debate_plaintiff(self, state: CourtState) -> Dict:
        evidence_list = state.get("evidence_list") or []
        law_list = state.get("law_list") or []
        strategy_hint = STRATEGY_MAP.get(normalize_strategy(state.get("strategy")), "")
        turn = state.get("debate_turn", 0)
        def_summary = "\n".join(f"- {p}" for p in (state.get("defendant_points") or []))
        system = (
            "你是本案【原告律师】，现在进入【法庭辩论阶段】。"
            "请针对争议焦点发表辩论意见，并有针对性地反驳被告方上一轮核心观点。"
            "使用第一人称。保持逻辑严密、层次分明。"
            "庭审已经为你准备好了事实证据材料。你必须引用分配给你的证据（使用 [引用:evidence_x] 或 [证据:evidence_x] 格式）进行强有力的辩护，绝对不允许以‘证据不足’或‘未检索到证据’为由推脱。\n\n"
            f"{strategy_hint}\n\n"
            f"{self._citation_instruction(evidence_list, law_list)}"
        )
        human = (
            f"案情描述：\n{state['case_description']}\n\n"
            f"参考法律条文：\n{state.get('legal_basis', '')}\n\n"
            f"当前辩论轮次：第 {turn + 1} 轮\n\n"
            f"被告方上一轮核心观点：\n{def_summary or '暂无'}"
        )
        content = await self._call_llm(system, human)
        pts = self._extract_key_points(content, "原告辩论意见需进一步补充")
        phase = PHASE_DEBATE_P if turn == 0 else f"法庭辩论·原告（第{turn + 1}轮）"
        msg = self._make_msg(f"msg_debate_p_{turn}", "原告律师", "plaintiff", phase, content)
        return {"current_phase": phase, "plaintiff_points": pts, "transcript": [msg]}

    async def _node_debate_defendant(self, state: CourtState) -> Dict:
        evidence_list = state.get("evidence_list") or []
        law_list = state.get("law_list") or []
        turn = state.get("debate_turn", 0)
        plt_summary = "\n".join(f"- {p}" for p in (state.get("plaintiff_points") or []))
        system = (
            "你是本案【被告律师】，现在进入【法庭辩论阶段】。"
            "请针对原告方的辩论意见逐条反驳，并强调被告方的核心抗辩逻辑。"
            "使用第一人称。保持简洁有力。"
            "庭审已经为你准备好了事实证据材料。你必须引用分配给你的证据（使用 [引用:evidence_x] 或 [证据:evidence_x] 格式）进行强有力的辩护，绝对不允许以‘证据不足’或‘未检索到证据’为由推脱。\n\n"
            f"{self._citation_instruction(evidence_list, law_list)}"
        )
        human = (
            f"案情描述：\n{state['case_description']}\n\n"
            f"参考法律条文：\n{state.get('legal_basis', '')}\n\n"
            f"当前辩论轮次：第 {turn + 1} 轮\n\n"
            f"原告方本轮辩论意见：\n{plt_summary or '暂无'}"
        )
        content = await self._call_llm(system, human)
        pts = self._extract_key_points(content, "被告辩论意见需进一步补充")
        phase = PHASE_DEBATE_D if turn == 0 else f"法庭辩论·被告（第{turn + 1}轮）"
        msg = self._make_msg(f"msg_debate_d_{turn}", "被告律师", "defendant", phase, content)
        return {"current_phase": phase, "debate_turn": turn + 1, "defendant_points": pts, "transcript": [msg]}

    async def _node_final_plaintiff(self, state: CourtState) -> Dict:
        system = (
            "你是本案【原告律师】，现在进入【最后陈述阶段】。"
            "请用 1-2 句简洁有力的话做最终陈述，浓缩你方最核心的诉求与主张。"
        )
        human = (
            f"案情描述：\n{state['case_description']}\n\n"
            "你方核心论点：\n" + "\n".join(f"- {p}" for p in (state.get("plaintiff_points") or []))
        )
        content = await self._call_llm(system, human)
        msg = self._make_msg("msg_final_p", "原告律师", "plaintiff", PHASE_FINAL_P, content)
        return {"current_phase": PHASE_FINAL_P, "transcript": [msg]}

    async def _node_final_defendant(self, state: CourtState) -> Dict:
        system = (
            "你是本案【被告律师】，现在进入【最后陈述阶段】。"
            "请用 1-2 句简洁有力的话做最终陈述，浓缩你方最核心的抗辩主张。"
        )
        human = (
            f"案情描述：\n{state['case_description']}\n\n"
            "你方核心论点：\n" + "\n".join(f"- {p}" for p in (state.get("defendant_points") or []))
        )
        content = await self._call_llm(system, human)
        msg = self._make_msg("msg_final_d", "被告律师", "defendant", PHASE_FINAL_D, content)
        return {"current_phase": PHASE_FINAL_D, "transcript": [msg]}

    async def _node_verdict(self, state: CourtState) -> Dict:
        evidence_list = state.get("evidence_list") or []
        law_list = state.get("law_list") or []
        plt_pts = "\n".join(f"- {p}" for p in (state.get("plaintiff_points") or []))
        def_pts = "\n".join(f"- {p}" for p in (state.get("defendant_points") or []))

        structured_system = (
            "你是本案的【主审法官】，现在进入【宣判阶段】。"
            "你必须输出结构化 VerdictResult："
            "1) plaintiff_win_rate 与 defendant_win_rate 均为 0-100 整数且相加为 100；"
            "2) verdict_text 必须是完整 Markdown 判决书，包含案情简介、争议焦点、法律适用和裁判结论。"
            "不得输出任何额外字段。\n\n"
            f"{self._citation_instruction(evidence_list, law_list)}"
        )
        structured_human = (
            f"案情描述：\n{state['case_description']}\n\n"
            f"参考法律条文：\n{state.get('legal_basis', '')}\n\n"
            f"原告方核心论点：\n{plt_pts or '暂无'}\n\n"
            f"被告方核心论点：\n{def_pts or '暂无'}"
        )

        fallback_text = (
            "## 裁判结论\n"
            "经综合审理，结合双方证据与法律依据，本庭作出如下裁判：\n"
            "1. 对原告诉请中有事实和法律依据的部分予以支持；\n"
            "2. 对缺乏充分证据支持的请求不予支持。"
        )
        verdict_result = await self._call_structured_verdict(structured_system, structured_human, fallback_text)

        original_verdict_text = verdict_result.verdict_text
        guarded_verdict_text = self._apply_guardrail_warning(original_verdict_text, law_list)
        risk_warning = None
        if guarded_verdict_text != original_verdict_text:
            risk_warning = "LAW_CITATION_UNVERIFIED"
            verdict_result = verdict_result.model_copy(update={"verdict_text": guarded_verdict_text})

        verdict_payload = verdict_result.model_dump()
        if risk_warning:
            verdict_payload["risk_warning"] = risk_warning

        verdict_json = json.dumps(verdict_payload, ensure_ascii=False)
        msg = self._make_msg("msg_verdict", "法官", "judge", PHASE_VERDICT, verdict_json)
        return {
            "current_phase": PHASE_VERDICT,
            "verdict": verdict_result.verdict_text,
            "verdict_result": verdict_payload,
            "transcript": [msg],
        }

    # ────── Streaming ──────

    _NODE_ROLE_MAP: Dict[str, Dict[str, str]] = {
        "opening":  {"role": "法官",   "role_key": "judge",     "phase": PHASE_OPENING},
        "invest_p": {"role": "原告律师", "role_key": "plaintiff", "phase": PHASE_INVEST_P},
        "invest_d": {"role": "被告律师", "role_key": "defendant", "phase": PHASE_INVEST_D},
        "debate_p": {"role": "原告律师", "role_key": "plaintiff", "phase": PHASE_DEBATE_P},
        "debate_d": {"role": "被告律师", "role_key": "defendant", "phase": PHASE_DEBATE_D},
        "final_p":  {"role": "原告律师", "role_key": "plaintiff", "phase": PHASE_FINAL_P},
        "final_d":  {"role": "被告律师", "role_key": "defendant", "phase": PHASE_FINAL_D},
        "verdict":  {"role": "法官",   "role_key": "judge",     "phase": PHASE_VERDICT},
    }

    def _extract_chunk_text(self, chunk: object) -> str:
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
                    t = part.get("text") or part.get("content") or ""
                    if t:
                        texts.append(str(t))
            return "".join(texts)
        return str(content)

    def _merge_human_evidences(
        self,
        evidence_list: List[Dict[str, str]],
        plaintiff_evidence: List[Dict[str, str]],
        defendant_evidence: List[Dict[str, str]],
        human_evidences: List[Dict[str, Any]],
    ) -> tuple[List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]]:
        merged_evidence = list(evidence_list)
        merged_plaintiff = list(plaintiff_evidence)
        merged_defendant = list(defendant_evidence)

        for idx, item in enumerate(human_evidences or [], 1):
            party = str(item.get("party") or "plaintiff").strip().lower()
            name = str(item.get("name") or f"人工补充证据{idx}").strip()
            desc = str(item.get("desc") or item.get("content") or "").strip()
            if not desc:
                continue
            ev_id = str(item.get("id") or f"human_ev_{party}_{idx}")

            merged_evidence.append({
                "id": ev_id,
                "title": name,
                "content": desc,
                "source": "人工补充",
            })

            party_item = {"id": ev_id, "name": name, "desc": desc}
            if party == "defendant":
                merged_defendant.append(party_item)
            else:
                merged_plaintiff.append(party_item)

        return (
            self._dedup_evidence_list(merged_evidence),
            self._dedup_party_evidence_list(merged_plaintiff),
            self._dedup_party_evidence_list(merged_defendant),
        )

    async def stream(
        self,
        case_description: str,
        strategy: str = "aggressive",
        thread_id: Optional[str] = None,
        rejudge_only: bool = False,
        human_evidences: Optional[List[Dict[str, Any]]] = None,
        evidence_list: Optional[List[Dict[str, str]]] = None,
        law_list: Optional[List[Dict[str, str]]] = None,
        plaintiff_evidence: Optional[List[Dict[str, str]]] = None,
        defendant_evidence: Optional[List[Dict[str, str]]] = None,
    ):
        """主流式接口，yield SSE 事件字典。"""
        if not case_description or len(case_description.strip()) < 20:
            raise ValueError("案情描述过短或为空")

        active_thread_id = thread_id or str(uuid.uuid4())
        config = {"configurable": {"thread_id": active_thread_id}}

        initial: CourtState = {
            "case_description": case_description,
            "strategy": normalize_strategy(strategy),
            "current_phase": "",
            "debate_turn": 0,
            "max_debate_turns": 2,
            "legal_basis": "",
            "law_list": list(law_list or []),
            "evidence_list": list(evidence_list or []),
            "plaintiff_evidence": list(plaintiff_evidence or []),
            "defendant_evidence": list(defendant_evidence or []),
            "transcript": [],
            "plaintiff_points": [],
            "defendant_points": [],
            "verdict": "",
            "verdict_result": {},
        }

        yield {"type": "thread", "thread_id": active_thread_id}

        if rejudge_only:
            existing_values: Dict[str, Any] = {}
            if thread_id:
                try:
                    snap = await self.graph.aget_state(config)
                    existing_values = snap.values or {}
                except Exception:
                    existing_values = {}

            merged_evidence_list, merged_plaintiff, merged_defendant = self._merge_human_evidences(
                evidence_list=initial["evidence_list"] or existing_values.get("evidence_list") or [],
                plaintiff_evidence=initial["plaintiff_evidence"] or existing_values.get("plaintiff_evidence") or [],
                defendant_evidence=initial["defendant_evidence"] or existing_values.get("defendant_evidence") or [],
                human_evidences=human_evidences or [],
            )

            verdict_state: CourtState = {
                **initial,
                "legal_basis": existing_values.get("legal_basis") or initial["legal_basis"],
                "law_list": initial["law_list"] or existing_values.get("law_list") or [],
                "evidence_list": merged_evidence_list,
                "plaintiff_evidence": merged_plaintiff,
                "defendant_evidence": merged_defendant,
                "plaintiff_points": existing_values.get("plaintiff_points") or [],
                "defendant_points": existing_values.get("defendant_points") or [],
                "transcript": existing_values.get("transcript") or [],
            }

            verdict_payload = await self._node_verdict(verdict_state)
            verdict_content = str(verdict_payload.get("verdict") or "")
            verdict_result = VerdictResult.model_validate(verdict_payload.get("verdict_result") or {
                "plaintiff_win_rate": self._estimate_win_rate(verdict_content),
                "defendant_win_rate": 100 - self._estimate_win_rate(verdict_content),
                "verdict_text": verdict_content,
            })
            verdict_msg = (verdict_payload.get("transcript") or [self._make_msg("", "法官", "judge", PHASE_VERDICT, verdict_content)])[-1]

            yield {
                "type": "new_message",
                "msg_id": verdict_msg.get("id", f"msg_stream_{uuid.uuid4().hex[:8]}"),
                "node": "verdict",
                "role": "法官",
                "role_key": "judge",
                "phase": PHASE_VERDICT,
            }
            if merged_evidence_list:
                yield {"type": "evidence_list", "evidence_list": merged_evidence_list}
            if verdict_state["law_list"]:
                yield {"type": "law_list", "law_list": verdict_state["law_list"]}
            if verdict_content:
                yield {
                    "type": "chunk",
                    "msg_id": verdict_msg.get("id", "msg_verdict"),
                    "node": "verdict",
                    "role": "法官",
                    "role_key": "judge",
                    "phase": PHASE_VERDICT,
                    "content": verdict_content,
                }

            final_transcript = self._dedup_transcript([
                *(existing_values.get("transcript") or []),
                verdict_msg,
            ])
            yield {
                "type": "result",
                "result": {
                    "transcript": final_transcript,
                    "verdict": verdict_content,
                    "evidence_list": merged_evidence_list,
                    "law_list": verdict_state["law_list"],
                    "laws": verdict_state["law_list"],
                    "plaintiff_evidence": merged_plaintiff,
                    "defendant_evidence": merged_defendant,
                    "legal_basis": [
                        ln for ln in (verdict_state.get("legal_basis") or "").splitlines() if ln.strip()
                    ][:8],
                    "plaintiff_win_rate": verdict_result.plaintiff_win_rate,
                    "defendant_win_rate": verdict_result.defendant_win_rate,
                    "verdict_result": verdict_result.model_dump(),
                },
            }
            return

        active_node: str | None = None
        evidence_emitted = False
        message_counter = 0
        active_msg_id_by_node: Dict[str, str] = {}

        async for event in self.graph.astream_events(initial, config=config, version="v2"):
            ev_type = event.get("event", "")
            meta = event.get("metadata") or {}
            node_name = meta.get("langgraph_node", "")

            role_info = self._NODE_ROLE_MAP.get(node_name, {})

            if (
                ev_type == "on_chain_start"
                and node_name
                and node_name in self._NODE_ROLE_MAP
                and node_name != active_node
            ):
                active_node = node_name
                message_counter += 1
                msg_id = f"msg_stream_{message_counter}"
                active_msg_id_by_node[node_name] = msg_id
                yield {
                    "type": "new_message",
                    "msg_id": msg_id,
                    "node": node_name,
                    "role": role_info["role"],
                    "role_key": role_info["role_key"],
                    "phase": role_info["phase"],
                }

            if ev_type == "on_chat_model_stream" and node_name:
                chunk = (event.get("data") or {}).get("chunk")
                text = self._extract_chunk_text(chunk)
                if text and role_info:
                    state_snapshot = await self.graph.aget_state(config)
                    current_laws = (state_snapshot.values or {}).get("law_list") or []
                    guarded_text = self._apply_guardrail_warning(text, current_laws)
                    yield {
                        "type": "chunk",
                        "msg_id": active_msg_id_by_node.get(node_name),
                        "node": node_name,
                        "role": role_info.get("role", ""),
                        "role_key": role_info.get("role_key", "judge"),
                        "phase": role_info.get("phase", ""),
                        "content": guarded_text,
                    }
                    for eid in self._extract_evidence_ids(guarded_text):
                        yield {
                            "type": "evidence_reference",
                            "evidence_id": eid,
                            "role": role_info.get("role", ""),
                        }
                    for lid in self._extract_law_ids(guarded_text):
                        yield {
                            "type": "law_reference",
                            "law_id": lid,
                            "role": role_info.get("role", ""),
                        }

            if ev_type == "on_chain_end" and node_name and not evidence_emitted:
                try:
                    snap = await self.graph.aget_state(config)
                    ev_list = (snap.values or {}).get("evidence_list") or []
                    law_items = (snap.values or {}).get("law_list") or []
                    if ev_list or law_items:
                        evidence_emitted = True
                    if ev_list:
                        yield {"type": "evidence_list", "evidence_list": ev_list}
                    if law_items:
                        yield {"type": "law_list", "law_list": law_items}
                except Exception:
                    pass

        try:
            snap = await self.graph.aget_state(config)
            values = snap.values or {}
            transcript = self._dedup_transcript(values.get("transcript") or [])
            base_evidence_list = self._dedup_evidence_list(values.get("evidence_list") or [])
            base_law_list = self._dedup_evidence_list(values.get("law_list") or [])
            base_plaintiff_evidence = values.get("plaintiff_evidence") or []
            base_defendant_evidence = values.get("defendant_evidence") or []

            merged_evidence_list, merged_plaintiff, merged_defendant = self._merge_human_evidences(
                evidence_list=base_evidence_list,
                plaintiff_evidence=base_plaintiff_evidence,
                defendant_evidence=base_defendant_evidence,
                human_evidences=human_evidences or [],
            )

            verdict_result_raw = values.get("verdict_result") or {}
            plaintiff_win_rate = int(verdict_result_raw.get("plaintiff_win_rate", self._estimate_win_rate(values.get("verdict", ""))))
            plaintiff_win_rate = max(0, min(100, plaintiff_win_rate))
            defendant_win_rate = int(verdict_result_raw.get("defendant_win_rate", 100 - plaintiff_win_rate))
            if plaintiff_win_rate + defendant_win_rate != 100:
                defendant_win_rate = 100 - plaintiff_win_rate

            parsed_verdict = VerdictResult.model_validate({
                "plaintiff_win_rate": plaintiff_win_rate,
                "defendant_win_rate": defendant_win_rate,
                "verdict_text": str(verdict_result_raw.get("verdict_text") or values.get("verdict", "")),
            })

            yield {
                "type": "result",
                "result": {
                    "transcript": transcript,
                    "verdict": values.get("verdict", ""),
                    "evidence_list": merged_evidence_list,
                    "law_list": base_law_list,
                    "laws": base_law_list,
                    "plaintiff_evidence": merged_plaintiff,
                    "defendant_evidence": merged_defendant,
                    "legal_basis": [
                        ln for ln in (values.get("legal_basis", "")).splitlines() if ln.strip()
                    ][:8],
                    "plaintiff_win_rate": parsed_verdict.plaintiff_win_rate,
                    "defendant_win_rate": parsed_verdict.defendant_win_rate,
                    "verdict_result": parsed_verdict.model_dump(),
                },
            }
        except Exception as e:
            app_logger.warning(f"拉取最终 state 失败: {e}")
    async def run_stream(
        self,
        case_description: str,
        plaintiff_name: str = "原告",
        defendant_name: str = "被告",
        strategy: str = "aggressive",
        human_evidence: Optional[List[Dict[str, Any]]] = None,
        custom_config: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """兼容旧路由的流式输出接口（前端友好事件格式）。"""
        _ = (plaintiff_name, defendant_name, custom_config)

        async for event in self.stream(
            case_description=case_description,
            strategy=strategy,
            human_evidences=human_evidence or [],
        ):
            ev_type = event.get("type")

            if ev_type == "chunk":
                phase = str(event.get("phase") or "")
                role_key = str(event.get("role_key") or "")
                content = str(event.get("content") or "")
                if not content:
                    continue

                if phase == PHASE_OPENING:
                    yield {"type": "opening", "content": content}
                elif role_key == "plaintiff":
                    yield {"type": "plaintiff", "content": content}
                elif role_key == "defendant":
                    yield {"type": "defendant", "content": content}
                elif role_key == "judge":
                    yield {"type": "judge", "content": content}
                else:
                    yield {"type": "log", "message": content}

            elif ev_type == "result":
                result = event.get("result") or {}
                verdict_result = result.get("verdict_result") or {}
                verdict_text = str(
                    verdict_result.get("verdict_text")
                    or result.get("verdict")
                    or ""
                )
                plaintiff_rate = int(result.get("plaintiff_win_rate", 50))
                plaintiff_rate = max(0, min(100, plaintiff_rate))
                defendant_rate = int(result.get("defendant_win_rate", 100 - plaintiff_rate))
                if plaintiff_rate + defendant_rate != 100:
                    defendant_rate = 100 - plaintiff_rate

                yield {
                    "type": "verdict",
                    "content": verdict_text,
                    "win_probability": {
                        "plaintiff": plaintiff_rate,
                        "defendant": defendant_rate,
                    },
                }

            elif ev_type == "error":
                yield {"type": "error", "message": str(event.get("message") or "庭审执行失败")}


# ─────────────────────────── 补丁 ───────────────────────────
# 修复法条幻觉 + rejudge_only 重跑全流程
from app.services._court_agent_patches import apply_patches as _apply_court_patches
_apply_court_patches()

# ─────────────────────────── 单例 ───────────────────────────

_court_agent_instance: CourtDebateAgent | None = None


def get_court_agent() -> CourtDebateAgent:
    global _court_agent_instance
    if _court_agent_instance is None:
        _court_agent_instance = CourtDebateAgent()
    return _court_agent_instance

            