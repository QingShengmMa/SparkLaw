"""
法律工具专用路由

全量委托 CalculatorFactory + 策略模式处理 14 种计算器，
以及 LLM 驱动的文书起草、证据评估、合规体检工具。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.dependencies import require_usage_context
from app.core.logger import app_logger
from app.services.legal_agent import legal_agent

router = APIRouter(
    prefix="/tools",
    tags=["法律工具"],
    dependencies=[Depends(require_usage_context)],
)


# ═══════════════════════════════════════════════════════════
# Pydantic 模型
# ═══════════════════════════════════════════════════════════

class AIToolRequest(BaseModel):
    """AI 工具通用请求"""
    content: str = Field(..., min_length=1, max_length=6000, description="用户输入内容")
    session_id: str = Field(default="tools", description="会话 ID")


class AIToolResponse(BaseModel):
    """AI 工具通用响应"""
    result: str
    session_id: str


# ═══════════════════════════════════════════════════════════
# AI 工具端点（LLM，系统提示在服务端）
# ═══════════════════════════════════════════════════════════

_DRAFTING_PROMPT = """你是专业法律文书起草助手。根据用户描述的案情和诉求，起草格式规范、要素完整的法律文书（起诉状/律师函/仲裁申请书/和解协议等）。
要求：
1. 明确当事人基本信息（可用占位符）
2. 分段标注：诉讼请求 / 事实与理由 / 法律依据 / 证据清单
3. 每个关键主张须引用具体法律条文
4. 语言严谨、格式规范，符合司法实践要求"""

_EVIDENCE_PROMPT = """你是证据法专家。用户会提交一个证据包，包含待证事实、证据类型、取得方式、原始载体、保管链条和对方异议风险。
请按司法实务出具证据评估意见，必须包含：
1. 【证据包结论】整体证明方向、综合评分 0-100、核心证据数量、主要短板
2. 【逐项证据评估】用表格列出每项证据的真实性、合法性、关联性、证明力等级、对方可能异议
3. 【证明力排序】按庭审使用价值排序，说明先后顺序
4. 【补强动作】逐项说明需要补原件、平台导出、公证保全、证人/第三方记录、损失票据等
5. 【庭审使用建议】说明哪些证据用于主张事实，哪些用于反驳对方抗辩
6. 【法律依据】引用证据规则或民事诉讼相关规定，并说明对应关系。
请直接给专业意见，不要泛泛提示。"""

_COMPLIANCE_PROMPT = """你是企业劳动法合规审查专家。用户会提交企业画像和七个用工模块的状态：劳动合同、社保公积金、工时加班、薪酬发放、规章制度、外包派遣、竞业保密。
请出具可执行的合规审查报告，必须包含：
1. 【合规总览】合规评分 0-100、风险等级、最优先整改领域
2. 【重大风险项】逐项说明风险事实、法律后果、具体法条、整改动作
3. 【待确认事项】列出需要补充核查的材料，例如合同台账、社保缴费明细、考勤记录、制度公示证据
4. 【整改台账】按优先级列 Top 5，包含责任部门、周期、交付物
5. 【制度补强】给出流程、模板、审批、留痕机制建议
6. 【合规亮点】列出已合规或低风险模块。
请使用结构化格式输出，避免空泛建议。"""

_RISK_PREDICTION_PROMPT = """你是资深诉讼策略分析师。用户会提交案情画像：纠纷类型、当事人身份、案件阶段、证据强度、金额规模、核心事实、主要诉求、对方抗辩和前端初算胜率。
请输出诉讼风险预测报告，必须包含：
1. 【综合判断】给出悲观/基准/乐观胜率区间、风险等级和一句话结论
2. 【关键争点】列出 3-5 个会影响裁判结果的核心争点，并说明哪一方举证
3. 【证据强弱】说明当前证据优势、证据缺口、补强优先级
4. 【金额/责任区间】如涉及赔偿、补偿、违约金或费用，给出合理区间和计算逻辑
5. 【对方抗辩压力】逐条拆解对方可能抗辩及反制思路
6. 【策略路径】分别给出诉讼/仲裁推进、调解和解、证据补强三条路径
7. 【下一步清单】列 3-5 个立即执行动作。
请保持审慎，不承诺确定结果；事实不足时明确指出缺失信息。"""


async def _ai_call(
    system_prompt: str,
    user_content: str,
    session_id: str,
) -> str:
    """统一 AI 调用封装，复用 legal_agent.chat 逻辑。"""
    full_prompt = f"{system_prompt}\n\n用户输入：{user_content}"
    try:
        result = await legal_agent.chat(
            question=full_prompt,
            session_id=session_id,
            personality="machine",
        )
        return result.get("answer", "")
    except Exception as e:
        app_logger.error(f"AI 工具调用失败 session={session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"AI 服务暂时不可用: {str(e)}")


@router.post(
    "/drafting",
    response_model=AIToolResponse,
    summary="AI 文书起草",
    description="根据用户描述的案情自动生成格式规范的法律文书（起诉状/律师函/仲裁申请书等）。",
)
async def drafting(
    req: AIToolRequest,
) -> AIToolResponse:
    answer = await _ai_call(
        system_prompt=_DRAFTING_PROMPT,
        user_content=req.content,
        session_id=f"drafting-{req.session_id}",
    )
    return AIToolResponse(result=answer, session_id=req.session_id)


@router.post(
    "/evidence",
    response_model=AIToolResponse,
    summary="AI 证据效力评估",
    description="从真实性、合法性、关联性三维度评估证据效力，给出综合评分与补强建议。",
)
async def evidence(
    req: AIToolRequest,
) -> AIToolResponse:
    answer = await _ai_call(
        system_prompt=_EVIDENCE_PROMPT,
        user_content=req.content,
        session_id=f"evidence-{req.session_id}",
    )
    return AIToolResponse(result=answer, session_id=req.session_id)


@router.post(
    "/compliance",
    response_model=AIToolResponse,
    summary="AI 合规体检",
    description="诊断企业用工合规风险，给出评分、高中风险项、整改建议及优先级清单。",
)
async def compliance(
    req: AIToolRequest,
) -> AIToolResponse:
    answer = await _ai_call(
        system_prompt=_COMPLIANCE_PROMPT,
        user_content=req.content,
        session_id=f"compliance-{req.session_id}",
    )
    return AIToolResponse(result=answer, session_id=req.session_id)


@router.post(
    "/risk-prediction",
    response_model=AIToolResponse,
    summary="AI 诉讼风险预测",
    description="基于案件事实、证据强弱和法律依据，预测诉讼风险、胜诉概率区间与行动策略。",
)
async def risk_prediction(
    req: AIToolRequest,
) -> AIToolResponse:
    answer = await _ai_call(
        system_prompt=_RISK_PREDICTION_PROMPT,
        user_content=req.content,
        session_id=f"risk-{req.session_id}",
    )
    return AIToolResponse(result=answer, session_id=req.session_id)


# ═══════════════════════════════════════════════════════
# 统一计算器网关接口
# ═══════════════════════════════════════════════════════

from typing import Any, Dict, List
from pydantic import model_validator


class BreakdownItem(BaseModel):
    label: str
    amount: float


class CalcResultData(BaseModel):
    totalAmount: float
    breakdown: List[BreakdownItem]
    formula: str
    legalBasis: str
    note: str = ""


class CalcGatewayRequest(BaseModel):
    calcType: str
    params: Dict[str, Any]


class CalcGatewayResponse(BaseModel):
    success: bool
    data: CalcResultData


@router.post(
    "/calculator/calculate",
    response_model=CalcGatewayResponse,
    summary="统一计算器网关",
    description="接收 calcType + params，动态调度对应算法策略并返回标准化结果。",
)
def calc_gateway(req: CalcGatewayRequest) -> CalcGatewayResponse:
    """统一计算器网关 — 全量委托工厂+策略模式调度，无内联计算逻辑。"""
    try:
        from app.tools.calculators.factory import CalculatorFactory
        result = CalculatorFactory.calculate(req.calcType, req.params)
        return CalcGatewayResponse(
            success=True,
            data=CalcResultData(
                totalAmount=result.data.totalAmount,
                breakdown=[BreakdownItem(label=b.label, amount=b.amount) for b in result.data.breakdown],
                formula=result.data.formula,
                legalBasis=result.data.legalBasis,
                note=result.data.note,
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        app_logger.error(f"计算器工厂调用失败 calcType={req.calcType}: {e}")
        raise HTTPException(status_code=500, detail=f"计算失败：{str(e)}")


# ═══════════════════════════════════════════════════════
# 文书起草 — SSE 流式接口
# ═══════════════════════════════════════════════════════

import json as _json
from fastapi import UploadFile, File, Form
from fastapi.responses import StreamingResponse
from app.services.llm_factory import LLMFactory
from app.services.document_parser import DocumentParser

_DRAFT_SYSTEM = """你是中国资深诉讼律师兼法律文书专家，拥有 20 年一线实务经验。
你的任务是根据当事人提供的案件事实，起草格式规范、条理清晰、法律依据充分的法律文书。

