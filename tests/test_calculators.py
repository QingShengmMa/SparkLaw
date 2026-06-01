"""
测试全部 14 个法律计算器 + CalculatorFactory
"""

import pytest
from app.tools.calculators.factory import CalculatorFactory
from app.tools.calculators.labor_compensation import LaborCompensationCalculator
from app.tools.calculators.litigation_fee import LitigationFeeCalculator
from app.tools.calculators.lpr_interest import LprInterestCalculator
from app.tools.calculators.unpaid_wages import UnpaidWagesCalculator


# ==================== CalculatorFactory ====================


class TestCalculatorFactory:
    """计算器工厂"""

    def test_supported_types_returns_14_calculators(self):
        types = CalculatorFactory.supported_types()
        assert len(types) == 14
        assert "labor_compensation" in types
        assert "litigation_fee" in types
        assert "lpr_interest" in types
        assert "unpaid_wages" in types

    def test_unknown_calc_type_raises(self):
        with pytest.raises(ValueError, match="未知的 calcType"):
            CalculatorFactory.calculate("invalid_type", {})

    def test_factory_calculates_labor_compensation(self):
        result = CalculatorFactory.calculate("labor_compensation", {
            "monthly_salary": 10000,
            "years_worked": 3,
            "dismissal_type": "N",
        })
        assert result.success is True
        assert result.data.totalAmount > 0

    def test_factory_calculates_litigation_fee(self):
        result = CalculatorFactory.calculate("litigation_fee", {
            "claim_amount": 50000,
        })
        assert result.success is True
        assert len(result.data.breakdown) > 0

    def test_factory_calculates_lpr_interest(self):
        result = CalculatorFactory.calculate("lpr_interest", {
            "principal": 100000,
            "months": 6,
            "lpr_rate": 3.45,
        })
        assert result.success is True
        assert result.data.totalAmount > 0

    def test_factory_calculates_unpaid_wages(self):
        result = CalculatorFactory.calculate("unpaid_wages", {
            "monthly_salary": 8000,
            "months_no_contract": 6,
            "arrears_months": 2,
            "years_worked": 3,
        })
        assert result.success is True
        assert result.data.totalAmount > 0


# ==================== LaborCompensationCalculator ====================


class TestLaborCompensation:
    """劳动补偿计算器"""

    def test_n_compensation_3_years(self):
        calc = LaborCompensationCalculator()
        result = calc.calculate({
            "monthly_salary": 10000,
            "years_worked": 3,
            "dismissal_type": "N",
        })
        assert result.success is True
        assert result.data.totalAmount == 30000.0
        assert "第 47 条" in result.data.legalBasis

    def test_n1_compensation(self):
        calc = LaborCompensationCalculator()
        result = calc.calculate({
            "monthly_salary": 10000,
            "years_worked": 2,
            "dismissal_type": "N1",
        })
        assert result.success is True
        assert result.data.totalAmount == 30000.0  # (2+1) * 10000

    def test_2n_compensation(self):
        calc = LaborCompensationCalculator()
        result = calc.calculate({
            "monthly_salary": 8000,
            "years_worked": 4,
            "dismissal_type": "2N",
        })
        assert result.success is True
        assert result.data.totalAmount == 64000.0  # 2 * 4 * 8000

    def test_less_than_6_months_count_as_half(self):
        calc = LaborCompensationCalculator()
        result = calc.calculate({
            "monthly_salary": 10000,
            "years_worked": 1.3,
            "dismissal_type": "N",
        })
        # 1 年整 + 0.3 < 0.5，故补偿月数 = 1 + 0.5 = 1.5
        assert result.data.totalAmount == 15000.0

    def test_half_year_rounded_to_one(self):
        calc = LaborCompensationCalculator()
        result = calc.calculate({
            "monthly_salary": 10000,
            "years_worked": 2.5,
            "dismissal_type": "N",
        })
        # 2 年整 + 0.5 → 补偿月数 = 3
        assert result.data.totalAmount == 30000.0

    def test_over_half_year_rounded_to_one(self):
        calc = LaborCompensationCalculator()
        result = calc.calculate({
            "monthly_salary": 10000,
            "years_worked": 1.7,
            "dismissal_type": "N",
        })
        # 1 年整 + 0.7 >= 0.5 → 补偿月数 = 2
        assert result.data.totalAmount == 20000.0

    def test_zero_salary_raises(self):
        calc = LaborCompensationCalculator()
        with pytest.raises(ValueError, match="月工资必须大于 0"):
            calc.calculate({
                "monthly_salary": 0,
                "years_worked": 3,
                "dismissal_type": "N",
            })

    def test_negative_years_raises(self):
        calc = LaborCompensationCalculator()
        with pytest.raises(ValueError, match="工作年限不能为负数"):
            calc.calculate({
                "monthly_salary": 10000,
                "years_worked": -1,
                "dismissal_type": "N",
            })

    def test_invalid_dismissal_type_raises(self):
        calc = LaborCompensationCalculator()
        with pytest.raises(ValueError, match="补偿类型必须为 N、N1 或 2N"):
            calc.calculate({
                "monthly_salary": 10000,
                "years_worked": 3,
                "dismissal_type": "3N",
            })

    def test_breakdown_contains_required_fields(self):
        calc = LaborCompensationCalculator()
        result = calc.calculate({
            "monthly_salary": 10000,
            "years_worked": 1,
            "dismissal_type": "N",
        })
        labels = [b.label for b in result.data.breakdown]
        assert "月工资" in labels
        assert "补偿月数" in labels
        assert "计算金额" in labels


