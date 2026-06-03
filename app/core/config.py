"""
核心配置模块
使用 pydantic-settings 管理环境变量配置
"""

from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用基础配置
    APP_NAME: str = "SparkLaw"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # LLM 模式配置
    LLM_MODE: Literal["local", "cloud"] = "local"
    
    # 本地模式配置（Ollama）
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    OLLAMA_TEMPERATURE: float = 0.3
    OLLAMA_MAX_TOKENS: int = 2048
    
    # 云端模式配置（OpenAI 兼容接口）
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OPENAI_TEMPERATURE: float = 0.3
    OPENAI_MAX_TOKENS: int = 2048

    # 云端供应商路由：优先 Groq，额度/限流后自动回退 DeepSeek
    LLM_PROVIDER_ORDER: str = "groq,deepseek"
    GROQ_API_KEY: Optional[str] = None
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    GROQ_INPUT_COST_PER_1M: float = 0.05
    GROQ_OUTPUT_COST_PER_1M: float = 0.08
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_INPUT_COST_PER_1M: float = 0.27
    DEEPSEEK_OUTPUT_COST_PER_1M: float = 1.10
    
    # Agent 配置
    AGENT_MAX_ITERATIONS: int = 5
    AGENT_VERBOSE: bool = True
    
    # LLM 超时与重试配置
    LLM_TIMEOUT_SECONDS: int = 60
    LLM_RETRY_ATTEMPTS: int = 2
    
    # 工具配置
    ENABLE_WEB_SEARCH: bool = True
    ENABLE_CALCULATOR: bool = False
    ENABLE_OBSERVABILITY: bool = False
    
    # 法律辖区配置
    DEFAULT_JURISDICTION: str = "中国"
    
    # API 配置
    API_PREFIX: str = "/api"
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # 认证配置
    AUTH_ENABLED: bool = True
    AUTH_ALLOW_REGISTRATION: bool = True
    AUTH_REGISTRATION_INVITE_CODE: Optional[str] = None
    AUTH_DB_PATH: str = "data/sparklaw.sqlite3"
    AUTH_COOKIE_NAME: str = "sparklaw_session"
    AUTH_COOKIE_SECURE: bool = False
    AUTH_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    AUTH_SESSION_TTL_DAYS: int = 14
    AUTH_PASSWORD_MIN_LENGTH: int = 10
    
    # 日志配置
    LOG_FILE: str = "logs/app.log"
    LOG_ROTATION: str = "500 MB"
    LOG_RETENTION: str = "10 days"

    # 向量数据库配置 (Qdrant)
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_CONTRACTS: str = "legal_contracts"
    QDRANT_COLLECTION_LAWS: str = "legal_corpus"
    QDRANT_VECTOR_SIZE: int = 512  # BAAI/bge-small-zh-v1.5 的向量维度
    ENABLE_SEMANTIC_MEMORY: bool = False
    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"
    EMBEDDING_LOCAL_ONLY: bool = False
    
    # 兼容旧配置（用于数据迁移）
    CHROMA_PERSIST_DIR: str = "./data/chroma_db"
    
    # 语义缓存配置
    ENABLE_SEMANTIC_CACHE: bool = False
    SEMANTIC_CACHE_THRESHOLD: float = 0.92
    SEMANTIC_CACHE_TOP_K: int = 1
    SEMANTIC_CACHE_TTL_DAYS: int = 30

    # Redis / Celery 配置
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    def get_llm_config(self) -> dict:
        """获取当前 LLM 配置"""
        if self.LLM_MODE == "local":
            return {
                "mode": "local",
                "base_url": self.OLLAMA_BASE_URL,
                "model": self.OLLAMA_MODEL,
                "temperature": self.OLLAMA_TEMPERATURE,
                "max_tokens": self.OLLAMA_MAX_TOKENS,
            }
        else:
            return {
                "mode": "cloud",
                "providers": self.get_cloud_provider_names(),
                "temperature": self.OPENAI_TEMPERATURE,
                "max_tokens": self.OPENAI_MAX_TOKENS,
            }

    def get_cloud_provider_names(self) -> list[str]:
        return [
            item.strip().lower()
            for item in self.LLM_PROVIDER_ORDER.split(",")
            if item.strip()
        ]


# 创建全局配置实例
settings = Settings()
