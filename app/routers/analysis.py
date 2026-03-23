"""
智能分析路由
提供合同审查和多智能体辩论接口
"""

import json
from typing import Optional, Any
from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.celery_app import celery_app
from app.core.logger import app_logger
from app.services.contract_reviewer import get_contract_reviewer
from app.services.multimodal_contract_reviewer import multimodal_contract_review_task
from app.services.supervisor_agent import get_supervisor_agent
from app.models.response import (
    ContractReviewResponse,
    DebateResponse,
    ReviewTaskSubmitResponse,
    ReviewTaskStatusResponse,
)


# 创建路由器
router = APIRouter(prefix="/analysis", tags=["智能分析"])


# ==================== 示例合同文本 ====================

DEMO_CONTRACT_TEXT = """
劳动合同

甲方（用人单位）：某某科技有限公司
乙方（劳动者）：张三

第一条 合同期限
本合同为固定期限劳动合同，期限为三年，自2024年1月1日起至2026年12月31日止。试用期为六个月。

第二条 工作内容和工作地点
1. 乙方同意根据甲方工作需要，从事软件开发工作。
2. **甲方有权根据业务需要单方面调整乙方的工作岗位和工作地点，乙方必须无条件服从。**
3. 工作地点：甲方指定的任何办公场所。

第三条 工作时间和休息休假
1. 实行标准工时制，每周工作五天，每天工作八小时。
2. **因工作需要，乙方应当服从甲方安排的加班，周末和节假日加班不另行支付加班费。**
3. 乙方每年享有带薪年休假5天。

第四条 劳动报酬
1. 乙方月工资为人民币8000元（税前）。
2. **试用期内不缴纳社会保险和住房公积金。**
3. **工资发放时间由甲方根据经营状况决定，可能延迟发放。**

第五条 社会保险和福利待遇
1. 甲方依法为乙方缴纳社会保险（试用期除外）。
2. **乙方因工负伤的，医疗费用由乙方自行承担50%。**

第六条 劳动纪律
1. 乙方应当遵守甲方的规章制度。
2. **乙方不得拒绝甲方安排的任何工作任务，否则视为严重违反劳动纪律。**
3. **乙方每月迟到或早退累计超过3次，甲方有权扣除当月全部工资。**

第七条 保密和竞业限制
1. **乙方在职期间及离职后五年内，不得从事与甲方相同或相似的业务。**
2. **违反竞业限制的，乙方应当向甲方支付违约金人民币50万元。**

第八条 合同的解除和终止
1. **乙方提前解除合同的，应当提前三个月书面通知甲方，并支付违约金人民币10万元。**
2. **甲方可以随时解除本合同，无需支付任何经济补偿。**

第九条 其他
1. 本合同一式两份，甲乙双方各执一份。
2. 本合同自双方签字盖章之日起生效。

甲方（盖章）：某某科技有限公司
乙方（签字）：张三
日期：2024年1月1日
""".strip()


# ==================== 请求模型 ====================

class DebateRequest(BaseModel):
    """辩论请求模型"""
    case_description: str = Field(
        ..., 
        description="案情描述",
        min_length=20,
        examples=["员工张三因拒绝周末加班被公司以严重违反规章制度为由辞退。张三认为公司要求的加班不合理，且未支付加班费，公司辞退行为违法。公司则认为张三多次拒绝工作安排，严重影响工作进度，符合公司规章制度规定的辞退条件。"]
    )


# ==================== 路由端点 ====================

