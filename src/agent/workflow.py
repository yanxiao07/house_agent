"""Deterministic routing with optional LLM-polished responses."""

import re
from collections.abc import Callable

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from agent.common.llm import get_model, is_configured
from agent.state import Intent, RentalState

RECOMMENDATION_KEYWORDS = ("找房", "推荐", "房源", "整租", "合租", "一居", "两居")
RESERVATION_KEYWORDS = ("预约", "看房", "订房", "预订")
PREFERENCE_KEYWORDS = ("我的", "历史", "偏好", "订单", "预约记录")


def latest_human_message(messages: list[BaseMessage]) -> str:
    """Return the latest human message text, or an empty string."""
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def detect_intent(content: str) -> Intent:
    """Classify common rental tasks without requiring a model round trip."""
    if any(keyword in content for keyword in RESERVATION_KEYWORDS):
        return "reserve"
    if any(keyword in content for keyword in PREFERENCE_KEYWORDS):
        return "preferences"
    if any(keyword in content for keyword in RECOMMENDATION_KEYWORDS):
        return "recommend"
    return "general"


def extract_budget(content: str) -> tuple[int | None, int | None]:
    """Extract a simple monthly-rent range from user text."""
    values = [
        int(value) for value in re.findall(r"(?<!\d)(\d{3,5})(?:\s*[元块])?", content)
    ]
    if len(values) >= 2:
        return min(values[0], values[1]), max(values[0], values[1])
    if values and any(token in content for token in ("以内", "以下", "不超过")):
        return 0, values[0]
    if values and any(token in content for token in ("以上", "起", "至少")):
        return values[0], None
    return None, None


def optional_llm_reply(system_prompt: str, content: str, fallback: str) -> str:
    """Use the configured model when available, while retaining offline behavior."""
    if not is_configured():
        return fallback
    try:
        response = get_model().invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=content)]
        )
        return str(response.content).strip() or fallback
    except Exception:
        return fallback


def classify_node(state: RentalState) -> dict[str, Intent]:
    """Store the current user intent for conditional graph routing."""
    return {"intent": detect_intent(latest_human_message(state["messages"]))}


def recommendation_node(state: RentalState) -> dict[str, object]:
    """Prepare a concise recommendation response and retain budget preferences."""
    content = latest_human_message(state["messages"])
    budget_min, budget_max = extract_budget(content)
    preference = dict(state.get("user_preferences") or {})
    if budget_min is not None:
        preference["budget_min"] = budget_min
    if budget_max is not None:
        preference["budget_max"] = budget_max

    budget_text = ""
    if budget_min is not None or budget_max is not None:
        budget_text = (
            f" 预算范围已记录为 {budget_min or 0}-{budget_max or '不限'} 元/月。"
        )
    fallback = (
        "我会优先匹配通勤便利、房源状态可核验的房子。"
        f"{budget_text} 请补充意向城市、区域和户型，我会继续缩小范围。"
    )
    answer = optional_llm_reply(
        "你是专业长租顾问。简洁确认用户找房需求，不编造房源或价格，并提示缺失条件。",
        content,
        fallback,
    )
    return {"messages": [AIMessage(content=answer)], "user_preferences": preference}


def reservation_node(state: RentalState) -> dict[str, list[AIMessage]]:
    """Acknowledge a viewing request and collect the minimum appointment details."""
    content = latest_human_message(state["messages"])
    fallback = (
        "可以安排看房。请确认意向房源名称、可看房时段和联系电话，顾问会为你核验档期。"
    )
    answer = optional_llm_reply(
        "你是专业租赁顾问。确认看房预约请求，只索取房源、时间和联系电话，不索取身份证信息。",
        content,
        fallback,
    )
    return {"messages": [AIMessage(content=answer)]}


def preferences_node(state: RentalState) -> dict[str, list[AIMessage]]:
    """Summarize stored conversation preferences without inventing data."""
    preferences = state.get("user_preferences") or {}
    budget_min = preferences.get("budget_min")
    budget_max = preferences.get("budget_max")
    if budget_min is None and budget_max is None:
        answer = "暂未保存你的预算偏好。告诉我理想区域、预算和户型后，我会在后续推荐中优先考虑。"
    else:
        answer = f"当前已记录的月租预算为 {budget_min or 0}-{budget_max or '不限'} 元。你也可以随时更新区域和户型偏好。"
    return {"messages": [AIMessage(content=answer)]}


def general_node(state: RentalState) -> dict[str, list[AIMessage]]:
    """Respond to non-routing questions in the rental domain."""
    content = latest_human_message(state["messages"])
    answer = optional_llm_reply(
        "你是专业租赁顾问。回答与租房相关的问题，内容准确、简洁，不杜撰政策或房源。",
        content,
        "我可以协助你找房、筛选房源、安排看房和查看已记录偏好。你想从哪一步开始？",
    )
    return {"messages": [AIMessage(content=answer)]}


ROUTE_HANDLERS: dict[str, Callable[[RentalState], dict[str, object]]] = {
    "recommend": recommendation_node,
    "reserve": reservation_node,
    "preferences": preferences_node,
    "general": general_node,
}
