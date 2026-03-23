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
from app.services.llm_factory import LLMFactory
from app.core.memory_manager import memory_manager
from app.core.logger import app_logger

router = APIRouter(prefix="/legal", tags=["法律咨询"])


@router.post("/chat", response_model=ChatResponse, summary="法律咨询")
async def chat(
    request: ChatRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_api_base_url: Optional[str] = Header(None, alias="X-API-Base-URL"),
    x_api_model: Optional[str] = Header(None, alias="X-API-Model"),
    x_api_temperature: Optional[float] = Header(None, alias="X-API-Temperature"),
    x_api_max_tokens: Optional[int] = Header(None, alias="X-API-Max-Tokens")
):
    """
    法律咨询接口
    
    接收用户问题，返回 AI 回答
    
    - **question**: 用户问题（必填）
    - **session_id**: 会话ID（可选，默认为 "default"）
    - **jurisdiction**: 法律辖区（可选，默认为 "中国"）
    
    请求头（可选）：
    - **X-API-Key**: 自定义 API Key
    - **X-API-Base-URL**: 自定义 API Base URL
    - **X-API-Model**: 自定义模型名称
    - **X-API-Temperature**: 自定义温度参数
    - **X-API-Max-Tokens**: 自定义最大输出长度
    """
    try:
        # 构建自定义配置
        custom_config = None
        if x_api_key:
            custom_config = {
                "api_key": x_api_key,
                "base_url": x_api_base_url,
                "model": x_api_model,
                "temperature": x_api_temperature,
                "max_tokens": x_api_max_tokens
            }
            app_logger.info(f"使用自定义 LLM 配置: model={x_api_model}, base_url={x_api_base_url}")
        
        result = await legal_agent.chat(
            question=request.question,
            session_id=request.session_id,
            personality=request.personality,
            custom_config=custom_config
        )
        
        return ChatResponse(**result)
    
    except Exception as e:
        app_logger.error(f"聊天接口错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream", summary="法律咨询（SSE 流式）")
async def chat_stream(
    request: ChatRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_api_base_url: Optional[str] = Header(None, alias="X-API-Base-URL"),
    x_api_model: Optional[str] = Header(None, alias="X-API-Model"),
    x_api_temperature: Optional[float] = Header(None, alias="X-API-Temperature"),
    x_api_max_tokens: Optional[int] = Header(None, alias="X-API-Max-Tokens")
):
    """基于 ReAct Tool Loop 的流式输出，实时推送工具调用状态。"""

    custom_config = None
    if x_api_key:
        custom_config = {
            "api_key": x_api_key,
            "base_url": x_api_base_url,
            "model": x_api_model,
            "temperature": x_api_temperature,
            "max_tokens": x_api_max_tokens,
        }

    async def event_generator():
        try:
            history = legal_agent._get_session_history(request.session_id)

            await memory_manager.maybe_update_summary(request.session_id, history)
            summary_memory = memory_manager.get_summary(request.session_id)
            semantic_memories = memory_manager.search_semantic_memory(request.session_id, request.question, top_k=3)

            legal_context = await legal_agent._retrieve_legal_context(request.question, top_k=3)
            messages = legal_agent._build_messages(
                session_id=request.session_id,
                user_input=request.question,
                personality=request.personality,
                summary_memory=summary_memory,
                semantic_memories=semantic_memories,
                legal_context=legal_context,
            )

            graph_to_use = legal_agent.graph
            if custom_config and custom_config.get("api_key"):
                llm = LLMFactory.create_llm(
                    api_key=custom_config.get("api_key"),
                    base_url=custom_config.get("base_url"),
                    model=custom_config.get("model"),
                    temperature=custom_config.get("temperature"),
                    max_tokens=custom_config.get("max_tokens"),
                )
                graph_to_use = legal_agent._build_react_graph(llm.bind_tools(legal_agent.tools))

            yield f"data: {json.dumps({'event': 'start', 'message': '开始处理问题'}, ensure_ascii=False)}\n\n"

            final_answer = ""
            async for evt in legal_agent.run_react_stream(messages, graph_to_use=graph_to_use):
                if evt.get("event") == "tool_call":
                    payload = {
                        "event": "status",
                        "message": f"正在调用工具: {evt.get('tool_name', 'unknown')}"
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                elif evt.get("event") == "tool_result":
                    payload = {
                        "event": "tool_result",
                        "content": evt.get("content", "")
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                elif evt.get("event") == "final":
                    final_answer = evt.get("content", "")
                    payload = {
                        "event": "final",
                        "answer": final_answer,
                        "session_id": request.session_id,
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

            history.append({"role": "user", "content": request.question})
            history.append({"role": "assistant", "content": final_answer})

            try:
                memory_manager.schedule_semantic_memory_write(request.session_id, request.question, final_answer)
            except Exception:
                pass

            yield "data: [DONE]\n\n"

        except Exception as e:
            err = {"event": "error", "message": str(e)}
            yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/reset", response_model=ResetResponse, summary="重置会话")
async def reset_session(request: ResetRequest):
    """
    重置会话历史
    
    清除指定会话的对话历史
    
    - **session_id**: 会话ID（必填）
    """
    try:
        success = legal_agent.reset_session(request.session_id)
        
        return ResetResponse(
            success=success,
            message="会话已重置" if success else "重置失败",
            session_id=request.session_id
        )
    
    except Exception as e:
        app_logger.error(f"重置会话错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}", summary="获取会话历史")
async def get_history(session_id: str):
    """
    获取会话历史
    
    返回指定会话的对话历史
    
    - **session_id**: 会话ID
    """
    try:
        history = legal_agent.get_session_history(session_id)
        
        return {
            "session_id": session_id,
            "history": history,
            "count": len(history)
        }
    
    except Exception as e:
        app_logger.error(f"获取历史错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
