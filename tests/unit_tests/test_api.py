from fastapi.testclient import TestClient

from agent.api import app


def test_health_and_contract_analysis_endpoints() -> None:
    with TestClient(app) as client:
        health = client.get("/api/health")
        analysis = client.post(
            "/api/contracts/analyze",
            json={"text": "押金不退，房东可随时进入房屋，租客还需要承担全部维修责任。"},
        )

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert analysis.status_code == 200
    assert analysis.json()["risks"]


def test_conversation_and_booking_endpoints(monkeypatch, tmp_path) -> None:
    from agent import api
    from agent.persistence import BusinessRepository

    repository = BusinessRepository(f"sqlite:///{tmp_path / 'api.db'}")
    repository.initialize()
    monkeypatch.setattr(api, "_repository", lambda: repository)

    with TestClient(app) as client:
        turn = client.post(
            "/api/conversations",
            json={"user_id": "u-1", "session_id": "s-1", "role": "user", "content": "预算 8000"},
        )
        history = client.get("/api/users/u-1/conversations/s-1")
        booking = client.put(
            "/api/bookings/order-1",
            json={"order_id": "order-1", "user_id": "u-1", "house_title": "测试房源", "phone_number": "13800000000"},
        )
        cancelled = client.post("/api/users/u-1/bookings/order-1/cancel")

    assert turn.status_code == 201
    assert history.json()["items"][0]["content"] == "预算 8000"
    assert booking.json()["status"] == "confirmed"
    assert cancelled.json()["status"] == "cancelled"
