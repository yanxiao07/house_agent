from langgraph.constants import END, START
from langgraph.graph import StateGraph

from agent.common.context import ContextSchema
from agent.node.recommend import (
    call_get_schema,
    check_query,
    collect_user_info,
    generate_query,
    get_schema_node,
    list_tables,
    run_query_node,
)
from agent.state.recommend import RecommendState

builder = StateGraph(RecommendState, context_schema=ContextSchema)
builder.add_node("collect_user_info", collect_user_info)
builder.add_node("list_tables", list_tables)
builder.add_node("call_get_schema", call_get_schema)
builder.add_node("get_schema", get_schema_node)
builder.add_node("generate_query", generate_query)
builder.add_node("check_query", check_query)
builder.add_node("run_query", run_query_node)
builder.add_edge(START, "collect_user_info")
builder.add_edge("collect_user_info", "list_tables")
builder.add_edge("list_tables", "call_get_schema")
builder.add_edge("call_get_schema", "get_schema")
builder.add_edge("get_schema", "generate_query")
builder.add_conditional_edges(
    "generate_query",
    lambda state: "check_query" if state["messages"][-1].tool_calls else END,
    {"check_query": "check_query", END: END},
)
builder.add_edge("check_query", "run_query")
builder.add_edge("run_query", "generate_query")
recommend_graph = builder.compile()
