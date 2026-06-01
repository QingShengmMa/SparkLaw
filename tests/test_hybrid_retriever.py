"""
混合检索器单元测试
测试 Vector + BM25 + RRF 融合功能
"""

import pytest
from app.knowledge.retrievers.hybrid_retriever import HybridRetriever


def test_bm25_index_building():
    """测试 BM25 索引构建"""
    retriever = HybridRetriever()
    
    documents = [
        "合同第一条规定了双方的权利义务",
        "违约责任条款明确了赔偿标准",
        "保密协议要求双方保护商业秘密",
    ]
    
    retriever.build_bm25_index(documents)
    
    assert retriever.bm25_index is not None
    assert len(retriever.corpus_texts) == 3


def test_bm25_retrieve():
    """测试 BM25 检索功能"""
    retriever = HybridRetriever()
    
    documents = [
        "合同第一条规定了双方的权利义务",
        "违约责任条款明确了赔偿标准",
        "保密协议要求双方保护商业秘密",
    ]
    
    retriever.build_bm25_index(documents)
    
    # 测试关键词检索
    results = retriever.bm25_retrieve("违约责任", top_k=2)
    
    assert len(results) > 0
    assert "违约责任" in results[0]["text"]
    assert "bm25_score" in results[0]


def test_rrf_fusion():
    """测试 RRF 融合算法"""
    retriever = HybridRetriever(k=60)
    
    vector_results = [
        {"text": "文档A", "similarity": 0.9, "metadata": {}},
        {"text": "文档B", "similarity": 0.8, "metadata": {}},
        {"text": "文档C", "similarity": 0.7, "metadata": {}},
    ]
    
    bm25_results = [
        {"text": "文档B", "bm25_score": 15.5},
        {"text": "文档D", "bm25_score": 12.3},
        {"text": "文档A", "bm25_score": 10.1},
    ]
    
    fused = retriever.rrf_fusion(vector_results, bm25_results, top_k=3)
    
    assert len(fused) == 3
    assert "rrf_score" in fused[0]
    
    # 文档B 在两个列表中都排名靠前，应该得分最高
    assert fused[0]["text"] in ["文档A", "文档B"]


def test_hybrid_retrieve():
    """测试完整的混合检索流程"""
    retriever = HybridRetriever()
    
    # 模拟向量检索结果
    vector_results = [
        {"text": "合同第一条规定了双方的权利义务", "similarity": 0.85, "metadata": {}},
        {"text": "违约责任条款明确了赔偿标准", "similarity": 0.80, "metadata": {}},
        {"text": "保密协议要求双方保护商业秘密", "similarity": 0.75, "metadata": {}},
    ]
    
    query = "违约赔偿"
    
    # 执行混合检索
    results = retriever.hybrid_retrieve(
        query=query,
        vector_results=vector_results,
        top_k=2,
        bm25_top_k=3,
    )
    
    assert len(results) <= 2
    assert "rrf_score" in results[0]
    assert "text" in results[0]


def test_tokenize():
    """测试分词器"""
    retriever = HybridRetriever()
    
    # 测试中文分词
    tokens_zh = retriever._tokenize("合同违约责任")
    assert "合" in tokens_zh
    assert "同" in tokens_zh
    
    # 测试英文分词
    tokens_en = retriever._tokenize("contract breach liability")
    assert "contract" in tokens_en
    assert "breach" in tokens_en


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
