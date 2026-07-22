"""State contracts used by House Agent graphs."""

from typing import Literal

from langgraph.graph import MessagesState

Intent = Literal["recommend", "reserve", "preferences", "general"]


class RentalState(MessagesState):
    """Conversation state for the rental assistant."""

    intent: Intent
    user_preferences: dict[str, object]
    matches: list[dict[str, object]]
    booking: dict[str, object]
