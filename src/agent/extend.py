"""Standalone general rental-support graph."""

from langgraph.constants import END, START
from langgraph.graph import StateGraph

from agent.common.context import ContextSchema
from agent.state import RentalState
from agent.workflow import general_node

builder = StateGraph(RentalState, context_schema=ContextSchema)
builder.add_node("general", general_node)
builder.add_edge(START, "general")
builder.add_edge("general", END)
extend_graph = builder.compile()
