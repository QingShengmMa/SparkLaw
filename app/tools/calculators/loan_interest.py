"""
民间借贷利息计算器
依据：《最高人民法院关于审理民间借贷案件适用法律若干问题的规定》（2021修订）
最高保护利率：LPR×4倍；超出部分不受法律保护
"""
from __future__ import annotations
from typing import Any, Dict
from .base import BaseCalculator, CalcResponse


class LoanInterestCalculator(BaseCalculator):

    def calculate(self, params: Dict[str, Any]) -> CalcResponse:
        principal: float = float(params.get("principal", 0))
        annual_rate: float = float(params.get("annual_rate", 0))  # 约定年利率%
        months: float = float(params.get("months", 0))
        lpr_rate: float = float(params.get("lpr_rate", 3.45))  # 当期LPR

        if principal <= 0:
            raise ValueError("本金必须大于0")
        if months <= 0:
            raise ValueError("借贷月数必须大于0")

        lpr4_rate = lpr_rate * 4  # LPR×4倍年化
        protected_rate = min(annual_rate, lpr4_rate) if annual_rate > 0 else lpr_rate

        monthly_rate = protected_rate / 100 / 12
        protected_interest = principal * monthly_rate * months

        agreed_interest = principal * (annual_rate / 100 / 12) * months if annual_rate > 0 else 0
        excess = max(0, agreed_interest - protected_interest)

        # 折息转换：年利率 → 月利率 → 日利率
        daily_rate = protected_rate / 100 / 365

        breakdown = [
            self._b("本金", principal),
            self._b(f"当期LPR年利率（{lpr_rate}%）", lpr_rate),
            self._b(f"LPR×4倍保护上限（{lpr4_rate:.2f}%）", lpr4_rate),
            self._b(f"实际适用年利率（{protected_rate:.2f}%）", protected_rate),
            self._b(f"受法律保护利息（{months}个月）", protected_interest),
        ]
        if excess > 0:
            breakdown.append(self._b(f"约定利息（{annual_rate}%）", agreed_interest))
            breakdown.append(self._b("超出保护上限不受法律保护部分", excess))
        breakdown.append(self._b(f"日利率（{daily_rate:.6f}）", daily_rate))

        return self._ok(
            protected_interest, breakdown,
            f"{principal:,.2f} × {protected_rate:.2f}% / 12 × {months}月",
            "《最高人民法院关于审理民间借贷案件适用法律若干问题的规定》（2021修订）第25条："
            "借贷利率不超过LPR×4倍部分受法律保护",
            "超出LPR×4倍的利息约定无效，借款人可主张返还。",
        )
