"""Legal calculators package — exports factory and all strategy classes."""
from .factory import CalculatorFactory
from .base import BaseCalculator, CalcResponse, CalcData, BreakdownItem

__all__ = ["CalculatorFactory", "BaseCalculator", "CalcResponse", "CalcData", "BreakdownItem"]
