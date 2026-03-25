"""Reranker 模块：对向量召回候选进行重排序。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests
from sentence_transformers import CrossEncoder

from app.core.logger import app_logger


class Reranker:
    """支持本地 Cross-Encoder，预留外部 Rerank API 接口。"""

    DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def __init__(
        self,
        model_name: Optional[str] = None,
        score_threshold: float = 0.0,
        external_api_url: Optional[str] = None,
        external_api_key: Optional[str] = None,
    ):
        self.model_name = model_name or self.DEFAULT_MODEL
        self.score_threshold = score_threshold
        self.external_api_url = external_api_url
        self.external_api_key = external_api_key
        self.cross_encoder: Optional[CrossEncoder] = None

        if not self.external_api_url:
            try:
                app_logger.info(f"🔄 正在加载 Reranker 模型: {self.model_name}")
                self.cross_encoder = CrossEncoder(self.model_name)
                app_logger.info("✅ Reranker 模型加载完成")
            except Exception as e:
                app_logger.warning(f"本地 Reranker 初始化失败，将回退向量排序: {str(e)}")

    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
        """对候选切片进行重排并返回 Top-K。"""
        if not candidates:
            return []

        if self.external_api_url:
            return self._rerank_with_external_api(query, candidates, top_k)

        if not self.cross_encoder:
            return sorted(
                candidates,
                key=lambda x: x.get("similarity") if x.get("similarity") is not None else -1,
                reverse=True,
            )[:top_k]

        try:
            pairs = [(query, c.get("text", "")) for c in candidates]
            scores = self.cross_encoder.predict(pairs).tolist()
            enriched = [{**item, "rerank_score": float(scores[idx])} for idx, item in enumerate(candidates)]
            enriched.sort(key=lambda x: x.get("rerank_score", -1.0), reverse=True)
            filtered = [x for x in enriched if x.get("rerank_score", -1.0) >= self.score_threshold]
            return (filtered if filtered else enriched)[:top_k]
        except Exception as e:
            app_logger.warning(f"Rerank 失败，回退向量排序: {str(e)}")
            return sorted(
                candidates,
                key=lambda x: x.get("similarity") if x.get("similarity") is not None else -1,
                reverse=True,
            )[:top_k]

    def _rerank_with_external_api(self, query: str, candidates: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        """外部 Rerank API 预留实现。"""
        try:
            payload = {"query": query, "documents": [c.get("text", "") for c in candidates], "top_k": top_k}
            headers = {"Content-Type": "application/json"}
            if self.external_api_key:
                headers["Authorization"] = f"Bearer {self.external_api_key}"
            resp = requests.post(self.external_api_url, json=payload, headers=headers, timeout=20)
            resp.raise_for_status()
            ranked = resp.json().get("results", [])
            output: List[Dict[str, Any]] = []
            for item in ranked:
                idx = item.get("index")
                if idx is None or idx < 0 or idx >= len(candidates):
                    continue
                output.append({**candidates[idx], "rerank_score": item.get("score")})
            return output[:top_k] if output else candidates[:top_k]
        except Exception as e:
            app_logger.warning(f"外部 Rerank API 调用失败，回退向量排序: {str(e)}")
            return sorted(
                candidates,
                key=lambda x: x.get("similarity") if x.get("similarity") is not None else -1,
                reverse=True,
            )[:top_k]
