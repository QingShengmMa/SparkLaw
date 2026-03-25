"""
智能分析路由
提供合同审查和多智能体辩论接口
"""
import json
from typing import Optional, Any
from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException, Header, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.workers.celery_app import celery_app
from app.core.logger import app_logger
from app.services.contract_reviewer import get_contract_reviewer
from app.services.multimodal_contract_reviewer import (
    multimodal_contract_review_task,
    get_multimodal_reviewer,
    load_contract_text_from_vector_store,
)
from app.services.court_agent import get_court_agent
from app.models.response import (
    ContractReviewResponse,
    ReviewTaskSubmitResponse,
    ReviewTaskStatusResponse,
    DebateResponse,
)

router = APIRouter(prefix="/analysis", tags=["智能分析"])


class DebateRequest(BaseModel):
    case_description: str = Field(..., description="案情描述")


class CourtDebateRequest(BaseModel):
    case_description: str = Field(..., description="案情描述")
    plaintiff_name: Optional[str] = Field(default="原告", description="原告名称")
    defendant_name: Optional[str] = Field(default="被告", description="被告名称")
    strategy: Optional[str] = Field(default="aggressive", description="辩论策略")
    human_evidence: Optional[list] = Field(default=None, description="人工证据列表")


def _auto_fill_party_evidence(human_evidence: Optional[list]) -> tuple[list, bool, bool]:
    evidence = list(human_evidence or [])

    def _party_of(item: Any) -> str:
        return str((item or {}).get("party") or "").strip().lower()

    has_plaintiff = any(_party_of(item) == "plaintiff" for item in evidence)
    has_defendant = any(_party_of(item) == "defendant" for item in evidence)

    if not has_plaintiff:
        evidence.extend([
            {
                "id": "auto_plaintiff_1",
                "party": "plaintiff",
                "name": "原告主张沟通记录",
                "desc": "可能包括聊天记录、邮件或函件，用于证明原告曾明确提出主张并通知被告。",
            },
            {
                "id": "auto_plaintiff_2",
                "party": "plaintiff",
                "name": "原告履约或付款凭证",
                "desc": "可能包括转账记录、收据、合同附件等，用于证明原告已履行相应义务或发生实际损失。",
            },
        ])

    if not has_defendant:
        evidence.extend([
            {
                "id": "auto_defendant_1",
                "party": "defendant",
                "name": "被告抗辩事实材料",
                "desc": "可能包括考勤记录、业务日志、履约记录等，用于支撑被告对关键事实的抗辩。",
            },
            {
                "id": "auto_defendant_2",
                "party": "defendant",
                "name": "被告制度与告知文件",
                "desc": "可能包括制度公告、通知记录、签收凭据等，用于证明被告已履行管理或告知义务。",
            },
        ])

    return evidence, (not has_plaintiff), (not has_defendant)


def _build_case_description_with_evidence(case_description: str, evidence: list) -> str:
    plaintiff_lines = [
        f"- {item.get('name', '未命名证据')}：{item.get('desc', '')}"
        for item in evidence
        if str(item.get("party") or "").strip().lower() == "plaintiff"
    ]
    defendant_lines = [
        f"- {item.get('name', '未命名证据')}：{item.get('desc', '')}"
        for item in evidence
        if str(item.get("party") or "").strip().lower() == "defendant"
    ]

    return (
        f"{case_description}\n\n"
        "[原告证据清单]\n"
        + ("\n".join(plaintiff_lines) if plaintiff_lines else "- 无")
        + "\n\n[被告证据清单]\n"
        + ("\n".join(defendant_lines) if defendant_lines else "- 无")
    )


class ContractReviewStreamRequest(BaseModel):
    contract_id: Optional[str] = Field(default=None, description="已上传合同的 contract_id")
    contract_text: Optional[str] = Field(default=None, description="直接传入的合同文本")
    template_id: Optional[str] = Field(default=None, description="示例合同模板 ID")


# ─── 合同审查 SSE 流式接口 ──────────────────────────────────────────────

# ─── 示例合同模板接口 ──────────────────────────────────────────────────

import asyncio
from pathlib import Path as _Path

_TEMPLATES_DIR = _Path(__file__).parent.parent.parent.parent.parent / "app" / "data" / "templates"
_TEMPLATE_MAP = {
    "housing_lease": "housing_lease.txt",
    "labor_contract": "labor_contract.txt",
    "purchase_agreement": "purchase_agreement.txt",
}


