from langgraph.constants import END, START
from langgraph.graph import MessagesState, StateGraph

from agent.catalog import list_all


class BrowseState(MessagesState):
    listings: list[dict]


def load_listings(state: BrowseState):
    return {"listings": list_all()}


builder = StateGraph(BrowseState)
builder.add_node("load_listings", load_listings)
builder.add_edge(START, "load_listings")
builder.add_edge("load_listings", END)
browse_graph = builder.compile()
