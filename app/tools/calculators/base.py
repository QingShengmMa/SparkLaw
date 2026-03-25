"""
计算器基础接口 — 所有策略类必须实现 calculate() 方法
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from pydantic import BaseModel


class BreakdownItem(BaseModel):
    label: str
    amount: float


class CalcData(BaseModel):
    totalAmount: float
    breakdown: List[BreakdownItem]
    formula: str
    legalBasis: str
    note: str = ""


class CalcResponse(BaseModel):
    success: bool = True
    data: CalcData


class BaseCalculator(ABC):
    """所有法律计算器的抽象基类"""

    @abstractmethod
    def calculate(self, params: Dict[str, Any]) -> CalcResponse:
        """执行计算并返回标准结构"""
        ...

    @staticmethod
    def _b(label: str, amount: float) -> BreakdownItem:
        return BreakdownItem(label=label, amount=round(amount, 2))

    @staticmethod
    def _ok(total: float, breakdown: List[BreakdownItem], formula: str,
            basis: str, note: str = "") -> CalcResponse:
        return CalcResponse(
            success=True,
            data=CalcData(
                totalAmount=round(total, 2),
                breakdown=breakdown,
                formula=formula,
                legalBasis=basis,
                note=note,
            ),
        )
