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
    message: str = Field(..., description="消息")
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
    HIGH = "高风险"
    MEDIUM = "中风险"
    LOW = "低风险"


class RiskItem(BaseModel):
    """风险项模型"""
    risk_level: RiskLevel = Field(..., description="风险等级")
    original_clause: str = Field(..., description="原合同条款原文")
    original_text_quote: str = Field(..., description="原文精确引用（用于高亮定位）")
    risk_explanation: str = Field(..., description="用大白话解释为什么有风险/坑在哪里")
    legal_basis: List[str] = Field(default_factory=list, description="法律依据（法条原文）")
    legal_basis_links: List[str] = Field(default_factory=list, description="法律依据官方链接")
    revise_suggestion: str = Field(..., description="修改建议或标准的对等条款")
    confidence_score: float = Field(default=0.0, description="置信度分数（0-1）", ge=0.0, le=1.0)
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "risk_level": "高风险",
                    "original_clause": "第五条 乙方在试用期内，甲方可随时解除劳动合同，无需支付任何补偿。",
                    "original_text_quote": "甲方可随时解除劳动合同，无需支付任何补偿",
                    "risk_explanation": "这是典型的霸王条款。根据《劳动合同法》第21条，试用期内用人单位解除合同必须证明劳动者不符合录用条件，不能随意解除。且即使合法解除，也应支付相应工资。",
                    "legal_basis": [
                        "《劳动合同法》第二十一条：在试用期中，除劳动者有本法第三十九条和第四十条第一项、第二项规定的情形外，用人单位不得解除劳动合同。用人单位在试用期解除劳动合同的，应当向劳动者说明理由。",
                        "《劳动合同法》第三十九条：劳动者有下列情形之一的，用人单位可以解除劳动合同：（一）在试用期间被证明不符合录用条件的..."
                    ],
                    "legal_basis_links": [
                        "http://www.npc.gov.cn/npc/c30834/202006/75ba6483b8344591abd07917e1d25cc8.shtml"
                    ],
                    "revise_suggestion": "建议修改为：'试用期内，如乙方不符合录用条件，甲方可提前三日通知解除合同，并支付乙方已工作期间的工资。'",
                    "confidence_score": 0.95
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
                            "risk_level": "高风险",
                            "original_clause": "第五条 乙方在试用期内...",
                            "original_text_quote": "甲方可随时解除劳动合同",
                            "risk_explanation": "这是典型的霸王条款...",
                            "legal_basis": ["《劳动合同法》第二十一条：..."],
                            "legal_basis_links": ["http://www.npc.gov.cn/..."],
                            "revise_suggestion": "建议修改为...",
                            "confidence_score": 0.95
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
    """智能体论点模型"""
    agent_role: str = Field(..., description="智能体角色")
    argument: str = Field(..., description="论点内容")
    legal_basis: List[str] = Field(default_factory=list, description="法律依据")
    key_points: List[str] = Field(default_factory=list, description="关键要点")


class DebateResponse(BaseModel):
    """多智能体辩论响应模型"""
    case_description: str = Field(..., description="案情描述")
    plaintiff_argument: AgentArgument = Field(..., description="原告方论点")
    defendant_argument: AgentArgument = Field(..., description="被告方论点")
    judge_opinion: AgentArgument = Field(..., description="法官意见")
    win_probability: dict = Field(..., description="胜诉概率预测")
    debate_timestamp: datetime = Field(default_factory=datetime.now, description="辩论时间戳")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "case_description": "员工因拒绝加班被公司辞退...",
                    "plaintiff_argument": {
                        "agent_role": "原告律师",
                        "argument": "公司违法解除劳动合同...",
                        "legal_basis": ["《劳动合同法》第39条"],
                        "key_points": ["公司未证明员工严重违纪", "加班应征得员工同意"]
                    },
                    "defendant_argument": {
                        "agent_role": "被告律师",
                        "argument": "员工严重违反公司规章制度...",
                        "legal_basis": ["《劳动合同法》第4条"],
                        "key_points": ["公司规章制度合法有效", "员工多次拒绝工作安排"]
                    },
                    "judge_opinion": {
                        "agent_role": "法官",
                        "argument": "综合双方证据和法律规定...",
                        "legal_basis": ["《劳动合同法》第39条、第87条"],
                        "key_points": ["关键在于加班是否合理", "公司举证责任"]
                    },
                    "win_probability": {
                        "plaintiff": 0.65,
                        "defendant": 0.35
                    },
                    "debate_timestamp": "2026-03-07T16:00:00Z"
                }
            ]
        }
    }
