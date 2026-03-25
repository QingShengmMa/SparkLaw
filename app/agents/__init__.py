"""Agents package exports."""
from app.agents.legal_agent import (
    LegalAgentService,
    LegalAgentGraphState,
    LLMConnectionError,
    PersonalityType,
    PERSONALITY_PROMPTS,
    normalize_personality,
)
from app.services.debate_agent import AceAttorneyDebateAgent, get_debate_agent

__all__ = [
    "LegalAgentService",
    "LegalAgentGraphState",
    "LLMConnectionError",
    "PersonalityType",
    "PERSONALITY_PROMPTS",
    "normalize_personality",
    "AceAttorneyDebateAgent",
    "get_debate_agent",
]