@router.get("/template/{template_id}", summary="获取示例合同原文")
async def get_template(template_id: str):
    """返回指定示例合同的纯文本内容，用于前端预览。"""
    if template_id not in _TEMPLATE_MAP:
        raise HTTPException(status_code=404, detail=f"模板 {template_id} 不存在")
    file_path = _TEMPLATES_DIR / _TEMPLATE_MAP[template_id]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="模板文件不存在")
    text = file_path.read_text(encoding="utf-8")
    return {"template_id": template_id, "content": text}


@router.post("/review/stream", summary="合同审查 SSE 流式（无需 Celery/Redis）")
async def review_contract_stream(
    request: ContractReviewStreamRequest,
    x_api_key: Optional[str] = Header(default=None),
    x_api_base_url: Optional[str] = Header(default=None),
    x_api_model: Optional[str] = Header(default=None),
):
    """
    SSE 流式合同审查接口。
    先流式返回日志事件（type=log），最后返回完整结果（type=result）。
    输入：contract_id 或 contract_text 二选一。
    """
    async def generate():
        def sse(event_type: str, payload: Any) -> str:
            return f"data: {json.dumps({'type': event_type, **payload}, ensure_ascii=False)}\n\n"

        try:
            reviewer = get_multimodal_reviewer()

            # 获取合同文本
            if request.contract_text:
                contract_text = request.contract_text
                contract_id = "inline_text"
            elif request.template_id:
                yield sse("log", {"progress": 5, "message": f"正在加载示例合同：{request.template_id}..."})
                if request.template_id not in _TEMPLATE_MAP:
                    yield sse("error", {"message": f"模板 {request.template_id} 不存在"})
                    return
                file_path = _TEMPLATES_DIR / _TEMPLATE_MAP[request.template_id]
                contract_text = file_path.read_text(encoding="utf-8")
                contract_id = request.template_id
            elif request.contract_id:
                yield sse("log", {"progress": 5, "message": "正在从向量库加载合同内容..."})
                contract_text = load_contract_text_from_vector_store(request.contract_id)
                contract_id = request.contract_id
            else:
                yield sse("error", {"message": "请提供 contract_id、template_id 或 contract_text"})
                return

            yield sse("log", {"progress": 10, "message": "文档解析完成，正在加载待审条款..."})
            await asyncio.sleep(0.05)

            yield sse("log", {"progress": 25, "message": "正在识别合同类型与双方主体..."})
            await asyncio.sleep(0.05)

            yield sse("log", {"progress": 40, "message": "正在提取关键条款，匹配【民法典】相关条文..."})
            await asyncio.sleep(0.05)

            yield sse("log", {"progress": 55, "message": "正在检查违约金条款、俧权条款及管辖权内容..."})
            await asyncio.sleep(0.05)

            yield sse("log", {"progress": 70, "message": "调用大模型进行法务风险分析..."})

            # 调用审查器
            result: ContractReviewResponse = await reviewer.review_from_text(contract_text, contract_id)

            yield sse("log", {"progress": 90, "message": "正在整理风险条款与修改建议..."})
            await asyncio.sleep(0.05)

            yield sse("log", {"progress": 98, "message": f"审查完成，共发现 {len(result.risks)} 个风险点。"})
            await asyncio.sleep(0.05)

            # 将建立的内部模型转换为前端期望的格式
            risks_payload = []
            for i, risk in enumerate(result.risks):
                severity = (
                    "High Risk" if risk.risk_level.value == "high"
                    else "Medium Risk" if risk.risk_level.value == "medium"
                    else "Low Risk"
                )
                risks_payload.append({
                    "id": str(i + 1),
                    "severity": severity,
                    "title": risk.clause_text[:30].rstrip("，。;") + ("…" if len(risk.clause_text) > 30 else ""),
                    "originalText": risk.clause_text,
                    "analysis": risk.risk_analysis,
                    "suggestion": risk.revision_suggestion,
                    # 兼容旧字段
                    "risk_level": risk.risk_level.value,
                    "clause_text": risk.clause_text,
                    "risk_analysis": risk.risk_analysis,
                    "revision_suggestion": risk.revision_suggestion,
                })

            high_count = sum(1 for r in result.risks if r.risk_level.value == "high")
            mid_count = sum(1 for r in result.risks if r.risk_level.value == "medium")
            score = max(10, 100 - high_count * 20 - mid_count * 8)

            yield sse("result", {
                "score": score,
                "riskCount": len(result.risks),
                "overall_summary": result.overall_summary,
                "contract_id": contract_id,
                "risks": risks_payload,
                "processing_steps": result.processing_steps,
            })

        except ValueError as e:
            app_logger.error(f"合同审查 SSE 失败（参数错误）: {e}")
            yield sse("error", {"message": str(e)})
        except Exception as e:
            app_logger.error(f"合同审查 SSE 失败: {e}")
            yield sse("error", {"message": f"审查失败：{str(e)}"})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ─── 合同审查（Celery 异步，兼容旧接口）─────────────────────────────────

