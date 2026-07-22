"""Standalone viewing-reservation graph."""

from langgraph.constants import END, START
from langgraph.graph import StateGraph

from agent.common.context import ContextSchema
from agent.state import RentalState
from agent.workflow import reservation_node

builder = StateGraph(RentalState, context_schema=ContextSchema)
builder.add_node("reserve", reservation_node)
builder.add_edge(START, "reserve")
builder.add_edge("reserve", END)
reserve_graph = builder.compile()
