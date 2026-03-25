"""
Legal QA Graph — 普法问答编排入口。
真实实现位于 app/agents/legal_agent.py（LegalAgentService）。
"""
from app.agents.legal_agent import LegalAgentService
from app.agents.chat_methods import legal_agent, get_legal_agent

__all__ = ["LegalAgentService", "legal_agent", "get_legal_agent"]
