from langchain_core.messages import AIMessage, HumanMessage
from langgraph.pregel import Pregel

from agent.graph import graph


def test_placeholder() -> None:
    assert isinstance(graph, Pregel)


def test_routes_recommendation_without_provider(monkeypatch) -> None:
    monkeypatch.setattr("agent.workflow.is_configured", lambda: False)

    result = graph.invoke(
        {"messages": [HumanMessage(content="在静安找一居室，预算 8000 以内")]}
    )

    assert result["intent"] == "recommend"
    assert result["user_preferences"] == {"budget_min": 0, "budget_max": 8000}
    assert isinstance(result["messages"][-1], AIMessage)


def test_routes_viewing_reservation_without_provider(monkeypatch) -> None:
    monkeypatch.setattr("agent.workflow.is_configured", lambda: False)

    result = graph.invoke({"messages": [HumanMessage(content="帮我预约周六看房")]})

    assert result["intent"] == "reserve"
    assert "房源名称" in result["messages"][-1].content
