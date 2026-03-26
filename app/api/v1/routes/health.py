"""
健康检查路由
"""
from typing import Optional

from fastapi import APIRouter, Header

from app.core.config import settings
from app.models.response import HealthResponse

router = APIRouter(prefix="/health", tags=["健康检查"])


@router.get("", response_model=HealthResponse, summary="健康检查")
async def health_check(
    x_api_key: Optional[str] = Header(default=None),
    x_api_model: Optional[str] = Header(default=None),
):
    """返回服务状态、版本信息和当前生效的 LLM 配置"""
    llm_config = settings.get_llm_config()

    effective_mode = settings.LLM_MODE
    effective_model = llm_config.get("model", "unknown")

    # 当请求携带自定义 API Key 时，说明本次请求将使用前端本地配置
    if x_api_key:
        effective_mode = "local"
        effective_model = x_api_model or settings.OPENAI_MODEL

    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        llm_mode=effective_mode,
        llm_model=effective_model,
    )
