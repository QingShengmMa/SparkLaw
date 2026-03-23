"""
LLM 工厂模式实现
根据配置创建不同的 LLM 实例
"""

from typing import Union, Optional
from langchain_community.chat_models import ChatOllama
from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.core.logger import app_logger


class LLMFactory:
    """
    LLM 工厂类
    
    负责根据配置创建不同的 LLM 实例，支持云端和本地两种模式。
    云端模式使用 OpenAI 兼容的 API（如 Groq），本地模式使用 Ollama。
    """
    
    @staticmethod
    def create_llm(
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Union[ChatOllama, ChatOpenAI]:
        """
        根据配置创建 LLM 实例
        
        优先使用云端 API（Groq），如果未配置则使用本地 Ollama。
        如果创建失败，会自动降级到本地模式。
        
        Args:
            api_key: 自定义 API Key（可选）
            base_url: 自定义 Base URL（可选）
            model: 自定义模型名称（可选）
        
        Returns:
            Union[ChatOllama, ChatOpenAI]: LLM 实例
            
        Raises:
            Exception: 当云端和本地模式都无法创建时抛出异常
        """
        try:
            # 如果提供了自定义配置，直接使用
            if api_key:
                app_logger.info(f"✅ 使用自定义配置创建 LLM: model={model or settings.OPENAI_MODEL}")
                return ChatOpenAI(
                    api_key=api_key,
                    base_url=base_url or settings.OPENAI_BASE_URL,
                    model=model or settings.OPENAI_MODEL,
                    temperature=temperature if temperature is not None else settings.OPENAI_TEMPERATURE,
                    max_tokens=max_tokens if max_tokens is not None else settings.OPENAI_MAX_TOKENS,
                )
            
            if settings.LLM_MODE == "cloud":
                # 云端模式 - 使用 Groq API
                if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your_groq_api_key_here":
                    app_logger.warning("⚠️  未配置有效的 API Key，尝试使用本地 Ollama")
                    return LLMFactory._create_local_llm()
                
                app_logger.info(f"✅ 创建云端 LLM 实例: {settings.OPENAI_MODEL}")
                return ChatOpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL,
                    model=settings.OPENAI_MODEL,
                    temperature=temperature if temperature is not None else settings.OPENAI_TEMPERATURE,
                    max_tokens=max_tokens if max_tokens is not None else settings.OPENAI_MAX_TOKENS,
                )
            else:
                # 本地模式 - 使用 Ollama
                return LLMFactory._create_local_llm()
                
        except Exception as e:
            app_logger.error(f"❌ 创建 LLM 失败: {str(e)}")
            # 降级到本地模式
            app_logger.info("🔄 尝试降级到本地 Ollama")
            try:
                return LLMFactory._create_local_llm()
            except Exception as fallback_error:
                app_logger.error(f"❌ 本地 LLM 创建也失败: {str(fallback_error)}")
                raise Exception(
                    "无法创建 LLM 实例。请检查：\n"
                    "1. 云端模式：OPENAI_API_KEY 是否正确配置\n"
                    "2. 本地模式：Ollama 服务是否启动"
                )
    
    @staticmethod
    def _create_local_llm() -> ChatOllama:
        """
        创建本地 Ollama LLM 实例
        
        Returns:
            ChatOllama: 本地 Ollama LLM 实例
            
        Raises:
            Exception: 当 Ollama 服务不可用时抛出异常
        """
        app_logger.info(f"✅ 创建本地 LLM 实例: {settings.OLLAMA_MODEL}")
        try:
            return ChatOllama(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.OLLAMA_MODEL,
                temperature=settings.OLLAMA_TEMPERATURE,
                num_predict=settings.OLLAMA_MAX_TOKENS,
            )
        except Exception as e:
            app_logger.error(f"❌ 无法连接到 Ollama 服务 ({settings.OLLAMA_BASE_URL}): {str(e)}")
            raise
    
    @staticmethod
    def get_llm_info() -> dict:
        """
        获取当前 LLM 配置信息
        
        用于健康检查和调试，会自动隐藏敏感的 API Key 信息。
        
        Returns:
            dict: LLM 配置信息字典，包含模式、模型名称等信息
        """
        llm_config = settings.get_llm_config()
        
        # 隐藏敏感信息（只显示前8位和后4位）
        if "api_key" in llm_config and llm_config["api_key"]:
            key = llm_config["api_key"]
            if len(key) > 12:
                llm_config["api_key"] = key[:8] + "..." + key[-4:]
            else:
                llm_config["api_key"] = "***"
        
        return llm_config
