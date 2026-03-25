"""
Privacy Redactor — 脱敏处理敏感个人信息。
TODO: 对接 NER 模型，识别并替换姓名/身份证/手机号等。
"""
from __future__ import annotations
import re


class PrivacyRedactor:
    """简单规则式脱敏器。"""

    _PHONE = re.compile(r"1[3-9]\d{9}")
    _ID_CARD = re.compile(r"\d{17}[\dXx]")

    def redact(self, text: str) -> str:
        text = self._PHONE.sub("[手机号已脱敏]", text)
        text = self._ID_CARD.sub("[证件号已脱敏]", text)
        return text
