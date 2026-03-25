"""
Vector Store adapter — Chroma / FAISS 统一接口。
TODO: 封装 LangChain VectorStore，支持切换 Chroma / FAISS / Milvus。
"""
from __future__ import annotations


class VectorStoreAdapter:
    """向量库统一适配器（占位）。"""

    def __init__(self, store):
        self._store = store

    def similarity_search(self, query: str, k: int = 5):
        return self._store.similarity_search(query, k=k)
