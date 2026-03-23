"""
文档管理路由
提供文档上传、入库、检索等接口
"""

from typing import Optional
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel, Field
from app.core.logger import app_logger
from app.services.document_parser import DocumentParser
from app.services.rag_service import get_rag_service


# 创建路由器
router = APIRouter(prefix="/document", tags=["文档管理"])


# ==================== 请求/响应模型 ====================

class UploadResponse(BaseModel):
    """文档上传响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    contract_id: str = Field(..., description="合同唯一标识")
    chunk_count: int = Field(..., description="切片数量")
    text_length: int = Field(..., description="文本总长度")


class RetrieveRequest(BaseModel):
    """检索请求"""
    query: str = Field(..., description="查询文本", min_length=1)
    contract_id: Optional[str] = Field(None, description="指定合同ID（可选）")
    top_k: int = Field(3, description="返回结果数量", ge=1, le=10)


class RetrieveResponse(BaseModel):
    """检索响应"""
    success: bool = Field(..., description="是否成功")
    query: str = Field(..., description="查询文本")
    results: list = Field(..., description="检索结果列表")
    result_count: int = Field(..., description="结果数量")


class ContractInfoResponse(BaseModel):
    """合同信息响应"""
    success: bool = Field(..., description="是否成功")
    contract_id: str = Field(..., description="合同ID")
    exists: bool = Field(..., description="是否存在")
    chunk_count: int = Field(..., description="切片数量")


class DeleteResponse(BaseModel):
    """删除响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    contract_id: str = Field(..., description="合同ID")
    deleted_count: int = Field(..., description="删除的切片数量")


class ContractListResponse(BaseModel):
    """合同列表响应"""
    success: bool = Field(..., description="是否成功")
    contracts: list = Field(..., description="合同ID列表")
    total_count: int = Field(..., description="合同总数")


# ==================== 路由端点 ====================

@router.post("/upload", response_model=UploadResponse, summary="上传并入库合同文档")
async def upload_document(
    file: UploadFile = File(..., description="上传的文档文件（支持 PDF、Word、图像）"),
    contract_id: Optional[str] = Query(None, description="自定义合同ID（可选，不提供则自动生成）")
):
    """
    上传合同文档并自动完成以下流程：
    
    **支持的文件格式：**
    - PDF (.pdf)
    - Word (.docx, .doc)
    - 图像 (.jpg, .jpeg, .png) - 使用多模态 Vision LLM 识别
    
    **处理流程：**
    1. 如果是图像文件，跳过传统文档解析器，直接使用 Vision LLM 识别
    2. 如果是 PDF/Word，使用传统解析器提取文本
    3. 向量化并存入 ChromaDB
    4. 返回合同ID和切片统计信息
    
    **返回信息：**
    - contract_id: 合同的唯一标识，用于后续检索
    - chunk_count: 切片数量
    - text_length: 文本总长度
    """
    try:
        app_logger.info(f"📤 收到文件上传请求: {file.filename}")
        
        # 获取文件扩展名
        file_extension = Path(file.filename or "").suffix.lower()
        
        # 判断是否为图像文件
        is_image = file_extension in {'.jpg', '.jpeg', '.png', '.webp'}
        
        if is_image:
            # 图像文件：读取二进制数据，暂存到元数据中
            app_logger.info(f"🖼️  检测到图像文件，将在审查时使用 Vision LLM 识别")
            image_data = await file.read()
            
            if not image_data:
                raise HTTPException(status_code=400, detail="图像文件为空")
            
            # 为图像文件创建一个占位文本（实际识别在审查时进行）
            text = f"[图像合同占位符 - 文件名: {file.filename}]"
            
            # 入库到向量数据库（带图像标记）
            rag_service = get_rag_service()
            result = rag_service.ingest_contract(
                text=text,
                contract_id=contract_id,
                metadata={
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "is_image": True,
                    "image_format": file_extension.lstrip('.')
                }
            )
            
            return UploadResponse(
                success=True,
                message="图像文件上传成功，将在审查时进行 OCR 识别",
                contract_id=result["contract_id"],
                chunk_count=result["chunk_count"],
                text_length=len(image_data)
            )
        
        else:
            # 传统文档：使用文档解析器
            parser = DocumentParser()
            text = await parser.parse_file(file)
            
            if not text or not text.strip():
                raise HTTPException(status_code=400, detail="文档内容为空，无法入库")
            
            # 入库到向量数据库
            rag_service = get_rag_service()
            result = rag_service.ingest_contract(
                text=text,
                contract_id=contract_id,
                metadata={
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "is_image": False
                }
            )
            
            if result["status"] == "empty":
                raise HTTPException(status_code=400, detail="文档切片结果为空，无法入库")
            
            return UploadResponse(
                success=True,
                message="文档上传并入库成功",
                contract_id=result["contract_id"],
                chunk_count=result["chunk_count"],
                text_length=len(text)
            )
    
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"❌ 文档上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文档上传失败: {str(e)}")


