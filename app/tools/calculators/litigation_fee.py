"""
诉讼费速算计算器 — 策略类
依据：《诉讼费用交纳办法》（2006 国务院令第 481 号）第 13 条
"""
from __future__ import annotations
from typing import Any, Dict
from .base import BaseCalculator, CalcResponse, BreakdownItem


class LitigationFeeCalculator(BaseCalculator):
    """诉讼费（案件受理费）阶梯累进计算器"""

    def calculate(self, params: Dict[str, Any]) -> CalcResponse:
        claim_amount: float = float(params.get("claim_amount", 0))

        if claim_amount <= 0:
            raise ValueError("诉讼标的金额必须大于 0")

        a = claim_amount
        if a <= 10_000:
            fee = 50.0
        elif a <= 100_000:
            fee = 50 + (a - 10_000) * 0.03
        elif a <= 200_000:
            fee = 2_750 + (a - 100_000) * 0.02
        elif a <= 500_000:
            fee = 4_750 + (a - 200_000) * 0.015
        elif a <= 1_000_000:
            fee = 9_250 + (a - 500_000) * 0.01
        elif a <= 2_000_000:
            fee = 14_250 + (a - 1_000_000) * 0.009
        else:
            fee = 23_250 + (a - 2_000_000) * 0.007

        breakdown: list[BreakdownItem] = []
        if a <= 10_000:
            breakdown.append(self._b("1 万元以内（最低 50 元）", 50.0))
        else:
            breakdown.append(self._b("1 万元以内", 50.0))
            if a > 10_000:
                breakdown.append(self._b("1万～10万部分（3%）", round(min(a, 100_000) - 10_000, 2) * 0.03))
            if a > 100_000:
                breakdown.append(self._b("10万～20万部分（2%）", round((min(a, 200_000) - 100_000) * 0.02, 2)))
            if a > 200_000:
                breakdown.append(self._b("20万～50万部分（1.5%）", round((min(a, 500_000) - 200_000) * 0.015, 2)))
            if a > 500_000:
                breakdown.append(self._b("50万～100万部分（1%）", round((min(a, 1_000_000) - 500_000) * 0.01, 2)))
            if a > 1_000_000:
                breakdown.append(self._b("100万～200万部分（0.9%）", round((min(a, 2_000_000) - 1_000_000) * 0.009, 2)))
            if a > 2_000_000:
                breakdown.append(self._b("200万以上部分（0.7%）", round((a - 2_000_000) * 0.007, 2)))

        return self._ok(
            round(fee, 2),
            breakdown,
            f"阶梯累进计算，标的额 {a:,.0f} 元",
            "《诉讼费用交纳办法》（2006 国务院令第 481 号）第 13 条",
            "申请财产保全、鉴定、公告等费用另计；实际以法院收费通知为准。",
        )
