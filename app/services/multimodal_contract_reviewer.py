"""
多模态合同审查服务
支持图像识别和文本分析的统一 Pipeline
"""

import asyncio
import base64
import json
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path
from celery.exceptions import MaxRetriesExceededError
from langchain_core.messages import HumanMessage
from app.celery_app import celery_app
from app.core.logger import app_logger
from app.services.llm_factory import LLMFactory
from app.services.rag_service import get_rag_service
from app.models.response import ContractReviewResponse, RiskItem, RiskLevel


class MultimodalContractReviewer:
    """
    多模态合同审查器
    
    核心功能：
    1. 支持图像文件（JPG/PNG）直接识别
    2. 支持传统文本合同审查
    3. 使用 Vision LLM 进行端到端分析
    4. 提供流式思考链（CoT）日志
    5. 强引用法律依据
    
    技术栈：
    - Vision LLM: gpt-4o-mini / qwen-vl（兼容 OpenAI 格式）
    - 思考链：实时生成处理步骤日志
    - 法律知识库：内置常用法条
    """
    
    # 支持的图像格式
    SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.webp'}
    
    # 法律知识库（核心法条）
    LEGAL_BASIS_DATABASE = {
        "劳动合同法_试用期": {
            "title": "《劳动合同法》第二十一条",
            "content": "在试用期中，除劳动者有本法第三十九条和第四十条第一项、第二项规定的情形外，用人单位不得解除劳动合同。用人单位在试用期解除劳动合同的，应当向劳动者说明理由。",
            "link": "http://www.npc.gov.cn/npc/c30834/202006/75ba6483b8344591abd07917e1d25cc8.shtml"
        },
        "劳动合同法_违约金": {
            "title": "《劳动合同法》第二十五条",
            "content": "除本法第二十二条和第二十三条规定的情形外，用人单位不得与劳动者约定由劳动者承担违约金。",
            "link": "http://www.npc.gov.cn/npc/c30834/202006/75ba6483b8344591abd07917e1d25cc8.shtml"
        },
        "劳动合同法_竞业限制": {
            "title": "《劳动合同法》第二十四条",
            "content": "竞业限制的人员限于用人单位的高级管理人员、高级技术人员和其他负有保密义务的人员。竞业限制的范围、地域、期限由用人单位与劳动者约定，竞业限制的期限不得超过二年。",
            "link": "http://www.npc.gov.cn/npc/c30834/202006/75ba6483b8344591abd07917e1d25cc8.shtml"
        },
        "民法典_格式条款": {
            "title": "《民法典》第四百九十六条",
            "content": "格式条款是当事人为了重复使用而预先拟定，并在订立合同时未与对方协商的条款。采用格式条款订立合同的，提供格式条款的一方应当遵循公平原则确定当事人之间的权利和义务，并采取合理的方式提示对方注意免除或者减轻其责任等与对方有重大利害关系的条款，按照对方的要求，对该条款予以说明。提供格式条款的一方未履行提示或者说明义务，致使对方没有注意或者理解与其有重大利害关系的条款的，对方可以主张该条款不成为合同的内容。",
            "link": "http://www.npc.gov.cn/npc/c30834/202006/75ba6483b8344591abd07917e1d25cc8.shtml"
        }
    }
    
    # 专业法务审查系统提示词（增强版）
    SYSTEM_PROMPT = """你是一位拥有 20 年经验的中国顶尖企业法务专家，专门保护弱势方（劳动者、租客、外包接包方等）的合法权益。

你的任务是审查合同条款，找出所有可能损害弱势方利益的问题，包括但不限于：
1. **霸王条款**：明显不公平、违反法律强制性规定的条款
2. **隐藏陷阱**：表面合理但实际上对弱势方极为不利的条款
3. **法律漏洞**：利用法律模糊地带侵害弱势方权益的条款
4. **权利义务失衡**：强势方权利过大、弱势方义务过重的条款
5. **违约责任不对等**：对弱势方的违约惩罚过重，对强势方的违约责任过轻

审查标准：
- 严格依据《劳动合同法》《民法典》《消费者权益保护法》等法律法规
- 参考最高人民法院相关司法解释
- 考虑实际执行中的风险
- 宁可误报也不漏报，保护弱势方利益

输出要求：
- 必须严格按照 JSON 格式输出
- 每个风险项必须包含：风险等级、原条款、精确引用、风险解释、法律依据、修改建议、置信度
- 风险解释要用大白话，让普通人能看懂
- 法律依据必须引用具体法条原文
- 修改建议要具体可行，最好提供标准条款范本
- 整体总结要全面客观，给出明确的风险评级

风险等级判定标准：
- **高风险**：严重违法或极度不公平，可能导致重大损失（置信度 > 0.8）
- **中风险**：存在明显不利条款，可能导致一定损失（置信度 0.5-0.8）
- **低风险**：条款不够完善或表述不清，建议优化（置信度 < 0.5）"""

    def __init__(self):
        """初始化多模态合同审查器"""
        self.llm = LLMFactory.create_llm()
        self.processing_steps: List[str] = []
        app_logger.info("🎨 MultimodalContractReviewer 初始化完成")
    
    def _add_step(self, step: str) -> None:
        """
        添加处理步骤日志
        
        Args:
            step: 步骤描述
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {step}"
        self.processing_steps.append(log_entry)
        app_logger.info(log_entry)
    
    def _is_image_file(self, file_path: str) -> bool:
        """
        判断是否为图像文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否为图像文件
        """
        suffix = Path(file_path).suffix.lower()
        return suffix in self.SUPPORTED_IMAGE_FORMATS
    
    async def review_from_image(
        self,
        image_data: bytes,
        image_format: str,
        contract_id: str
    ) -> ContractReviewResponse:
        """
        从图像识别并审查合同
        
        Args:
            image_data: 图像二进制数据
            image_format: 图像格式（jpg/png）
            contract_id: 合同ID
            
        Returns:
            ContractReviewResponse: 审查结果
        """
        self.processing_steps = []
        
        try:
            self._add_step("📸 正在进行多模态视觉理解...")
            
            # 1. 将图像转换为 base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # 2. 构建多模态提示词
            self._add_step("🔍 正在提取合同文本内容...")
            
            # 3. 调用 Vision LLM 进行 OCR + 理解
            contract_text = await self._extract_text_from_image(image_base64, image_format)
            
            if not contract_text or len(contract_text.strip()) < 50:
                raise ValueError("图像识别失败或内容过短，请确保图像清晰且包含合同文本")
            
            self._add_step(f"✅ 成功提取 {len(contract_text)} 字符的合同文本")
            
            # 4. 进行合同审查
            self._add_step("⚖️ 正在进行法律知识库对比...")
            review_result = await self._review_contract_text(contract_text, contract_id, is_image=True)
            
            self._add_step("🎯 正在识别隐蔽条款和霸王条款...")
            
            # 5. 添加处理步骤到结果
            review_result.processing_steps = self.processing_steps
            review_result.is_image_based = True
            
            self._add_step(f"✅ 审查完成，发现 {len(review_result.risks)} 个风险项")
            
            return review_result
        
        except Exception as e:
            self._add_step(f"❌ 审查失败: {str(e)}")
            app_logger.error(f"❌ 图像合同审查失败: {str(e)}")
            raise
    
    async def review_from_text(
        self,
        contract_text: str,
        contract_id: str
    ) -> ContractReviewResponse:
        """
        从文本审查合同
        
        Args:
            contract_text: 合同文本
            contract_id: 合同ID
            
        Returns:
            ContractReviewResponse: 审查结果
        """
        self.processing_steps = []
        
        try:
            self._add_step("📄 正在分析合同文本结构...")
            
            if not contract_text or len(contract_text.strip()) < 100:
                raise ValueError("合同文本过短或为空，无法进行有效审查")
            
            self._add_step(f"✅ 合同文本长度: {len(contract_text)} 字符")
            
            # 进行合同审查
            self._add_step("⚖️ 正在进行法律知识库对比...")
            review_result = await self._review_contract_text(contract_text, contract_id, is_image=False)
            
            self._add_step("🎯 正在识别隐蔽条款和霸王条款...")
            
            # 添加处理步骤到结果
            review_result.processing_steps = self.processing_steps
            review_result.is_image_based = False
            
            self._add_step(f"✅ 审查完成，发现 {len(review_result.risks)} 个风险项")
            
            return review_result
        
        except Exception as e:
            self._add_step(f"❌ 审查失败: {str(e)}")
            app_logger.error(f"❌ 文本合同审查失败: {str(e)}")
            raise
    
    async def _extract_text_from_image(
        self,
        image_base64: str,
        image_format: str
    ) -> str:
        """
        使用 Vision LLM 从图像中提取文本
        
        Args:
            image_base64: Base64 编码的图像
            image_format: 图像格式
            
        Returns:
            str: 提取的文本
        """
        try:
            # 构建多模态消息
            message = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": "请仔细识别这份合同图像中的所有文字内容，按照原文顺序完整输出。注意：\n1. 保持原有的章节结构\n2. 不要遗漏任何条款\n3. 如果图像模糊或文字不清，请标注[不清晰]\n4. 只输出识别的文字，不要添加任何解释"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{image_format};base64,{image_base64}"
                        }
                    }
                ]
            )
            
            # 调用 Vision LLM
            response = await self.llm.ainvoke([message])
            
            # 提取文本
            if hasattr(response, "content"):
                text = response.content
            else:
                text = str(response)
            
            return text.strip()
        
        except Exception as e:
            app_logger.error(f"❌ 图像文本提取失败: {str(e)}")
            raise Exception(f"图像文本提取失败: {str(e)}")
    
    async def _review_contract_text(
        self,
        contract_text: str,
        contract_id: str,
        is_image: bool = False
    ) -> ContractReviewResponse:
        """
        审查合同文本
        
        Args:
            contract_text: 合同文本
            contract_id: 合同ID
            is_image: 是否来自图像识别
            
        Returns:
            ContractReviewResponse: 审查结果
        """
        try:
            # 构建审查提示词
            prompt = self._build_review_prompt(contract_text)
            
            # 调用 LLM 进行审查
            review_result = await self._call_llm_for_review(prompt)
            
            # 解析结果
            parsed_result = self._parse_review_result(review_result, contract_id)
            
            return parsed_result
        
        except Exception as e:
            app_logger.error(f"❌ 合同文本审查失败: {str(e)}")
            raise
    
    def _build_review_prompt(self, contract_text: str) -> str:
        """
        构建审查提示词
        
        Args:
            contract_text: 合同文本
            
        Returns:
            str: 完整的提示词
        """
        # 如果合同过长，进行截断
        max_length = 8000
        if len(contract_text) > max_length:
            half = max_length // 2
            contract_text = (
                contract_text[:half] + 
                "\n\n...[中间部分已省略]...\n\n" + 
                contract_text[-half:]
            )
            app_logger.warning(f"⚠️  合同文本过长，已截断至 {max_length} 字符")
        
        prompt = f"""{self.SYSTEM_PROMPT}

