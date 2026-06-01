"""
测试 ContractReviewer — JSON 提取 / 结果解析 / 提示词构建 / 错误处理
"""

import sys
import json
import pytest
from importlib.util import spec_from_file_location, module_from_spec
from app.models.response import RiskLevel

# 从文件路径直接加载模块，绕过 app/services/__init__.py
_mod_path = "app/services/contract_reviewer.py"
_spec = spec_from_file_location("sparklaw_contract_reviewer", _mod_path)
_mod = module_from_spec(_spec)
sys.modules["sparklaw_contract_reviewer"] = _mod
_spec.loader.exec_module(_mod)
ContractReviewer = _mod.ContractReviewer


# ==================== JSON 提取 ====================


class TestJsonExtraction:
    """JSON 提取逻辑"""

    def test_extract_pure_json(self):
        reviewer = ContractReviewer.__new__(ContractReviewer)
        text = '{"risks": [], "overall_summary": "ok"}'
        result = reviewer._extract_json(text)
        assert result == text

    def test_extract_json_with_surrounding_text(self):
        reviewer = ContractReviewer.__new__(ContractReviewer)
        text = '以下为审查结果：\n{"risks": [{"risk_level": "高风险"}], "overall_summary": "存在风险"}\n以上为审查结果。'
        result = reviewer._extract_json(text)
        assert result.startswith("{")
        assert result.endswith("}")
        parsed = json.loads(result)
        assert parsed["overall_summary"] == "存在风险"

    def test_extract_nested_json(self):
        reviewer = ContractReviewer.__new__(ContractReviewer)
        text = '{"risks": [{"risk_level": "高风险", "original_clause": "条款内容", "risk_explanation": "解释", "revise_suggestion": "建议"}], "overall_summary": "总结"}'
        result = reviewer._extract_json(text)
        parsed = json.loads(result)
        assert len(parsed["risks"]) == 1
        assert parsed["overall_summary"] == "总结"

    def test_no_json_returns_original(self):
        reviewer = ContractReviewer.__new__(ContractReviewer)
        text = "没有JSON格式的纯文本回答"
        result = reviewer._extract_json(text)
        assert result == text


# ==================== 审查结果解析 ====================


class TestResultParsing:
    """审查结果解析"""

    def test_parse_valid_result(self):
        reviewer = ContractReviewer.__new__(ContractReviewer)
        llm_output = json.dumps({
            "risks": [
                {
                    "risk_level": "高风险",
                    "original_clause": "甲方可随时解除合同",
                    "risk_explanation": "违反劳动合同法",
                    "revise_suggestion": "删除或修改此条款",
                },
                {
                    "risk_level": "低风险",
                    "original_clause": "合同一式两份",
                    "risk_explanation": "表述不够严谨",
                    "revise_suggestion": "建议明确双方各持一份",
                },
            ],
            "overall_summary": "存在1个高风险和1个低风险项",
        }, ensure_ascii=False)

        result = reviewer._parse_review_result(llm_output, "contract_001")
        assert result.contract_id == "contract_001"
        assert len(result.risks) == 2
        assert result.risks[0].risk_level == RiskLevel.HIGH
        assert result.risks[1].risk_level == RiskLevel.LOW
        assert "高风险" in result.overall_summary

    def test_parse_medium_risk(self):
        reviewer = ContractReviewer.__new__(ContractReviewer)
        llm_output = json.dumps({
            "risks": [
                {
                    "risk_level": "中风险",
                    "original_clause": "违约金为合同总额的50%",
                    "risk_explanation": "违约金过高",
                    "revise_suggestion": "降低违约金比例",
                }
            ],
            "overall_summary": "1个中风险",
        }, ensure_ascii=False)

        result = reviewer._parse_review_result(llm_output, "contract_002")
        assert result.risks[0].risk_level == RiskLevel.MEDIUM

    def test_parse_english_risk_levels(self):
        reviewer = ContractReviewer.__new__(ContractReviewer)
        llm_output = json.dumps({
            "risks": [
                {"risk_level": "high", "original_clause": "c1", "risk_explanation": "e1", "revise_suggestion": "s1"},
                {"risk_level": "medium", "original_clause": "c2", "risk_explanation": "e2", "revise_suggestion": "s2"},
                {"risk_level": "low", "original_clause": "c3", "risk_explanation": "e3", "revise_suggestion": "s3"},
            ],
            "overall_summary": "3 risks",
        })

        result = reviewer._parse_review_result(llm_output, "contract_003")
        assert result.risks[0].risk_level == RiskLevel.HIGH
        assert result.risks[1].risk_level == RiskLevel.MEDIUM
        assert result.risks[2].risk_level == RiskLevel.LOW

    def test_parse_invalid_json_returns_fallback(self):
        reviewer = ContractReviewer.__new__(ContractReviewer)
        llm_output = "这不是有效的 JSON 格式"

        result = reviewer._parse_review_result(llm_output, "contract_fallback")
        assert result.contract_id == "contract_fallback"
        assert len(result.risks) == 1
        assert result.risks[0].risk_level == RiskLevel.MEDIUM
        assert "无法解析" in result.risks[0].risk_analysis
        assert "格式解析错误" in result.overall_summary

    def test_parse_empty_risks(self):
        reviewer = ContractReviewer.__new__(ContractReviewer)
        llm_output = json.dumps({
            "risks": [],
            "overall_summary": "未发现风险",
        })

        result = reviewer._parse_review_result(llm_output, "contract_good")
        assert result.risks == []
        assert result.overall_summary == "未发现风险"


# ==================== 提示词构建 ====================


class TestPromptBuilding:
    """提示词构建"""

    def test_build_review_prompt_includes_contract_text(self):
        reviewer = ContractReviewer.__new__(ContractReviewer)
        prompt = reviewer._build_review_prompt("第一条 合同双方权利义务")
        assert "第一条 合同双方权利义务" in prompt
        assert "JSON 格式" in prompt

    def test_build_review_prompt_truncates_long_text(self):
        reviewer = ContractReviewer.__new__(ContractReviewer)
        long_text = "条款内容。" * 2000
        prompt = reviewer._build_review_prompt(long_text)
        assert len(prompt) < len(long_text) + 5000
        assert "中间部分已省略" in prompt

    def test_build_review_prompt_contains_risk_levels(self):
        reviewer = ContractReviewer.__new__(ContractReviewer)
        prompt = reviewer._build_review_prompt("测试合同内容")
        assert "高风险" in prompt
        assert "中风险" in prompt
        assert "低风险" in prompt
