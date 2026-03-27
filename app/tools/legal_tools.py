"""
自定义工具模块
为 Legal Agent 提供计算与联网检索能力
"""

from __future__ import annotations

import json
import time
from urllib.parse import urlparse
from langchain_core.tools import tool
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from app.core.logger import app_logger


LEGAL_DOMAIN_WHITELIST = [
    "gov.cn",
    "court.gov.cn",
    "npc.gov.cn",
    "moj.gov.cn",
    "csrc.gov.cn",
    "cbirc.gov.cn",
]


def _is_preferred_legal_domain(url: str) -> bool:
    if not url:
        return False
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith(f".{d}") for d in LEGAL_DOMAIN_WHITELIST)


def _format_search_results(results: list[dict], top_k: int) -> str:
    preferred = [r for r in results if _is_preferred_legal_domain(r.get("link", ""))]
    others = [r for r in results if not _is_preferred_legal_domain(r.get("link", ""))]
    ranked = preferred + others

    if not ranked:
        return ""

    lines = []
    for idx, item in enumerate(ranked[:top_k], start=1):
        title = (item.get("title") or "未命名来源").strip()
        link = (item.get("link") or "").strip()
        snippet = (item.get("snippet") or "暂无摘要").strip()
        lines.append(f"[来源{idx}] {title} - {snippet} ({link})")
    return "\n".join(lines)


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
    started = time.perf_counter()
    args = {"monthly_salary": monthly_salary, "working_years": working_years}
    app_logger.info(f"[TOOL_AUDIT] tool_name=calculate_labor_compensation arguments={args} status=start")
    status = "success"
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
        status = "failed"
        app_logger.error(f"calculate_labor_compensation error: {str(e)}")
        return json.dumps({"error": f"计算失败: {str(e)}"}, ensure_ascii=False)
    finally:
        latency = int((time.perf_counter() - started) * 1000)
        app_logger.info(
            f"[TOOL_AUDIT] tool_name=calculate_labor_compensation arguments={args} latency={latency}ms status={status}"
        )


@tool
def search_latest_legal_cases(query: str, max_results: int = 5) -> str:
    """
    联网搜索与用户问题直接相关的最新法律资讯、法规条文及司法判例。

    适用场景：用户询问相关法律规定、最新判例、司法解释、监管政策等。
    使用用户原始问题关键词检索，不要生构或限定领域。

    参数说明：
    - query (str): 查询关键词，应直接来自用户问题。
    - max_results (int): 期望返回条数，默认 5。
    """
    started = time.perf_counter()
    args = {"query": query, "max_results": max_results}
    app_logger.info(f"[TOOL_AUDIT] tool_name=search_latest_legal_cases arguments={args} status=start")
    status = "success"

    retries = 3

    try:
        if not query or not query.strip():
            status = "failed"
            return "请提供有效的检索关键词。"

        top_k = max(1, min(max_results, 10))
        enhanced_query = f"{query.strip()} 中国 法律 site:gov.cn OR site:court.gov.cn OR site:npc.gov.cn"
        search = DuckDuckGoSearchAPIWrapper(max_results=top_k * 2)
        last_error: Exception | None = None

        for attempt in range(1, retries + 1):
            try:
                results = search.results(enhanced_query, max_results=top_k * 2)
                if results:
                    formatted = _format_search_results(results, top_k)
                    if formatted:
                        return formatted
                break
            except Exception as e:
                last_error = e
                app_logger.warning(
                    f"search_latest_legal_cases attempt={attempt}/{retries} failed: {str(e)}"
                )
                if attempt < retries:
                    time.sleep(0.4 * attempt)

        # fallback: run()
        try:
            result_text = search.run(enhanced_query)
            if result_text and result_text.strip():
                return f"[来源1] DuckDuckGo 摘要 - {result_text.strip()} (https://duckduckgo.com/)"
        except Exception as fallback_err:
            last_error = fallback_err

        if last_error:
            raise last_error
    except Exception as e:
        status = "failed"
        app_logger.warning(f"search_latest_legal_cases error: {str(e)}")
        return (
            f"联网检索暂时不可用（可能超时或连接受限）。"
            f"建议优先在中国裁判文书网、最高法官网、国家法律法规数据库检索「{query}」。"
        )
    finally:
        latency = int((time.perf_counter() - started) * 1000)
        app_logger.info(
            f"[TOOL_AUDIT] tool_name=search_latest_legal_cases arguments={args} latency={latency}ms status={status}"
        )


def get_tools(enable_search: bool = True, enable_calculator: bool = True) -> list:
    """获取 Legal Agent 工具列表。"""
    tools = []
    if enable_calculator:
        tools.append(calculate_labor_compensation)
    if enable_search:
        tools.append(search_latest_legal_cases)
    return tools
