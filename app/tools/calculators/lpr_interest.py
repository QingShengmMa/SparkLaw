"""
逾期利息计算器（LPR）— 策略类
依据：《最高人民法院关于审理民间借贷案件适用法律若干问题的规定》第 25 条
"""
from __future__ import annotations
from typing import Any, Dict
from .base import BaseCalculator, CalcResponse


class LprInterestCalculator(BaseCalculator):
    """逾期利息计算器（正常利息 + LPR×1.5 逾期利息）"""

    def calculate(self, params: Dict[str, Any]) -> CalcResponse:
        principal: float = float(params.get("principal", 0))
        months: float = float(params.get("months", 0))
        lpr_rate: float = float(params.get("lpr_rate", 3.45))

        if principal <= 0:
            raise ValueError("本金必须大于 0")
        if months <= 0:
            raise ValueError("逾期月数必须大于 0")
        if lpr_rate <= 0:
            raise ValueError("LPR 年利率必须大于 0")

        monthly_rate = lpr_rate / 100 / 12
        normal_interest = round(principal * monthly_rate * months, 2)
        overdue_interest = round(principal * monthly_rate * 1.5 * months, 2)

        breakdown = [
            self._b("本金", principal),
            self._b("LPR 年利率（%）", lpr_rate),
            self._b(f"月利率（LPR/12，%）", round(monthly_rate * 100, 6)),
            self._b("逾期月数", months),
            self._b("正常利息（按 LPR）", normal_interest),
            self._b("逾期利息（按 LPR×1.5）", overdue_interest),
        ]

        return self._ok(
            overdue_interest,
            breakdown,
            f"{principal:,.2f} × {round(monthly_rate * 100, 4):.4f}% × 1.5 × {months} 月",
            "《最高人民法院关于审理民间借贷案件适用法律若干问题的规定》第 25 条；"
            "逾期利率不超过 LPR×4 倍上限。",
            "正常利息适用合同期内，逾期利息按 LPR×1.5 倍计算。",
        )
