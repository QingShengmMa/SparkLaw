"""
Hallucination Guard

검출 기준:
- 引用了 RAG 列表之外的法条编号
- 输出包含编造的案号或当事人

TODO: 实现基于 law_list 的引用校验逻辑。
"""
from __future__ import annotations


class HallucinationGuard:
    """检测并过滤法条幻觉。"""

    def check(self, text: str, allowed_law_ids: list[str]) -> list[str]:
        """返回出现在 text 中但不在 allowed_law_ids 里的法条 ID。"""
        import re
        cited = re.findall(r"\[法条:(law_\d+)\]", text)
        return [c for c in cited if c not in allowed_law_ids]
