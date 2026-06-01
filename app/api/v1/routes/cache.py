"""
语义缓存管理 API
提供缓存统计、清理等管理接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.knowledge.rag_service import get_rag_service
from app.core.logger import app_logger


router = APIRouter(prefix="/cache", tags=["Semantic Cache"])


class CacheStatsResponse(BaseModel):
    """缓存统计响应"""
    enabled: bool
    total_entries: int
    threshold: float
    ttl_days: Optional[int] = None
    collection_name: Optional[str] = None


class ClearCacheRequest(BaseModel):
    """清理缓存请求"""
    days: Optional[int] = None
    clear_all: bool = False


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """
    获取语义缓存统计信息
    
    Returns:
        缓存统计数据
    """
    try:
        rag_service = get_rag_service()
        if not rag_service.semantic_cache:
            return CacheStatsResponse(
                enabled=False,
                total_entries=0,
                threshold=0.0,
            )
        
        stats = rag_service.semantic_cache.get_cache_stats()
        return CacheStatsResponse(**stats)
        
    except Exception as e:
        app_logger.error(f"获取缓存统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取缓存统计失败: {str(e)}")


@router.post("/clear")
async def clear_cache(request: ClearCacheRequest):
    """
    清理语义缓存
    
    Args:
        request: 清理请求
            - days: 清理 N 天前的缓存
            - clear_all: 是否清空所有缓存（危险操作）
    
    Returns:
        清理结果
    """
    try:
        rag_service = get_rag_service()
        if not rag_service.semantic_cache:
            raise HTTPException(status_code=400, detail="语义缓存未启用")
        
        if request.clear_all:
            success = rag_service.semantic_cache.clear_all_cache()
            if success:
                return {
                    "status": "success",
                    "message": "已清空所有缓存",
                    "cleared_count": "all",
                }
            else:
                raise HTTPException(status_code=500, detail="清空缓存失败")
        
        cleared_count = rag_service.semantic_cache.clear_expired_cache(days=request.days)
        return {
            "status": "success",
            "message": f"已清理 {cleared_count} 条过期缓存",
            "cleared_count": cleared_count,
            "days": request.days,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"清理缓存失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清理缓存失败: {str(e)}")


@router.get("/health")
async def cache_health_check():
    """
    缓存健康检查
    
    Returns:
        缓存服务状态
    """
    try:
        rag_service = get_rag_service()
        if not rag_service.semantic_cache:
            return {
                "status": "disabled",
                "message": "语义缓存未启用",
            }
        
        stats = rag_service.semantic_cache.get_cache_stats()
        return {
            "status": "healthy",
            "enabled": stats.get("enabled", False),
            "total_entries": stats.get("total_entries", 0),
            "threshold": stats.get("threshold", 0.0),
        }
        
    except Exception as e:
        app_logger.error(f"缓存健康检查失败: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }
