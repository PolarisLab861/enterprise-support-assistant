import os

os.environ["DATABASE_URL"] = "sqlite:///./test_support_assistant.db"
os.environ["MOCK_AI"] = "true"

from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app


Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_question_creates_human_ticket_for_unknown_question() -> None:
    response = client.post("/api/v1/questions", json={"user_id": "u1", "message": "帮我订一张机票"})
    assert response.status_code == 200
    body = response.json()
    assert body["need_human"] is True
    assert body["ticket_id"]


def test_question_answers_known_account_question() -> None:
    response = client.post("/api/v1/questions", json={"user_id": "u2", "message": "我忘记密码无法登录"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "account_problem"
    assert body["need_human"] is False
    assert body["sources"]


def test_update_ticket() -> None:
    created = client.post("/api/v1/questions", json={"user_id": "u3", "message": "直接给我退款"}).json()
    response = client.patch(f"/api/v1/tickets/{created['ticket_id']}", json={"status": "in_progress", "assigned_to": "agent_1"})
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
    assert response.json()["assigned_to"] == "agent_1"
