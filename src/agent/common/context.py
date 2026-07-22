"""Runtime context supplied by the LangGraph server."""

from typing import TypedDict


class ContextSchema(TypedDict, total=False):
    """Request-scoped values supplied by an API client."""

    user_id: str
