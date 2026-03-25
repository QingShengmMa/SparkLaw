"""
计算器工厂 — 根据 calcType 动态实例化对应策略类
"""
from __future__ import annotations
from typing import Any, Dict
from .base import BaseCalculator, CalcResponse
from .labor_compensation import LaborCompensationCalculator
from .litigation_fee import LitigationFeeCalculator
from .lpr_interest import LprInterestCalculator
from .work_injury import WorkInjuryCalculator
from .traffic_accident import TrafficAccidentCalculator
from .personal_injury import PersonalInjuryCalculator
from .divorce_property import DivorcePropertyCalculator
from .lawyer_fee import LawyerFeeCalculator
from .property_preservation import PropertyPreservationCalculator
from .notary_fee import NotaryFeeCalculator
from .arbitration_fee import ArbitrationFeeCalculator
from .default_penalty import DefaultPenaltyCalculator
from .loan_interest import LoanInterestCalculator
from .unpaid_wages import UnpaidWagesCalculator

_REGISTRY: Dict[str, type[BaseCalculator]] = {
    "labor_compensation":    LaborCompensationCalculator,
    "litigation_fee":        LitigationFeeCalculator,
    "lpr_interest":          LprInterestCalculator,
    "work_injury":            WorkInjuryCalculator,
    "traffic_accident":       TrafficAccidentCalculator,
    "personal_injury":        PersonalInjuryCalculator,
    "divorce_property":       DivorcePropertyCalculator,
    "lawyer_fee":             LawyerFeeCalculator,
    "property_preservation":  PropertyPreservationCalculator,
    "notary_fee":             NotaryFeeCalculator,
    "arbitration_fee":        ArbitrationFeeCalculator,
    "default_penalty":        DefaultPenaltyCalculator,
    "loan_interest":          LoanInterestCalculator,
    "unpaid_wages":           UnpaidWagesCalculator,
}


class CalculatorFactory:
    """根据 calcType 字符串实例化并调用对应计算器策略类"""

    @staticmethod
    def calculate(calc_type: str, params: Dict[str, Any]) -> CalcResponse:
        cls = _REGISTRY.get(calc_type)
        if cls is None:
            raise ValueError(f"未知的 calcType: {calc_type}。支持的类型: {list(_REGISTRY.keys())}")
        return cls().calculate(params)

    @staticmethod
    def supported_types() -> list[str]:
        return list(_REGISTRY.keys())
