"""
测试 HallucinationGuard — 法条引用幻觉检测 / 违规异常 / 兼容旧接口
"""

import pytest
from app.guardrails.hallucination_guard import (
    HallucinationGuard,
    GuardrailViolationError,
    GuardrailCheckResult,
)


class TestCitationExtraction:
    """法条引用提取"""

    def test_extract_single_citation(self):
        guard = HallucinationGuard()
        cited = guard._extract_cited_laws("根据 [法条:law_1] 规定")
        assert cited == ["law_1"]

    def test_extract_multiple_citations(self):
        guard = HallucinationGuard()
        cited = guard._extract_cited_laws("[法条:law_1] 和 [法条:law_3] 均适用")
        assert cited == ["law_1", "law_3"]

    def test_extract_deduplicates(self):
        guard = HallucinationGuard()
        cited = guard._extract_cited_laws("[法条:law_1] 再次引用 [法条:law_1]")
        assert cited == ["law_1"]

    def test_no_citations_returns_empty(self):
        guard = HallucinationGuard()
        cited = guard._extract_cited_laws("没有法条引用的普通回答")
        assert cited == []

    def test_empty_or_none_text(self):
        guard = HallucinationGuard()
        assert guard._extract_cited_laws("") == []
        assert guard._extract_cited_laws(None) == []


class TestAllowedLawIdNormalization:
    """允许法条列表标准化"""

    def test_dict_with_id(self):
        guard = HallucinationGuard()
        result = guard._normalize_allowed_law_ids([
            {"id": "law_1"}, {"id": "law_2"}
        ])
        assert set(result) == {"law_1", "law_2"}

    def test_dict_without_id_falls_back_to_index(self):
        guard = HallucinationGuard()
        result = guard._normalize_allowed_law_ids([
            {"title": "劳动合同法第47条"},
            {"title": "民法典第585条"},
        ])
        assert set(result) == {"law_1", "law_2"}

    def test_mixed_list(self):
        guard = HallucinationGuard()
        result = guard._normalize_allowed_law_ids([
            {"id": "law_1"},
            {"title": "无 id 文本"},
        ])
        assert "law_1" in result
        assert "law_2" in result

    def test_empty_returns_none(self):
        guard = HallucinationGuard()
        assert guard._normalize_allowed_law_ids([]) == []


class TestHallucinationCheck:
    """幻觉检测核心逻辑"""

    def test_all_citations_valid(self):
        guard = HallucinationGuard()
        result = guard.check_hallucination(
            "根据 [法条:law_1] 和 [法条:law_2]",
            [{"id": "law_1"}, {"id": "law_2"}, {"id": "law_3"}],
        )
        assert result.passed is True
        assert result.violations == []

    def test_partial_violation(self):
        guard = HallucinationGuard()
        result = guard.check_hallucination(
            "[法条:law_1] [法条:law_99] [法条:law_3]",
            [{"id": "law_1"}, {"id": "law_3"}],
        )
        assert result.passed is False
        assert result.violations == ["law_99"]
        assert "仅引用当前 RAG 召回法条" in result.suggestion

    def test_no_citations_always_passes(self):
        guard = HallucinationGuard()
        result = guard.check_hallucination(
            "没有任何法条引用的回答",
            [{"id": "law_1"}],
        )
        assert result.passed is True

    def test_raises_on_violation(self):
        guard = HallucinationGuard()
        with pytest.raises(GuardrailViolationError) as exc_info:
            guard.check_hallucination(
                "[法条:law_fake]",
                [{"id": "law_1"}],
                raise_on_violation=True,
            )
        assert "law_fake" in str(exc_info.value)
        assert exc_info.value.violations == ["law_fake"]

    def test_does_not_raise_when_flag_is_false(self):
        guard = HallucinationGuard()
        result = guard.check_hallucination(
            "[法条:law_fake]",
            [{"id": "law_1"}],
            raise_on_violation=False,
        )
        assert isinstance(result, GuardrailCheckResult)
        assert result.passed is False


class TestLegacyCheckInterface:
    """兼容旧 check() 接口"""

    def test_legacy_check_returns_violations_list(self):
        guard = HallucinationGuard()
        violations = guard.check(
            "[法条:law_1] [法条:law_bad]",
            ["law_1", "law_3"],
        )
        assert violations == ["law_bad"]

    def test_legacy_check_no_violations(self):
        guard = HallucinationGuard()
        violations = guard.check(
            "[法条:law_1]",
            ["law_1", "law_2"],
        )
        assert violations == []


def test_guardrail_violation_error_stores_violations():
    err = GuardrailViolationError(
        message="检测到未命中知识库的法条",
        violations=["law_x", "law_y"],
    )
    assert err.violations == ["law_x", "law_y"]
