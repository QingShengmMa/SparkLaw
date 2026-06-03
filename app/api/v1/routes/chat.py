"""
法律咨询路由
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.auth.dependencies import require_usage_context
from app.models.request import ChatRequest, ResetRequest
from app.models.response import ChatResponse, ResetResponse
from app.services.legal_agent import legal_agent
from app.llm.factory import LLMFactory
from app.core.memory_manager import memory_manager
from app.core.logger import app_logger

router = APIRouter(
    prefix="/legal",
    tags=["法律咨询"],
    dependencies=[Depends(require_usage_context)],
)


@router.post("/chat", response_model=ChatResponse, summary="法律咨询")
async def chat(
    request: ChatRequest,
):
    result = await legal_agent.chat(
        question=request.question,
        session_id=request.session_id,
        personality=request.personality,
        thread_id=request.thread_id,
    )
    return ChatResponse(
        answer=result.get("answer", ""),
        session_id=request.session_id,
        sources=result.get("sources", []),
    )


@router.post("/stream", summary="流式法律咨询")
async def chat_stream(
    request: ChatRequest,
):
    async def generate():
        agent = None
        history = []
        messages = []
        summary_memory = ""
        semantic_memories = []
        legal_context = ""

        def is_tool_generation_error(error_text: str) -> bool:
            lower = (error_text or "").lower()
            return (
                "failed_generation" in lower
                or "failed to call a function" in lower
                or "tool_use_failed" in lower
            )

        try:
            from app.agents.chat_methods import get_legal_agent
            from app.tools.legal_tools import get_tools
            from app.core.profiler import TTFTTracker
            agent = get_legal_agent()

            # 根据前端开关动态构建工具列表
            tools = get_tools(
                enable_search=request.enable_web_search,
                enable_calculator=True,
            )

            history = agent._get_session_history(request.session_id)
            await memory_manager.maybe_update_summary(request.session_id, history)
            summary_memory = memory_manager.get_summary(request.session_id)

            # 知识库检索开关
            legal_context = ""
            if request.enable_knowledge_retrieve:
                legal_context = await agent._retrieve_legal_context(request.question, top_k=3)

            semantic_memories = memory_manager.search_semantic_memory(
                session_id=request.session_id, query=request.question, top_k=3
            )

            messages = agent._build_messages(
                session_id=request.session_id,
                user_input=request.question,
                personality=request.personality,
                summary_memory=summary_memory,
                semantic_memories=semantic_memories,
                legal_context=legal_context,
                enable_deep_think=request.enable_deep_think,
            )

            # 构建使用动态工具列表的 graph
            base_llm = LLMFactory.create_llm()
            llm_with_tools = base_llm.bind_tools(tools)
            graph_to_use = agent._build_react_graph(llm_with_tools)

            # [PERF_CTX] 上下文 Token 用量明细
            from app.core.profiler import log_context_tokens, E2ETimer
            _history_msgs = [m for m in messages[1:-1]]  # 去掉 system 和最后一条 user
            log_context_tokens(
                session_id=request.session_id,
                system_prompt=messages[0].content if messages else "",
                summary_memory=summary_memory or "",
                semantic_memories=semantic_memories or [],
                legal_context=legal_context or "",
                history_messages=_history_msgs,
                user_input=request.question,
            )
            tracker = TTFTTracker(session_id=request.session_id)
            effective_thread_id = request.thread_id or request.session_id
            async for chunk in agent.run_react_event_stream(
                messages,
                graph_to_use=graph_to_use,
                thread_id=effective_thread_id,
                enable_deep_think=request.enable_deep_think,
                enable_web_search=request.enable_web_search,
                legal_context=legal_context,
            ):
                tracker.mark_first_token(chunk)
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        except Exception as e:
            app_logger.error(f"流式输出错误: {e}")
            err_text = str(e)
            if "GUARDRAIL_BLOCKED" in err_text:
                payload = {
                    "type": "error",
                    "role": "error",
                    "error_code": "GUARDRAIL_BLOCKED",
                    "message": "回答因合规校验未通过而被拦截，请调整问题后重试。",
                }
                yield f"event: error\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            elif is_tool_generation_error(err_text) and messages:
                try:
                    app_logger.warning("工具调用生成失败，降级为无工具普通回答")
                    fallback_llm = LLMFactory.create_llm()
                    response = await fallback_llm.ainvoke(messages)
                    answer = response.content if hasattr(response, "content") else str(response)
                    if isinstance(answer, list):
                        answer = "".join(
                            item.get("text", "") if isinstance(item, dict) else str(item)
                            for item in answer
                        )
                    answer = str(answer).strip()

                    if history is not None:
                        history.append({"role": "user", "content": request.question})
                        history.append({"role": "assistant", "content": answer})
                    if agent is not None:
                        memory_manager.schedule_semantic_memory_write(
                            session_id=request.session_id,
                            user_question=request.question,
                            assistant_answer=answer,
                        )

                    yield f"data: {json.dumps({'type': 'text', 'content': answer}, ensure_ascii=False)}\n\n"
                    yield f"data: {json.dumps({'type': 'final', 'answer': answer}, ensure_ascii=False)}\n\n"
                except Exception as fallback_error:
                    app_logger.error(f"无工具降级回答失败: {fallback_error}")
                    payload = {
                        "type": "error",
                        "role": "error",
                        "error_code": "STREAM_FALLBACK_ERROR",
                        "message": "模型工具调用失败，降级回答也未成功。请稍后重试或关闭联网搜索后再试。",
                        "content": str(fallback_error),
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            else:
                payload = {
                    "type": "error",
                    "role": "error",
                    "error_code": "STREAM_RUNTIME_ERROR",
                    "message": err_text,
                    "content": err_text,
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/reset", response_model=ResetResponse, summary="重置会话")
async def reset(request: ResetRequest):
    success = legal_agent.reset_session(request.session_id)
    return ResetResponse(
        success=success,
        message="会话已重置" if success else "会话重置失败",
        session_id=request.session_id,
    )
