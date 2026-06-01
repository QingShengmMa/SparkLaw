"""OpenAI-compatible chat model router with provider fallback and usage logging."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator, Iterable, Optional

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from app.auth.store import auth_store
from app.core.config import settings
from app.core.logger import app_logger
from app.llm.usage_context import get_usage_context


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    api_key: str
    base_url: str
    model: str
    input_cost_per_1m: float
    output_cost_per_1m: float


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    chinese_chars = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    other_chars = len(text) - chinese_chars
    return max(1, int(chinese_chars / 1.5 + other_chars / 4))


def serialize_prompt(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, BaseMessage):
        return str(value.content)
    if isinstance(value, list):
        return "\n".join(serialize_prompt(item) for item in value)
    if isinstance(value, tuple):
        return "\n".join(serialize_prompt(item) for item in value)
    if isinstance(value, dict):
        if "messages" in value:
            return serialize_prompt(value["messages"])
        return "\n".join(f"{key}: {serialize_prompt(item)}" for key, item in value.items())
    return str(value)


def extract_text(value: Any) -> str:
    if value is None:
        return ""
    content = getattr(value, "content", value)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
        return "".join(parts)
    return str(content)


def extract_token_usage(value: Any) -> tuple[Optional[int], Optional[int]]:
    usage = getattr(value, "usage_metadata", None)
    if isinstance(usage, dict):
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        if input_tokens is not None or output_tokens is not None:
            return input_tokens, output_tokens

    metadata = getattr(value, "response_metadata", None)
    if isinstance(metadata, dict):
        token_usage = metadata.get("token_usage") or {}
        input_tokens = token_usage.get("prompt_tokens")
        output_tokens = token_usage.get("completion_tokens")
        if input_tokens is not None or output_tokens is not None:
            return input_tokens, output_tokens

    return None, None


def is_fallback_error(exc: Exception) -> bool:
    text = str(exc).lower()
    markers = [
        "429",
        "rate limit",
        "rate_limit",
        "too many requests",
        "quota",
        "insufficient_quota",
        "exceeded",
    ]
    return any(marker in text for marker in markers)


class RoutedChatModel:
    """A tiny adapter that tries providers in order and records usage."""

    def __init__(
        self,
        providers: Iterable[ProviderConfig],
        *,
        temperature: float,
        max_tokens: int,
        tools: Optional[list[Any]] = None,
    ):
        self.providers = [provider for provider in providers if provider.api_key]
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.tools = tools
        if not self.providers:
            raise ValueError("No cloud LLM provider is configured.")

    def bind_tools(self, tools: list[Any]):
        return RoutedChatModel(
            self.providers,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            tools=tools,
        )

    async def ainvoke(self, prompt: Any, *args: Any, **kwargs: Any) -> Any:
        last_error: Optional[Exception] = None
        for index, provider in enumerate(self.providers):
            model = self._build_model(provider)
            try:
                result = await model.ainvoke(prompt, *args, **kwargs)
                self._record_usage(provider, prompt, extract_text(result), result)
                return result
            except Exception as exc:
                last_error = exc
                if index < len(self.providers) - 1 and is_fallback_error(exc):
                    app_logger.warning(
                        f"LLM provider {provider.name} reached a limit; falling back to {self.providers[index + 1].name}."
                    )
                    continue
                raise
        raise last_error or RuntimeError("No LLM provider returned a response.")

    async def astream(self, prompt: Any, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        last_error: Optional[Exception] = None
        for index, provider in enumerate(self.providers):
            model = self._build_model(provider)
            output_parts: list[str] = []
            yielded = False
            try:
                async for chunk in model.astream(prompt, *args, **kwargs):
                    yielded = True
                    output_parts.append(extract_text(chunk))
                    yield chunk
                self._record_usage(provider, prompt, "".join(output_parts), None)
                return
            except Exception as exc:
                last_error = exc
                if yielded:
                    raise
                if index < len(self.providers) - 1 and is_fallback_error(exc):
                    app_logger.warning(
                        f"Streaming provider {provider.name} reached a limit; falling back to {self.providers[index + 1].name}."
                    )
                    continue
                raise
        raise last_error or RuntimeError("No LLM provider returned a stream.")

    def _build_model(self, provider: ProviderConfig):
        model = ChatOpenAI(
            api_key=provider.api_key,
            base_url=provider.base_url,
            model=provider.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=settings.LLM_TIMEOUT_SECONDS,
            max_retries=0,
        )
        return model.bind_tools(self.tools) if self.tools else model

    def _record_usage(
        self,
        provider: ProviderConfig,
        prompt: Any,
        output_text: str,
        result: Any,
    ) -> None:
        context = get_usage_context()
        if context is None or context.user_id <= 0:
            return

        prompt_text = serialize_prompt(prompt)
        input_tokens, output_tokens = extract_token_usage(result)
        input_count = int(input_tokens) if input_tokens is not None else estimate_tokens(prompt_text)
        output_count = int(output_tokens) if output_tokens is not None else estimate_tokens(output_text)
        input_cost = input_count * provider.input_cost_per_1m / 1_000_000
        output_cost = output_count * provider.output_cost_per_1m / 1_000_000

        try:
            auth_store.record_usage(
                user_id=context.user_id,
                provider=provider.name,
                model=provider.model,
                endpoint=context.endpoint,
                input_tokens=input_count,
                output_tokens=output_count,
                input_cost_usd=input_cost,
                output_cost_usd=output_cost,
            )
        except Exception as exc:
            app_logger.warning(f"LLM usage logging failed: {exc}")
