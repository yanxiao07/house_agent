import os
import uuid
from functools import lru_cache

from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    filter_messages,
)
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime
from langgraph.store.base import BaseStore
from langgraph.types import interrupt
from pydantic import BaseModel

from agent.catalog import list_for_query
from agent.common.context import ContextSchema
from agent.common.llm import get_model
from agent.common.store import UserPreferences
from agent.state.recommend import RecommendState, get_recommend_info


class UserInfo(BaseModel):
    city: str | None = None
    district: str | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    room_type: str | None = None
    orientation: str | None = None
    room_count: int | None = None
    others: str | None = None


@lru_cache(maxsize=1)
def _tools():
    required = ("DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"数据库配置缺失：{', '.join(missing)}")
    uri = "mysql+pymysql://{user}:{password}@{host}:{port}/{name}".format(
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        name=os.environ["DB_NAME"],
    )
    return SQLDatabaseToolkit(db=SQLDatabase.from_uri(uri), llm=get_model()).get_tools()


def _tool(name: str):
    return next(tool for tool in _tools() if tool.name == name)


def collect_user_info(
    state: RecommendState, runtime: Runtime[ContextSchema], *, store: BaseStore
):
    messages = filter_messages(state["messages"], include_types="human")
    prompt = """你是租房需求结构化提取专家。提取 city、district、budget_min、budget_max、room_type、orientation、room_count、others。未提及字段为 null；x元以内最小值为0，x元以上最大值为50000。"""
    info = (
        get_model()
        .with_structured_output(UserInfo)
        .invoke([SystemMessage(content=prompt), messages[-1]])
    )
    updated = info.model_dump(exclude_none=True)
    missing = []
    if not updated.get("city"):
        missing.append("城市")
    if updated.get("budget_min") is None or updated.get("budget_max") is None:
        missing.append("预算范围")
    if missing:
        answer = interrupt(
            f"为了推荐合适房源，请补充：{'、'.join(missing)}；不提供请输入“不提供”。"
        )
        if str(answer).strip() != "不提供":
            supplement = (
                get_model()
                .with_structured_output(UserInfo)
                .invoke(
                    [SystemMessage(content=prompt), HumanMessage(content=str(answer))]
                )
            )
            updated.update(supplement.model_dump(exclude_none=True))
    updated.setdefault("city", "未指定")
    updated.setdefault("budget_min", 0)
    updated.setdefault("budget_max", 50000)
    updated.setdefault("room_count", 5)
    user_id = runtime.context.get("user_id", "anonymous")
    records = store.search((user_id, "preference"))
    preferences = UserPreferences(
        budget_min=updated["budget_min"], budget_max=updated["budget_max"]
    )
    if records:
        value = records[0].value or {}
        value.update(preferences.model_dump(exclude_none=True))
        store.put((user_id, "preference"), records[0].key, value)
    else:
        value = preferences.model_dump(exclude_none=True)
        store.put((user_id, "preference"), str(uuid.uuid4()), value)
    updated["user_preferences"] = value
    updated["messages"] = [HumanMessage(content=get_recommend_info(updated))]
    return updated


def list_tables(state: RecommendState):
    call = {
        "name": "sql_db_list_tables",
        "args": {},
        "id": "list-tables",
        "type": "tool_call",
    }
    request = AIMessage(content="", tool_calls=[call])
    result = _tool("sql_db_list_tables").invoke(call)
    return {
        "messages": [request, result, AIMessage(content=f"可用的表：{result.content}")]
    }


def call_get_schema(state: RecommendState):
    response = get_model().bind_tools([_tool("sql_db_schema")]).invoke(state["messages"])
    return {"messages": [response]}


def get_schema_node(state: RecommendState):
    if not state["messages"][-1].tool_calls:
        return {"messages": []}
    return ToolNode([_tool("sql_db_schema")], name="get_schema").invoke(state)


def generate_query(state: RecommendState):
    prompt = """你是用于与 SQL 数据库交互的租房代理。生成语法正确的查询，只查询所需列，最多返回 {top_k} 条，禁止任何 DML。调用 sql_db_query 执行查询。""".format(
        top_k=state.get("room_count", 5)
    )
    response = (
        get_model()
        .bind_tools([_tool("sql_db_query")])
        .invoke([SystemMessage(content=prompt), *state["messages"]])
    )
    return {"messages": [response]}


def check_query(state: RecommendState):
    last = state["messages"][-1]
    query = last.tool_calls[0]["args"]["query"]
    response = get_model().bind_tools([_tool("sql_db_query")]).invoke(
        [SystemMessage(content="检查 SQL 查询并调用 sql_db_query 执行。"), HumanMessage(content=query)]
    )
    if not response.tool_calls:
        response = last
    else:
        response.id = last.id
    return {"messages": [response]}


def run_query_node(state: RecommendState):
    result = ToolNode([_tool("sql_db_query")], name="run_query").invoke(state)
    query = state["messages"][-1].tool_calls[0]["args"].get("query", "")
    result["listings"] = list_for_query(query)
    return result
