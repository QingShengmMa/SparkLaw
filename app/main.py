"""
FastAPI 应用主入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logger import app_logger
from app.api.v1.routes import health_router, legal_router, document_router, analysis_router, legal_tools_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    app_logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    app_logger.info(f"📊 LLM 模式: {settings.LLM_MODE}")
    app_logger.info(f"🔧 调试模式: {settings.DEBUG}")
    
    yield
    
    # 关闭时执行
    app_logger.info(f"👋 {settings.APP_NAME} 正在关闭...")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="开源智能法律助手 - 基于 LangChain 和 FastAPI",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health_router, prefix=settings.API_PREFIX)
app.include_router(legal_router, prefix=settings.API_PREFIX)
app.include_router(document_router, prefix=settings.API_PREFIX)
app.include_router(analysis_router, prefix=settings.API_PREFIX)
app.include_router(legal_tools_router, prefix=settings.API_PREFIX)


@app.get("/", tags=["根路径"])
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": f"{settings.API_PREFIX}/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
