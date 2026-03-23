"""
智能合同审查服务
基于 LLM 和 RAG 实现合同风险识别与条款审查
"""

import json
from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.core.config import settings
from app.core.logger import app_logger
from app.services.llm_factory import LLMFactory
from app.services.rag_service import get_rag_service
from app.models.response import ContractReviewResponse, RiskItem, RiskLevel


class ContractReviewer:
    """
    智能合同审查器
    
    核心功能：
    1. 从向量库中提取完整合同内容
    2. 使用专业法务视角审查合同条款
    3. 识别霸王条款、隐藏陷阱和法律漏洞
    4. 输出结构化的风险评估报告
    
    设计理念：
    - 站在弱势方（劳动者、租客、外包接包方）的立场
    - 严苛审查，宁可误报也不漏报
    - 提供实用的修改建议
    """
    
    # 专业法务审查系统提示词
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
- 每个风险项必须包含：风险等级、原条款、风险解释、修改建议
- 风险解释要用大白话，让普通人能看懂
- 修改建议要具体可行，最好提供标准条款范本
- 整体总结要全面客观，给出明确的风险评级

风险等级判定标准：
- **高风险**：严重违法或极度不公平，可能导致重大损失
- **中风险**：存在明显不利条款，可能导致一定损失
- **低风险**：条款不够完善或表述不清，建议优化"""

    def __init__(self):
        """初始化合同审查器"""
        self.llm = LLMFactory.create_llm()
        self.rag_service = get_rag_service()
        app_logger.info("⚖️  ContractReviewer 初始化完成")
    
    async def review_contract(self, contract_id: str) -> ContractReviewResponse:
        """
        审查指定合同，识别风险并提供建议
        
        Args:
            contract_id: 合同唯一标识
            
        Returns:
            ContractReviewResponse: 结构化的审查结果
            
        Raises:
            ValueError: 合同不存在或内容为空
            Exception: 审查过程中的其他错误
        """
        app_logger.info(f"🔍 开始审查合同: {contract_id}")
        
        try:
            # 1. 检查合同是否存在
            contract_info = self.rag_service.get_contract_info(contract_id)
            if not contract_info["exists"]:
                raise ValueError(f"合同 {contract_id} 不存在，请先上传合同文档")
            
            app_logger.info(f"📊 合同 {contract_id} 共有 {contract_info['chunk_count']} 个切片")
            
            # 2. 获取合同完整内容
            contract_text = self._get_full_contract_text(contract_id)
            
            if not contract_text or len(contract_text.strip()) < 100:
                raise ValueError(f"合同 {contract_id} 内容过短或为空，无法进行有效审查")
            
            app_logger.info(f"📄 合同文本长度: {len(contract_text)} 字符")
            
            # 3. 构建审查提示词
            review_prompt = self._build_review_prompt(contract_text)
            
            # 4. 调用 LLM 进行审查
            app_logger.info("🤖 正在调用 LLM 进行合同审查...")
            review_result = await self._call_llm_for_review(review_prompt)
            
            # 5. 解析并验证结果
            parsed_result = self._parse_review_result(review_result, contract_id)
            
            app_logger.info(f"✅ 合同审查完成，发现 {len(parsed_result.risks)} 个风险项")
            
            return parsed_result
        
        except ValueError as e:
            app_logger.error(f"❌ 合同审查失败（参数错误）: {str(e)}")
            raise
        except Exception as e:
            app_logger.error(f"❌ 合同审查失败: {str(e)}")
            raise Exception(f"合同审查失败: {str(e)}")
    
    def _get_full_contract_text(self, contract_id: str) -> str:
        """
        从向量库中获取合同的完整文本
        
        Args:
            contract_id: 合同唯一标识
            
        Returns:
            str: 合同完整文本
        """
        # 获取该合同的所有切片
        results = self.rag_service.collection.get(
            where={"contract_id": contract_id}
        )
        
        if not results or not results["documents"]:
            return ""
        
        # 按 chunk_index 排序
        chunks_with_index = []
        for i, doc in enumerate(results["documents"]):
            metadata = results["metadatas"][i] if results["metadatas"] else {}
            chunk_index = metadata.get("chunk_index", i)
            chunks_with_index.append((chunk_index, doc))
        
        # 排序并合并
        chunks_with_index.sort(key=lambda x: x[0])
        full_text = "\n\n".join([chunk[1] for chunk in chunks_with_index])
        
        return full_text
    
    def _build_review_prompt(self, contract_text: str) -> str:
        """
        构建审查提示词
        
        Args:
            contract_text: 合同文本
            
        Returns:
            str: 完整的提示词
        """
        # 如果合同过长，进行截断（保留前后部分）
        max_length = 8000  # 根据模型上下文长度调整
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
            "risk_explanation": "用大白话解释风险",
            "revise_suggestion": "具体的修改建议"
        }}
    ],
    "overall_summary": "整体风险评估总结"
}}

注意：
1. 必须输出有效的 JSON 格式
2. 至少找出 3-5 个风险点（如果合同确实存在问题）
3. 如果合同非常规范，也要指出可以优化的地方
4. 风险解释要通俗易懂，避免法律术语堆砌
5. 修改建议要具体可操作"""

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
            # 使用 LangChain 调用 LLM
            response = await self.llm.ainvoke(prompt)
            
            # 提取文本内容
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
            # 尝试提取 JSON 部分（LLM 可能会输出额外的文本）
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
                
                risk_item = RiskItem(
                    risk_level=risk_level,
                    original_clause=risk_data.get("original_clause", ""),
                    risk_explanation=risk_data.get("risk_explanation", ""),
                    revise_suggestion=risk_data.get("revise_suggestion", "")
                )
                risks.append(risk_item)
            
            # 构建响应
            response = ContractReviewResponse(
                contract_id=contract_id,
                risks=risks,
                overall_summary=data.get("overall_summary", "审查完成，详见风险项列表。")
            )
            
            return response
        
        except json.JSONDecodeError as e:
            app_logger.error(f"❌ JSON 解析失败: {str(e)}")
            app_logger.debug(f"LLM 原始输出: {llm_output[:500]}...")
            
            # 返回一个包含错误信息的默认响应
            return ContractReviewResponse(
                contract_id=contract_id,
                risks=[
                    RiskItem(
                        risk_level=RiskLevel.MEDIUM,
                        original_clause="[解析失败]",
                        risk_explanation=f"LLM 输出格式异常，无法解析为结构化数据。原始输出：{llm_output[:200]}...",
                        revise_suggestion="请重新审查或联系技术支持。"
                    )
                ],
                overall_summary="审查过程中出现格式解析错误，建议重新审查。"
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


# 全局单例实例（延迟初始化）
_contract_reviewer_instance = None


def get_contract_reviewer() -> ContractReviewer:
    """
    获取合同审查器的全局单例实例
    
    Returns:
        ContractReviewer: 合同审查器实例
    """
    global _contract_reviewer_instance
    
    if _contract_reviewer_instance is None:
        _contract_reviewer_instance = ContractReviewer()
    
    return _contract_reviewer_instance
