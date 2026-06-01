"""Request-local LLM usage context."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class UsageContext:
    user_id: int
    endpoint: str


_usage_context: ContextVar[Optional[UsageContext]] = ContextVar(
    "sparklaw_llm_usage_context",
    default=None,
)


def get_usage_context() -> Optional[UsageContext]:
    return _usage_context.get()


def set_usage_context(context: UsageContext):
    return _usage_context.set(context)


def reset_usage_context(token) -> None:
    _usage_context.reset(token)
