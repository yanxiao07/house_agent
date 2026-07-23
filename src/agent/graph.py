from typing import Literal

from langgraph.constants import END, START
from langgraph.graph import StateGraph

from agent.common.context import ContextSchema
from agent.contracts import contracts_graph
from agent.extend import extend_graph
from agent.node.main import (
    get_store_info,
    get_user_preferences,
    indentify_question,
    need_reserve,
)
from agent.recommend import recommend_graph
from agent.reserve import reserve_graph
from agent.state.main import NeedReserveOutput, State

builder = StateGraph(State, context_schema=ContextSchema)
builder.add_node("get_store_info", get_store_info)
builder.add_node("indentify_question", indentify_question)
builder.add_node("recommend_graph", recommend_graph)
builder.add_node("reserve_graph", reserve_graph)
builder.add_node("contracts_graph", contracts_graph)
builder.add_node("extend_graph", extend_graph)
builder.add_node("get_user_preferences", get_user_preferences)
builder.add_node("need_reserve", need_reserve)
builder.add_edge(START, "get_store_info")
builder.add_edge("get_store_info", "indentify_question")


def route_message(
    state: State,
) -> Literal[
    "recommend_graph", "reserve_graph", "contracts_graph", "extend_graph", "get_user_preferences"
]:
    return {
        "recommend_house": "recommend_graph",
        "reserve_house": "reserve_graph",
        "contract_review": "contracts_graph",
        "get_info": "get_user_preferences",
    }.get(state["user_intent"], "extend_graph")


def should_reserve(state: NeedReserveOutput):
    return "reserve_graph" if state["reserve"] == "需要" else END


builder.add_conditional_edges("indentify_question", route_message)
builder.add_edge("recommend_graph", "need_reserve")
builder.add_conditional_edges(
    "need_reserve", should_reserve, {"reserve_graph": "reserve_graph", END: END}
)
builder.add_edge("reserve_graph", END)
builder.add_edge("contracts_graph", END)
builder.add_edge("get_user_preferences", END)
builder.add_edge("extend_graph", END)
graph = builder.compile()
