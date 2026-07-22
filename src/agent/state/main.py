from typing import Literal, TypedDict

from langgraph.graph import MessagesState


class State(MessagesState):
    user_preferences: dict
    user_intent: str


class NeedReserveOutput(TypedDict):
    reserve: Literal["需要", "不需要"]
