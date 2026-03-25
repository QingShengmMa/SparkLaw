"""
Source Linker — 将检索结果 chunk 关联回原始法律文档。
TODO: 从向量库 metadata 中提取 source_url / article_number 并生成跳转链接。
"""
from __future__ import annotations
from typing import Any


def build_source_link(metadata: dict[str, Any]) -> str:
    """根据 chunk metadata 生成可读来源标注。"""
    law_name = metadata.get("law_name") or metadata.get("source") or "未知法律"
    article = metadata.get("article") or ""
    return f"{law_name}{(' 第' + article + '条') if article else ''}"
