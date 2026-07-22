"""Standalone recommendation graph."""

from langgraph.constants import END, START
from langgraph.graph import StateGraph

from agent.common.context import ContextSchema
from agent.state import RentalState
from agent.workflow import recommendation_node

builder = StateGraph(RentalState, context_schema=ContextSchema)
builder.add_node("recommend", recommendation_node)
builder.add_edge(START, "recommend")
builder.add_edge("recommend", END)
recommend_graph = builder.compile()
