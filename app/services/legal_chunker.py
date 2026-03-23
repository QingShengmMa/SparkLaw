"""
法律文档结构化切片器
专门针对中文合同与法律条文的语义完整性切片
"""

import re
from typing import List, Tuple
from app.core.logger import app_logger


class LegalChunker:
    """
    法律文档智能切片器
    
    核心特性：
    1. 基于正则表达式识别中文法律文档的层级结构
    2. 按照"章"、"条"、"款"等法律单元进行切片
    3. 保证每个切片的法律语义完整性
    4. 避免简单的字数切分导致的语义破坏
    """
    
    # 章节标题正则：匹配"第X章"、"第X节"等
    CHAPTER_PATTERN = re.compile(
        r"第[一二三四五六七八九十百千万零壹贰叁肆伍陆柒捌玖拾佰仟萬\d]+[章节篇编部分]"
    )
    
    # 条款标题正则：匹配"第X条"
    ARTICLE_PATTERN = re.compile(
        r"第[一二三四五六七八九十百千万零壹贰叁肆伍陆柒捌玖拾佰仟萬\d]+条"
    )
    
    # 款项标题正则：匹配"（一）"、"(1)"、"1."、"一、"等
    CLAUSE_PATTERN = re.compile(
        r"^[\(（]?[一二三四五六七八九十\d]+[\)）]?[、\.]"
    )
    
    # 最小切片长度（字符数）
    MIN_CHUNK_SIZE = 50
    
    # 最大切片长度（字符数）
    MAX_CHUNK_SIZE = 1500
    
    def __init__(self):
        """初始化法律切片器"""
        app_logger.info("⚖️  LegalChunker 初始化完成")
    
    def chunk_text(self, text: str) -> List[str]:
        """
        对法律文本进行结构化切片
        
        Args:
            text: 完整的法律文档文本
            
        Returns:
            List[str]: 切片后的文本列表，每个元素是一个语义完整的法律单元
        """
        if not text or not text.strip():
            app_logger.warning("⚠️  输入文本为空，返回空列表")
            return []
        
        app_logger.info(f"开始法律文档切片，原文长度: {len(text)} 字符")
        
        # 第一步：按行分割
        lines = text.split("\n")
        
        # 第二步：识别结构并分组
        chunks = self._split_by_structure(lines)
        
        # 第三步：合并过小的切片
        chunks = self._merge_small_chunks(chunks)
        
        # 第四步：拆分过大的切片
        chunks = self._split_large_chunks(chunks)
        
        # 过滤空切片
        chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
        
        app_logger.info(f"✅ 切片完成，共生成 {len(chunks)} 个切片")
        
        return chunks
    
    def _split_by_structure(self, lines: List[str]) -> List[str]:
        """
        根据法律文档结构进行初步切片
        
        Args:
            lines: 文本行列表
            
        Returns:
            List[str]: 初步切片结果
        """
        chunks = []
        current_chunk = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检查是否是章节标题
            if self.CHAPTER_PATTERN.search(line):
                # 保存当前切片
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = []
                # 开始新切片（章节标题作为开头）
                current_chunk.append(line)
                app_logger.debug(f"检测到章节: {line}")
            
            # 检查是否是条款标题
            elif self.ARTICLE_PATTERN.search(line):
                # 保存当前切片
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = []
                # 开始新切片（条款标题作为开头）
                current_chunk.append(line)
                app_logger.debug(f"检测到条款: {line}")
            
            # 普通内容行
            else:
                current_chunk.append(line)
        
        # 保存最后一个切片
        if current_chunk:
            chunks.append("\n".join(current_chunk))
        
        return chunks
    
    def _merge_small_chunks(self, chunks: List[str]) -> List[str]:
        """
        合并过小的切片，避免碎片化
        
        Args:
            chunks: 初步切片列表
            
        Returns:
            List[str]: 合并后的切片列表
        """
        if not chunks:
            return []
        
        merged = []
        buffer = []
        buffer_size = 0
        
        for chunk in chunks:
            chunk_size = len(chunk)
            
            # 如果当前切片足够大，直接添加
            if chunk_size >= self.MIN_CHUNK_SIZE:
                # 先清空缓冲区
                if buffer:
                    merged.append("\n".join(buffer))
                    buffer = []
                    buffer_size = 0
                # 添加当前切片
                merged.append(chunk)
            
            # 如果当前切片太小，加入缓冲区
            else:
                buffer.append(chunk)
                buffer_size += chunk_size
                
                # 缓冲区达到最小大小，合并输出
                if buffer_size >= self.MIN_CHUNK_SIZE:
                    merged.append("\n".join(buffer))
                    buffer = []
                    buffer_size = 0
        
        # 处理剩余的缓冲区
        if buffer:
            if merged:
                # 合并到最后一个切片
                merged[-1] = merged[-1] + "\n" + "\n".join(buffer)
            else:
                # 没有其他切片，直接添加
                merged.append("\n".join(buffer))
        
        return merged
    
    def _split_large_chunks(self, chunks: List[str]) -> List[str]:
        """
        拆分过大的切片，避免超出模型上下文限制
        
        Args:
            chunks: 切片列表
            
        Returns:
            List[str]: 拆分后的切片列表
        """
        result = []
        
        for chunk in chunks:
            if len(chunk) <= self.MAX_CHUNK_SIZE:
                result.append(chunk)
            else:
                # 对超大切片进行二次切分
                sub_chunks = self._split_large_chunk(chunk)
                result.extend(sub_chunks)
        
        return result
    
    def _split_large_chunk(self, chunk: str) -> List[str]:
        """
        拆分单个超大切片
        
        策略：
        1. 优先按款项（一、二、三）切分
        2. 其次按句号切分
        3. 最后按字数强制切分
        
        Args:
            chunk: 超大切片
            
        Returns:
            List[str]: 拆分后的子切片列表
        """
        lines = chunk.split("\n")
        sub_chunks = []
        current_sub = []
        current_size = 0
        
        for line in lines:
            line_size = len(line)
            
            # 如果加上这行会超出限制
            if current_size + line_size > self.MAX_CHUNK_SIZE and current_sub:
                # 保存当前子切片
                sub_chunks.append("\n".join(current_sub))
                current_sub = [line]
                current_size = line_size
            else:
                current_sub.append(line)
                current_size += line_size
        
        # 保存最后一个子切片
        if current_sub:
            sub_chunks.append("\n".join(current_sub))
        
        # 如果还有超大的子切片，按句号强制切分
        final_chunks = []
        for sub in sub_chunks:
            if len(sub) <= self.MAX_CHUNK_SIZE:
                final_chunks.append(sub)
            else:
                # 按句号切分
                sentences = re.split(r"([。！？；])", sub)
                temp_chunk = ""
                for i in range(0, len(sentences), 2):
                    sentence = sentences[i]
                    punctuation = sentences[i + 1] if i + 1 < len(sentences) else ""
                    
                    if len(temp_chunk) + len(sentence) + len(punctuation) > self.MAX_CHUNK_SIZE:
                        if temp_chunk:
                            final_chunks.append(temp_chunk)
                        temp_chunk = sentence + punctuation
                    else:
                        temp_chunk += sentence + punctuation
                
                if temp_chunk:
                    final_chunks.append(temp_chunk)
        
        return final_chunks
    
    def get_chunk_metadata(self, chunk: str) -> dict:
        """
        提取切片的元数据（章节、条款信息）
        
        Args:
            chunk: 切片文本
            
        Returns:
            dict: 元数据字典
        """
        metadata = {
            "chapter": None,
            "article": None,
            "length": len(chunk)
        }
        
        # 提取章节信息
        chapter_match = self.CHAPTER_PATTERN.search(chunk)
        if chapter_match:
            metadata["chapter"] = chapter_match.group()
        
        # 提取条款信息
        article_match = self.ARTICLE_PATTERN.search(chunk)
        if article_match:
            metadata["article"] = article_match.group()
        
        return metadata
