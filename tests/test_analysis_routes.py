"""
测试智能分析路由（合同审查 / 模拟法庭 / SSE 错误处理）。
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _read_sse_events(raw_text: str) -> list[dict]:
    """将 SSE 文本切分并解析为事件字典列表。"""
    events: list[dict] = []
    for block in raw_text.split("\n\n"):
        block = block.strip()
        if not block or not block.startswith("data: "):
            continue
        payload = block[len("data: ") :]
        try:
            events.append(json.loads(payload))
        except json.JSONDecodeError:
            continue
    return events


def test_review_contract_submit_returns_task_id(monkeypatch):
    """提交异步审查任务应返回 task_id 和 processing。"""

    class DummyTaskResult:
        id = "task_123"

    class DummyTask:
        @staticmethod
        def delay(contract_id, contract_text=None):
            assert contract_id == "contract_001"
            assert contract_text is None
            return DummyTaskResult()

    from app.api.v1.routes import tools as tools_module

    monkeypatch.setattr(tools_module, "multimodal_contract_review_task", DummyTask())

    response = client.post("/api/analysis/review/contract_001")
    assert response.status_code == 200

    data = response.json()
    assert data["task_id"] == "task_123"
    assert data["status"] == "processing"


def test_review_contract_status_success(monkeypatch):
    """任务 SUCCESS 时应返回 success + result。"""

    class DummyAsyncResult:
        def __init__(self, task_id, _app=None):
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

    from app.api.v1.routes import tools as tools_module

    monkeypatch.setattr(tools_module, "AsyncResult", DummyAsyncResult)

    response = client.get("/api/analysis/review/status/task_123")
    assert response.status_code == 200

    data = response.json()
    assert data["task_id"] == "task_123"
    assert data["status"] == "success"
    assert data["result"]["contract_id"] == "contract_001"


def test_review_stream_rejects_unknown_template():
    """SSE 合同审查在模板不存在时应返回 error 事件。"""
    response = client.post(
        "/api/analysis/review/stream",
        json={"template_id": "unknown_template"},
    )

    assert response.status_code == 200
    events = _read_sse_events(response.text)
    assert any(e.get("type") == "error" for e in events)


def test_court_debate_stream_yields_events(monkeypatch):
    """模拟法庭 SSE 应输出日志/正文/结果事件。"""

    class DummyCourtAgent:
        async def stream(self, case_description, strategy, human_evidences, **_kwargs):
            assert "[原告证据清单]" in case_description
            assert strategy == "aggressive"
            assert isinstance(human_evidences, list)

            yield {"type": "log", "message": "准备开庭"}
            yield {
                "type": "chunk",
                "phase": "opening",
                "role": "审判长",
                "role_key": "judge",
                "content": "现在开庭。",
            }
            yield {
                "type": "result",
                "result": {
                    "verdict": "判决如下",
                    "plaintiff_win_rate": 60,
                    "defendant_win_rate": 40,
                    "verdict_result": {
                        "plaintiff_win_rate": 60,
                        "defendant_win_rate": 40,
                        "verdict_text": "判决如下",
                    },
                },
            }

    from app.api.v1.routes import tools as tools_module

    monkeypatch.setattr(tools_module, "get_court_agent", lambda: DummyCourtAgent())

    response = client.post(
        "/api/analysis/debate/court",
        json={
            "case_description": "员工主张违法解除劳动合同并请求赔偿。",
            "strategy": "aggressive",
            "human_evidence": [
                {"party": "plaintiff", "name": "聊天记录", "desc": "存在解除通知"},
                {"party": "defendant", "name": "规章制度", "desc": "曾公示"},
            ],
        },
    )

    assert response.status_code == 200
    events = _read_sse_events(response.text)
    assert any(e.get("type") == "chunk" for e in events)
    assert any(e.get("type") == "result" for e in events)


def test_court_debate_stream_rate_limit_error_is_friendly(monkeypatch):
    """429 限流应被转换为可读中文提示，而非原始异常全文。"""

    class DummyCourtAgent:
        async def stream(self, **_kwargs):
            if False:
                yield {"type": "noop"}
            raise Exception(
                "Error code: 429 - {'error': {'message': 'Rate limit reached for model `llama-3.3-70b-versatile` "
                "in organization `org_xxx` service tier `on_demand` on tokens per day (TPD): "
                "Limit 100000, Used 99972, Requested 781. Please try again in 10m50.592s.', "
                "'type': 'tokens', 'code': 'rate_limit_exceeded'}}"
            )

    from app.api.v1.routes import tools as tools_module

    monkeypatch.setattr(tools_module, "get_court_agent", lambda: DummyCourtAgent())

    response = client.post(
        "/api/analysis/debate/court",
        json={
            "case_description": "测试限流异常文案",
            "strategy": "aggressive",
            "human_evidence": [],
        },
    )

    assert response.status_code == 200
    events = _read_sse_events(response.text)
    error_events = [e for e in events if e.get("type") == "error"]
    assert error_events, "应至少返回 1 条 error 事件"

    message = error_events[0].get("message", "")
    assert "当前模型调用频率已达上限" in message
    assert "10 分" in message or "11 分" in message


def test_court_rejudge_stream_works(monkeypatch):
    """rejudge 接口应把 thread_id / rejudge_only 传入 agent.stream。"""
    captured = {}

    class DummyCourtAgent:
        async def stream(self, **kwargs):
            captured.update(kwargs)
            yield {"type": "log", "message": "rejudge started"}

    from app.api.v1.routes import tools as tools_module

    monkeypatch.setattr(tools_module, "get_court_agent", lambda: DummyCourtAgent())

    response = client.post(
        "/api/analysis/debate/court/rejudge",
        json={
            "thread_id": "thread_001",
            "case_description": "补充证据后申请重审",
            "strategy": "aggressive",
            "human_evidence": [],
        },
    )

    assert response.status_code == 200
    assert captured["thread_id"] == "thread_001"
    assert captured["rejudge_only"] is True
