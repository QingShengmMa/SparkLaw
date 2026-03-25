"""
工伤赔偿计算器
依据：《工伤保险条例》（2010修订）第35-37条
"""
from __future__ import annotations
from typing import Any, Dict
from .base import BaseCalculator, CalcResponse

# 一次性伤残补助金月数（1-10级）
_DISABILITY_MONTHS = {
    1: 27, 2: 25, 3: 23, 4: 21, 5: 18,
    6: 16, 7: 13, 8: 11, 9: 9, 10: 7,
}


class WorkInjuryCalculator(BaseCalculator):
    """工伤赔偿计算器（一次性伤残补助金 + 就业补助金 + 医疗补助金）"""

    def calculate(self, params: Dict[str, Any]) -> CalcResponse:
        salary: float = float(params.get("monthly_salary", 0))
        avg_salary: float = float(params.get("area_avg_salary", salary))
        level: int = int(params.get("disability_level", 10))
        medical_cost: float = float(params.get("medical_cost", 0))

        if salary <= 0:
            raise ValueError("月工资必须大于 0")
        if level < 1 or level > 10:
            raise ValueError("伤残等级必须在 1-10 级之间")

        months = _DISABILITY_MONTHS[level]
        disability_allowance = salary * months

        # 就业补助金（5-10级，劳动关系解除时适用），取 6-12 个月统筹区均工资
        employment_supplement_months = max(0, 12 - (level - 5) * 2) if level >= 5 else 0
        employment_supplement = avg_salary * employment_supplement_months if level >= 5 else 0

        # 医疗补助金（5-10级），取 6-12 个月统筹区均工资
        medical_supplement = avg_salary * employment_supplement_months if level >= 5 else 0

        total = disability_allowance + employment_supplement + medical_supplement + medical_cost

        breakdown = [
            self._b(f"一次性伤残补助金（{level}级 × {months}月 × 本人月薪）", disability_allowance),
        ]
        if level >= 5:
            breakdown.append(self._b(f"一次性就业补助金（{employment_supplement_months}月 × 统筹地区月均工资）", employment_supplement))
            breakdown.append(self._b(f"一次性医疗补助金（{employment_supplement_months}月 × 统筹地区月均工资）", medical_supplement))
        if medical_cost > 0:
            breakdown.append(self._b("医疗费", medical_cost))

        formula = (f"{salary:,.2f} × {months} 月 + 就业/医疗补助"
                   if level >= 5 else f"{salary:,.2f} × {months} 月")

        return self._ok(
            total, breakdown, formula,
            "《工伤保险条例》（国务院令第586号）第35-37条；"
            "《人力资源和社会保障部关于工伤保险待遇的规定》",
            "1-4级工伤不解除劳动关系，保留工伤保险关系，此处仅计算5-10级的一次性补助。"
            "具体金额以当地社保局核定为准。",
        )
