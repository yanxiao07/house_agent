from typing import Literal

from langchain_core.messages import SystemMessage, filter_messages
from langgraph.runtime import Runtime
from langgraph.store.base import BaseStore
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from agent.common.context import ContextSchema
from agent.common.llm import get_model
from agent.state.main import NeedReserveOutput, State


def get_store_info(state: State, runtime: Runtime[ContextSchema], *, store: BaseStore):
    user_id = runtime.context.get("user_id", "anonymous")
    records = store.search((user_id, "preference"))
    return {"user_preferences": records[0].value if records else {}}


class UserMessage(BaseModel):
    type: Literal["recommend_house", "reserve_house", "contract_review", "get_info", "others"] = Field(
        description="租房推荐、预约房源、合同审查、查询本人偏好或其他问题"
    )


def indentify_question(state: State):
    prompt = """将用户问题分类为且仅分类为：
recommend_house（找房、推荐、筛选房源），reserve_house（预约、下单、预订房源），
contract_review（租房合同、押金、租金、违约、解约风险审查），
get_info（查询本人历史订单、预算和偏好），others（其余问题）。"""
    result = (
        get_model()
        .with_structured_output(UserMessage)
        .invoke([SystemMessage(content=prompt), state["messages"][-1]])
    )
    return {"user_intent": result.type}


def need_reserve(state: State) -> NeedReserveOutput:
    answer = interrupt("已为您推荐房源，是否需要预约看房？请输入“需要”或“不需要”。")
    return {"reserve": "需要" if str(answer).strip() == "需要" else "不需要"}


def get_user_preferences(state: State):
    prefs = state.get("user_preferences", {})
    latest = filter_messages(state["messages"], include_types="human")[-1]
    prompt = (
        "你是租赁顾问。根据用户问题回答已保存偏好；没有的信息不要编造。\n"
        f"预算：{prefs.get('budget_min')} - {prefs.get('budget_max')}；"
        f"预约记录：{prefs.get('reserved_info', [])}"
    )
    return {"messages": [get_model().invoke([SystemMessage(content=prompt), latest])]}
