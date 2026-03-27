"""
Hallucination Guard

检测并拦截输出中的法条引用幻觉：
- 若模型引用了 [法条:xxx]，但 xxx 不在当前真实召回的法条列表中，则判定违规。
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable, List


class GuardrailViolationError(Exception):
    """Guardrail violation that may require degrade or block."""

    def __init__(self, message: str, violations: List[str] | None = None):
        super().__init__(message)
        self.violations = violations or []


@dataclass
class GuardrailCheckResult:
    passed: bool
    violations: List[str]
    suggestion: str = ""


class HallucinationGuard:
    """检测并过滤法条引用幻觉。"""

    LAW_CITE_PATTERN = re.compile(r"\[法条:([^\]]+)\]")

    def _extract_cited_laws(self, text: str) -> List[str]:
        cited = [m.strip() for m in self.LAW_CITE_PATTERN.findall(text or "") if m.strip()]
        # 去重且保序
        return list(dict.fromkeys(cited))

    def _normalize_allowed_law_ids(self, retrieved_law_list: Iterable[Any]) -> List[str]:
        allowed: List[str] = []
        for idx, law in enumerate(retrieved_law_list or [], start=1):
            if isinstance(law, dict):
                law_id = str(law.get("id") or "").strip()
                if law_id:
                    allowed.append(law_id)
                    continue
            # 兼容仅有文本列表的场景，回退到 law_{idx}
            allowed.append(f"law_{idx}")
        return list(dict.fromkeys(allowed))

    def check_hallucination(
        self,
        generated_text: str,
        retrieved_law_list: Iterable[Any],
        raise_on_violation: bool = False,
    ) -> GuardrailCheckResult:
        """校验输出中的法条引用是否都在召回列表内。"""
        cited_law_ids = self._extract_cited_laws(generated_text)
        if not cited_law_ids:
            return GuardrailCheckResult(passed=True, violations=[])

        allowed_law_ids = set(self._normalize_allowed_law_ids(retrieved_law_list))
        violations = [law_id for law_id in cited_law_ids if law_id not in allowed_law_ids]

        if violations and raise_on_violation:
            raise GuardrailViolationError(
                message=f"检测到未命中知识库的法条引用: {', '.join(violations)}",
                violations=violations,
            )

        return GuardrailCheckResult(
            passed=len(violations) == 0,
            violations=violations,
            suggestion="请仅引用当前 RAG 召回法条列表中的法条 ID（如 [法条:law_1]）。" if violations else "",
        )

    def check(self, text: str, allowed_law_ids: list[str]) -> list[str]:
        """兼容旧接口：返回未命中的法条 ID 列表。"""
        result = self.check_hallucination(text, [{"id": law_id} for law_id in allowed_law_ids])
        return result.violations
