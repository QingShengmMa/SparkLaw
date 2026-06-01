"""
测试 HybridMemoryManager — 实体提取 / 短期窗口 / 摘要记忆 / 集合命名
"""

import pytest
from app.core.memory_manager import HybridMemoryManager


class TestEntityExtraction:
    """实体提取单元测试"""

    def test_extract_salary_from_chinese_text(self):
        mgr = HybridMemoryManager(short_term_rounds=3)
        entities = mgr.extract_entities("我月薪8000元，被公司辞退了")
        assert entities["monthly_salary"] == 8000

    def test_extract_salary_with_wan(self):
        mgr = HybridMemoryManager(short_term_rounds=3)
        entities = mgr.extract_entities("工资12000块人民币")
        assert entities["monthly_salary"] == 12000

    def test_extract_city(self):
        mgr = HybridMemoryManager(short_term_rounds=3)
        for city in ["北京", "上海", "深圳", "杭州", "成都"]:
            entities = mgr.extract_entities(f"我在{city}上班")
            assert entities["city"] == city

    def test_extract_dispute_type_dismissal(self):
        mgr = HybridMemoryManager(short_term_rounds=3)
        entities = mgr.extract_entities("公司违法解除我的劳动合同")
        assert entities["dispute_type"] == "违法解除"

    def test_extract_dispute_type_arrears(self):
        mgr = HybridMemoryManager(short_term_rounds=3)
        entities = mgr.extract_entities("老板拖欠工资不给")
        assert entities["dispute_type"] == "工资拖欠"

    def test_extract_dispute_type_arbitration(self):
        mgr = HybridMemoryManager(short_term_rounds=3)
        entities = mgr.extract_entities("我去劳动仲裁委申请仲裁")
        assert entities["dispute_type"] == "劳动仲裁"

    def test_extract_dispute_type_non_compete(self):
        mgr = HybridMemoryManager(short_term_rounds=3)
        entities = mgr.extract_entities("竞业限制协议是否有效")
        assert entities["dispute_type"] == "竞业限制"

    def test_extract_empty_input(self):
        mgr = HybridMemoryManager(short_term_rounds=3)
        entities = mgr.extract_entities("")
        assert entities["monthly_salary"] is None
        assert entities["city"] is None
        assert entities["dispute_type"] is None


class TestShortTermWindow:
    """短期记忆滑动窗口测试"""

    def test_keeps_last_n_rounds(self):
        mgr = HybridMemoryManager(short_term_rounds=3)
        history = []
        for idx in range(5):
            history.append({"role": "user", "content": f"q{idx}"})
            history.append({"role": "assistant", "content": f"a{idx}"})

        result = mgr.get_short_term_messages(history)
        assert len(result) == 6  # 3 rounds × 2 messages
        assert result[0]["content"] == "q2"
        assert result[-1]["content"] == "a4"

    def test_history_shorter_than_window(self):
        mgr = HybridMemoryManager(short_term_rounds=10)
        history = [
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
        ]
        result = mgr.get_short_term_messages(history)
        assert len(result) == 2


class TestSummaryStore:
    """摘要存储测试"""

    def test_get_summary_returns_empty_for_new_session(self):
        mgr = HybridMemoryManager(short_term_rounds=5)
        assert mgr.get_summary("unknown_session") == ""

    def test_can_store_and_retrieve_summary(self):
        mgr = HybridMemoryManager(short_term_rounds=5)
        mgr._summary_store["s1"] = "用户在北京，月薪15000，涉及违法解除"
        assert "北京" in mgr.get_summary("s1")
        assert "15000" in mgr.get_summary("s1")


class TestCollectionName:
    """集合命名安全校验"""

    def test_normal_session_id(self):
        mgr = HybridMemoryManager(short_term_rounds=5)
        name = mgr._collection_name("user_123")
        assert name.startswith("memory_")
        assert "user_123" in name

    def test_special_characters_are_sanitized(self):
        mgr = HybridMemoryManager(short_term_rounds=5)
        name = mgr._collection_name("user@domain.com!test")
        assert "@" not in name
        assert "!" not in name

    def test_truncates_long_session_ids(self):
        mgr = HybridMemoryManager(short_term_rounds=5)
        long_id = "a" * 100
        name = mgr._collection_name(long_id)
        assert len(name) <= 60
