"""Query Rewrite 模块：将口语化问题改写为法律检索友好关键词。"""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from app.core.logger import app_logger
from app.llm.factory import LLMFactory


class QueryRewriter:
    """使用轻量 LLM 将用户 query 重写为 2-3 个法律术语关键词。"""

    def __init__(self):
        self.llm = self._create_rewriter_llm()

    def _create_rewriter_llm(self):
        try:
            return LLMFactory.create_llm(temperature=0.1, max_tokens=64)
        except Exception as e:
            app_logger.warning(f"QueryRewriter 小模型初始化失败，回退默认模型: {str(e)}")
            return LLMFactory.create_llm()

    async def rewrite(self, query: str) -> str:
        """将原始 query 改写为法律术语扩展检索词。"""
        clean_query = (query or "").strip()
        if not clean_query:
            return ""

        prompt = (
            "你是法律检索优化器。"
            "请把用户口语化问题改写成适合向量检索的法律术语关键词。\n"
            "要求：\n"
            "1) 仅输出 2-3 个中文关键词；\n"
            "2) 关键词之间用空格分隔；\n"
            "3) 不要输出解释、标点或编号。\n\n"
            f"用户问题：{clean_query}\n"
            "输出："
        )

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            rewritten = (response.content if hasattr(response, "content") else str(response)).strip()
            rewritten = rewritten.replace("\n", " ").strip()
            if not rewritten:
                return clean_query
            return rewritten
        except Exception as e:
            app_logger.warning(f"Query Rewrite 失败，使用原始 query: {str(e)}")
            return clean_query
