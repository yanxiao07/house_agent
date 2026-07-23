"""FastAPI gateway for rental business data and contract analysis.

LangGraph remains responsible for agent orchestration and interrupts. This gateway
offers conventional REST endpoints for clients that need health checks, user-owned
business records, or contract analysis without consuming the graph streaming API.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal

import anyio
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field

from agent.catalog import list_all
from agent.contracts import analyze_contract
from agent.persistence import BusinessRepository, get_repository


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize schema once at process start. PostgreSQL migrations can replace
    # this bootstrap in production without changing endpoint contracts.
    get_repository().initialize()
    yield


app = FastAPI(
    title="House Agent API",
    version="1.1.0",
    description="REST gateway for rental records, sessions, bookings, and contract review.",
    lifespan=lifespan,
)


class PreferencesPayload(BaseModel):
    preferences: dict = Field(default_factory=dict)


class ConversationPayload(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=10000)


class BookingPayload(BaseModel):
    order_id: str = Field(min_length=1, max_length=64)
    user_id: str = Field(min_length=1, max_length=128)
    house_title: str = Field(min_length=1, max_length=255)
    phone_number: str = Field(min_length=1, max_length=32)
    house_id: str | None = Field(default=None, max_length=64)
    viewing_time: datetime | None = None
    status: Literal["confirmed", "cancelled"] = "confirmed"


class ContractPayload(BaseModel):
    text: str = Field(min_length=20, max_length=50000)


def _repository() -> BusinessRepository:
    """Keep dependency lookup central so tests can override the cached repository."""
    return get_repository()


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "house-agent-api"}


@app.get("/api/listings")
async def listings(limit: int = Query(default=24, ge=1, le=100)) -> dict:
    # PyMySQL is blocking; move it to a worker thread to preserve FastAPI's event loop.
    records = await anyio.to_thread.run_sync(list_all, limit)
    return {"items": records, "count": len(records)}


@app.get("/api/users/{user_id}/preferences")
async def get_preferences(user_id: str) -> dict:
    return {"user_id": user_id, "preferences": await anyio.to_thread.run_sync(_repository().get_preferences, user_id)}


@app.put("/api/users/{user_id}/preferences")
async def put_preferences(user_id: str, payload: PreferencesPayload) -> dict:
    preferences = await anyio.to_thread.run_sync(_repository().save_preferences, user_id, payload.preferences)
    return {"user_id": user_id, "preferences": preferences}


@app.post("/api/conversations", status_code=status.HTTP_201_CREATED)
async def create_conversation_turn(payload: ConversationPayload) -> dict:
    return await anyio.to_thread.run_sync(
        _repository().add_turn, payload.user_id, payload.session_id, payload.role, payload.content
    )


@app.get("/api/users/{user_id}/conversations/{session_id}")
async def conversation_history(user_id: str, session_id: str, limit: int = Query(default=100, ge=1, le=500)) -> dict:
    turns = await anyio.to_thread.run_sync(_repository().list_turns, user_id, session_id, limit)
    return {"items": turns, "count": len(turns)}


@app.get("/api/users/{user_id}/bookings")
async def bookings(user_id: str) -> dict:
    items = await anyio.to_thread.run_sync(_repository().list_bookings, user_id)
    return {"items": items, "count": len(items)}


@app.put("/api/bookings/{order_id}")
async def put_booking(order_id: str, payload: BookingPayload) -> dict:
    if order_id != payload.order_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order ID mismatch")
    return await anyio.to_thread.run_sync(_repository().upsert_booking, payload.model_dump())


@app.post("/api/users/{user_id}/bookings/{order_id}/cancel")
async def cancel_booking(user_id: str, order_id: str) -> dict:
    booking = await anyio.to_thread.run_sync(_repository().cancel_booking, user_id, order_id)
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking


@app.post("/api/contracts/analyze")
async def contract_analysis(payload: ContractPayload) -> dict:
    # Deterministic retrieval makes this endpoint usable without an LLM key.
    return analyze_contract(payload.text)