输出规范（严格遵守）：
1. 使用 Markdown 格式，标题用 # / ##，正文段落用缩进（首行空两格）
2. 必须包含：【标题】【致：/申请人/原告/被告等要素行】【正文】【落款签署区】
3. 每个关键主张必须引用具体法律条文（《民法典》《劳动合同法》等）
4. 语气专业严谨，不得使用口语化表达
5. 在正文前输出一行"---DRAFT_START---"，文书结束后输出"---DRAFT_END---"""

_REFINE_SYSTEM = """你是法律文书润色专家。用户将提供一份已有的法律文书全文，以及一条微调指令。
请在保持文书整体结构和法律严谨性不变的前提下，根据微调指令修改文书。
直接输出修改后的完整文书，不要添加任何解释性前缀。
在文书前输出"---DRAFT_START---"，文书结束后输出"---DRAFT_END---"""

_DRAFT_LOGS = [
    (5,  "解析案件事实与核心诉求..."),
    (15, "匹配法律文书类型与标准模板..."),
    (25, "提取关键权利义务关系与金额..."),
    (40, "检索关联法条：《民法典》《劳动合同法》..."),
    (55, "构建主张框架与证据链逻辑..."),
    (70, "调用大模型生成专业文书内容..."),
    (85, "排版优化与格式规范校验..."),
    (95, "完成文书生成，准备输出..."),
]


