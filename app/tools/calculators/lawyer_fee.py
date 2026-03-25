"""
律师费计算器（北京市律师服务收费标准，全国通用参考）
依据：《北京市律师服务收费管理实施办法》（2009）阶梯标准
"""
from __future__ import annotations
from typing import Any, Dict
from .base import BaseCalculator, CalcResponse


class LawyerFeeCalculator(BaseCalculator):
    """律师费阶梯计算器（按标的额分段累计）"""

    def calculate(self, params: Dict[str, Any]) -> CalcResponse:
        amount: float = float(params.get("claim_amount", 0))
        if amount <= 0:
            raise ValueError("标的额必须大于0")

        breakdown = []
        fee = 0.0

        # 北京市律师费指导价阶梯（分段累进）
        tiers = [
            (100_000,      0.08, "10万以内（8%）"),
            (400_000,      0.06, "10万-50万部分（6%）"),
            (500_000,      0.05, "50万-100万部分（5%）"),
            (900_000,      0.04, "100万-200万部分（4%）"),
            (3_000_000,    0.03, "200万-500万部分（3%）"),
            (5_000_000,    0.02, "500万-1000万部分（2%）"),
            (float("inf"), 0.01, "1000万以上部分（1%）"),
        ]

        prev = 0.0
        caps = [100_000, 500_000, 1_000_000, 2_000_000, 5_000_000, 10_000_000]
        caps_iter = iter(caps)
        cumulative_caps = [100_000, 500_000, 1_000_000, 2_000_000, 5_000_000, 10_000_000]
        boundaries = [0] + cumulative_caps
        rates = [0.08, 0.06, 0.05, 0.04, 0.03, 0.02, 0.01]
        labels = [
            "10万以内（8%）", "10万-50万部分（6%）", "50万-100万部分（5%）",
            "100万-200万部分（4%）", "200万-500万部分（3%）",
            "500万-1000万部分（2%）", "1000万以上部分（1%）",
        ]

        for i, (low, high) in enumerate(zip(boundaries[:-1], boundaries[1:] + [float("inf")])):
            if amount <= low:
                break
            seg = min(amount, boundaries[i + 1] if i + 1 < len(boundaries) else amount) - low
            if seg <= 0:
                continue
            seg_fee = seg * rates[i]
            breakdown.append(self._b(labels[i], seg_fee))
            fee += seg_fee

        # 最低收费 1000 元
        fee = max(fee, 1000.0)
        formula = f"标的额 {amount:,.0f} 元，阶梯累进计算"

        return self._ok(
            fee, breakdown, formula,
            "《北京市律师服务收费管理实施办法》（2009）；"
            "《国家发展改革委、司法部关于进一步规范律师服务收费的意见》（2022）",
            "律师费为市场调节价，实际收费由委托方与律师协商确定，此为指导参考价。",
        )
