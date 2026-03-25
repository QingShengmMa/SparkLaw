"""
Session Store — 短期会话记忆管理。
从 app/core/memory_manager.py 迁移，保留原有实现并通过兼容层导出。
"""
from app.core.memory_manager import HybridMemoryManager as MemoryManager, memory_manager

__all__ = ["MemoryManager", "memory_manager"]
