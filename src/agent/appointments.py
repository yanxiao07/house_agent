import json
from datetime import UTC, datetime

from langchain_core.messages import AIMessage
from langgraph.constants import END, START
from langgraph.graph import MessagesState, StateGraph
from langgraph.store.base import BaseStore

from agent.common.store import UserPreferences


class AppointmentState(MessagesState):
    appointments: list[dict]


def _load_preferences(store: BaseStore, phone_number: str):
    records = store.search((phone_number, "preference"))
    if not records:
        return None, None
    return records[0], UserPreferences.model_validate(records[0].value or {})


def manage_appointments(state: AppointmentState, *, store: BaseStore):
    try:
        request = json.loads(state["messages"][-1].content)
        phone_number = str(request["phone_number"]).strip()
        if not phone_number:
            raise ValueError("A phone number is required")

        record, preferences = _load_preferences(store, phone_number)
        action = request.get("action", "read")
        reservations = list((preferences or UserPreferences()).reserved_info or [])

        if action == "enrich":
            order_id = request["order_id"]
            for reservation in reservations:
                if reservation.order_id == order_id:
                    reservation.status = "confirmed"
                    reservation.viewing_time = request.get("viewing_time") or reservation.viewing_time
                    reservation.created_at = reservation.created_at or datetime.now(UTC).isoformat()
                    break
            else:
                raise ValueError("Reservation order was not found")
        elif action == "cancel":
            order_id = request["order_id"]
            for reservation in reservations:
                if reservation.order_id == order_id:
                    reservation.status = "cancelled"
                    break
            else:
                raise ValueError("Reservation order was not found")
        elif action != "read":
            raise ValueError("Unsupported appointment action")

        if record and action in {"enrich", "cancel"}:
            preferences.reserved_info = reservations
            store.put((phone_number, "preference"), record.key, preferences.model_dump(exclude_none=True))

        appointments = [item.model_dump(exclude_none=True) for item in reversed(reservations)]
        return {"appointments": appointments, "messages": [AIMessage(content="Appointments loaded.")]}
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        return {"appointments": [], "messages": [AIMessage(content=f"Appointment request failed: {error}")]}


builder = StateGraph(AppointmentState)
builder.add_node("manage_appointments", manage_appointments)
builder.add_edge(START, "manage_appointments")
builder.add_edge("manage_appointments", END)
appointments_graph = builder.compile()
