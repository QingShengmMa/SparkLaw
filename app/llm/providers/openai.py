"""
OpenAI provider adapter.
TODO: wrap LangChain ChatOpenAI with retry/timeout/cost tracking.
"""
from __future__ import annotations
from langchain_openai import ChatOpenAI
from app.core.config import settings


def get_openai_llm(**kwargs):
    return ChatOpenAI(
        model=kwargs.get("model", settings.OPENAI_MODEL),
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL or None,
        temperature=kwargs.get("temperature", settings.LLM_TEMPERATURE),
        max_tokens=kwargs.get("max_tokens", settings.LLM_MAX_TOKENS),
        streaming=True,
    )
