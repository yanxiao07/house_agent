"""Rental workflow nodes shared by the LangGraph entry points."""

import re
from collections.abc import Callable
from datetime import datetime
from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from agent.catalog import LISTINGS, search_listings
from agent.common.llm import get_model, is_configured
from agent.state import Intent, RentalState

RECOMMENDATION_KEYWORDS = (
    "找房",
    "推荐",
    "房源",
    "整租",
    "合租",
    "一居",
    "两居",
    "筛选",
)
RESERVATION_KEYWORDS = ("预约", "看房", "订房", "预订")
PREFERENCE_KEYWORDS = ("我的", "历史", "偏好", "订单", "预约记录")
DISTRICTS = tuple({str(listing["district"]) for listing in LISTINGS})


def latest_human_message(messages: list[BaseMessage]) -> str:
    """Return the latest human message text, or an empty string."""
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def detect_intent(content: str) -> Intent:
    """Classify common rental tasks without a model round trip."""
    if any(keyword in content for keyword in RESERVATION_KEYWORDS):
        return "reserve"
    if any(keyword in content for keyword in PREFERENCE_KEYWORDS):
        return "preferences"
    if any(keyword in content for keyword in RECOMMENDATION_KEYWORDS):
        return "recommend"
    return "general"


def extract_budget(content: str) -> tuple[int | None, int | None]:
    """Extract a monthly-rent range from user text."""
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


def extract_districts(content: str) -> list[str]:
    """Extract supported district names from free-form user input."""
    return [district for district in DISTRICTS if district in content]


def optional_llm_reply(system_prompt: str, content: str, fallback: str) -> str:
    """Use a configured LLM for language only, never for workflow state."""
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
    """Store the user intent for conditional graph routing."""
    return {"intent": detect_intent(latest_human_message(state["messages"]))}


def recommendation_node(state: RentalState) -> dict[str, object]:
    """Search the backend catalog and return results in graph state."""
    content = latest_human_message(state["messages"])
    budget_min, budget_max = extract_budget(content)
    districts = extract_districts(content)
    preferences = dict(state.get("user_preferences") or {})
    if budget_min is not None:
        preferences["budget_min"] = budget_min
    if budget_max is not None:
        preferences["budget_max"] = budget_max
    if districts:
        preferences["districts"] = districts

    matches = search_listings(
        city="上海" if "上海" in content else None,
        districts=districts,
        budget_min=budget_min,
        budget_max=budget_max,
    )
    if matches:
        answer = f"已从后端房源目录匹配到 {len(matches)} 套房源，结果已同步到列表。"
    else:
        answer = "当前条件没有匹配房源。可以放宽预算或区域，我会重新从后端目录筛选。"

    return {
        "messages": [AIMessage(content=answer)],
        "matches": matches,
        "user_preferences": preferences,
    }


def reservation_node(state: RentalState) -> dict[str, object]:
    """Create a viewing request only when property, time, and phone are present."""
    content = latest_human_message(state["messages"])
    selected_listing = next(
        (listing for listing in LISTINGS if str(listing["title"]) in content), None
    )
    phone = next(iter(re.findall(r"(?<!\d)1\d{10}(?!\d)", content)), "")
    has_time = bool(
        re.search(r"\d{4}-\d{1,2}-\d{1,2}|今天|明天|周[一二三四五六日末]", content)
    )
    if not selected_listing or not phone or not has_time:
        missing = []
        if not selected_listing:
            missing.append("房源名称")
        if not has_time:
            missing.append("看房时间")
        if not phone:
            missing.append("联系电话")
        return {
            "messages": [
                AIMessage(
                    content=f"预约还缺少：{'、'.join(missing)}。请补充后我再提交工单。"
                )
            ],
            "booking": {"status": "draft", "missing": missing},
        }

    booking = {
        "status": "submitted",
        "id": f"VR-{datetime.now():%Y%m%d}-{uuid4().hex[:6].upper()}",
        "listing_id": selected_listing["id"],
        "listing_title": selected_listing["title"],
    }
    return {
        "messages": [
            AIMessage(
                content=f"预约已提交，工单号 {booking['id']}。顾问会尽快联系你确认带看。"
            )
        ],
        "booking": booking,
    }


def preferences_node(state: RentalState) -> dict[str, list[AIMessage]]:
    """Summarize preferences that were stored by earlier graph turns."""
    preferences = state.get("user_preferences") or {}
    budget_min = preferences.get("budget_min")
    budget_max = preferences.get("budget_max")
    districts = "、".join(preferences.get("districts", [])) or "不限"
    if budget_min is None and budget_max is None:
        answer = "暂未保存你的预算偏好。告诉我预算和区域后，我会用于后续推荐。"
    else:
        answer = (
            f"当前偏好：{districts}，月租 {budget_min or 0}-{budget_max or '不限'} 元。"
        )
    return {"messages": [AIMessage(content=answer)]}


def general_node(state: RentalState) -> dict[str, list[AIMessage]]:
    """Answer general questions without affecting catalog or booking state."""
    content = latest_human_message(state["messages"])
    answer = optional_llm_reply(
        "你是专业租赁顾问。回答与租房相关的问题，内容准确、简洁，不编造政策或房源。",
        content,
        "我可以从后端房源目录为你找房、提交预约和查看偏好。请告诉我预算、区域或意向房源。",
    )
    return {"messages": [AIMessage(content=answer)]}


ROUTE_HANDLERS: dict[str, Callable[[RentalState], dict[str, object]]] = {
    "recommend": recommendation_node,
    "reserve": reservation_node,
    "preferences": preferences_node,
    "general": general_node,
}
