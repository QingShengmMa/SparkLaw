"""
Moot Court Graph — 模拟庭审编排入口。
真实实现位于 app/services/court_agent.py（CourtDebateAgent）。
此文件作为标准分层入口，re-export 庭审 agent 并在后续版本逐步内联实现。
"""
from app.services.court_agent import CourtDebateAgent, get_court_agent

__all__ = ["CourtDebateAgent", "get_court_agent"]
