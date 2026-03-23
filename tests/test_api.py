"""
测试 API 路由
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """测试健康检查接口"""
    response = client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "llm_mode" in data


def test_root():
    """测试根路径"""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert "name" in data
    assert "version" in data


def test_legal_chat_accepts_personality_and_custom_headers(monkeypatch):
    """测试聊天接口可接收人格字段与自定义模型参数头"""
    captured = {}

    async def fake_chat(question, session_id, personality, custom_config=None):
        captured["question"] = question
        captured["session_id"] = session_id
        captured["personality"] = personality
        captured["custom_config"] = custom_config
        return {
            "answer": "ok",
            "session_id": session_id,
            "sources": []
        }

    from app.routers import legal as legal_router_module
    monkeypatch.setattr(legal_router_module.legal_agent, "chat", fake_chat)

    response = client.post(
        "/api/legal/chat",
        json={
            "question": "我该怎么维权？",
            "session_id": "s1",
            "personality": "cost_expert"
        },
        headers={
            "X-API-Key": "sk-test",
            "X-API-Base-URL": "https://api.test.com/v1",
            "X-API-Model": "test-model",
            "X-API-Temperature": "0.5",
            "X-API-Max-Tokens": "1024",
        },
    )

    assert response.status_code == 200
    assert captured["question"] == "我该怎么维权？"
    assert captured["session_id"] == "s1"
    assert captured["personality"] == "cost_expert"
    assert captured["custom_config"]["api_key"] == "sk-test"
    assert captured["custom_config"]["temperature"] == 0.5
    assert captured["custom_config"]["max_tokens"] == 1024
