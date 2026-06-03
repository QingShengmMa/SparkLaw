"""
LLM 工厂模式实现
根据配置创建不同的 LLM 实例
"""

from typing import Any, Optional, Union
from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.core.logger import app_logger
from app.llm.routed_chat_model import ProviderConfig, RoutedChatModel


class LLMFactory:
    """
    LLM 工厂类

    负责根据配置创建不同的 LLM 实例，支持云端和本地两种模式。
    云端模式使用 OpenAI 兼容的 API，本地模式使用 Ollama。
    """

    @staticmethod
    def create_llm(
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Union[Any, ChatOpenAI, RoutedChatModel]:
        try:
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
                providers = LLMFactory._cloud_providers()
                if not providers:
                    app_logger.warning("⚠️  未配置有效的 API Key，尝试使用本地 Ollama")
                    return LLMFactory._create_local_llm()

                app_logger.info(
                    "✅ 创建云端 LLM 路由: "
                    + " -> ".join(f"{item.name}:{item.model}" for item in providers)
                )
                return RoutedChatModel(
                    providers,
                    temperature=temperature if temperature is not None else settings.OPENAI_TEMPERATURE,
                    max_tokens=max_tokens if max_tokens is not None else settings.OPENAI_MAX_TOKENS,
                )
            else:
                return LLMFactory._create_local_llm()

        except Exception as e:
            app_logger.error(f"❌ 创建 LLM 失败: {str(e)}")
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
    def _create_local_llm() -> Any:
        app_logger.info(f"✅ 创建本地 LLM 实例: {settings.OLLAMA_MODEL}")
        try:
            ChatOllama = LLMFactory._get_chat_ollama_class()
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
    def _get_chat_ollama_class():
        try:
            from langchain_ollama import ChatOllama

            return ChatOllama
        except ImportError:
            pass

        try:
            from langchain_community.chat_models.ollama import ChatOllama

            return ChatOllama
        except ImportError:
            pass

        try:
            from langchain_community.chat_models import ChatOllama

            return ChatOllama
        except ImportError as exc:
            raise ImportError(
                "Ollama 本地模式依赖未安装。云端部署请设置 LLM_MODE=cloud；"
                "本地 Ollama 模式请安装 langchain-ollama。"
            ) from exc

    @staticmethod
    def _cloud_providers() -> list[ProviderConfig]:
        configured = {
            "groq": ProviderConfig(
                name="groq",
                api_key=settings.GROQ_API_KEY or "",
                base_url=settings.GROQ_BASE_URL,
                model=settings.GROQ_MODEL,
                input_cost_per_1m=settings.GROQ_INPUT_COST_PER_1M,
                output_cost_per_1m=settings.GROQ_OUTPUT_COST_PER_1M,
            ),
            "deepseek": ProviderConfig(
                name="deepseek",
                api_key=settings.DEEPSEEK_API_KEY or "",
                base_url=settings.DEEPSEEK_BASE_URL,
                model=settings.DEEPSEEK_MODEL,
                input_cost_per_1m=settings.DEEPSEEK_INPUT_COST_PER_1M,
                output_cost_per_1m=settings.DEEPSEEK_OUTPUT_COST_PER_1M,
            ),
        }

        providers: list[ProviderConfig] = []
        for name in settings.get_cloud_provider_names():
            provider = configured.get(name)
            if provider and provider.api_key:
                providers.append(provider)

        if not providers and settings.OPENAI_API_KEY:
            providers.append(
                ProviderConfig(
                    name="openai-compatible",
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL,
                    model=settings.OPENAI_MODEL,
                    input_cost_per_1m=0.0,
                    output_cost_per_1m=0.0,
                )
            )
        return providers

    @staticmethod
    def get_llm_info() -> dict:
        llm_config = settings.get_llm_config()
        if "api_key" in llm_config and llm_config["api_key"]:
            key = llm_config["api_key"]
            if len(key) > 12:
                llm_config["api_key"] = key[:8] + "..." + key[-4:]
            else:
                llm_config["api_key"] = "***"
        return llm_config
