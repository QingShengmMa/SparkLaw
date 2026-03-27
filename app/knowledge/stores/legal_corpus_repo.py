"""
Legal Corpus Repository — 法律法规语料库访问接口。
"""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from app.knowledge.stores.vector_store import VectorStoreAdapter


class LegalCorpusRepo:
    """法律法规语料库仓储层。"""

    def __init__(self, vector_store: VectorStoreAdapter):
        self.vector_store = vector_store

    def _format_candidates(self, raw_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        docs = (raw_results or {}).get("documents", [[]])[0] if raw_results else []
        metas = (raw_results or {}).get("metadatas", [[]])[0] if raw_results else []
        dists = (raw_results or {}).get("distances", [[]])[0] if raw_results else []

        for i, doc in enumerate(docs or []):
            dist = dists[i] if i < len(dists) else None
            sim = (1 - dist) if dist is not None else None
            candidates.append(
                {
                    "text": doc,
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": dist,
                    "similarity": sim,
                }
            )
        return candidates

    def _dedup_candidates(self, candidates: List[Dict[str, Any]], similarity_threshold: float = 0.96) -> List[Dict[str, Any]]:
        deduped: List[Dict[str, Any]] = []
        seen_texts: List[str] = []
        for item in candidates:
            text = (item.get("text") or "").strip()
            if not text:
                continue
            duplicated = any(
                text == ex or SequenceMatcher(None, text, ex).ratio() >= similarity_threshold
                for ex in seen_texts
            )
            if not duplicated:
                deduped.append(item)
                seen_texts.append(text)
        return deduped

    def retrieve_by_query(
        self,
        *,
        query_embedding: List[float],
        top_k: int = 5,
        recall_top_k: int = 20,
        law_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        where = {"law_name": law_name} if law_name else None
        raw = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=max(top_k, recall_top_k),
            where=where,
        )
        return self._dedup_candidates(self._format_candidates(raw))

    def get_by_law_id(self, law_name: str) -> List[Dict[str, Any]]:
        results = self.vector_store.get(where={"law_name": law_name})
        docs = (results or {}).get("documents", [])
        metas = (results or {}).get("metadatas", [])
        ids = (results or {}).get("ids", [])

        out: List[Dict[str, Any]] = []
        for i, doc in enumerate(docs or []):
            out.append(
                {
                    "id": ids[i] if i < len(ids) else None,
                    "text": doc,
                    "metadata": metas[i] if i < len(metas) else {},
                }
            )
        return out

    def add_law_chunks(
        self,
        *,
        ids: List[str],
        chunks: List[str],
        metadatas: List[Dict[str, Any]],
        embeddings: Optional[List[List[float]]] = None,
    ) -> None:
        self.vector_store.add_documents(
            ids=ids,
            documents=chunks,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def delete_by_law_id(self, law_name: str) -> int:
        existing = self.vector_store.get(where={"law_name": law_name})
        ids = (existing or {}).get("ids", [])
        if not ids:
            return 0
        self.vector_store.delete(ids=ids)
        return len(ids)

    def count(self) -> int:
        return self.vector_store.count()
