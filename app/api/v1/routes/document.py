"""
文档管理路由
提供文档上传、入库、检索、列表、删除等接口
同时提供法律条文库的独立管理接口
"""
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel, Field
from app.core.logger import app_logger
from app.services.document_parser import DocumentParser
from app.services.rag_service import get_rag_service

router = APIRouter(prefix="/document", tags=["文档管理"])


# ── 合同库响应模型 ─────────────────────────────────────────────

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


class DeleteResponse(BaseModel):
    success: bool
    contract_id: str
    deleted_count: int
    message: str


class ListResponse(BaseModel):
    success: bool
    contracts: list
    total: int


class ResetResponse(BaseModel):
    success: bool
    message: str


# ── 法律条文库响应模型 ──────────────────────────────────────────

class LawUploadResponse(BaseModel):
    success: bool
    message: str
    law_name: str
    chunk_count: int
    text_length: int


class LawListResponse(BaseModel):
    success: bool
    laws: list
    total: int


class LawDeleteResponse(BaseModel):
    success: bool
    law_name: str
    deleted_count: int
    message: str


class LawRetrieveRequest(BaseModel):
    query: str = Field(..., description="检索查询")
    law_name: Optional[str] = Field(default=None, description="限定法律名称")
    top_k: int = Field(default=5, description="返回数量")


# ── 合同库接口 ─────────────────────────────────────────────────

@router.post("/upload", response_model=UploadResponse, summary="上传并解析合同文档")
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


@router.post("/retrieve", response_model=RetrieveResponse, summary="检索合同文档")
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


@router.get("/list", response_model=ListResponse, summary="列出所有已入库合同文档")
async def list_documents():
    rag = get_rag_service()
    try:
        contracts = rag.list_contracts()
        return ListResponse(success=True, contracts=contracts, total=len(contracts))
    except Exception as e:
        app_logger.error(f"列出文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{contract_id}", response_model=DeleteResponse, summary="删除指定合同文档")
async def delete_document(contract_id: str):
    rag = get_rag_service()
    try:
        result = rag.delete_contract(contract_id)
        if result["status"] == "not_found":
            raise HTTPException(status_code=404, detail=f"文档 {contract_id} 不存在")
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result.get("error", "删除失败"))
        return DeleteResponse(
            success=True,
            contract_id=contract_id,
            deleted_count=result["deleted_count"],
            message=f"已删除 {result['deleted_count']} 个向量片段",
        )
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/reset-all", response_model=ResetResponse, summary="清空合同向量库（危险操作）")
async def reset_all_documents():
    """清空合同向量库中所有文档，用于清除污染数据。"""
    rag = get_rag_service()
    try:
        contracts = rag.list_contracts()
        total_deleted = 0
        for cid in contracts:
            result = rag.delete_contract(cid)
            total_deleted += result.get("deleted_count", 0)
        app_logger.info(f"向量库已清空，共删除 {total_deleted} 个片段，涉及 {len(contracts)} 个文档")
        return ResetResponse(
            success=True,
            message=f"已清空 {len(contracts)} 个文档，共 {total_deleted} 个向量片段",
        )
    except Exception as e:
        app_logger.error(f"清空向量库失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── 法律条文库接口 ──────────────────────────────────────────────

@router.post("/upload-law", response_model=LawUploadResponse, summary="上传法律条文文件入库")
async def upload_law(
    file: UploadFile = File(...),
    law_name: Optional[str] = Query(default=None, description="法律名称，默认使用文件名"),
):
    """
    上传 PDF/Word/TXT 法律条文文件，解析后存入独立的法律条文向量库。
    同名法律自动覆盖旧版本（幂等）。支持格式：PDF、DOCX、TXT。
    """
    parser = DocumentParser()
    rag = get_rag_service()
    try:
        text = await parser.parse_file(file)
        name = (law_name or "").strip() or (file.filename or "").rsplit(".", 1)[0] or "未命名法律"
        result = rag.ingest_law(text=text, law_name=name, source=file.filename or name)
        app_logger.info(f"法律条文入库成功: {name}, chunks={result['chunk_count']}")
        return LawUploadResponse(
            success=True,
            message=f"法律条文「{name}」入库成功",
            law_name=name,
            chunk_count=result["chunk_count"],
            text_length=len(text),
        )
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"法律条文上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrieve-law", response_model=RetrieveResponse, summary="检索法律条文库")
async def retrieve_law(request: LawRetrieveRequest):
    """从法律条文向量库检索相关法条，不混入合同数据。"""
    rag = get_rag_service()
    try:
        results = await rag.retrieve_law(
            query=request.query,
            top_k=request.top_k,
            law_name=request.law_name,
        )
        return RetrieveResponse(
            success=True, query=request.query,
            results=results, result_count=len(results),
        )
    except Exception as e:
        app_logger.error(f"法律条文检索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list-laws", response_model=LawListResponse, summary="列出已入库的法律条文")
async def list_laws():
    rag = get_rag_service()
    try:
        laws = rag.list_laws()
        return LawListResponse(success=True, laws=laws, total=len(laws))
    except Exception as e:
        app_logger.error(f"列出法律条文失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete-law/{law_name}", response_model=LawDeleteResponse, summary="删除指定法律条文")
async def delete_law(law_name: str):
    rag = get_rag_service()
    try:
        result = rag.delete_law(law_name)
        if result["status"] == "not_found":
            raise HTTPException(status_code=404, detail=f"法律「{law_name}」不存在")
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result.get("error", "删除失败"))
        return LawDeleteResponse(
            success=True,
            law_name=law_name,
            deleted_count=result["deleted_count"],
            message=f"已删除「{law_name}」{result['deleted_count']} 个向量片段",
        )
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"删除法律条文失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
