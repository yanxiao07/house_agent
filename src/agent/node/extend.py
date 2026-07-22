from langchain_core.messages import SystemMessage
from langgraph.graph import MessagesState

from agent.common.llm import get_model


def extend_node(state: MessagesState):
    return {
        "messages": [
            get_model().invoke(
                [
                    SystemMessage(
                        content="你是乐于助人的租房助手，请结合历史对话回答问题。"
                    )
                ]
                + state["messages"]
            )
        ]
    }