# ==================== LitigationFeeCalculator ====================


class TestLitigationFee:
    """诉讼费计算器"""

    def test_under_10k_flat_50(self):
        calc = LitigationFeeCalculator()
        result = calc.calculate({"claim_amount": 5000})
        assert result.data.totalAmount == 50.0

    def test_50k_range(self):
        calc = LitigationFeeCalculator()
        result = calc.calculate({"claim_amount": 50000})
        # 50 + (50000 - 10000) * 0.03 = 50 + 1200 = 1250
        assert result.data.totalAmount == 1250.0

    def test_150k_range(self):
        calc = LitigationFeeCalculator()
        result = calc.calculate({"claim_amount": 150000})
        # 2750 + (150000 - 100000) * 0.02 = 2750 + 1000 = 3750
        assert result.data.totalAmount == 3750.0

    def test_300k_range(self):
        calc = LitigationFeeCalculator()
        result = calc.calculate({"claim_amount": 300000})
        # 4750 + (300000 - 200000) * 0.015 = 4750 + 1500 = 6250
        assert result.data.totalAmount == 6250.0

    def test_800k_range(self):
        calc = LitigationFeeCalculator()
        result = calc.calculate({"claim_amount": 800000})
        # 9250 + (800000 - 500000) * 0.01 = 9250 + 3000 = 12250
        assert result.data.totalAmount == 12250.0

    def test_1_5m_range(self):
        calc = LitigationFeeCalculator()
        result = calc.calculate({"claim_amount": 1500000})
        # 14250 + (1500000 - 1000000) * 0.009 = 14250 + 4500 = 18750
        assert result.data.totalAmount == 18750.0

    def test_over_2m_range(self):
        calc = LitigationFeeCalculator()
        result = calc.calculate({"claim_amount": 3000000})
        # 23250 + (3000000 - 2000000) * 0.007 = 23250 + 7000 = 30250
        assert result.data.totalAmount == 30250.0

    def test_zero_claim_raises(self):
        calc = LitigationFeeCalculator()
        with pytest.raises(ValueError, match="诉讼标的金额必须大于 0"):
            calc.calculate({"claim_amount": 0})

    def test_negative_claim_raises(self):
        calc = LitigationFeeCalculator()
        with pytest.raises(ValueError, match="诉讼标的金额必须大于 0"):
            calc.calculate({"claim_amount": -1000})


# ==================== LprInterestCalculator ====================


class TestLprInterest:
    """LPR 逾期利息计算器"""

    def test_basic_calculation(self):
        calc = LprInterestCalculator()
        result = calc.calculate({
            "principal": 100000,
            "months": 12,
            "lpr_rate": 3.45,
        })
        assert result.success is True
        # monthly_rate = 0.0345 / 12 = 0.002875
        # normal = 100000 * 0.002875 * 12 = 3450
        # overdue = 100000 * 0.002875 * 1.5 * 12 = 5175
        assert result.data.totalAmount == 5175.0

    def test_zero_principal_raises(self):
        calc = LprInterestCalculator()
        with pytest.raises(ValueError, match="本金必须大于 0"):
            calc.calculate({"principal": 0, "months": 6, "lpr_rate": 3.45})

    def test_zero_months_raises(self):
        calc = LprInterestCalculator()
        with pytest.raises(ValueError, match="逾期月数必须大于 0"):
            calc.calculate({"principal": 10000, "months": 0, "lpr_rate": 3.45})

    def test_zero_lpr_raises(self):
        calc = LprInterestCalculator()
        with pytest.raises(ValueError, match="LPR 年利率必须大于 0"):
            calc.calculate({"principal": 10000, "months": 6, "lpr_rate": 0})

    def test_breakdown_has_6_items(self):
        calc = LprInterestCalculator()
        result = calc.calculate({
            "principal": 50000,
            "months": 3,
            "lpr_rate": 3.85,
        })
        assert len(result.data.breakdown) == 6


