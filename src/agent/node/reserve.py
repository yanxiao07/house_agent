import uuid
from typing import Annotated, Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedStore, ToolNode
from langgraph.types import interrupt

from agent.common.llm import get_model
from agent.common.store import ReservedInfo, UserPreferences
from agent.state.reserve import ReserveState


def get_title(state: ReserveState):
    title = interrupt("请输入要预订的房源名称")
    return {"title": str(title).strip()}


def get_phone(state: ReserveState):
    phone_number = interrupt("请输入要预订的手机号码")
    return {"phone_number": str(phone_number).strip()}


def get_id(state: ReserveState):
    id_card = interrupt("请输入预约人的身份证号码")
    return {"id_card": str(id_card).strip()}


def add_reserve_message(state: ReserveState):
    return {
        "messages": [
            HumanMessage(
                content=(
                    "根据以下信息生成预约工单："
                    f"房源={state['title']}，联系电话={state['phone_number']}，身份证={state['id_card']}"
                )
            )
        ]
    }


@tool
def generate_orders(
    phone_number: str,
    id_card: str,
    house_title: str,
    store: Annotated[Any, InjectedStore()],
) -> str:
    """根据已确认的预约信息生成工单并保存用户预约记录。"""
    order_id = str(uuid.uuid4())
    info = ReservedInfo(order_id=order_id, title=house_title, phone_number=phone_number)
    namespace = (phone_number, "preference")
    records = store.search(namespace)
    if records:
        preferences = UserPreferences.model_validate(records[0].value or {})
        preferences.reserved_info = [*(preferences.reserved_info or []), info]
        store.put(namespace, records[0].key, preferences.model_dump(exclude_none=True))
    else:
        preferences = UserPreferences(reserved_info=[info])
        store.put(
            namespace, str(uuid.uuid4()), preferences.model_dump(exclude_none=True)
        )
    return f"已成功预约房源：{house_title}，工单号为：{order_id}"


tool_node = ToolNode([generate_orders])


def call_orders(state: ReserveState):
    return {
        "messages": [
            get_model()
            .bind_tools([generate_orders])
            .invoke(
                [
                    SystemMessage(
                        content="你是工单生成助手，必须调用工具完成预约工单生成。"
                    )
                ]
                + state["messages"]
            )
        ]
    }
