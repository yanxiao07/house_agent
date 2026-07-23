from agent.contracts import analyze_contract, contracts_graph


def test_contract_analysis_flags_high_risk_deposit_clause() -> None:
    result = analyze_contract("押金为两个月租金，房东可随时没收且概不退还。违约金按全部租金计算。")

    assert any(item["category"] == "押金" and item["level"] == "high" for item in result["risks"])
    assert any(item["category"] == "违约与解除" for item in result["risks"])
    assert result["knowledge"]


def test_contract_graph_exposes_structured_analysis() -> None:
    state = contracts_graph.invoke({"messages": [("human", "租金可由房东单方调整，押金不退。")]})

    assert "contract_analysis" in state
    assert state["contract_analysis"]["risks"]
