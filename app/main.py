"""
FastAPI 应用主入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logger import app_logger
from app.api.v1.routes import (
    analysis_router,
    auth_router,
    document_router,
    health_router,
    legal_router,
    legal_tools_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    app_logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    app_logger.info(f"📊 LLM 模式: {settings.LLM_MODE}")
    app_logger.info(f"🔧 调试模式: {settings.DEBUG}")
    
    # 启动 Arize Phoenix 本地可观测性
    try:
        import phoenix as px
        from phoenix.otel import register
        from openinference.instrumentation.langchain import LangChainInstrumentor
        
        # 步骤1：启动 Phoenix 服务器（默认端口 6006）
        phoenix_session = px.launch_app()
        app_logger.info(f"🔭 Phoenix 可观测性已启动: {phoenix_session.url}")
        
        # 步骤2：使用 Phoenix 的 register() 方法自动配置 Tracer
        # 注意：endpoint 必须包含完整的 /v1/traces 路径
        tracer_provider = register(
            project_name="SparkLaw",
            endpoint=f"{phoenix_session.url}v1/traces",  # 添加完整路径
        )
        app_logger.info(f"📡 Phoenix Tracer 已注册: {phoenix_session.url}v1/traces")
        
        # 步骤3：自动追踪所有 LangChain 调用（包括 LangGraph）
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
        app_logger.info("✅ LangChain 追踪器已挂载（支持 LangGraph）")
        
    except ImportError as e:
        app_logger.warning(f"⚠️  Phoenix 依赖未完整安装: {str(e)}")
        app_logger.warning("   请运行: pip install 'arize-phoenix[evals]' openinference-instrumentation-langchain")
    except Exception as e:
        app_logger.warning(f"⚠️  Phoenix 启动失败，跳过可观测性: {str(e)}")
        import traceback
        app_logger.debug(traceback.format_exc())
    
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
app.include_router(auth_router, prefix=settings.API_PREFIX)
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
