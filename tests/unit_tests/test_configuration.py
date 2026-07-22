from langgraph.pregel import Pregel

from agent.graph import graph


def test_placeholder() -> None:
    assert isinstance(graph, Pregel)
