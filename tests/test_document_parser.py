"""
测试 DocumentParser — 扩展名提取 / 文本清洗 / 编解码 / 格式校验
"""

import sys
import pytest
from importlib.util import spec_from_file_location, module_from_spec

# 从文件路径直接加载模块，绕过 app/services/__init__.py
_mod_path = "app/services/document_parser.py"
_spec = spec_from_file_location("sparklaw_document_parser", _mod_path)
_mod = module_from_spec(_spec)
sys.modules["sparklaw_document_parser"] = _mod
_spec.loader.exec_module(_mod)
DocumentParser = _mod.DocumentParser


# ==================== 扩展名检测 ====================


class TestExtensionDetection:
    """文件扩展名检测"""

    def test_pdf_extension(self):
        parser = DocumentParser()
        assert parser._get_file_extension("contract.pdf") == ".pdf"

    def test_docx_extension(self):
        parser = DocumentParser()
        assert parser._get_file_extension("file.docx") == ".docx"

    def test_doc_extension(self):
        parser = DocumentParser()
        assert parser._get_file_extension("file.doc") == ".doc"

    def test_txt_extension(self):
        parser = DocumentParser()
        assert parser._get_file_extension("notes.txt") == ".txt"

    def test_uppercase_extension_is_lowered(self):
        parser = DocumentParser()
        assert parser._get_file_extension("REPORT.PDF") == ".pdf"
        assert parser._get_file_extension("Doc.DOCX") == ".docx"

    def test_no_extension(self):
        parser = DocumentParser()
        assert parser._get_file_extension("no_ext_file") == ""

    def test_empty_filename(self):
        parser = DocumentParser()
        assert parser._get_file_extension("") == ""
        assert parser._get_file_extension(None) == ""

    def test_multiple_dots(self):
        parser = DocumentParser()
        assert parser._get_file_extension("contract.v2.pdf") == ".pdf"


# ==================== 文本清洗 ====================


class TestTextCleaning:
    """文本清洗"""

    def test_normalize_line_endings(self):
        parser = DocumentParser()
        text = "line1\r\nline2\rline3\nline4"
        cleaned = parser._clean_text(text)
        assert "\r\n" not in cleaned
        assert "\r" not in cleaned
        lines = [l for l in cleaned.split("\n") if l]
        assert len(lines) == 4

    def test_compress_multiple_spaces(self):
        parser = DocumentParser()
        text = "甲方    应当      赔偿    乙方"
        cleaned = parser._clean_text(text)
        assert "     " not in cleaned
        assert "应当" in cleaned

    def test_strip_trailing_whitespace(self):
        parser = DocumentParser()
        text = "  条款一  \n  条款二  "
        cleaned = parser._clean_text(text)
        assert cleaned.startswith("条款一")
        assert cleaned.endswith("条款二")

    def test_remove_empty_lines(self):
        parser = DocumentParser()
        text = "第一条 权利\n\n\n第二条 义务\n   \n第三条 责任"
        cleaned = parser._clean_text(text)
        lines = cleaned.split("\n")
        assert "" not in lines
        assert "   " not in lines
        assert len(lines) == 3

    def test_empty_text(self):
        parser = DocumentParser()
        assert parser._clean_text("") == ""
        assert parser._clean_text(None) == ""


# ==================== 纯文本解析 ====================


class TestTxtParsing:
    """纯文本解析（编解码）"""

    def test_utf8_decoding(self):
        parser = DocumentParser()
        text = parser._parse_txt("合同条款：违约责任".encode("utf-8"))
        assert "违约责任" in text

    def test_gbk_decoding(self):
        parser = DocumentParser()
        text = parser._parse_txt("劳动合同法第47条".encode("gbk"))
        assert "劳动合同法" in text


# ==================== 支持的文件格式 ====================


class TestSupportedFormats:
    """支持的文件扩展名"""

    def test_supported_extensions_set(self):
        parser = DocumentParser()
        assert ".pdf" in parser.SUPPORTED_EXTENSIONS
        assert ".docx" in parser.SUPPORTED_EXTENSIONS
        assert ".doc" in parser.SUPPORTED_EXTENSIONS
        assert ".txt" in parser.SUPPORTED_EXTENSIONS

    def test_unsupported_formats_not_in_set(self):
        parser = DocumentParser()
        assert ".jpg" not in parser.SUPPORTED_EXTENSIONS
        assert ".png" not in parser.SUPPORTED_EXTENSIONS
        assert ".xlsx" not in parser.SUPPORTED_EXTENSIONS
