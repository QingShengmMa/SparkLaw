"""
违约金上限测算计算器
依据：《民法典》第585条、《最高人民法院关于审理民间借贷案件适用法律若干问题的规定》
违约金不超过实际损失的30%（过分高于损失标准）；借贷类不超过LPR×4倍年化
"""
from __future__ import annotations
from typing import Any, Dict
from .base import BaseCalculator, CalcResponse


class DefaultPenaltyCalculator(BaseCalculator):

    def calculate(self, params: Dict[str, Any]) -> CalcResponse:
        contract_amount: float = float(params.get("contract_amount", 0))
        actual_loss: float = float(params.get("actual_loss", 0))
        agreed_penalty: float = float(params.get("agreed_penalty", 0))
        lpr_rate: float = float(params.get("lpr_rate", 3.45))
        months: float = float(params.get("months", 12))

        if contract_amount <= 0:
            raise ValueError("合同金额必须大于0")

        # 最高法：约定违约金超过实际损失130%（即损失×1.3）可申请调减
        loss_cap_130 = actual_loss * 1.3 if actual_loss > 0 else 0
        # 年化24%上限（借贷类参考）
        annual_24_cap = contract_amount * 0.24 / 12 * months
        # LPR×4倍上限
        lpr4_cap = contract_amount * (lpr_rate / 100 * 4) / 12 * months

        breakdown = [
            self._b("合同金额", contract_amount),
            self._b("实际损失（估算）", actual_loss),
        ]
        if loss_cap_130 > 0:
            breakdown.append(self._b("损失×130%（法院调减基准）", loss_cap_130))
        breakdown.append(self._b(f"年化24%上限（{months}个月）", annual_24_cap))
        breakdown.append(self._b(f"LPR×4倍上限（{lpr_rate}%×4，{months}个月）", lpr4_cap))

        if agreed_penalty > 0:
            breakdown.append(self._b("约定违约金", agreed_penalty))
            if loss_cap_130 > 0 and agreed_penalty > loss_cap_130:
                breakdown.append(self._b("超出损失130%部分（可申请调减）", agreed_penalty - loss_cap_130))

        recommended = min(x for x in [loss_cap_130, annual_24_cap, lpr4_cap] if x > 0) if any(
            x > 0 for x in [loss_cap_130, annual_24_cap, lpr4_cap]) else annual_24_cap

        return self._ok(
            recommended, breakdown,
            f"min(损失×130%, 年化24%, LPR×4) = {recommended:,.2f}",
            "《民法典》第585条；《最高人民法院关于审理民间借贷案件适用法律若干问题的规定》第25条",
            "违约金超过损失130%时对方可申请法院调减；借贷类受LPR×4倍保护上限约束。",
        )