@router.post("/review/{contract_id}", response_model=ReviewTaskSubmitResponse, summary="提交合同审查任务")
async def submit_review(contract_id: str):
    try:
        task = multimodal_contract_review_task.delay(contract_id)
        return ReviewTaskSubmitResponse(task_id=task.id, status="processing")
    except Exception as e:
        app_logger.error(f"提交审查任务失败: {e}")
        raise HTTPException(status_code=503, detail=f"审查队列暂时不可用: {str(e)}")


@router.get("/review/status/{task_id}", response_model=ReviewTaskStatusResponse, summary="查询审查任务状态")
async def get_review_status(task_id: str):
    try:
        result = AsyncResult(task_id, app=celery_app)
        if result.state == "PENDING":
            return ReviewTaskStatusResponse(task_id=task_id, status="processing", progress=0, message="任务排队中...")
        elif result.state == "PROGRESS":
            meta = result.info or {}
            return ReviewTaskStatusResponse(
                task_id=task_id, status="processing",
                progress=meta.get("progress", 0), message=meta.get("message", "处理中..."),
            )
        elif result.state == "SUCCESS":
            return ReviewTaskStatusResponse(
                task_id=task_id, status="success", progress=100, message="审查完成",
                result=result.result,
            )
        else:
            return ReviewTaskStatusResponse(
                task_id=task_id, status="failed", progress=0,
                message="任务失败", error=str(result.info),
            )
    except Exception as e:
        app_logger.error(f"查询任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── 模拟法庭 ────────────────────────────────────────────────────────────────────

@router.post("/debate", response_model=DebateResponse, summary="多智能体法律辩论")
async def debate(request: DebateRequest):
    from app.services.supervisor_agent import get_supervisor_agent
    try:
        agent = get_supervisor_agent()
        result = await agent.run(request.case_description)
        return result
    except Exception as e:
        app_logger.error(f"辩论失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/debate/court", summary="模拟庭审（流式 SSE）")
async def court_debate(
    request: CourtDebateRequest,
    x_api_key: Optional[str] = Header(default=None),
    x_api_base_url: Optional[str] = Header(default=None),
    x_api_model: Optional[str] = Header(default=None),
):
    _ = (x_api_key, x_api_base_url, x_api_model)

    async def generate():
        try:
            agent = get_court_agent()
            merged_evidence, auto_plaintiff, auto_defendant = _auto_fill_party_evidence(request.human_evidence)
            case_description = _build_case_description_with_evidence(request.case_description, merged_evidence)

            if auto_plaintiff:
                yield f"data: {json.dumps({'type': 'log', 'message': '未检测到原告证据，SparkLaw 已自动补充原告可能证据。'}, ensure_ascii=False)}\n\n"
            if auto_defendant:
                yield f"data: {json.dumps({'type': 'log', 'message': '未检测到被告证据，SparkLaw 已自动补充被告可能证据。'}, ensure_ascii=False)}\n\n"

            async for event in agent.stream(
                case_description=case_description,
                plaintiff_name=request.plaintiff_name or "原告",
                defendant_name=request.defendant_name or "被告",
                strategy=request.strategy or "aggressive",
                human_evidence=merged_evidence,
                custom_config=custom_config,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            app_logger.error(f"庭审流式输出错误: {e}")
            yield f"data: {json.dumps({'type':'error','message':str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/debate/court/rejudge", summary="补充证据重新庭审（流式 SSE）")
async def court_debate_rejudge(
    request: CourtDebateRequest,
    x_api_key: Optional[str] = Header(default=None),
    x_api_base_url: Optional[str] = Header(default=None),
    x_api_model: Optional[str] = Header(default=None),
):
    return await court_debate(request, x_api_key=x_api_key, x_api_base_url=x_api_base_url, x_api_model=x_api_model) 