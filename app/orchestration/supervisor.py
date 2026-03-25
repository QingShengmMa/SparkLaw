"""
Supervisor orchestration — 多 Agent 任务分发与收敛。
真实实现位于 app/services/supervisor_agent.py (SupervisorDebateAgent)。
此文件作为标准分层入口，re-export supervisor 并在后续版本逐步内联实现。
"""
from app.services.supervisor_agent import SupervisorDebateAgent, get_supervisor_agent

__all__ = ["SupervisorDebateAgent", "get_supervisor_agent"]
