"""
多模态合同审查服务
支持图像识别和文本分析的统一 Pipeline
"""

import asyncio
import base64
import json as _json_mod
import re as _re_mod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal

from celery.exceptions import MaxRetriesExceededError
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from app.celery_app import celery_app
from app.core.logger import app_logger
from app.models.response import ContractReviewResponse, RiskItem
from app.services.llm_factory import LLMFactory
from app.services.rag_service import get_rag_service

# JSON schema 描述（纯字符串拼接，不依赖 f-string 花括号转义）
_JSON_SCHEMA_DESC = (
    '{"overall_summary": "<合同总体评价，不超过150字>",'
    ' "risks": [{"risk_level": "<high|medium|low>",'
    ' "clause_text": "<原文条款片段>",'
    ' "risk_analysis": "<风险原因>",'
    ' "revision_suggestion": "<修改建议>"}]}'
)


class StructuredRiskItem(BaseModel):
    risk_level: Literal["high", "medium", "low"] = Field(
        description="风险等级"
    )
    clause_text: str = Field(description="原文中存在风险的条款片段")
    risk_analysis: str = Field(description="为什么有风险的法律分析")
    revision_suggestion: str = Field(description="具体的修改建议或推荐替换的条款文本")


class ContractReviewResult(BaseModel):
    overall_summary: str = Field(description="对整份合同的总体法律评价")
    risks: List[StructuredRiskItem] = Field(description="识别出的风险点列表")


class MultimodalContractReviewer:
    """多模态合同审查器"""

    SUPPORTED_IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".webp"}

    SYSTEM_PROMPT = (
        "你是一位中国合同审查律师，请识别合同中的法律与商业风险。\n"
        "请严格依据用户提供的合同文本进行分析，不要编造不存在的条款。\n"
        "只输出纯 JSON，不要任何前缀、后缀或 markdown 代码块。"
    )

    def __init__(self):
        self.llm = LLMFactory.create_llm()
        self.processing_steps: List[str] = []
        app_logger.info("🎨 MultimodalContractReviewer 初始化完成")

    def _add_step(self, step: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {step}"
        self.processing_steps.append(log_entry)
        app_logger.info(log_entry)

    def _is_image_file(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() in self.SUPPORTED_IMAGE_FORMATS

    async def review_from_image(
        self, image_data: bytes, image_format: str, contract_id: str
    ) -> ContractReviewResponse:
        self.processing_steps = []
        try:
            self._add_step("📸 正在进行多模态视觉理解...")
            image_base64 = base64.b64encode(image_data).decode("utf-8")
            self._add_step("🔍 正在提取合同文本内容...")
            contract_text = await self._extract_text_from_image(image_base64, image_format)
            if not contract_text or len(contract_text.strip()) < 50:
                raise ValueError("图像识别失败或内容过短，请确保图像清晰且包含合同文本")
            self._add_step(f"✅ 成功提取 {len(contract_text)} 字符的合同文本")
            self._add_step("⚖️ 正在进行结构化风险审查...")
            review_result = await self._review_contract_text(contract_text, contract_id, is_image=True)
            review_result.processing_steps = self.processing_steps
            review_result.is_image_based = True
            self._add_step(f"✅ 审查完成，发现 {len(review_result.risks)} 个风险项")
            return review_result
        except Exception as e:
            self._add_step(f"❌ 审查失败: {str(e)}")
            app_logger.error(f"❌ 图像合同审查失败: {str(e)}")
            raise

    async def review_from_text(
        self, contract_text: str, contract_id: str
    ) -> ContractReviewResponse:
        self.processing_steps = []
        try:
            self._add_step("📄 正在分析合同文本结构...")
            if not contract_text or len(contract_text.strip()) < 100:
                raise ValueError("合同文本过短或为空，无法进行有效审查")
            self._add_step(f"✅ 合同文本长度: {len(contract_text)} 字符")
            self._add_step("⚖️ 正在进行结构化风险审查...")
            review_result = await self._review_contract_text(contract_text, contract_id, is_image=False)
            review_result.processing_steps = self.processing_steps
            review_result.is_image_based = False
            self._add_step(f"✅ 审查完成，发现 {len(review_result.risks)} 个风险项")
            return review_result
        except Exception as e:
            self._add_step(f"❌ 审查失败: {str(e)}")
            app_logger.error(f"❌ 文本合同审查失败: {str(e)}")
            raise

    async def _extract_text_from_image(self, image_base64: str, image_format: str) -> str:
        try:
            message = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": "请仔细识别这份合同图像中的所有文字内容，按照原文顺序完整输出，不要添加解释。",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/{image_format};base64,{image_base64}"},
                    },
                ]
            )
            response = await self.llm.ainvoke([message])
            text = response.content if hasattr(response, "content") else str(response)
            return text.strip()
        except Exception as e:
            app_logger.error(f"❌ 图像文本提取失败: {str(e)}")
            raise Exception(f"图像文本提取失败: {str(e)}")

    async def _review_contract_text(
        self, contract_text: str, contract_id: str, is_image: bool = False
    ) -> ContractReviewResponse:
        try:
            prompt = self._build_review_prompt(contract_text)
            structured = await self._call_llm_for_review(prompt)
            return self._parse_review_result(structured, contract_id)
        except Exception as e:
            app_logger.error(f"❌ 合同文本审查失败: {str(e)}")
            raise

    def _build_review_prompt(self, contract_text: str) -> str:
        """构建审查提示词（不使用 f-string 花括号转义，避免 JSON 模板污染）"""
        max_length = 8000
        if len(contract_text) > max_length:
            half = max_length // 2
            contract_text = (
                contract_text[:half]
                + "\n\n...[中间部分已省略]...\n\n"
                + contract_text[-half:]
            )
            app_logger.warning(f"⚠️  合同文本过长，已截断至 {max_length} 字符")

        parts = [
            self.SYSTEM_PROMPT,
            "",
            "请审查以下合同内容：",
            "",
            "===== 合同内容开始 =====",
            contract_text,
            "===== 合同内容结束 =====",
            "",
            "输出规则（必须严格遵守）：",
            "1. 只输出纯 JSON 对象，不要任何前缀、后缀或 markdown 代码块",
            "2. 所有字符串值内不得包含未转义的双引号",
            "3. 数组和对象末尾不得有多余的逗号",
            "4. risk_level 只能是 high、medium 或 low",
            "5. JSON 结构如下：",
            _JSON_SCHEMA_DESC,
        ]
        return "\n".join(parts)

    @staticmethod
    def _repair_json(raw: str) -> str:
        """修复 LLM 输出的常见 JSON 格式问题"""
        # 1. 提取 markdown 代码块
        m = _re_mod.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
        if m:
            raw = m.group(1).strip()
        else:
            # 提取最外层 { ... }
            start = raw.find('{')
            end = raw.rfind('}')
            if start != -1 and end != -1 and end > start:
                raw = raw[start:end + 1]

        # 2. 去除尾随逗号（, } 或 , ]）
        raw = _re_mod.sub(r',\s*([\}\]])', r'\1', raw)

        # 3. 去除控制字符（换行/制表在字符串值内会破坏 JSON）
        # 只替换真正的控制字符，保留普通中文字符
        raw = _re_mod.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', raw)

        return raw

    async def _call_llm_for_review(self, prompt: str) -> ContractReviewResult:
        """prompt-based JSON 解析，兼容不支持 json_schema 的模型（如 Groq llama）"""
        try:
            response = await self.llm.ainvoke(prompt)
            raw = response.content if hasattr(response, "content") else str(response)

            # 修复常见 JSON 格式问题
            json_str = self._repair_json(raw)

            try:
                data = _json_mod.loads(json_str)
            except _json_mod.JSONDecodeError as parse_err:
                app_logger.warning(
                    f"⚠️ JSON 解析失败（{parse_err}），原始输出前 400 字:\n{raw[:400]}"
                )
                raise ValueError(f"JSON 解析错误: {parse_err}")

            return ContractReviewResult.model_validate(data)
        except Exception as e:
            app_logger.error(f"❌ LLM 结构化调用失败: {str(e)}")
            raise Exception(f"LLM 结构化调用失败: {str(e)}")

    def _parse_review_result(
        self, llm_output: ContractReviewResult, contract_id: str
    ) -> ContractReviewResponse:
        try:
            risks = [
                RiskItem(
                    risk_level=item.risk_level,
                    clause_text=item.clause_text,
                    risk_analysis=item.risk_analysis,
                    revision_suggestion=item.revision_suggestion,
                )
                for item in llm_output.risks
            ]
            return ContractReviewResponse(
                contract_id=contract_id,
                risks=risks,
                overall_summary=llm_output.overall_summary,
                processing_steps=self.processing_steps,
            )
        except Exception as e:
            app_logger.error(f"❌ 结果解析失败: {str(e)}")
            raise Exception(f"结果解析失败: {str(e)}")


