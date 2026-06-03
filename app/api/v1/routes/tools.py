"""
智能分析路由
提供合同审查和多智能体辩论接口
"""
import json
import re
from typing import Optional, Any
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.auth.dependencies import require_usage_context
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

router = APIRouter(
    prefix="/analysis",
    tags=["智能分析"],
    dependencies=[Depends(require_usage_context)],
)


class DebateRequest(BaseModel):
    case_description: str = Field(..., description="案情描述")


class CourtDebateRequest(BaseModel):
    case_description: str = Field(..., description="案情描述")
    plaintiff_name: Optional[str] = Field(default="原告", description="原告名称")
    defendant_name: Optional[str] = Field(default="被告", description="被告名称")
    strategy: Optional[str] = Field(default="aggressive", description="辩论策略")
    human_evidence: Optional[list] = Field(default=None, description="人工证据列表")
    session_id: Optional[str] = Field(default=None, description="会话ID（前端透传）")


class CourtRejudgeRequest(CourtDebateRequest):
    thread_id: Optional[str] = Field(default=None, description="庭审线程ID（可选）")


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


def _extract_retry_wait_seconds(error_text: str) -> Optional[int]:
    text = error_text or ""
    match = re.search(r"Please try again in\s*([0-9]+)m([0-9]+(?:\.[0-9]+)?)s", text)
    if match:
        minutes = int(match.group(1))
        seconds = float(match.group(2))
        return int(minutes * 60 + seconds + 1)

    match = re.search(r"Please try again in\s*([0-9]+(?:\.[0-9]+)?)s", text)
    if match:
        return int(float(match.group(1)) + 1)

    return None


def _friendly_stream_error_message(error_text: str) -> str:
    text = error_text or ""
    if "rate_limit" in text.lower() or "Rate limit" in text:
        wait_seconds = _extract_retry_wait_seconds(text)
        if wait_seconds:
            minutes, seconds = divmod(wait_seconds, 60)
            if minutes > 0:
                return f"当前模型调用频率已达上限，请约 {minutes} 分 {seconds} 秒后重试（或切换模型）。"
            return f"当前模型调用频率已达上限，请约 {seconds} 秒后重试（或切换模型）。"
        return "当前模型调用频率已达上限，请稍后重试（或切换模型）。"
    return text


def _fallback_laws_for_case(case_description: str) -> list[dict[str, str]]:
    text = case_description or ""
    if re.search(r"劳动|社保|加班|工资|解除|辞退|补偿|仲裁", text):
        return [
            {
                "id": "law_1",
                "title": "《劳动合同法》第四十条",
                "content": "特定情形下，用人单位提前三十日书面通知劳动者本人或者额外支付劳动者一个月工资后，可以解除劳动合同。",
                "source": "轻量兜底法条",
                "party": "both",
            },
            {
                "id": "law_2",
                "title": "《劳动合同法》第四十六条",
                "content": "规定用人单位应当向劳动者支付经济补偿的主要情形。",
                "source": "轻量兜底法条",
                "party": "both",
            },
            {
                "id": "law_3",
                "title": "《劳动合同法》第四十七条",
                "content": "经济补偿按劳动者在本单位工作的年限，每满一年支付一个月工资；六个月以上不满一年按一年计算，不满六个月支付半个月工资。",
                "source": "轻量兜底法条",
                "party": "both",
            },
        ]

    return [
        {
            "id": "law_1",
            "title": "《民法典》第五百零九条",
            "content": "当事人应当按照约定全面履行自己的义务，并遵循诚信原则。",
            "source": "轻量兜底法条",
            "party": "both",
        },
        {
            "id": "law_2",
            "title": "《民法典》第五百七十七条",
            "content": "一方不履行合同义务或者履行不符合约定的，应承担继续履行、采取补救措施或者赔偿损失等违约责任。",
            "source": "轻量兜底法条",
            "party": "both",
        },
    ]


