"""
工具函数模块
"""

from typing import Any, Dict
import json


def format_json(data: Any) -> str:
    """
    格式化 JSON 数据
    
    Args:
        data: 要格式化的数据
        
    Returns:
        格式化后的 JSON 字符串
    """
    return json.dumps(data, ensure_ascii=False, indent=2)


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    截断文本
    
    Args:
        text: 原始文本
        max_length: 最大长度
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def sanitize_session_id(session_id: str) -> str:
    """
    清理会话 ID
    
    Args:
        session_id: 原始会话 ID
        
    Returns:
        清理后的会话 ID
    """
    # 移除特殊字符，只保留字母、数字、下划线和连字符
    import re
    return re.sub(r'[^a-zA-Z0-9_-]', '', session_id)
