"""
仲裁费计算器（商事仲裁）
依据：中国国际经济贸易仲裁委员会仲裁规则（2024）附件三
以及《劳动人事争议仲裁办案规则》（2017）
"""
from __future__ import annotations
from typing import Any, Dict
from .base import BaseCalculator, CalcResponse


class ArbitrationFeeCalculator(BaseCalculator):

    def calculate(self, params: Dict[str, Any]) -> CalcResponse:
        amount: float = float(params.get("claim_amount", 0))
        arb_type: str = str(params.get("arb_type", "commercial"))

        if arb_type == "labor":
            return self._ok(0.0, [self._b("劳动人事争议仲裁（免费）", 0.0)],
                "劳动仲裁免收仲裁费",
                "《劳动人事争议仲裁办案规则》（人社部令第33号）第48条",
                "劳动争议仲裁不收取费用，当事人凭申请书直接立案。")

        if amount <= 0:
            raise ValueError("争议金额必须大于0")

        boundaries = [0, 1_000_000, 2_000_000, 5_000_000, 10_000_000, 50_000_000]
        rates = [0.014, 0.009, 0.006, 0.004, 0.002, 0.001]
        labels = [
            "100万以内（1.4%）", "100万-200万部分（0.9%）",
            "200万-500万部分（0.6%）", "500万-1000万部分（0.4%）",
            "1000万-5000万部分（0.2%）", "5000万以上部分（0.1%）",
        ]

        acceptance_fee = 0.0
        breakdown = []
        for i in range(len(rates)):
            low = boundaries[i]
            high = boundaries[i + 1] if i + 1 < len(boundaries) else float("inf")
            if amount <= low:
                break
            seg = min(amount, high) - low
            seg_fee = seg * rates[i]
            breakdown.append(self._b(labels[i], seg_fee))
            acceptance_fee += seg_fee

        acceptance_fee = max(acceptance_fee, 10_000.0)
        handling_fee = acceptance_fee * 0.5
        breakdown.append(self._b("处理费（受理费×50%估算）", handling_fee))
        total = acceptance_fee + handling_fee

        return self._ok(total, breakdown,
            f"争议金额 {amount:,.0f} 元，受理费+处理费",
            "《中国国际经济贸易仲裁委员会仲裁规则》（2024）附件三",
            "处理费由仲裁庭酌定，实际以仲裁机构通知为准。")
