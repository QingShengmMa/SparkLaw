"""
一般人身损害赔偿计算器
依据：《最高人民法院关于审理人身损害赔偿案件适用法律若干问题的解释》（2022修订）
"""
from __future__ import annotations
from typing import Any, Dict
from .base import BaseCalculator, CalcResponse


class PersonalInjuryCalculator(BaseCalculator):
    """一般人身侵权损害赔偿计算器"""

    def calculate(self, params: Dict[str, Any]) -> CalcResponse:
        medical_cost: float = float(params.get("medical_cost", 0))
        lost_work_days: float = float(params.get("lost_work_days", 0))
        daily_income: float = float(params.get("daily_income", 0))
        nursing_days: float = float(params.get("nursing_days", 0))
        nursing_daily_rate: float = float(params.get("nursing_daily_rate", 200))
        transport_cost: float = float(params.get("transport_cost", 0))
        hospitalization_days: float = float(params.get("hospitalization_days", 0))
        # 住院伙食补助：参照国家机关一般工作人员标准，默认100元/天
        hospital_meal_rate: float = float(params.get("hospital_meal_rate", 100))

        breakdown = []

        if medical_cost > 0:
            breakdown.append(self._b("医疗费", medical_cost))

        lost_work_fee = lost_work_days * daily_income
        if lost_work_fee > 0:
            breakdown.append(self._b(f"误工费（{lost_work_days}天 × {daily_income:.2f}元/天）", lost_work_fee))

        nursing_fee = nursing_days * nursing_daily_rate
        if nursing_fee > 0:
            breakdown.append(self._b(f"护理费（{nursing_days}天 × {nursing_daily_rate:.0f}元/天）", nursing_fee))

        meal_subsidy = hospitalization_days * hospital_meal_rate
        if meal_subsidy > 0:
            breakdown.append(self._b(f"住院伙食补助（{hospitalization_days}天 × {hospital_meal_rate:.0f}元/天）", meal_subsidy))

        if transport_cost > 0:
            breakdown.append(self._b("交通费", transport_cost))

        total = sum(b.amount for b in breakdown)

        formula = " + ".join(b.label.split("（")[0] for b in breakdown) if breakdown else "0"

        return self._ok(
            total, breakdown, formula,
            "《最高人民法院关于审理人身损害赔偿案件适用法律若干问题的解释》（2022修订）第6-10条；"
            "《民法典》第1179条",
            "精神损害赔偿、残疾赔偿金等项目请使用交通事故专项计算器。"
            "具体金额以当地标准和法院判决为准。",
        )
