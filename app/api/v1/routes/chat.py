"""
法律咨询路由
"""
import json
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import StreamingResponse
from typing import Optional
from app.models.request import ChatRequest, ResetRequest
from app.models.response import ChatResponse, ResetResponse
from app.services.legal_agent import legal_agent
from app.llm.factory import LLMFactory
from app.core.memory_manager import memory_manager
from app.core.logger import app_logger

router = APIRouter(prefix="/legal", tags=["法律咨询"])


@router.post("/chat", response_model=ChatResponse, summary="法律咨询")
async def chat(
    request: ChatRequest,
    x_api_key: Optional[str] = Header(default=None),
    x_api_base_url: Optional[str] = Header(default=None),
    x_api_model: Optional[str] = Header(default=None),
    x_api_temperature: Optional[str] = Header(default=None),
    x_api_max_tokens: Optional[str] = Header(default=None),
):
    custom_config = None
    if x_api_key:
        custom_config = {
            "api_key": x_api_key,
            "base_url": x_api_base_url,
            "model": x_api_model,
            "temperature": float(x_api_temperature) if x_api_temperature else None,
            "max_tokens": int(x_api_max_tokens) if x_api_max_tokens else None,
        }
    result = await legal_agent.chat(
        question=request.question,
        session_id=request.session_id,
        personality=request.personality,
        custom_config=custom_config,
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
    x_api_key: Optional[str] = Header(default=None),
    x_api_base_url: Optional[str] = Header(default=None),
    x_api_model: Optional[str] = Header(default=None),
    x_api_temperature: Optional[str] = Header(default=None),
    x_api_max_tokens: Optional[str] = Header(default=None),
):
    custom_config = None
    if x_api_key:
        custom_config = {
            "api_key": x_api_key,
            "base_url": x_api_base_url,
            "model": x_api_model,
            "temperature": float(x_api_temperature) if x_api_temperature else None,
            "max_tokens": int(x_api_max_tokens) if x_api_max_tokens else None,
        }

    async def generate():
        try:
            from app.agents.legal_agent import LegalAgentService
            from app.agents.chat_methods import get_legal_agent
            agent = get_legal_agent()
            history = agent._get_session_history(request.session_id)
            await memory_manager.maybe_update_summary(request.session_id, history)
            summary_memory = memory_manager.get_summary(request.session_id)
            semantic_memories = memory_manager.search_semantic_memory(
                session_id=request.session_id, query=request.question, top_k=3
            )
            legal_context = await agent._retrieve_legal_context(request.question, top_k=3)
            messages = agent._build_messages(
                session_id=request.session_id,
                user_input=request.question,
                personality=request.personality,
                summary_memory=summary_memory,
                semantic_memories=semantic_memories,
                legal_context=legal_context,
            )
            graph_to_use = agent.graph
            if custom_config and custom_config.get("api_key"):
                custom_llm = LLMFactory.create_llm(**{k: v for k, v in custom_config.items() if v})
                graph_to_use = agent._build_react_graph(custom_llm.bind_tools(agent.tools))
            async for chunk in agent.run_react_stream(messages, graph_to_use=graph_to_use, thread_id=request.thread_id):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        except Exception as e:
            app_logger.error(f"流式输出错误: {e}")
            yield f"data: {json.dumps({'role':'error','content':str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/reset", response_model=ResetResponse, summary="重置会话")
async def reset(request: ResetRequest):
    success = legal_agent.reset_session(request.session_id)
    return ResetResponse(success=success, session_id=request.session_id)
