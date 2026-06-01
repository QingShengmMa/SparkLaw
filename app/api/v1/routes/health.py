"""
健康检查路由
"""
from fastapi import APIRouter

from app.core.config import settings
from app.models.response import HealthResponse

router = APIRouter(prefix="/health", tags=["健康检查"])


@router.get("", response_model=HealthResponse, summary="健康检查")
async def health_check():
    """返回服务状态、版本信息和当前生效的 LLM 配置"""
    llm_config = settings.get_llm_config()
    providers = llm_config.get("providers")
    effective_model = " -> ".join(providers) if providers else llm_config.get("model", "unknown")

    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        llm_mode=settings.LLM_MODE,
        llm_model=effective_model,
    )
