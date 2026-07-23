import json

from langchain_core.messages import HumanMessage
from langgraph.store.memory import InMemoryStore

from agent.appointments import manage_appointments


def _request(action: str, **payload) -> dict:
    """Run the appointment node with a browser-shaped request message."""
    return {
        "messages": [
            HumanMessage(content=json.dumps({"action": action, **payload}))
        ]
    }


def test_appointment_node_reads_enriches_and_cancels_reservation() -> None:
    """The tenant appointment center must only mutate its own saved order."""
    phone_number = "13900000001"
    store = InMemoryStore()
    store.put(
        (phone_number, "preference"),
        "tenant-appointment-test",
        {
            "reserved_info": [
                {
                    "order_id": "order-1",
                    "title": "Sample apartment",
                    "phone_number": phone_number,
                    "status": "confirmed",
                }
            ]
        },
    )

    read_result = manage_appointments(
        _request("read", phone_number=phone_number), store=store
    )
    enrich_result = manage_appointments(
        _request(
            "enrich",
            phone_number=phone_number,
            order_id="order-1",
            viewing_time="2026-07-24T10:00:00+00:00",
        ),
        store=store,
    )
    cancel_result = manage_appointments(
        _request("cancel", phone_number=phone_number, order_id="order-1"),
        store=store,
    )

    assert read_result["appointments"][0]["title"] == "Sample apartment"
    assert enrich_result["appointments"][0]["viewing_time"] == "2026-07-24T10:00:00+00:00"
    assert cancel_result["appointments"][0]["status"] == "cancelled"
