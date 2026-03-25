"""
离婚财产分割预估计算器
依据：《民法典》第1087条、《最高人民法院关于适用婚姻家庭编的解释（一）》
"""
from __future__ import annotations
from typing import Any, Dict
from .base import BaseCalculator, CalcResponse


class DivorcePropertyCalculator(BaseCalculator):
    """离婚共同财产分割预估计算器"""

    def calculate(self, params: Dict[str, Any]) -> CalcResponse:
        total_joint: float = float(params.get("total_joint_property", 0))
        joint_debt: float = float(params.get("joint_debt", 0))
        fault_deduction_pct: float = float(params.get("fault_deduction_pct", 0))
        child_care_bonus_pct: float = float(params.get("child_care_bonus_pct", 0))
        is_fault_party: bool = str(params.get("is_fault_party", "false")).lower() == "true"

        if total_joint < 0:
            raise ValueError("共同财产总额不能为负")

        net_property = total_joint - joint_debt
        base_share = net_property / 2

        fault_deduction = base_share * (fault_deduction_pct / 100) if is_fault_party else 0
        child_bonus = base_share * (child_care_bonus_pct / 100)
        my_share = base_share - fault_deduction + child_bonus
        other_share = net_property - my_share

        breakdown = [
            self._b("共同财产总额", total_joint),
            self._b("共同债务", joint_debt),
            self._b("净共同财产", net_property),
            self._b("基础各半份额", base_share),
        ]
        if fault_deduction > 0:
            breakdown.append(self._b(f"过错方扣减（{fault_deduction_pct}%）", -fault_deduction))
        if child_bonus > 0:
            breakdown.append(self._b(f"抚养子女补偿（{child_care_bonus_pct}%）", child_bonus))
        breakdown.append(self._b("本方预估分得", my_share))
        breakdown.append(self._b("对方预估分得", other_share))

        return self._ok(
            my_share, breakdown,
            f"净财产{net_property:,.2f} / 2 ± 调整",
            "《民法典》第1087条；《最高人民法院关于适用〈中华人民共和国民法典〉婚姻家庭编的解释（一）》第76-78条",
            "离婚财产分割由法院综合考量，此处为预估参考，不作为法律依据。",
        )
