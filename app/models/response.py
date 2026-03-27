"""
响应数据模型
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime
from enum import Enum


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="应用版本")
    llm_mode: str = Field(..., description="LLM 模式")
    llm_model: str = Field(..., description="LLM 模型")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "healthy",
                    "version": "1.0.0",
                    "llm_mode": "local",
                    "llm_model": "qwen2.5:7b",
                    "timestamp": "2026-03-07T16:00:00Z"
                }
            ]
        }
    }


class ChatResponse(BaseModel):
    """聊天响应模型"""
    answer: str = Field(..., description="AI 回答")
    session_id: str = Field(..., description="会话ID")
    sources: List[str] = Field(default_factory=list, description="引用来源")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    error: Optional[str] = Field(default=None, description="错误信息")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "answer": "试用期是指用人单位和劳动者在劳动合同中约定的...",
                    "session_id": "user_123",
                    "sources": ["《劳动合同法》第十九条"],
                    "timestamp": "2026-03-07T16:00:00Z"
                }
            ]
        }
    }


class ResetResponse(BaseModel):
    """重置会话响应模型"""
    success: bool = Field(..., description="是否成功")
    message: Optional[str] = Field(default=None, description="消息")
    session_id: str = Field(..., description="会话ID")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "message": "会话已重置",
                    "session_id": "user_123"
                }
            ]
        }
    }


# ==================== 阶段三：智能合同分析模型 ====================

class RiskLevel(str, Enum):
    """风险等级枚举"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskItem(BaseModel):
    """风险项模型"""
    risk_level: RiskLevel = Field(..., description="风险等级：high/medium/low")
    clause_text: str = Field(..., description="原文中存在风险的条款片段")
    risk_analysis: str = Field(..., description="为什么有风险的法律分析")
    revision_suggestion: str = Field(..., description="具体的修改建议或推荐替换的条款文本")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "risk_level": "high",
                    "clause_text": "甲方可以随时解除本合同，无需支付任何经济补偿。",
                    "risk_analysis": "该条款违反《劳动合同法》对解除劳动合同的法定条件要求，属于明显免除用人单位法定义务的无效条款。",
                    "revision_suggestion": "建议改为：\"甲方解除劳动合同应符合法定条件，并依法履行通知或补偿义务。\""
                }
            ]
        }
    }


class ContractReviewResponse(BaseModel):
    """合同审查响应模型"""
    contract_id: str = Field(..., description="合同唯一标识")
    risks: List[RiskItem] = Field(..., description="风险项列表")
    overall_summary: str = Field(..., description="整体合同风险评估总结")
    review_timestamp: datetime = Field(default_factory=datetime.now, description="审查时间戳")
    processing_steps: List[str] = Field(default_factory=list, description="处理步骤日志（用于前端流式展示）")
    is_image_based: bool = Field(default=False, description="是否基于图像识别")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "contract_id": "contract_001",
                    "risks": [
                        {
                            "risk_level": "high",
                            "clause_text": "甲方可以随时解除本合同，无需支付任何经济补偿。",
                            "risk_analysis": "该条款明显免除了用人单位法定义务，可能被认定无效。",
                            "revision_suggestion": "建议改为：解除劳动合同需符合法定条件并依法补偿。"
                        }
                    ],
                    "overall_summary": "该合同存在3处高风险条款，主要集中在试用期解除、违约责任和竞业限制方面...",
                    "review_timestamp": "2026-03-07T16:00:00Z",
                    "processing_steps": [
                        "[10:00:01] 📸 正在进行多模态视觉理解...",
                        "[10:00:03] 🔍 发现隐蔽条款：第三章第二条...",
                        "[10:00:05] ⚖️ 正在进行法律知识库对比..."
                    ],
                    "is_image_based": False
                }
            ]
        }
    }


class ReviewTaskSubmitResponse(BaseModel):
    """合同审查异步任务提交响应"""
    task_id: str = Field(..., description="Celery 任务 ID")
    status: str = Field(default="processing", description="任务状态")


class ReviewTaskStatusResponse(BaseModel):
    """合同审查异步任务状态响应"""
    task_id: str = Field(..., description="Celery 任务 ID")
    status: str = Field(..., description="任务状态")
    progress: int = Field(default=0, description="任务进度（0-100）")
    message: str = Field(default="", description="任务提示信息")
    result: Optional[ContractReviewResponse] = Field(default=None, description="任务完成后的审查结果")
    error: Optional[str] = Field(default=None, description="任务失败错误信息")
    meta: Optional[Any] = Field(default=None, description="任务元数据")


class AgentArgument(BaseModel):
    """智能体论点模型（兼容旧版 Supervisor 输出）"""
    agent_role: str = Field(..., description="智能体角色")
    argument: str = Field(..., description="论点内容")
    legal_basis: List[str] = Field(default_factory=list, description="法律依据")
    key_points: List[str] = Field(default_factory=list, description="关键要点")


class DebateResponse(BaseModel):
    """多智能体辩论响应模型（兼容旧版接口）"""
    case_description: str = Field(..., description="案情描述")
    plaintiff_argument: AgentArgument = Field(..., description="原告方论点")
    defendant_argument: AgentArgument = Field(..., description="被告方论点")
    judge_opinion: AgentArgument = Field(..., description="法官意见")
    win_probability: dict = Field(..., description="胜诉概率预测")
    debate_timestamp: datetime = Field(default_factory=datetime.now, description="辩论时间戳")
