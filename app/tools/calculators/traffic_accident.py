"""
交通事故赔偿计算器
依据：《最高人民法院关于审理人身损害赔偿案件适用法律若干问题的解释》（2022修订）
"""
from __future__ import annotations
from typing import Any, Dict
from .base import BaseCalculator, CalcResponse

# 伤残系数（1-10级，对应1.0-0.1）
_DISABILITY_COEFF = {
    1: 1.0, 2: 0.9, 3: 0.8, 4: 0.7, 5: 0.6,
    6: 0.5, 7: 0.4, 8: 0.3, 9: 0.2, 10: 0.1,
}


class TrafficAccidentCalculator(BaseCalculator):
    """交通事故人身损害赔偿计算器"""

    def calculate(self, params: Dict[str, Any]) -> CalcResponse:
        medical_cost: float = float(params.get("medical_cost", 0))
        lost_work_days: float = float(params.get("lost_work_days", 0))
        daily_income: float = float(params.get("daily_income", 0))
        nursing_days: float = float(params.get("nursing_days", 0))
        disability_level: int = int(params.get("disability_level", 0))
        area_annual_income: float = float(params.get("area_annual_income", 0))
        is_urban: bool = str(params.get("is_urban", "true")).lower() == "true"
        years: int = int(params.get("compensation_years", 20))

        breakdown = []

        # 医疗费
        if medical_cost > 0:
            breakdown.append(self._b("医疗费", medical_cost))

        # 误工费
        lost_work_fee = daily_income * lost_work_days
        if lost_work_fee > 0:
            breakdown.append(self._b(f"误工费（{lost_work_days}天 × 日收入{daily_income:.2f}元）", lost_work_fee))

        # 护理费（按当地护工价格，默认200元/天）
        nursing_rate = float(params.get("nursing_daily_rate", 200))
        nursing_fee = nursing_days * nursing_rate
        if nursing_fee > 0:
            breakdown.append(self._b(f"护理费（{nursing_days}天 × {nursing_rate:.0f}元/天）", nursing_fee))

        # 残疾赔偿金
        disability_comp = 0.0
        if disability_level > 0 and area_annual_income > 0:
            coeff = _DISABILITY_COEFF.get(disability_level, 0)
            disability_comp = area_annual_income * years * coeff
            label = "城镇" if is_urban else "农村"
            breakdown.append(self._b(
                f"残疾赔偿金（{label}年收入{area_annual_income:,.0f}元 × {years}年 × {coeff:.1f}系数）",
                disability_comp,
            ))

        # 精神损害抚慰金（一般为残疾赔偿金的10-30%，取15%估算）
        mental_comp = disability_comp * 0.15 if disability_level > 0 else 0
        if mental_comp > 0:
            breakdown.append(self._b("精神损害抚慰金（残疾赔偿金×15%，法院酌定）", mental_comp))

        total = medical_cost + lost_work_fee + nursing_fee + disability_comp + mental_comp
        if total == 0:
            total = medical_cost

        formula = " + ".join([f"{b.label.split('（')[0]}" for b in breakdown])

        return self._ok(
            total, breakdown, formula,
            "《最高人民法院关于审理人身损害赔偿案件适用法律若干问题的解释》（2022修订）第6-12条；"
            "《道路交通事故受伤人员伤残评定》GB 18667-2002",
            "精神损害抚慰金由法院酌定，赔偿标准因省市而异，具体以当地上年度城镇/农村居民人均可支配收入为准。",
        )
