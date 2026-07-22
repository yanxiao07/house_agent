from typing import Literal

from langgraph.graph import MessagesState
from typing_extensions import TypedDict


class State(MessagesState):
    user_preferences: dict
    user_intent: str


class NeedReserveOutput(TypedDict):
    reserve: Literal["需要", "不需要"]