@router.post(
    "/review/{contract_id}",
    response_model=ReviewTaskSubmitResponse,
    summary="智能合同审查（异步任务）",
    description="提交合同审查任务并立即返回 task_id，前端通过状态接口轮询结果"
)
async def review_contract(contract_id: str):
    """提交异步合同审查任务"""
    try:
        app_logger.info(f"📋 收到合同审查异步任务请求: {contract_id}")

        contract_text = DEMO_CONTRACT_TEXT if contract_id.startswith("demo_") else None
        async_result = multimodal_contract_review_task.delay(contract_id=contract_id, contract_text=contract_text)

        return ReviewTaskSubmitResponse(task_id=async_result.id, status="processing")

    except Exception as e:
        app_logger.error(f"❌ 提交合同审查任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"提交审查任务失败: {str(e)}")


@router.get(
    "/review/status/{task_id}",
    response_model=ReviewTaskStatusResponse,
    summary="查询合同审查任务状态",
    description="查询 Celery 任务进度、失败信息及最终风险卡片结果"
)
async def review_contract_status(task_id: str):
    """查询合同审查异步任务状态"""
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        state = task_result.state

        if state == "PENDING":
            return ReviewTaskStatusResponse(
                task_id=task_id,
                status="processing",
                progress=0,
                message="任务排队中...",
            )

        if state == "PROGRESS":
            meta = task_result.info or {}
            return ReviewTaskStatusResponse(
                task_id=task_id,
                status="processing",
                progress=int(meta.get("progress", 0)),
                message=str(meta.get("message", "处理中...")),
                meta=meta,
            )

        if state == "SUCCESS":
            payload: Any = task_result.result or {}
            result = ContractReviewResponse(**payload)
            return ReviewTaskStatusResponse(
                task_id=task_id,
                status="success",
                progress=100,
                message="审查完成",
                result=result,
            )

        if state in {"FAILURE", "REVOKED"}:
            error_message = str(task_result.result)
            return ReviewTaskStatusResponse(
                task_id=task_id,
                status="failed",
                progress=100,
                message="审查任务失败",
                error=error_message,
            )

        return ReviewTaskStatusResponse(
            task_id=task_id,
            status="processing",
            progress=0,
            message=f"当前状态: {state}",
        )

    except Exception as e:
        app_logger.error(f"❌ 查询合同审查任务状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询任务状态失败: {str(e)}")


@router.post(
    "/debate",
    response_model=DebateResponse,
    summary="多智能体法律辩论",
    description="模拟原告律师、被告律师、法官三方对案件进行辩论，输出结构化的辩论结果和胜诉概率预测"
)
async def simulate_debate(request: DebateRequest):
    """
    多智能体法律辩论接口
    
    **功能说明：**
    - 模拟真实的法律诉讼辩论过程
    - 原告律师：积极维权，寻找有利证据和法律依据
    - 被告律师：寻找漏洞，提出反驳和抗辩理由
    - 法官：中立客观，综合双方观点给出专业意见
    
    **辩论流程：**
    1. 原告律师根据案情提出起诉理由和索赔依据
    2. 被告律师针对原告论点进行抗辩和反驳
    3. 法官综合双方观点，给出中立意见和胜诉概率预测
    
    **返回信息：**
    - plaintiff_argument: 原告方论点（包含论点、法律依据、关键要点）
    - defendant_argument: 被告方论点（包含论点、法律依据、关键要点）
    - judge_opinion: 法官意见（包含意见、法律依据、关键要点）
    - win_probability: 胜诉概率预测（原告和被告的胜诉概率）
    
    **使用场景：**
    - 诉讼前的风险评估
    - 了解案件的法律争议焦点
    - 预测可能的判决结果
    - 准备诉讼策略和证据
    
    **注意事项：**
    - 案情描述应尽量详细，包含关键事实和证据
    - 辩论过程可能需要 20-60 秒，请耐心等待
    - 辩论结果仅供参考，不构成法律建议
    - 实际案件结果受多种因素影响，预测概率仅供参考
    """
    try:
        app_logger.info(f"⚖️  收到辩论模拟请求，案情长度: {len(request.case_description)} 字符")
        
        # 获取辩论引擎实例
        debate_agent = get_supervisor_agent()
        
        # 执行辩论模拟
        result = await debate_agent.simulate_debate(request.case_description)
        
        return result
    
    except ValueError as e:
        # 参数错误（如案情描述过短）
        app_logger.warning(f"⚠️  辩论请求无效: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        # 其他错误
        app_logger.error(f"❌ 辩论模拟失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"辩论模拟失败: {str(e)}")


@router.post(
    "/debate/stream",
    summary="多智能体法律辩论（流式 SSE）",
    description="《逆转裁判》风格的流式辩论，支持实时动作标签和打字机效果"
)
async def simulate_debate_stream(
    request: DebateRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_api_base_url: Optional[str] = Header(None, alias="X-API-Base-URL"),
    x_api_model: Optional[str] = Header(None, alias="X-API-Model"),
    x_api_temperature: Optional[float] = Header(None, alias="X-API-Temperature"),
    x_api_max_tokens: Optional[int] = Header(None, alias="X-API-Max-Tokens")
):
    """
    流式辩论接口（SSE）
    
    **功能说明：**
    - 实时推送辩论过程
    - 支持动作标签（OBJECTION、HOLD_IT、TAKE_THAT 等）
    - 支持打字机效果
    
    **事件类型：**
    - speaker_change: 发言人切换
    - action: 动作标签（异议、拍桌等）
    - content: 对话内容（分段推送）
    - probability: 胜诉概率
    
    **使用场景：**
    - 《逆转裁判》风格的沉浸式法庭体验
    - 实时展示辩论过程
    """
    try:
        app_logger.info(f"⚖️  收到流式辩论请求，案情长度: {len(request.case_description)} 字符")
        
        # 构建自定义配置
        custom_config = None
        if x_api_key:
            custom_config = {
                "api_key": x_api_key,
                "base_url": x_api_base_url,
                "model": x_api_model,
                "temperature": x_api_temperature,
                "max_tokens": x_api_max_tokens
            }
            app_logger.info(f"使用自定义 LLM 配置: model={x_api_model}, base_url={x_api_base_url}")
        
        # 获取辩论引擎实例
        debate_agent = get_supervisor_agent()
        
        async def event_generator():
            """SSE 事件生成器"""
            try:
                async for event in debate_agent.simulate_debate_stream(
                    request.case_description,
                    custom_config=custom_config
                ):
                    # 转换为 SSE 格式
                    event_data = json.dumps(event, ensure_ascii=False)
                    yield f"data: {event_data}\n\n"
                
                # 发送结束事件
                yield f"data: {json.dumps({'event': 'done'})}\n\n"
            
            except Exception as e:
                app_logger.error(f"❌ 流式辩论失败: {str(e)}")
                error_event = json.dumps({
                    "event": "error",
                    "message": str(e)
                }, ensure_ascii=False)
                yield f"data: {error_event}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    except ValueError as e:
        app_logger.warning(f"⚠️  流式辩论请求无效: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        app_logger.error(f"❌ 流式辩论失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"流式辩论失败: {str(e)}")


@router.get(
    "/health",
    summary="分析服务健康检查",
    description="检查智能分析服务是否正常运行"
)
async def analysis_health():
    """
    分析服务健康检查
    
    **返回信息：**
    - status: 服务状态
    - services: 各子服务的状态
    """
    try:
        # 检查各服务是否可用
        reviewer = get_contract_reviewer()
        debate_agent = get_supervisor_agent()
        
        return {
            "status": "healthy",
            "services": {
                "contract_reviewer": "available" if reviewer else "unavailable",
                "debate_agent": "available" if debate_agent else "unavailable"
            },
            "message": "智能分析服务运行正常"
        }
    
    except Exception as e:
        app_logger.error(f"❌ 分析服务健康检查失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务异常: {str(e)}")


# 导出路由器
__all__ = ["router"]
