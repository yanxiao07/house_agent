import json

from langchain_core.messages import AIMessage
from langgraph.constants import END, START
from langgraph.graph import MessagesState, StateGraph

from agent.catalog import create_listing, delete_listing, list_all, update_listing


class CatalogAdminState(MessagesState):
    listings: list[dict]


def manage_listing(state: CatalogAdminState):
    try:
        request = json.loads(state["messages"][-1].content)
        action = request.get("action")
        if action == "create":
            detail = f"Created listing {create_listing(request.get('listing') or {})}."
        elif action == "update":
            update_listing(request["listing_id"], request.get("listing") or {})
            detail = "Listing updated."
        elif action == "delete":
            delete_listing(request["listing_id"])
            detail = "Listing deleted."
        elif action == "read":
            detail = "Listings loaded."
        else:
            raise ValueError("Unsupported catalogue action")
        return {"listings": list_all(), "messages": [AIMessage(content=detail)]}
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        return {"listings": list_all(), "messages": [AIMessage(content=f"Catalogue action failed: {error}")]}


builder = StateGraph(CatalogAdminState)
builder.add_node("manage_listing", manage_listing)
builder.add_edge(START, "manage_listing")
builder.add_edge("manage_listing", END)
catalog_admin_graph = builder.compile()
