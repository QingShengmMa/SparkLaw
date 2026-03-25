"""
公证费计算器
依据：《公证服务收费管理办法》（2015）国家发改委、司法部
财产类民事法律行为按标的额分段
"""
from __future__ import annotations
from typing import Any, Dict
from .base import BaseCalculator, CalcResponse


class NotaryFeeCalculator(BaseCalculator):
    """公证费计算器（财产性民事法律行为）"""

    def calculate(self, params: Dict[str, Any]) -> CalcResponse:
        amount: float = float(params.get("claim_amount", 0))
        notary_type: str = str(params.get("notary_type", "property"))  # property / non_property

        if notary_type == "non_property":
            fee = 200.0
            breakdown = [self._b("非财产性公证（固定收费）", 200.0)]
            return self._ok(
                fee, breakdown, "非财产类公证固定200元",
                "《公证服务收费管理办法》（2015）第14条",
                "非财产性公证包括声明、委托、保全证据等，按件收取。",
            )

        if amount <= 0:
            raise ValueError("标的额必须大于0")

        breakdown = []
        fee = 0.0

        # 财产性公证阶梯费率
        boundaries = [0, 100_000, 500_000, 1_000_000, 5_000_000]
        rates      = [0.012, 0.006, 0.004, 0.002, 0.001]
        labels = [
            "10万以内（1.2%）", "10万-50万部分（0.6%）",
            "50万-100万部分（0.4%）", "100万-500万部分（0.2%）", "500万以上部分（0.1%）",
        ]

        for i in range(len(rates)):
            low = boundaries[i]
            high = boundaries[i + 1] if i + 1 < len(boundaries) else float("inf")
            if amount <= low:
                break
            seg = min(amount, high) - low
            seg_fee = seg * rates[i]
            breakdown.append(self._b(labels[i], seg_fee))
            fee += seg_fee

        fee = max(fee, 200.0)  # 最低200元

        return self._ok(
            fee, breakdown,
            f"标的额 {amount:,.0f} 元，阶梯累进计算（最低200元）",
            "《公证服务收费管理办法》（2015年国家发改委、司法部令）第14-16条",
            "公证费实行政府指导价，各地收费标准可能有所浮动。",
        )
