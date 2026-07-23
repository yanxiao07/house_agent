from agent.persistence import BusinessRepository


def test_repository_persists_user_session_and_booking(tmp_path) -> None:
    repository = BusinessRepository(f"sqlite:///{tmp_path / 'rental.db'}")
    repository.initialize()

    assert repository.save_preferences("u-1", {"budget_max": 8000}) == {"budget_max": 8000}
    assert repository.get_preferences("u-1")["budget_max"] == 8000

    repository.add_turn("u-1", "s-1", "user", "预算 8000")
    assert repository.list_turns("u-1", "s-1")[0]["content"] == "预算 8000"

    booking = repository.upsert_booking(
        {
            "order_id": "order-1",
            "user_id": "u-1",
            "house_id": "h-1",
            "house_title": "测试房源",
            "phone_number": "13800000000",
            "viewing_time": None,
            "status": "confirmed",
        }
    )
    assert booking["status"] == "confirmed"
    assert repository.cancel_booking("u-1", "order-1")["status"] == "cancelled"