请审查以下合同内容：

===== 合同内容开始 =====
{contract_text}
===== 合同内容结束 =====

请严格按照以下 JSON 格式输出审查结果：

{{
    "risks": [
        {{
            "risk_level": "高风险" | "中风险" | "低风险",
            "original_clause": "原条款完整内容",
            "original_text_quote": "原文精确引用片段（用于高亮定位，10-30字）",
            "risk_explanation": "用大白话解释风险",
            "legal_basis": ["《法律名称》第X条：法条原文", "..."],
            "revise_suggestion": "具体的修改建议",
            "confidence_score": 0.95
        }}
    ],
    "overall_summary": "整体风险评估总结"
}}

注意：
1. 必须输出有效的 JSON 格式
2. 至少找出 3-5 个风险点（如果合同确实存在问题）
3. legal_basis 必须包含具体法条原文，不能只写法条编号
4. original_text_quote 要精确摘录原文中的关键片段
5. confidence_score 要根据风险的明确程度给出 0-1 的分数
6. 风险解释要通俗易懂，避免法律术语堆砌"""

        return prompt
    
    async def _call_llm_for_review(self, prompt: str) -> str:
        """
        调用 LLM 进行审查
        
        Args:
            prompt: 审查提示词
            
        Returns:
            str: LLM 返回的审查结果
        """
        try:
            response = await self.llm.ainvoke(prompt)
            
            if hasattr(response, "content"):
                result = response.content
            else:
                result = str(response)
            
            return result
        
        except Exception as e:
            app_logger.error(f"❌ LLM 调用失败: {str(e)}")
            raise Exception(f"LLM 调用失败: {str(e)}")
    
    def _parse_review_result(
        self,
        llm_output: str,
        contract_id: str
    ) -> ContractReviewResponse:
        """
        解析 LLM 输出的审查结果
        
        Args:
            llm_output: LLM 的原始输出
            contract_id: 合同ID
            
        Returns:
            ContractReviewResponse: 解析后的结构化结果
        """
        try:
            # 提取 JSON 部分
            json_str = self._extract_json(llm_output)
            
            # 解析 JSON
            data = json.loads(json_str)
            
            # 构建 RiskItem 列表
            risks = []
            for risk_data in data.get("risks", []):
                # 转换风险等级
                risk_level_str = risk_data.get("risk_level", "中风险")
                if "高" in risk_level_str:
                    risk_level = RiskLevel.HIGH
                elif "低" in risk_level_str:
                    risk_level = RiskLevel.LOW
                else:
                    risk_level = RiskLevel.MEDIUM
                
                # 增强法律依据（如果 LLM 没有提供完整法条，从知识库补充）
                legal_basis = risk_data.get("legal_basis", [])
                legal_basis_links = []
                
                # 尝试匹配知识库中的法条
                for key, law_info in self.LEGAL_BASIS_DATABASE.items():
                    for basis in legal_basis:
                        if law_info["title"] in basis:
                            legal_basis_links.append(law_info["link"])
                            break
                
                risk_item = RiskItem(
                    risk_level=risk_level,
                    original_clause=risk_data.get("original_clause", ""),
                    original_text_quote=risk_data.get("original_text_quote", ""),
                    risk_explanation=risk_data.get("risk_explanation", ""),
                    legal_basis=legal_basis,
                    legal_basis_links=legal_basis_links,
                    revise_suggestion=risk_data.get("revise_suggestion", ""),
                    confidence_score=risk_data.get("confidence_score", 0.0)
                )
                risks.append(risk_item)
            
            # 构建响应
            response = ContractReviewResponse(
                contract_id=contract_id,
                risks=risks,
                overall_summary=data.get("overall_summary", "审查完成，详见风险项列表。"),
                processing_steps=self.processing_steps
            )
            
            return response
        
        except json.JSONDecodeError as e:
            app_logger.error(f"❌ JSON 解析失败: {str(e)}")
            app_logger.debug(f"LLM 原始输出: {llm_output[:500]}...")
            
            # 返回包含错误信息的默认响应
            return ContractReviewResponse(
                contract_id=contract_id,
                risks=[
                    RiskItem(
                        risk_level=RiskLevel.MEDIUM,
                        original_clause="[解析失败]",
                        original_text_quote="[解析失败]",
                        risk_explanation=f"LLM 输出格式异常，无法解析为结构化数据。",
                        legal_basis=[],
                        legal_basis_links=[],
                        revise_suggestion="请重新审查或联系技术支持。",
                        confidence_score=0.0
                    )
                ],
                overall_summary="审查过程中出现格式解析错误，建议重新审查。",
                processing_steps=self.processing_steps
            )
        
        except Exception as e:
            app_logger.error(f"❌ 结果解析失败: {str(e)}")
            raise Exception(f"结果解析失败: {str(e)}")
    
    def _extract_json(self, text: str) -> str:
        """
        从文本中提取 JSON 部分
        
        Args:
            text: 包含 JSON 的文本
            
        Returns:
            str: 提取的 JSON 字符串
        """
        # 尝试找到 JSON 的开始和结束位置
        start = text.find("{")
        end = text.rfind("}") + 1
        
        if start != -1 and end > start:
            return text[start:end]
        
        # 如果找不到，返回原文本
        return text


# 全局单例实例
_multimodal_reviewer_instance = None


def get_multimodal_reviewer() -> MultimodalContractReviewer:
    """
    获取多模态合同审查器的全局单例实例
    
    Returns:
        MultimodalContractReviewer: 多模态合同审查器实例
    """
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
def multimodal_contract_review_task(self, contract_id: str, contract_text: str | None = None) -> Dict[str, Any]:
    """执行合同审查异步任务（Celery）"""
    try:
        reviewer = get_multimodal_reviewer()

        self.update_state(state="PROGRESS", meta={"progress": 10, "message": "正在准备合同内容..."})

        if contract_text:
            full_text = contract_text
        else:
            full_text = load_contract_text_from_vector_store(contract_id)

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

