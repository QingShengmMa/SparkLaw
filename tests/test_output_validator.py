"""
测试 OutputValidator — 判决结果结构化校验
"""

from app.guardrails.output_validator import OutputValidator


class TestVerdictValidation:
    """判决结果校验"""

    def test_valid_verdict(self):
        validator = OutputValidator()
        payload = {
            "plaintiff_win_rate": 60,
            "defendant_win_rate": 40,
            "verdict_text": "原告部分胜诉，被告赔偿各项损失共计15万元。",
        }
        assert validator.validate_verdict(payload) is True

    def test_win_rates_sum_to_100(self):
        validator = OutputValidator()
        assert validator.validate_verdict({
            "plaintiff_win_rate": 80,
            "defendant_win_rate": 20,
            "verdict_text": "原告胜诉。",
        }) is True

    def test_win_rates_not_summing_to_100(self):
        validator = OutputValidator()
        assert validator.validate_verdict({
            "plaintiff_win_rate": 60,
            "defendant_win_rate": 60,
            "verdict_text": "双方各有理据。",
        }) is False

    def test_missing_required_field(self):
        validator = OutputValidator()
        assert validator.validate_verdict({
            "plaintiff_win_rate": 70,
            "defendant_win_rate": 30,
        }) is False  # 缺少 verdict_text

    def test_empty_payload(self):
        validator = OutputValidator()
        assert validator.validate_verdict({}) is False

    def test_non_integer_win_rates(self):
        validator = OutputValidator()
        assert validator.validate_verdict({
            "plaintiff_win_rate": 60.5,
            "defendant_win_rate": 39.5,
            "verdict_text": "判决如下",
        }) is False  # 要求 int 类型

    def test_extra_fields_are_ignored(self):
        validator = OutputValidator()
        payload = {
            "plaintiff_win_rate": 50,
            "defendant_win_rate": 50,
            "verdict_text": "调解结案。",
            "extra_field": "ignored",
            "another": 123,
        }
        assert validator.validate_verdict(payload) is True

    def test_zero_and_100(self):
        validator = OutputValidator()
        assert validator.validate_verdict({
            "plaintiff_win_rate": 0,
            "defendant_win_rate": 100,
            "verdict_text": "原告全部败诉。",
        }) is True

    def test_negative_win_rate_passes_current_impl(self):
        validator = OutputValidator()
        result = validator.validate_verdict({
            "plaintiff_win_rate": -10,
            "defendant_win_rate": 110,
            "verdict_text": "...",
        })
        # 当前实现仅校验字段存在 + sum == 100 + int 类型，不校验符号
        assert result is True