def _evidence_refs_from_items(evidence: list) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for idx, item in enumerate(evidence or [], 1):
        party = str(item.get("party") or "plaintiff").strip().lower()
        refs.append({
            "id": str(item.get("id") or f"evidence_{idx}"),
            "title": str(item.get("name") or f"证据{idx}"),
            "content": str(item.get("desc") or ""),
            "source": "庭审材料",
            "party": "defendant" if party == "defendant" else "plaintiff",
        })
    return refs


async def _yield_fallback_court_events(case_description: str, evidence: list, reason: str):
    laws = _fallback_laws_for_case(case_description)
    evidences = _evidence_refs_from_items(evidence)
    yield {"type": "evidence_list", "evidence_list": evidences}
    yield {"type": "law_list", "law_list": laws}

    opening = (
        f"【开庭准备】因云端模型暂时不可用，已启用轻量庭审兜底模式。原因：{reason}\n\n"
        f"本庭现在核对案由并进入开庭准备。案情摘要：{case_description[:180]}...\n\n"
        "本阶段先明确争议焦点：劳动关系存续、社保与加班事实、工资或补偿计算依据，以及双方证据能否形成完整证明链。"
    )
    plaintiff = (
        "【法庭调查·原告】原告方主张其在公司连续工作并存在社保、加班或劳动报酬争议。"
        "原告可围绕劳动合同、工资流水、考勤记录、社保缴纳记录等材料举证。"
        f"如涉及经济补偿或解除争议，可先引用 [法条:{laws[1]['id']}] 与 [法条:{laws[2]['id']}] 作为请求权基础。"
    )
    defendant = (
        "【法庭调查·被告】被告方应说明用工管理、考勤制度、工资发放、社保缴纳及加班审批规则。"
        "如主张不存在欠缴或加班，应提交制度公告、考勤系统导出、工资明细、社保记录等相反证据。"
    )

    messages = [
        ("fallback_opening", "法官", "judge", "opening", opening),
        ("fallback_plaintiff", "原告律师", "plaintiff", "investigation", plaintiff),
        ("fallback_defendant", "被告律师", "defendant", "investigation", defendant),
    ]
    for msg_id, role, role_key, phase, content in messages:
        yield {
            "type": "new_message",
            "msg_id": msg_id,
            "role": role,
            "role_key": role_key,
            "phase": phase,
        }
        yield {
            "type": "chunk",
            "msg_id": msg_id,
            "role": role,
            "role_key": role_key,
            "phase": phase,
            "content": content,
        }
        for law in re.findall(r"\[法条:(law_\d+)\]", content):
            yield {"type": "law_reference", "law_id": law, "role": role}


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
        result = await agent.execute(request.case_description)
        return result
    except Exception as e:
        app_logger.error(f"辩论失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/debate/court", summary="模拟庭审（流式 SSE）")
async def court_debate(
    request: CourtRejudgeRequest,
):
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


                strategy=request.strategy or "aggressive",
                thread_id=request.thread_id,
                human_evidences=merged_evidence,

            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            app_logger.error(f"庭审流式输出错误: {e}")
            friendly_msg = _friendly_stream_error_message(str(e))
            yield f"data: {json.dumps({'type':'error','message': friendly_msg}, ensure_ascii=False)}\n\n"
            if "rate" in str(e).lower() or "429" in str(e):
                async for event in _yield_fallback_court_events(request.case_description, request.human_evidence or [], friendly_msg):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/debate/court/rejudge", summary="补充证据重新庭审（流式 SSE）")
async def court_debate_rejudge(
    request: CourtRejudgeRequest,
):
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
                strategy=request.strategy or "aggressive",
                thread_id=request.thread_id,
                rejudge_only=True,
                human_evidences=merged_evidence,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            app_logger.error(f"重新开庭流式输出错误: {e}")
            friendly_msg = _friendly_stream_error_message(str(e))
            yield f"data: {json.dumps({'type':'error','message': friendly_msg}, ensure_ascii=False)}\n\n"
            if "rate" in str(e).lower() or "429" in str(e):
                async for event in _yield_fallback_court_events(request.case_description, request.human_evidence or [], friendly_msg):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream") 
