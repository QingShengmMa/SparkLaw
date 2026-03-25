"""
欠薪补偿计算器
依据：《劳动合同法》第82条（未签合同双倍工资）、第44条（带薪年休假300%）
《职工带薪年休假条例》（2007）
"""
from __future__ import annotations
from typing import Any, Dict
from .base import BaseCalculator, CalcResponse


class UnpaidWagesCalculator(BaseCalculator):

    def calculate(self, params: Dict[str, Any]) -> CalcResponse:
        monthly_salary: float = float(params.get("monthly_salary", 0))
        months_no_contract: float = float(params.get("months_no_contract", 0))  # 未签合同月数
        unused_annual_leave: float = float(params.get("unused_annual_leave", 0))  # 未休年假天数
        years_worked: float = float(params.get("years_worked", 1))
        arrears_months: float = float(params.get("arrears_months", 0))  # 拖欠工资月数

        if monthly_salary <= 0:
            raise ValueError("月工资必须大于0")

        # 日工资 = 月工资 / 21.75（法定工作日）
        daily_wage = monthly_salary / 21.75

        breakdown = []
        total = 0.0

        # 未签劳动合同二倍工资差额（第2-13个月，最多11个月）
        if months_no_contract > 0:
            capped_months = min(months_no_contract, 11)
            double_salary_diff = monthly_salary * capped_months  # 差额部分
            breakdown.append(self._b(
                f"未签合同二倍工资差额（{capped_months}月 × 月薪，最多11月）",
                double_salary_diff,
            ))
            total += double_salary_diff

        # 带薪年休假未休折算（300%日工资，扣除已支付100%，实补200%）
        if unused_annual_leave > 0:
            # 年假天数上限
            if years_worked < 10:
                annual_leave_cap = 5
            elif years_worked < 20:
                annual_leave_cap = 10
            else:
                annual_leave_cap = 15
            actual_days = min(unused_annual_leave, annual_leave_cap)
            leave_comp = daily_wage * actual_days * 2  # 额外支付200%
            breakdown.append(self._b(
                f"带薪年休假未休补偿（{actual_days}天 × 日工资{daily_wage:.2f} × 200%）",
                leave_comp,
            ))
            total += leave_comp

        # 拖欠工资本金
        if arrears_months > 0:
            arrears = monthly_salary * arrears_months
            breakdown.append(self._b(f"拖欠工资本金（{arrears_months}月）", arrears))
            # 额外赔偿金（超过15日未付，50%-100%加付赔偿，取75%估算）
            extra = arrears * 0.75
            breakdown.append(self._b("额外赔偿金（拖欠工资×75%，法院酌定50%-100%）", extra))
            total += arrears + extra

        if total == 0:
            breakdown.append(self._b("无欠薪补偿项目", 0.0))

        formula = " + ".join(b.label.split("（")[0] for b in breakdown)

        return self._ok(
            total, breakdown, formula,
            "《劳动合同法》第82条（未签合同双倍工资）、第44条（加班工资）；"
            "《职工带薪年休假条例》（2007）第5条（300%折算）；"
            "《劳动合同法》第85条（额外赔偿金50%-100%）",
            "未签合同双倍工资从第2个月起算，最多11个月；年休假天数以实际工作年限确定。",
        )