@router.post("/retrieve", response_model=RetrieveResponse, summary="检索相关合同条款")
async def retrieve_clauses(request: RetrieveRequest):
    """
    根据查询文本检索最相关的合同条款
    
    **参数说明：**
    - query: 查询文本（必填）
    - contract_id: 指定合同ID，如果提供则只在该合同中检索（可选）
    - top_k: 返回最相关的前 K 个结果（默认 3，最大 10）
    
    **返回信息：**
    - results: 检索结果列表，每个结果包含：
      - text: 条款原文
      - metadata: 元数据（章节、条款编号等）
      - similarity: 相似度分数（0-1，越大越相似）
    """
    try:
        app_logger.info(f"🔍 收到检索请求: {request.query[:50]}...")
        
        # 执行检索
        rag_service = get_rag_service()
        results = await rag_service.retrieve_clauses(
            query=request.query,
            contract_id=request.contract_id,
            top_k=request.top_k
        )
        
        return RetrieveResponse(
            success=True,
            query=request.query,
            results=results,
            result_count=len(results)
        )
    
    except Exception as e:
        app_logger.error(f"❌ 检索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")


@router.get("/info/{contract_id}", response_model=ContractInfoResponse, summary="获取合同信息")
async def get_contract_info(contract_id: str):
    """
    获取指定合同的基本信息
    
    **返回信息：**
    - exists: 合同是否存在
    - chunk_count: 切片数量
    """
    try:
        rag_service = get_rag_service()
        info = rag_service.get_contract_info(contract_id)
        
        return ContractInfoResponse(
            success=True,
            contract_id=contract_id,
            exists=info["exists"],
            chunk_count=info["chunk_count"]
        )
    
    except Exception as e:
        app_logger.error(f"❌ 获取合同信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取合同信息失败: {str(e)}")


@router.delete("/delete/{contract_id}", response_model=DeleteResponse, summary="删除合同")
async def delete_contract(contract_id: str):
    """
    删除指定合同的所有数据
    
    **注意：** 此操作不可逆，请谨慎使用
    """
    try:
        app_logger.info(f"🗑️  收到删除请求: {contract_id}")
        
        rag_service = get_rag_service()
        result = rag_service.delete_contract(contract_id)
        
        if result["status"] == "not_found":
            raise HTTPException(status_code=404, detail=f"合同 {contract_id} 不存在")
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result.get("error", "删除失败"))
        
        return DeleteResponse(
            success=True,
            message="合同删除成功",
            contract_id=contract_id,
            deleted_count=result["deleted_count"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"❌ 删除合同失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除合同失败: {str(e)}")


@router.get("/list", response_model=ContractListResponse, summary="列出所有合同")
async def list_contracts():
    """
    列出所有已存储的合同ID
    
    **返回信息：**
    - contracts: 合同ID列表
    - total_count: 合同总数
    """
    try:
        rag_service = get_rag_service()
        contracts = rag_service.list_contracts()
        
        return ContractListResponse(
            success=True,
            contracts=contracts,
            total_count=len(contracts)
        )
    
    except Exception as e:
        app_logger.error(f"❌ 列出合同失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"列出合同失败: {str(e)}")


# 导出路由器
__all__ = ["router"]
