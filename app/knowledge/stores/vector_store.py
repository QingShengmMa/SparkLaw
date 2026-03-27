"""
Vector Store adapter — ChromaDB 统一接口。

封装 Chroma PersistentClient，提供统一的文档写入与检索能力。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional

import chromadb
from chromadb.config import Settings


EmbeddingFunction = Callable[[List[str]], List[List[float]]]


class VectorStoreAdapter:
    """基于 ChromaDB 的向量库适配器。"""

    def __init__(
        self,
        *,
        persist_directory: str,
        collection_name: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding_function: Optional[Any] = None,
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.metadata = metadata or {}
        self.embedding_function = embedding_function

        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata=self.metadata,
        )

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if self.embedding_function is None:
            raise ValueError("embedding_function is required when embeddings are not provided")

        embedder = self.embedding_function
        if callable(embedder):
            vectors = embedder(texts)
        elif hasattr(embedder, "encode"):
            vectors = embedder.encode(texts, show_progress_bar=False, convert_to_numpy=True).tolist()
        else:
            raise TypeError("Unsupported embedding_function type")

        return vectors

    def add_documents(
        self,
        *,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[List[List[float]]] = None,
    ) -> None:
        if embeddings is None:
            embeddings = self._embed_texts(documents)

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def search(
        self,
        *,
        query_text: Optional[str] = None,
        query_embedding: Optional[List[float]] = None,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if query_embedding is None and query_text is None:
            raise ValueError("query_text or query_embedding must be provided")

        if query_embedding is None and query_text is not None:
            query_embedding = self._embed_texts([query_text])[0]

        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
        )

    # ---- Chroma 常用方法透传，供上层服务兼容复用 ----

    def add(self, **kwargs):
        return self.collection.add(**kwargs)

    def query(self, **kwargs):
        return self.collection.query(**kwargs)

    def get(self, **kwargs):
        return self.collection.get(**kwargs)

    def delete(self, **kwargs):
        return self.collection.delete(**kwargs)

    def count(self) -> int:
        return self.collection.count()
