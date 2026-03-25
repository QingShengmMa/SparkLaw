"""
Output Validator — 校验 LLM 输出是否符合结构化约束。
TODO: 接入 Pydantic 模型校验 + 法条真实性比对。
"""
from __future__ import annotations


class OutputValidator:
    """对 LLM 输出做结构化校验。"""

    def validate_verdict(self, payload: dict) -> bool:
        """检查 VerdictResult 字段是否完整且合法。"""
        required = {"plaintiff_win_rate", "defendant_win_rate", "verdict_text"}
        if not required.issubset(payload):
            return False
        p = payload.get("plaintiff_win_rate", -1)
        d = payload.get("defendant_win_rate", -1)
        return isinstance(p, int) and isinstance(d, int) and p + d == 100
