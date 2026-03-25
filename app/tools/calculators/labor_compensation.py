"""
劳动补偿计算器 — 策略类
依据：《劳动合同法》第47条（N）、第40条（N+1）、第87条（2N）
"""
from __future__ import annotations
from typing import Any, Dict
from .base import BaseCalculator, CalcResponse


class LaborCompensationCalculator(BaseCalculator):
    """劳动经济补偿金 / 赔偿金计算器（N / N+1 / 2N）"""

    def calculate(self, params: Dict[str, Any]) -> CalcResponse:
        monthly_salary: float = float(params.get("monthly_salary", 0))
        years_worked: float = float(params.get("years_worked", 0))
        dismissal_type: str = str(params.get("dismissal_type", "N1"))

        if monthly_salary <= 0:
            raise ValueError("月工资必须大于 0")
        if years_worked < 0:
            raise ValueError("工作年限不能为负数")
        if dismissal_type not in ("N", "N1", "2N"):
            raise ValueError("补偿类型必须为 N、N1 或 2N")

        full = int(years_worked)
        rem = years_worked - full
        comp_months = float(full)
        if rem >= 0.5:
            comp_months += 1.0
        elif rem > 0:
            comp_months += 0.5

        amounts = {
            "N":  round(comp_months * monthly_salary, 2),
            "N1": round((comp_months + 1) * monthly_salary, 2),
            "2N": round(2 * comp_months * monthly_salary, 2),
        }
        formulas = {
            "N":  f"{comp_months} 月 × ¥{monthly_salary:,.2f}",
            "N1": f"({comp_months}+1) 月 × ¥{monthly_salary:,.2f}",
            "2N": f"2 × {comp_months} 月 × ¥{monthly_salary:,.2f}",
        }
        basis = {
            "N":  "《劳动合同法》第 47 条",
            "N1": "《劳动合同法》第 40 条（代通知金）",
            "2N": "《劳动合同法》第 87 条（违法解除赔偿金）",
        }

        breakdown = [
            self._b("月工资", monthly_salary),
            self._b("补偿月数", comp_months),
            self._b("计算金额", amounts[dismissal_type]),
        ]

        return self._ok(
            amounts[dismissal_type],
            breakdown,
            formulas[dismissal_type],
            basis[dismissal_type],
            "月薪超当地社平工资 3 倍时按上限封顶（最多 12 个月），请以实际仲裁结果为准。",
        )
