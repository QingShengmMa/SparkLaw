"""
健康检查路由
"""
from fastapi import APIRouter
from app.models.response import HealthResponse
from app.core.config import settings
from app.llm.factory import LLMFactory

router = APIRouter(prefix="/health", tags=["健康检查"])


@router.get("", response_model=HealthResponse, summary="健康检查")
async def health_check():
    """返回服务状态、版本信息和 LLM 配置"""
    llm_config = settings.get_llm_config()
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        llm_mode=settings.LLM_MODE,
        llm_model=llm_config.get("model", "unknown"),
    )
