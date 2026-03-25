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
    
    # Agent 配置
    AGENT_MAX_ITERATIONS: int = 5
    AGENT_VERBOSE: bool = True
    
    # 工具配置
    ENABLE_WEB_SEARCH: bool = True
    ENABLE_CALCULATOR: bool = False
    
    # 法律辖区配置
    DEFAULT_JURISDICTION: str = "中国"
    
    # API 配置
    API_PREFIX: str = "/api"
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    
    # 日志配置
    LOG_FILE: str = "logs/app.log"
    LOG_ROTATION: str = "500 MB"
    LOG_RETENTION: str = "10 days"

    # 向量数据库配置
    CHROMA_PERSIST_DIR: str = "./data/chroma_db"
    ENABLE_SEMANTIC_MEMORY: bool = True
    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"
    EMBEDDING_LOCAL_ONLY: bool = False

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
                "api_key": self.OPENAI_API_KEY,
                "base_url": self.OPENAI_BASE_URL,
                "model": self.OPENAI_MODEL,
                "temperature": self.OPENAI_TEMPERATURE,
                "max_tokens": self.OPENAI_MAX_TOKENS,
            }


# 创建全局配置实例
settings = Settings()
