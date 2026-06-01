"""
性能监控与埋点工具
提供以下维度的统计能力，日志关键字速查：
  [PERF_TTFT]    - 首字响应时间 (Time To First Token)
  [PERF_TOKEN]   - 记忆压缩 Token 压缩率
  [PERF_RAG]     - RAG 四阶链路耗时（rewrite/recall/rerank/dedup）
  [PERF_LLM]     - LLM 主推理耗时（从第一个 token 到流结束）
  [PERF_TOOL]    - 单次工具调用耗时
  [PERF_RERANK]  - Rerank 候选数量与分数分布
  [PERF_CTX]     - 每次请求注入上下文的 Token 用量明细
  [PERF_E2E]     - 请求端到端全链路总耗时
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import List, Optional

# ---------------------------------------------------------------------------
# tiktoken 按需加载（不阻塞服务启动）
# ---------------------------------------------------------------------------
try:
    import tiktoken as _tiktoken
    _enc = _tiktoken.get_encoding("cl100k_base")

    def _count_tokens(text: str) -> int:
        return len(_enc.encode(text, disallowed_special=()))
except Exception:
    def _count_tokens(text: str) -> int:  # type: ignore[misc]
        return max(1, int(len(text) / 1.5))


# ---------------------------------------------------------------------------
# 1. TTFT — 首字响应时间
# ---------------------------------------------------------------------------

class TTFTTracker:
    """
    在 SSE 生成器内使用，记录从请求进入到第一个可见 text chunk 的毫秒数。

    用法（chat.py generate() 内）::

        tracker = TTFTTracker(session_id=request.session_id)
        async for chunk in agent.run_react_event_stream(...):
            tracker.mark_first_token(chunk)
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\\n\\n"
    """
    _FIRST_TOKEN_TYPES = {"text", "token", "chunk"}

    def __init__(self, session_id: str = ""):
        self.session_id = session_id
        self._start_ts: float = time.perf_counter()
        self._first_token_recorded: bool = False

    def mark_first_token(self, chunk: dict) -> None:
        if self._first_token_recorded:
            return
        if chunk.get("type", "") not in self._FIRST_TOKEN_TYPES:
            return
        if not (chunk.get("content", "") or chunk.get("text", "")):
            return
        ttft_ms = (time.perf_counter() - self._start_ts) * 1000
        self._first_token_recorded = True
        from app.core.logger import app_logger
        app_logger.info(
            f"[PERF_TTFT] session={self.session_id} ttft={ttft_ms:.1f}ms"
        )


# ---------------------------------------------------------------------------
# 2. PERF_TOKEN — 记忆压缩率
# ---------------------------------------------------------------------------

def log_compression_stats(session_id: str, before_text: str, after_text: str) -> None:
    """
    在 memory_manager.maybe_update_summary() 完成后调用。
    日志示例::
        [PERF_TOKEN] session=abc before_tokens=1240 after_tokens=186 ratio=85.0%
    """
    before_tokens = _count_tokens(before_text)
    after_tokens = _count_tokens(after_text)
    if before_tokens == 0:
        return
    ratio = (1 - after_tokens / before_tokens) * 100
    from app.core.logger import app_logger
    app_logger.info(
        f"[PERF_TOKEN] session={session_id} "
        f"before_tokens={before_tokens} after_tokens={after_tokens} ratio={ratio:.1f}%"
    )


# ---------------------------------------------------------------------------
# 3. PERF_RAG — RAG 四阶链路耗时
# ---------------------------------------------------------------------------

@contextmanager
def rag_stage_timer(stage: str, query_preview: str = ""):
    """
    包裹 RAG 每一阶段（rewrite/recall/rerank/dedup）并打印耗时。
    日志示例::
        [PERF_RAG] stage=rewrite  query='违法解除' elapsed=312.1ms
    """
    t0 = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        from app.core.logger import app_logger
        app_logger.info(
            f"[PERF_RAG] stage={stage:<8} query={query_preview!r} elapsed={elapsed_ms:.1f}ms"
        )


# ---------------------------------------------------------------------------
# 4. PERF_LLM — LLM 主推理流式耗时
# ---------------------------------------------------------------------------

class LLMStreamTimer:
    """
    追踪 LLM 流式推理总耗时（从第一个 on_chat_model_stream 到流结束）。
    同时统计输出 token 数量，计算吞吐量（tokens/s）。

    用法（chat_methods.py run_react_event_stream 内）::

        llm_timer = LLMStreamTimer(session_id=session_id)
        async for evt in event_stream:
            if evt["event"] == "on_chat_model_stream":
                llm_timer.on_token(text)   # 每个 token 调用一次
            ...
        llm_timer.finish()   # 流结束时调用
    """

    def __init__(self, session_id: str = ""):
        self.session_id = session_id
        self._start_ts: Optional[float] = None
        self._token_count: int = 0
        self._char_count: int = 0

    def on_token(self, text: str) -> None:
        """每收到一段 text chunk 时调用。"""
        if not text:
            return
        if self._start_ts is None:
            self._start_ts = time.perf_counter()
        # 估算 token 数（快速路径，不调用 tiktoken 避免影响流速）
        self._token_count += max(1, int(len(text) / 1.5))
        self._char_count += len(text)

    def finish(self) -> None:
        """流结束时调用，打印 LLM 推理总耗时与吞吐量。"""
        if self._start_ts is None:
            return
        elapsed_ms = (time.perf_counter() - self._start_ts) * 1000
        throughput = self._token_count / (elapsed_ms / 1000) if elapsed_ms > 0 else 0
        from app.core.logger import app_logger
        app_logger.info(
            f"[PERF_LLM] session={self.session_id} "
            f"llm_elapsed={elapsed_ms:.1f}ms "
            f"output_tokens~{self._token_count} "
            f"chars={self._char_count} "
            f"throughput~{throughput:.1f}tok/s"
        )


# ---------------------------------------------------------------------------
# 5. PERF_TOOL — 工具调用耗时
# ---------------------------------------------------------------------------

@contextmanager
def tool_call_timer(tool_name: str, session_id: str = ""):
    """
    包裹单次工具调用并打印耗时与状态。
    日志示例::
        [PERF_TOOL] tool=calculate_labor_compensation session=abc elapsed=2.3ms status=success
        [PERF_TOOL] tool=search_latest_legal_cases   session=abc elapsed=3241.0ms status=success
    """
    t0 = time.perf_counter()
    status = "success"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        from app.core.logger import app_logger
        app_logger.info(
            f"[PERF_TOOL] tool={tool_name:<40} session={session_id} "
            f"elapsed={elapsed_ms:.1f}ms status={status}"
        )


# ---------------------------------------------------------------------------
# 6. PERF_RERANK — Rerank 候选数与分数分布
# ---------------------------------------------------------------------------

def log_rerank_stats(query_preview: str, scores: List[float], top_k: int) -> None:
    """
    在 Reranker.rerank() 完成后调用，记录候选数、top-k 分数及最小/最大/均值。
    日志示例::
        [PERF_RERANK] query='违法解除' candidates=15 top_k=3 \
            score_max=8.42 score_min=-3.10 score_mean=1.23 \
            selected_min=5.67
    """
    if not scores:
        return
    score_max = max(scores)
    score_min = min(scores)
    score_mean = sum(scores) / len(scores)
    top_scores = sorted(scores, reverse=True)[:top_k]
    selected_min = min(top_scores) if top_scores else 0.0
    from app.core.logger import app_logger
    app_logger.info(
        f"[PERF_RERANK] query={query_preview!r} candidates={len(scores)} top_k={top_k} "
        f"score_max={score_max:.2f} score_min={score_min:.2f} score_mean={score_mean:.2f} "
        f"selected_min={selected_min:.2f}"
    )


# ---------------------------------------------------------------------------
# 7. PERF_CTX — 上下文 Token 用量明细
# ---------------------------------------------------------------------------

def log_context_tokens(
    session_id: str,
    system_prompt: str,
    summary_memory: str,
    semantic_memories: List[str],
    legal_context: str,
    history_messages: List,
    user_input: str,
) -> None:
    """
    在 _build_messages() 完成后调用，拆解每个上下文块的 Token 占比。
    日志示例::
        [PERF_CTX] session=abc total=2341 \
            system=312 summary=98 semantic=156 legal=487 history=1201 user=87
    """
    t_system   = _count_tokens(system_prompt)
    t_summary  = _count_tokens(summary_memory)
    t_semantic = _count_tokens(" ".join(semantic_memories))
    t_legal    = _count_tokens(legal_context)
    t_history  = sum(
        _count_tokens(str(getattr(m, "content", m)))
        for m in history_messages
    )
    t_user     = _count_tokens(user_input)
    t_total    = t_system + t_summary + t_semantic + t_legal + t_history + t_user
    from app.core.logger import app_logger
    app_logger.info(
        f"[PERF_CTX] session={session_id} total={t_total} "
        f"system={t_system} summary={t_summary} semantic={t_semantic} "
        f"legal={t_legal} history={t_history} user={t_user}"
    )


# ---------------------------------------------------------------------------
# 8. PERF_E2E — 请求端到端全链路计时
# ---------------------------------------------------------------------------

class E2ETimer:
    """
    追踪一次完整 /stream 请求从进入 generate() 到最后一个 chunk yield 的总耗时。

    用法（chat.py generate() 内）::

        e2e = E2ETimer(session_id=request.session_id)
        async for chunk in agent.run_react_event_stream(...):
            yield ...
        e2e.finish(tool_calls=tracker.tool_call_count)   # 流结束后调用
    """

    def __init__(self, session_id: str = ""):
        self.session_id = session_id
        self._start_ts = time.perf_counter()

    def finish(self, tool_calls: int = 0) -> None:
        elapsed_ms = (time.perf_counter() - self._start_ts) * 1000
        from app.core.logger import app_logger
        app_logger.info(
            f"[PERF_E2E] session={self.session_id} "
            f"total={elapsed_ms:.1f}ms tool_calls={tool_calls}"
        )
