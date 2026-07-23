"""Database-backed business records for the FastAPI gateway.

The operational housing inventory remains in the existing MySQL ``house`` table.
This module stores application-owned data and accepts PostgreSQL, MySQL, or SQLite
SQLAlchemy URLs, so local development does not require a PostgreSQL service.
"""

import os
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    """Base class for the business-data schema."""


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    session_id: Mapped[str] = mapped_column(String(128), index=True)
    role: Mapped[str] = mapped_column(String(24))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class BookingRecord(Base):
    __tablename__ = "booking_records"

    order_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    house_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    house_title: Mapped[str] = mapped_column(String(255))
    phone_number: Mapped[str] = mapped_column(String(32))
    viewing_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(24), default="confirmed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class BusinessRepository:
    """Small repository for user preferences, history, and appointment records."""

    def __init__(self, database_url: str | None = None):
        url = database_url or os.getenv(
            "DATABASE_URL", "sqlite:///./.langgraph_api/rental.db"
        )
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, future=True, connect_args=connect_args)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def initialize(self) -> None:
        Base.metadata.create_all(self.engine)

    def get_preferences(self, user_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            profile = session.get(UserProfile, user_id)
            return dict(profile.preferences) if profile else {}

    def save_preferences(
        self, user_id: str, preferences: dict[str, Any]
    ) -> dict[str, Any]:
        with self.sessions() as session:
            profile = session.get(UserProfile, user_id)
            if profile is None:
                profile = UserProfile(user_id=user_id, preferences=preferences)
                session.add(profile)
            else:
                profile.preferences = preferences
                profile.updated_at = datetime.now(UTC)
            session.commit()
            return dict(profile.preferences)

    def add_turn(
        self, user_id: str, session_id: str, role: str, content: str
    ) -> dict[str, Any]:
        with self.sessions() as session:
            turn = ConversationTurn(
                user_id=user_id, session_id=session_id, role=role, content=content
            )
            session.add(turn)
            session.commit()
            return self._turn_payload(turn)

    def list_turns(
        self, user_id: str, session_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        with self.sessions() as session:
            turns = session.scalars(
                select(ConversationTurn)
                .where(
                    ConversationTurn.user_id == user_id,
                    ConversationTurn.session_id == session_id,
                )
                .order_by(ConversationTurn.id.desc())
                .limit(limit)
            ).all()
            return [self._turn_payload(turn) for turn in reversed(turns)]

    def upsert_booking(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.sessions() as session:
            booking = session.get(BookingRecord, payload["order_id"])
            if booking is None:
                booking = BookingRecord(**payload)
                session.add(booking)
            else:
                for key, value in payload.items():
                    setattr(booking, key, value)
                booking.updated_at = datetime.now(UTC)
            session.commit()
            return self._booking_payload(booking)

    def list_bookings(self, user_id: str) -> list[dict[str, Any]]:
        with self.sessions() as session:
            bookings = session.scalars(
                select(BookingRecord)
                .where(BookingRecord.user_id == user_id)
                .order_by(BookingRecord.created_at.desc())
            ).all()
            return [self._booking_payload(booking) for booking in bookings]

    def cancel_booking(self, user_id: str, order_id: str) -> dict[str, Any] | None:
        with self.sessions() as session:
            booking = session.get(BookingRecord, order_id)
            if booking is None or booking.user_id != user_id:
                return None
            booking.status = "cancelled"
            booking.updated_at = datetime.now(UTC)
            session.commit()
            return self._booking_payload(booking)

    @staticmethod
    def _turn_payload(turn: ConversationTurn) -> dict[str, Any]:
        return {
            "id": turn.id,
            "role": turn.role,
            "content": turn.content,
            "created_at": turn.created_at.isoformat(),
        }

    @staticmethod
    def _booking_payload(booking: BookingRecord) -> dict[str, Any]:
        return {
            "order_id": booking.order_id,
            "user_id": booking.user_id,
            "house_id": booking.house_id,
            "house_title": booking.house_title,
            "phone_number": booking.phone_number,
            "viewing_time": booking.viewing_time.isoformat()
            if booking.viewing_time
            else None,
            "status": booking.status,
            "created_at": booking.created_at.isoformat(),
            "updated_at": booking.updated_at.isoformat(),
        }


@lru_cache(maxsize=1)
def get_repository() -> BusinessRepository:
    """Return the process-wide repository configured from ``DATABASE_URL``."""
    repository = BusinessRepository()
    repository.initialize()
    return repository
