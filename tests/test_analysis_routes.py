"""
测试智能分析异步审查与流式辩论
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_review_contract_submit_returns_task_id(monkeypatch):
    """提交审查应立即返回 task_id 和 processing 状态"""

    class DummyTaskResult:
        id = "task_123"

    class DummyTask:
        @staticmethod
        def delay(contract_id, contract_text=None):
            assert contract_id == "contract_001"
            assert contract_text is None
            return DummyTaskResult()

    from app.routers import analysis as analysis_router_module
    monkeypatch.setattr(analysis_router_module, "multimodal_contract_review_task", DummyTask())

    response = client.post("/api/analysis/review/contract_001")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "task_123"
    assert data["status"] == "processing"


def test_review_contract_status_success(monkeypatch):
    """任务成功时应返回 success 和风险结果"""

    class DummyAsyncResult:
        def __init__(self, task_id, app=None):
            self.state = "SUCCESS"
            self.result = {
                "contract_id": "contract_001",
                "risks": [],
                "overall_summary": "ok",
                "review_timestamp": "2026-03-07T16:00:00Z",
                "processing_steps": ["done"],
                "is_image_based": False,
            }
            self.info = None

    from app.routers import analysis as analysis_router_module
    monkeypatch.setattr(analysis_router_module, "AsyncResult", DummyAsyncResult)

    response = client.get("/api/analysis/review/status/task_123")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "task_123"
    assert data["status"] == "success"
    assert data["result"]["contract_id"] == "contract_001"


def test_debate_stream_emits_sse_events_and_passes_custom_config(monkeypatch):
    """流式辩论应输出 SSE 事件，并透传模型参数"""
    captured = {}

    class DummyDebateAgent:
        async def simulate_debate_stream(self, case_description, custom_config=None):
            captured["case_description"] = case_description
            captured["custom_config"] = custom_config
            yield {"event": "start", "role": "plaintiff"}
            yield {"event": "content", "content": "[OBJECTION] 异议！"}
            yield {"event": "end", "role": "plaintiff"}
            yield {
                "event": "result",
                "result": {
                    "plaintiff_win_rate": 70,
                    "plaintiff_winning_factors": ["证据充分"],
                    "defendant_winning_factors": ["程序瑕疵"],
                    "judge_summary": "综合评估后原告胜诉概率较高",
                },
            }

    from app.routers import analysis as analysis_router_module
    monkeypatch.setattr(analysis_router_module, "get_debate_agent", lambda: DummyDebateAgent())

    response = client.post(
        "/api/analysis/debate/stream",
        json={
            "case_description": "员工因拒绝加班被辞退，要求确认违法解除并赔偿，双方对规章制度效力存在争议。"
        },
        headers={
            "X-API-Key": "sk-test",
            "X-API-Base-URL": "https://api.test.com/v1",
            "X-API-Model": "test-model",
            "X-API-Temperature": "0.6",
            "X-API-Max-Tokens": "3072",
        },
    )

    assert response.status_code == 200
    assert "data:" in response.text
    assert '"event": "start"' in response.text
    assert '"event": "result"' in response.text
    assert captured["custom_config"]["temperature"] == 0.6
    assert captured["custom_config"]["max_tokens"] == 3072
