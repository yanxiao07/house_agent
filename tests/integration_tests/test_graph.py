import pytest

from agent.contracts import contracts_graph

pytestmark = pytest.mark.anyio


@pytest.mark.langsmith
async def test_contract_graph_returns_risk_state() -> None:
    # The contract workflow is deterministic, so it is suitable for CI without
    # requiring a model provider or the production housing database.
    result = await contracts_graph.ainvoke(
        {"messages": [("human", "押金概不退还，房东无需通知即可进入房屋。")]}
    )

    assert result["contract_analysis"]["risks"]