def _sse(payload: dict) -> str:
    return f"data: {_json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/drafting/generate", summary="文书起草 SSE 流式生成")
async def drafting_generate(
    prompt: str = Form(..., description="案件事实描述"),
    template_type: str = Form(default="", description="文书类型提示"),
    file: Optional[UploadFile] = File(default=None),
):
    """SSE 流式文书起草：先发进度日志，再流式输出文书内容。"""

    async def generate():
        try:
            # 1. 解析附件
            attachment_text = ""
            if file and file.filename:
                try:
                    yield _sse({"type": "log", "progress": 3, "message": f"正在解析附件：{file.filename}..."})
                    parser = DocumentParser()
                    attachment_text = await parser.parse_file(file)
                    yield _sse({"type": "log", "progress": 8, "message": f"附件解析完成，提取 {len(attachment_text)} 字符"})
                except Exception as e:
                    yield _sse({"type": "log", "progress": 8, "message": f"附件解析失败（将忽略）: {str(e)[:60]}"})

            # 2. 发送进度日志
            for progress, message in _DRAFT_LOGS:
                yield _sse({"type": "log", "progress": progress, "message": message})
                import asyncio
                await asyncio.sleep(0.08)

            # 3. 组装 Prompt
            user_content = f"文书类型要求：{template_type}\n\n案件事实：\n{prompt}"
            if attachment_text:
                user_content += f"\n\n附件背景材料（摘录）：\n{attachment_text[:3000]}"

            full_prompt = f"{_DRAFT_SYSTEM}\n\n{user_content}"

            # 4. 使用服务端统一配置的 LLM 路由
            llm = LLMFactory.create_llm()

            # 5. 流式输出文书内容（最多等待 110 秒）
            yield _sse({"type": "log", "progress": 70, "message": "大模型开始生成文书..."})
            full_content = ""

            async def _stream_llm():
                nonlocal full_content
                async for chunk in llm.astream(full_prompt):
                    token = chunk.content if hasattr(chunk, "content") else str(chunk)
                    if token:
                        full_content += token
                        yield _sse({"type": "token", "token": token})

            import asyncio as _asyncio
            try:
                async for sse_line in _stream_llm():
                    yield sse_line
            except _asyncio.TimeoutError:
                yield _sse({"type": "error", "message": "大模型响应超时，请稍后重试"})
                return

            if not full_content.strip():
                yield _sse({"type": "error", "message": "大模型未返回任何内容，请检查 API 配置后重试"})
                return

            yield _sse({"type": "done", "progress": 100, "content": full_content})

        except Exception as e:
            app_logger.error(f"文书生成失败: {e}")
            yield _sse({"type": "error", "message": str(e)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class RefineRequest(BaseModel):
    current_content: str = Field(..., description="当前文书全文")
    instruction: str = Field(..., description="微调指令")


@router.post("/drafting/refine", summary="文书细节润色 SSE 流式")
async def drafting_refine(
    req: RefineRequest,
):
    """SSE 流式文书润色：根据微调指令修改已有文书并流式返回。"""

    async def generate():
        try:
            full_prompt = (
                f"{_REFINE_SYSTEM}\n\n"
                f"【原始文书】\n{req.current_content}\n\n"
                f"【微调指令】\n{req.instruction}"
            )
            llm = LLMFactory.create_llm()
            full_content = ""
            async for chunk in llm.astream(full_prompt):
                token = chunk.content if hasattr(chunk, "content") else str(chunk)
                if token:
                    full_content += token
                    yield _sse({"type": "token", "token": token})
            if not full_content.strip():
                yield _sse({"type": "error", "message": "大模型未返回任何内容，请检查 API 配置后重试"})
                return
            yield _sse({"type": "done", "content": full_content})
        except Exception as e:
            app_logger.error(f"文书润色失败: {e}")
            yield _sse({"type": "error", "message": str(e)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
