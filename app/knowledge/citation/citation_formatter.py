"""
Citation Formatter — 将法条引用格式化为统一的 Markdown 输出。
"""
from __future__ import annotations


def format_law_citation(law_id: str, title: str, content: str, source: str = "") -> str:
    """生成统一的法条引用 Markdown 块。"""
    src = f"（来源：{source}）" if source else ""
    return f"**[{law_id}] {title}**{src}\n> {content}"
