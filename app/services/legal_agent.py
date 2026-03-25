"""
兼容层：从新分层路径重新导出 LegalAgentService 和 legal_agent 实例。
实际实现已迁移至 app/agents/legal_agent.py + app/agents/chat_methods.py
"""
from app.agents.chat_methods import LegalAgentService, legal_agent, get_legal_agent
from app.agents.legal_agent import (
    LLMConnectionError,
    PersonalityType,
    PERSONALITY_PROMPTS,
    normalize_personality,
    LegalAgentGraphState,
)

__all__ = [
    "LegalAgentService",
    "legal_agent",
    "get_legal_agent",
    "LLMConnectionError",
    "PersonalityType",
    "PERSONALITY_PROMPTS",
    "normalize_personality",
    "LegalAgentGraphState",
]
