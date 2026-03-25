"""
自定义工具模块
为 Legal Agent 提供计算与联网检索能力
"""

from __future__ import annotations

import json
from typing import Any
from langchain_core.tools import tool
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from app.core.logger import app_logger


@tool
def calculate_labor_compensation(monthly_salary: float, working_years: float) -> str:
    """
    计算劳动争议中的经济补偿金额（N / N+1 / 2N）。

    适用场景：用户询问"违法解除赔偿金""经济补偿怎么算""N+1 是多少"等。

    参数说明：
    - monthly_salary (float): 劳动者月工资（单位：人民币元），必须为正数。
    - working_years (float): 工作年限（单位：年），可为小数。

    返回：
    - JSON 字符串，包含 compensation_months、N、N_plus_1、double_N 以及说明字段。
    """
    try:
        if monthly_salary <= 0:
            return json.dumps({"error": "monthly_salary 必须大于 0"}, ensure_ascii=False)
        if working_years < 0:
            return json.dumps({"error": "working_years 不能为负数"}, ensure_ascii=False)

        full_years = int(working_years)
        remainder = working_years - full_years
        compensation_months = float(full_years)
        if remainder >= 0.5:
            compensation_months += 1.0
        elif remainder > 0:
            compensation_months += 0.5

        n_amount = round(compensation_months * monthly_salary, 2)
        n_plus_1_amount = round((compensation_months + 1.0) * monthly_salary, 2)
        double_n_amount = round(2.0 * compensation_months * monthly_salary, 2)

        return json.dumps(
            {
                "monthly_salary": monthly_salary,
                "working_years": working_years,
                "compensation_months": compensation_months,
                "N": n_amount,
                "N_plus_1": n_plus_1_amount,
                "double_N": double_n_amount,
                "currency": "CNY",
                "notes": [
                    "N=经济补偿基数月数x月工资",
                    "N+1 常见于代通知金场景（需结合案件事实判断）",
                    "2N 常见于违法解除赔偿金场景（需结合案件事实判断）",
                ],
            },
            ensure_ascii=False,
        )
    except Exception as e:
        app_logger.error(f"calculate_labor_compensation error: {str(e)}")
        return json.dumps({"error": f"计算失败: {str(e)}"}, ensure_ascii=False)


@tool
def search_latest_legal_cases(query: str, max_results: int = 3) -> str:
    """
    检索最新法律案例与实务资讯（联网优先，失败时回退到 mock 数据）。

    适用场景：用户询问"最近判例如何裁判""最新劳动争议案例""同类案件怎么判"。

    参数说明：
    - query (str): 查询主题。
    - max_results (int): 期望返回条数，默认 3。
    """
    if not query or not query.strip():
        return "请提供有效的案例检索关键词。"

    top_k = max(1, min(max_results, 10))

    try:
        search = DuckDuckGoSearchAPIWrapper()
        enhanced_query = f"{query} 劳动争议 最新 判例 中国"
        result_text = search.run(enhanced_query)
        if result_text and result_text.strip():
            return f"联网检索结果（前 {top_k} 条线索）：\n{result_text}"
    except Exception as e:
        app_logger.warning(f"search_latest_legal_cases fallback to mock: {str(e)}")

    mock_cases: list[dict[str, Any]] = [
        {
            "title": "某地高院：违法解除劳动合同，支持 2N 赔偿",
            "summary": "法院认为用人单位未履行法定程序且证据不足，判令支付违法解除赔偿金。",
        },
        {
            "title": "某中院：绩效不达标解除争议，N+1 适用边界",
            "summary": "判决指出需证明调岗培训与考核过程合法，程序瑕疵将影响解除合法性。",
        },
        {
            "title": "某仲裁委：未签书面劳动合同的双倍工资争议",
            "summary": "确认建立劳动关系后未签合同的期间，单位应依法承担双倍工资责任。",
        },
    ]

    selected = mock_cases[:top_k]
    lines = ["联网不可用，以下为模拟案例线索："]
    for idx, item in enumerate(selected, start=1):
        lines.append(f"{idx}. {item['title']} - {item['summary']}")
    return "\n".join(lines)


def get_tools(enable_search: bool = True, enable_calculator: bool = True) -> list:
    """获取 Legal Agent 工具列表。"""
    tools = []
    if enable_calculator:
        tools.append(calculate_labor_compensation)
    if enable_search:
        tools.append(search_latest_legal_cases)
    return tools