_multimodal_reviewer_instance = None


def get_multimodal_reviewer() -> MultimodalContractReviewer:
    global _multimodal_reviewer_instance
    if _multimodal_reviewer_instance is None:
        _multimodal_reviewer_instance = MultimodalContractReviewer()
    return _multimodal_reviewer_instance


def load_contract_text_from_vector_store(contract_id: str) -> str:
    """从向量库加载合同全文（按 chunk_index 顺序拼接）"""
    rag_service = get_rag_service()
    contract_info = rag_service.get_contract_info(contract_id)
    if not contract_info["exists"]:
        raise ValueError(f"合同 {contract_id} 不存在，请先上传合同文档")
    results = rag_service.collection.get(where={"contract_id": contract_id})
    if not results or not results.get("documents"):
        raise ValueError(f"合同 {contract_id} 内容为空")
    chunks_with_index = []
    for i, doc in enumerate(results["documents"]):
        metadata = results["metadatas"][i] if results.get("metadatas") else {}
        chunk_index = metadata.get("chunk_index", i)
        chunks_with_index.append((chunk_index, doc))
    chunks_with_index.sort(key=lambda x: x[0])
    return "\n\n".join([chunk[1] for chunk in chunks_with_index])


@celery_app.task(
    bind=True,
    name="app.multimodal_contract_review_task",
    max_retries=3,
    default_retry_delay=3,
)
def multimodal_contract_review_task(
    self, contract_id: str, contract_text: str | None = None
) -> Dict[str, Any]:
    """执行合同审查异步任务（Celery）"""
    try:
        reviewer = get_multimodal_reviewer()
        self.update_state(state="PROGRESS", meta={"progress": 10, "message": "正在准备合同内容..."})
        full_text = contract_text if contract_text else load_contract_text_from_vector_store(contract_id)
        self.update_state(state="PROGRESS", meta={"progress": 35, "message": "正在调用多模态法务模型解析..."})
        result = asyncio.run(reviewer.review_from_text(full_text, contract_id))
        self.update_state(state="PROGRESS", meta={"progress": 90, "message": "正在整理风险卡片..."})
        return result.model_dump(mode="json")
    except MaxRetriesExceededError as exc:
        app_logger.error(f"❌ 审查任务重试次数耗尽: {contract_id}, error={str(exc)}")
        raise
    except Exception as exc:
        app_logger.error(f"❌ 审查任务失败: {contract_id}, error={str(exc)}")
        if self.request.retries >= self.max_retries:
            raise
        raise self.retry(exc=exc)
