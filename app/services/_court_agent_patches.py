"""
庭审引擎补丁：
1. _citation_instruction — 修复法条幻觉
2. stream rejudge_only — 清空旧记录并注入人工证据重跑全流程
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional


def _patched_citation_instruction(
    self,
    evidence_list: List[Dict[str, str]],
    law_list: List[Dict[str, str]],
) -> str:
    evidence_lines = [
        f"- {e['id']}: {e.get('title', '')} | {e.get('content', '')}"
        for e in (evidence_list or [])
    ]
    law_lines = [
        f"- {l['id']}: {l.get('title', '')} | {l.get('content', '')}"
        for l in (law_list or [])
    ]
    ev_block = "\n".join(evidence_lines) if evidence_lines else "暂无可用证据，发言时必须说明证据不足。"
    law_block = "\n".join(law_lines) if law_lines else "暂无可用法条，必须说明现有材料暂无直接对应法条。"
    return (
        "严格约束：下列是本次庭审全部可用材料，禁止引用列表之外的任何法律条文或证据。\n\n"
        f"【事实证据列表（只能引用这些 ID）】\n{ev_block}\n\n"
        f"【法律条文列表（只能引用这些 ID）】\n{law_block}\n\n"
        "【强制引用格式】\n"
        "- 引用事实材料时，必须使用 [证据:evidence_x]（x 为上表中的编号）\n"
        "- 引用法律条文时，必须使用 [法条:law_x]（x 为上表中的编号）\n"
        "- 严禁凭记忆背诵列表外的任何法律条文（如劳动合同法等）\n"
        "- 如果列表中没有相关法条，必须说明'暂无直接对应法条'，禁止编造"
    )


async def _patched_stream(
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
    """
    修复版 stream:
    - rejudge_only=True: 将人工证据注入初始 state，重跑全庭审流程（新 thread_id）
    - rejudge_only=False: 行为不变
    """
    import uuid
    from app.services.court_agent import normalize_strategy

    if not case_description or len(case_description.strip()) < 20:
        raise ValueError("案情描述过短或为空")

    if rejudge_only:
        # 合并人工补充证据到 evidence_list / plaintiff_evidence / defendant_evidence
        merged_ev, merged_p, merged_d = self._merge_human_evidences(
            evidence_list=list(evidence_list or []),
            plaintiff_evidence=list(plaintiff_evidence or []),
            defendant_evidence=list(defendant_evidence or []),
            human_evidences=human_evidences or [],
        )
        # 生成全新 thread，彻底清空旧庭审
        new_thread_id = str(uuid.uuid4())
        # 用拼好的证据发起全新庭审（simulate_evidence 节点检测到 evidence_list 非空会跳过 AI 生成）
        async for event in self._original_stream(
            case_description=case_description,
            strategy=strategy,
            thread_id=new_thread_id,
            rejudge_only=False,
            human_evidences=None,
            evidence_list=merged_ev,
            law_list=list(law_list or []),
            plaintiff_evidence=merged_p,
            defendant_evidence=merged_d,
        ):
            yield event
        return

    # 正常流程
    async for event in self._original_stream(
        case_description=case_description,
        strategy=strategy,
        thread_id=thread_id,
        rejudge_only=False,
        human_evidences=human_evidences,
        evidence_list=evidence_list,
        law_list=law_list,
        plaintiff_evidence=plaintiff_evidence,
        defendant_evidence=defendant_evidence,
    ):
        yield event


def apply_patches() -> None:
    """将补丁应用到 CourtDebateAgent。"""
    from app.services.court_agent import CourtDebateAgent
    CourtDebateAgent._citation_instruction = _patched_citation_instruction
    # 保存原始 stream 为 _original_stream，再用补丁版替换
    if not hasattr(CourtDebateAgent, "_original_stream"):
        CourtDebateAgent._original_stream = CourtDebateAgent.stream
    CourtDebateAgent.stream = _patched_stream
