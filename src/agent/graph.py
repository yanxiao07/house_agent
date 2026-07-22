"""Main House Agent graph."""

from langgraph.constants import END, START
from langgraph.graph import StateGraph

from agent.common.context import ContextSchema
from agent.state import RentalState
from agent.workflow import (
    classify_node,
    general_node,
    preferences_node,
    recommendation_node,
    reservation_node,
)

builder = StateGraph(RentalState, context_schema=ContextSchema)
builder.add_node("classify", classify_node)
builder.add_node("recommend", recommendation_node)
builder.add_node("reserve", reservation_node)
builder.add_node("preferences", preferences_node)
builder.add_node("general", general_node)
builder.add_edge(START, "classify")
builder.add_conditional_edges(
    "classify",
    lambda state: state["intent"],
    {
        "recommend": "recommend",
        "reserve": "reserve",
        "preferences": "preferences",
        "general": "general",
    },
)
for name in ("recommend", "reserve", "preferences", "general"):
    builder.add_edge(name, END)

graph = builder.compile()
