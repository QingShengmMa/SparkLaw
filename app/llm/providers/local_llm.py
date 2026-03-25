"""
Local / Ollama LLM provider adapter.
TODO: wrap LangChain ChatOllama with health-check + fallback.
"""
from __future__ import annotations
from langchain_ollama import ChatOllama
from app.core.config import settings


def get_local_llm(**kwargs):
    return ChatOllama(
        model=kwargs.get("model", settings.OLLAMA_MODEL),
        base_url=settings.OLLAMA_BASE_URL,
        temperature=kwargs.get("temperature", settings.LLM_TEMPERATURE),
        num_predict=kwargs.get("max_tokens", settings.LLM_MAX_TOKENS),
    )
