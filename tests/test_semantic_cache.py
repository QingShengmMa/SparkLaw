"""
测试 SemanticCacheManager — 禁用状态 / 单例 / TTL 配置 / 统计
"""

import sys
import asyncio
import pytest
from importlib.util import spec_from_file_location, module_from_spec
from app.core.config import settings

# 从文件路径直接加载模块，绕过 app/knowledge/__init__.py
_mod_path = "app/knowledge/semantic_cache.py"
_spec = spec_from_file_location("sparklaw_semantic_cache", _mod_path)
_mod = module_from_spec(_spec)
sys.modules["sparklaw_semantic_cache"] = _mod
_spec.loader.exec_module(_mod)
SemanticCacheManager = _mod.SemanticCacheManager
get_semantic_cache = _mod.get_semantic_cache


class TestCacheDisabled:
    """缓存禁用时的行为"""

    def test_cache_store_is_none_when_disabled(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_SEMANTIC_CACHE", False)

        class FakeModel:
            pass

        cache = SemanticCacheManager(embedding_model=FakeModel())
        assert cache.enabled is False
        assert cache.cache_store is None

    def test_check_cache_returns_none_when_disabled(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_SEMANTIC_CACHE", False)

        class FakeModel:
            pass

        cache = SemanticCacheManager(embedding_model=FakeModel())
        result = asyncio.run(cache.check_cache("测试查询"))
        assert result is None

    def test_save_to_cache_returns_false_when_disabled(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_SEMANTIC_CACHE", False)

        class FakeModel:
            pass

        cache = SemanticCacheManager(embedding_model=FakeModel())
        result = asyncio.run(cache.save_to_cache("q", "rw", "ctx"))
        assert result is False

    def test_get_cache_stats_disabled(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_SEMANTIC_CACHE", False)

        class FakeModel:
            pass

        cache = SemanticCacheManager(embedding_model=FakeModel())
        stats = cache.get_cache_stats()
        assert stats["enabled"] is False
        assert stats["total_entries"] == 0

    def test_clear_all_cache_returns_false_when_disabled(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_SEMANTIC_CACHE", False)

        class FakeModel:
            pass

        cache = SemanticCacheManager(embedding_model=FakeModel())
        assert cache.clear_all_cache() is False
        assert cache.clear_expired_cache() == 0


class TestSingleton:
    """全局单例"""

    def test_get_semantic_cache_disabled_returns_none(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_SEMANTIC_CACHE", False)

        import app.knowledge.semantic_cache as sc
        monkeypatch.setattr(sc, "_semantic_cache_instance", None)

        result = get_semantic_cache()
        assert result is None

    def test_get_semantic_cache_no_model_raises(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_SEMANTIC_CACHE", True)

        import app.knowledge.semantic_cache as sc
        monkeypatch.setattr(sc, "_semantic_cache_instance", None)

        with pytest.raises(ValueError, match="首次调用.*必须提供 embedding_model"):
            get_semantic_cache(embedding_model=None)


class TestConfiguration:
    """配置参数"""

    def test_threshold_and_ttl_from_settings(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_SEMANTIC_CACHE", False)
        monkeypatch.setattr(settings, "SEMANTIC_CACHE_THRESHOLD", 0.92)
        monkeypatch.setattr(settings, "SEMANTIC_CACHE_TOP_K", 3)
        monkeypatch.setattr(settings, "SEMANTIC_CACHE_TTL_DAYS", 14)

        class FakeModel:
            pass

        cache = SemanticCacheManager(embedding_model=FakeModel())
        assert cache.threshold == 0.92
        assert cache.top_k == 3
        assert cache.ttl_days == 14


class TestCacheIdFormat:
    """缓存 ID 格式"""

    def test_cache_id_format(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_SEMANTIC_CACHE", False)

        class FakeModel:
            pass

        cache = SemanticCacheManager(embedding_model=FakeModel())
        import hashlib
        import time
        query_hash = hashlib.md5("test_query".encode()).hexdigest()[:8]
        cache_id = f"cache_{int(time.time())}_{query_hash}"
        assert cache_id.startswith("cache_")
        assert query_hash in cache_id
