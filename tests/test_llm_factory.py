"""
测试 LLM 工厂模式
"""

from app.services import llm_factory as llm_factory_module
from app.services.llm_factory import LLMFactory
from app.core.config import settings


class DummyChatOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class DummyChatOllama:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def test_create_llm_local(monkeypatch):
    """测试创建本地 LLM"""
    monkeypatch.setattr(llm_factory_module, "ChatOllama", DummyChatOllama)
    settings.LLM_MODE = "local"

    llm = LLMFactory.create_llm()
    assert isinstance(llm, DummyChatOllama)
    assert llm.kwargs["model"] == settings.OLLAMA_MODEL


def test_create_llm_cloud(monkeypatch):
    """测试创建云端 LLM"""
    monkeypatch.setattr(llm_factory_module, "ChatOpenAI", DummyChatOpenAI)
    settings.LLM_MODE = "cloud"
    settings.OPENAI_API_KEY = "test_key"

    llm = LLMFactory.create_llm()
    assert isinstance(llm, DummyChatOpenAI)
    assert llm.kwargs["api_key"] == "test_key"


def test_create_llm_with_custom_temperature_and_max_tokens(monkeypatch):
    """测试自定义 temperature/max_tokens 能正确透传"""
    monkeypatch.setattr(llm_factory_module, "ChatOpenAI", DummyChatOpenAI)

    llm = LLMFactory.create_llm(
        api_key="sk-custom",
        base_url="https://api.custom.com/v1",
        model="custom-model",
        temperature=0.8,
        max_tokens=4096,
    )

    assert isinstance(llm, DummyChatOpenAI)
    assert llm.kwargs["api_key"] == "sk-custom"
    assert llm.kwargs["base_url"] == "https://api.custom.com/v1"
    assert llm.kwargs["model"] == "custom-model"
    assert llm.kwargs["temperature"] == 0.8
    assert llm.kwargs["max_tokens"] == 4096


def test_get_llm_info():
    """测试获取 LLM 信息"""
    info = LLMFactory.get_llm_info()
    assert "mode" in info
    assert "model" in info
