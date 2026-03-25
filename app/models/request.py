"""
请求数据模型
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class ChatRequest(BaseModel):
    """聊天请求模型"""
    question: str = Field(..., description="用户问题", min_length=1, max_length=1000)
    session_id: str = Field(default="default", description="会话ID")
    thread_id: Optional[str] = Field(default=None, description="LangGraph Thread ID，用于跨轮状态持久化")
    jurisdiction: Optional[str] = Field(default="中国", description="法律辖区")
    personality: Literal["machine", "empathy", "cost", "cost_expert", "aggressive", "educator"] = Field(
        default="empathy",
        description="律师人格"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "什么是劳动合同的试用期？",
                    "session_id": "user_123",
                    "thread_id": "thread_abc123",
                    "jurisdiction": "中国",
                    "personality": "empathy"
                }
            ]
        }
    }


class ResetRequest(BaseModel):
    """重置会话请求模型"""
    session_id: str = Field(..., description="会话ID")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "session_id": "user_123"
                }
            ]
        }
    }
