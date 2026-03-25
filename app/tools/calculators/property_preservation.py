"""
财产保全费计算器
依据：《诉讼费用交纳办法》（2007）第29条
最高收费不超过 5000 元
"""
from __future__ import annotations
from typing import Any, Dict
from .base import BaseCalculator, CalcResponse


class PropertyPreservationCalculator(BaseCalculator):
    """财产保全费计算器"""

    def calculate(self, params: Dict[str, Any]) -> CalcResponse:
        amount: float = float(params.get("claim_amount", 0))
        if amount <= 0:
            raise ValueError("申请保全金额必须大于0")

        breakdown = []
        fee = 0.0

        if amount <= 1_000:
            fee = 30.0
            breakdown.append(self._b("1000元以下（固定30元）", 30.0))
        elif amount <= 10_000:
            seg = amount - 1_000
            part = seg * 0.01
            fee = 30.0 + part
            breakdown.append(self._b("1000元以下部分", 30.0))
            breakdown.append(self._b(f"1000-1万元部分（1%）", part))
        elif amount <= 100_000:
            part1 = 9_000 * 0.01  # 90
            part2 = (amount - 10_000) * 0.005
            fee = 30 + part1 + part2
            breakdown.append(self._b("1000元以下部分", 30.0))
            breakdown.append(self._b("1千-1万部分（1%）", part1))
            breakdown.append(self._b(f"1万-10万部分（0.5%）", part2))
        elif amount <= 1_000_000:
            part1 = 30 + 90 + 450  # 570
            part2 = (amount - 100_000) * 0.001
            fee = part1 + part2
            breakdown.append(self._b("10万以内部分", part1))
            breakdown.append(self._b(f"10万-100万部分（0.1%）", part2))
        else:
            part1 = 30 + 90 + 450 + 900  # 1470
            part2 = (amount - 1_000_000) * 0.0005
            fee = part1 + part2
            breakdown.append(self._b("100万以内部分", part1))
            breakdown.append(self._b(f"100万以上部分（0.05%）", part2))

        # 法定上限 5000 元
        if fee > 5000:
            breakdown.append(self._b("适用法定上限封顶", 5000 - fee))
            fee = 5000.0

        return self._ok(
            fee, breakdown,
            f"申请保全金额 {amount:,.0f} 元，阶梯计算（上限5000元）",
            "《诉讼费用交纳办法》（2007年国务院令第481号）第29条",
            "财产保全费在申请保全时预交，最高不超过5000元。",
        )
