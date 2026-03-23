"""
Hybrid Memory Manager
负责 Short-term / Summary / Semantic 三层记忆管理
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Dict, List, Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.core.logger import app_logger
from app.services.llm_factory import LLMFactory


class HybridMemoryManager:
    """混合记忆管理器：滑动窗口 + 摘要记忆 + 语义记忆。"""

    def __init__(self, short_term_rounds: int = 5):
        self.short_term_rounds = short_term_rounds
        self._summary_store: Dict[str, str] = {}

        memory_dir = f"{settings.CHROMA_PERSIST_DIR}/user_memory"
        self.chroma_client = chromadb.PersistentClient(
            path=memory_dir,
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
        )
        self.embedding_model = SentenceTransformer("BAAI/bge-small-zh-v1.5")

        self.summary_llm = self._create_summary_llm()

    def _create_summary_llm(self):
        """创建低成本摘要模型，失败时回退默认模型。"""
        try:
            if settings.OPENAI_API_KEY:
                return LLMFactory.create_llm(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL,
                    model="gpt-4o-mini",
                    temperature=0.1,
                    max_tokens=512,
                )
            return LLMFactory.create_llm(temperature=0.1, max_tokens=512)
        except Exception as e:
            app_logger.warning(f"摘要模型创建失败，回退默认 LLM: {str(e)}")
            return LLMFactory.create_llm()

    def _collection_name(self, session_id: str) -> str:
        safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", session_id)
        return f"memory_{safe_id}"[:60]

    def _get_collection(self, session_id: str):
        return self.chroma_client.get_or_create_collection(
            name=self._collection_name(session_id),
            metadata={"description": f"session memory for {session_id}"},
        )

    def get_short_term_messages(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """仅保留最近 N 轮（每轮用户+助手两条消息）。"""
        max_messages = self.short_term_rounds * 2
        return history[-max_messages:]

    def get_summary(self, session_id: str) -> str:
        """获取长期摘要记忆。"""
        return self._summary_store.get(session_id, "")

    async def maybe_update_summary(self, session_id: str, history: List[Dict[str, Any]]) -> None:
        """当历史超出窗口阈值时，压缩旧对话到长期摘要。"""
        max_messages = self.short_term_rounds * 2
        if len(history) <= max_messages:
            return

        overflow_history = history[:-max_messages]
        overflow_text = "\n".join(
            [f"{m['role']}: {m['content']}" for m in overflow_history]
        )
        previous_summary = self._summary_store.get(session_id, "")

        prompt = (
            "请将以下用户历史对话压缩为‘User Profile & Context Summary’。\n"
            "要求：提取稳定事实（城市、身份、收入、争议类型、关键诉求、时间线），避免冗余。\n"
            "输出为中文，最多 200 字。\n\n"
            f"已有摘要：{previous_summary or '无'}\n\n"
            f"新增历史：\n{overflow_text}"
        )

        try:
            response = await self.summary_llm.ainvoke([HumanMessage(content=prompt)])
            summary = response.content if hasattr(response, "content") else str(response)
            self._summary_store[session_id] = summary.strip()
        except Exception as e:
            app_logger.warning(f"更新摘要记忆失败 [session={session_id}]: {str(e)}")

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """从文本中提取关键实体（轻量规则版）。"""
        entities: Dict[str, Any] = {
            "monthly_salary": None,
            "city": None,
            "dispute_type": None,
        }

        salary_match = re.search(r"(\d{3,6})\s*(元|块|人民币|月薪)", text)
        if salary_match:
            entities["monthly_salary"] = int(salary_match.group(1))

        city_keywords = ["北京", "上海", "广州", "深圳", "杭州", "成都", "重庆", "武汉", "西安", "南京", "苏州"]
        for city in city_keywords:
            if city in text:
                entities["city"] = city
                break

        dispute_map = {
            "劳动仲裁": ["仲裁", "劳动争议", "仲裁委"],
            "违法解除": ["违法解除", "辞退", "开除"],
            "工资拖欠": ["拖欠工资", "欠薪", "不发工资"],
            "竞业限制": ["竞业", "保密协议"],
        }
        for dispute_type, keywords in dispute_map.items():
            if any(keyword in text for keyword in keywords):
                entities["dispute_type"] = dispute_type
                break

        return entities

    async def upsert_semantic_memory(
        self,
        session_id: str,
        user_question: str,
        assistant_answer: str,
    ) -> None:
        """异步写入语义记忆。"""
        try:
            entities = self.extract_entities(user_question)
            memory_text = (
                f"用户问题: {user_question}\n"
                f"助手回答摘要: {assistant_answer[:300]}\n"
                f"实体: {entities}"
            )

            embedding = self.embedding_model.encode([memory_text], convert_to_numpy=True).tolist()[0]
            collection = self._get_collection(session_id)
            doc_id = f"{session_id}_{int(datetime.now().timestamp() * 1000)}"

            collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[memory_text],
                metadatas=[{
                    "session_id": session_id,
                    "created_at": datetime.now().isoformat(),
                    "monthly_salary": entities.get("monthly_salary") or 0,
                    "city": entities.get("city") or "",
                    "dispute_type": entities.get("dispute_type") or "",
                }],
            )
        except Exception as e:
            app_logger.warning(f"语义记忆写入失败 [session={session_id}]: {str(e)}")

    def search_semantic_memory(self, session_id: str, query: str, top_k: int = 3) -> List[str]:
        """检索用户历史语义档案。"""
        try:
            collection = self._get_collection(session_id)
            query_embedding = self.embedding_model.encode([query], convert_to_numpy=True).tolist()[0]
            result = collection.query(query_embeddings=[query_embedding], n_results=top_k)

            if not result or not result.get("documents") or not result["documents"][0]:
                return []

            return result["documents"][0]
        except Exception as e:
            app_logger.warning(f"语义记忆检索失败 [session={session_id}]: {str(e)}")
            return []

    def schedule_semantic_memory_write(self, session_id: str, user_question: str, assistant_answer: str) -> None:
        """后台异步写入，避免阻塞主链路。"""
        asyncio.create_task(self.upsert_semantic_memory(session_id, user_question, assistant_answer))


memory_manager = HybridMemoryManager(short_term_rounds=5)