# ==================== UnpaidWagesCalculator ====================


class TestUnpaidWages:
    """欠薪补偿计算器"""

    def test_no_contract_double_salary(self):
        calc = UnpaidWagesCalculator()
        result = calc.calculate({
            "monthly_salary": 8000,
            "months_no_contract": 5,
            "years_worked": 1,
            "unused_annual_leave": 0,
            "arrears_months": 0,
        })
        assert result.success is True
        assert result.data.totalAmount == 40000.0  # 5 * 8000

    def test_capped_at_11_months(self):
        calc = UnpaidWagesCalculator()
        result = calc.calculate({
            "monthly_salary": 8000,
            "months_no_contract": 15,
            "years_worked": 1,
            "unused_annual_leave": 0,
            "arrears_months": 0,
        })
        assert result.data.totalAmount == 88000.0  # capped at 11 * 8000

    def test_annual_leave_compensation_under_10_years(self):
        calc = UnpaidWagesCalculator()
        result = calc.calculate({
            "monthly_salary": 10000,
            "months_no_contract": 0,
            "years_worked": 5,
            "unused_annual_leave": 6,
            "arrears_months": 0,
        })
        # cap = 5 天, daily = 10000/21.75 ≈ 459.77
        # comp = 5 * 459.77 * 2 ≈ 4597.70
        assert result.data.totalAmount > 0

    def test_annual_leave_capped_by_years(self):
        calc = UnpaidWagesCalculator()
        result = calc.calculate({
            "monthly_salary": 10000,
            "months_no_contract": 0,
            "years_worked": 8,
            "unused_annual_leave": 20,
            "arrears_months": 0,
        })
        # cap = 5 (< 10 years), daily ≈ 459.77
        # comp = 5 * 459.77 * 2 ≈ 4597.70
        assert result.data.totalAmount < 10000  # capped at 5 days

    def test_annual_leave_10_to_20_years(self):
        calc = UnpaidWagesCalculator()
        result = calc.calculate({
            "monthly_salary": 10000,
            "months_no_contract": 0,
            "years_worked": 15,
            "unused_annual_leave": 20,
            "arrears_months": 0,
        })
        # cap = 10 (10-20 years), daily ≈ 459.77
        # comp = 10 * 459.77 * 2 = 9195.40
        assert 9000 <= result.data.totalAmount <= 9200

    def test_annual_leave_over_20_years(self):
        calc = UnpaidWagesCalculator()
        result = calc.calculate({
            "monthly_salary": 10000,
            "months_no_contract": 0,
            "years_worked": 25,
            "unused_annual_leave": 20,
            "arrears_months": 0,
        })
        # cap = 15, daily ≈ 459.77
        # comp = 15 * 459.77 * 2 = 13793.10
        assert 13700 <= result.data.totalAmount <= 13800

    def test_arrears_with_penalty(self):
        calc = UnpaidWagesCalculator()
        result = calc.calculate({
            "monthly_salary": 10000,
            "months_no_contract": 0,
            "years_worked": 1,
            "unused_annual_leave": 0,
            "arrears_months": 3,
        })
        # arrears = 30000, extra = 30000 * 0.75 = 22500
        assert result.data.totalAmount == 52500.0

    def test_zero_salary_raises(self):
        calc = UnpaidWagesCalculator()
        with pytest.raises(ValueError, match="月工资必须大于0"):
            calc.calculate({
                "monthly_salary": 0,
                "months_no_contract": 1,
            })

    def test_no_claims_returns_zero(self):
        calc = UnpaidWagesCalculator()
        result = calc.calculate({
            "monthly_salary": 8000,
            "months_no_contract": 0,
            "years_worked": 1,
            "unused_annual_leave": 0,
            "arrears_months": 0,
        })
        assert result.success is True
        assert result.data.totalAmount == 0.0
