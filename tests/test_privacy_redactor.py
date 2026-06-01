"""
测试 PrivacyRedactor — 手机号 / 身份证号脱敏
"""

from app.guardrails.privacy_redactor import PrivacyRedactor


class TestPhoneRedaction:
    """手机号脱敏"""

    def test_redact_standard_mobile(self):
        redactor = PrivacyRedactor()
        result = redactor.redact("联系电话：13812345678，请核实")
        assert "13812345678" not in result
        assert "[手机号已脱敏]" in result

    def test_redact_multiple_phones(self):
        redactor = PrivacyRedactor()
        result = redactor.redact("原告13900001111，被告15900002222")
        assert result.count("[手机号已脱敏]") == 2

    def test_redact_various_carriers(self):
        redactor = PrivacyRedactor()
        for phone in ["13312345678", "15312345678", "18812345678", "17012345678"]:
            result = redactor.redact(phone)
            assert "[手机号已脱敏]" in result

    def test_preserves_non_phone_numbers(self):
        redactor = PrivacyRedactor()
        result = redactor.redact("金额50000元，电话不详")
        assert "50000" in result


class TestIdCardRedaction:
    """身份证号脱敏"""

    def test_redact_18_digit_id(self):
        redactor = PrivacyRedactor()
        result = redactor.redact("身份证号：110101199003074519")
        assert "110101199003074519" not in result
        assert "[手机号已脱敏]" in result or "[证件号已脱敏]" in result

    def test_redact_id_with_X_suffix(self):
        redactor = PrivacyRedactor()
        result = redactor.redact("证件：11010119900307451X")
        assert "[手机号已脱敏]" in result or "[证件号已脱敏]" in result

    def test_redact_id_with_lowercase_x(self):
        redactor = PrivacyRedactor()
        result = redactor.redact("证件：11010119900307451x")
        assert "[手机号已脱敏]" in result or "[证件号已脱敏]" in result


class TestCombinedRedaction:
    """同时脱敏多种信息"""

    def test_redact_phone_and_id_together(self):
        redactor = PrivacyRedactor()
        result = redactor.redact(
            "张三，手机13812345678，身份证110101199003074519"
        )
        assert "[手机号已脱敏]" in result
        assert "张三" in result  # 姓名暂不脱敏
        assert "13812345678" not in result

    def test_empty_text(self):
        redactor = PrivacyRedactor()
        assert redactor.redact("") == ""

    def test_no_pii(self):
        redactor = PrivacyRedactor()
        result = redactor.redact("合同第三条：违约责任由双方协商确定。")
        assert result == "合同第三条：违约责任由双方协商确定。"
