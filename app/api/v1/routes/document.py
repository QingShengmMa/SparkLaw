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

router = APIRouter(prefix="/document", tags=["文档管理"])


class UploadResponse(BaseModel):
    success: bool
    message: str
    contract_id: str
    chunk_count: int
    text_length: int


class RetrieveRequest(BaseModel):
    query: str = Field(..., description="检索查询")
    contract_id: Optional[str] = Field(default=None, description="合同ID过滤")
    top_k: int = Field(default=5, description="返回数量")


class RetrieveResponse(BaseModel):
    success: bool
    query: str
    results: list
    result_count: int


@router.post("/upload", response_model=UploadResponse, summary="上传并解析文档")
async def upload_document(
    file: UploadFile = File(...),
    contract_id: Optional[str] = Query(default=None),
):
    import uuid
    parser = DocumentParser()
    rag = get_rag_service()
    try:
        text = await parser.parse_file(file)
        cid = contract_id or str(uuid.uuid4())
        chunks = await rag.add_document(text=text, contract_id=cid)
        app_logger.info(f"文档入库成功: {cid}, chunks={chunks}")
        return UploadResponse(
            success=True, message="文档解析并入库成功",
            contract_id=cid, chunk_count=chunks, text_length=len(text),
        )
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"文档上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrieve", response_model=RetrieveResponse, summary="检索文档")
async def retrieve_clauses(request: RetrieveRequest):
    rag = get_rag_service()
    try:
        results = await rag.retrieve_clauses(
            query=request.query,
            top_k=request.top_k,
            contract_id=request.contract_id,
        )
        return RetrieveResponse(
            success=True, query=request.query,
            results=results, result_count=len(results),
        )
    except Exception as e:
        app_logger.error(f"检索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
