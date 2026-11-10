"""N5: persistent MySQL chat sessions, messages and audited tool calls.

Registered with SQLAlchemy when imported by hotel.services.chatbot_engine.
Tables are created by the application's existing Base.metadata.create_all(engine).
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hotel.models.common import utc_now
from hotel.models.database import Base


class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), index=True, nullable=True)
    role_context: Mapped[str] = mapped_column(String(30), nullable=False)
    context_json: Mapped[str] = mapped_column(Text, default='{}', nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey('chat_sessions.id'), index=True, nullable=False)
    sender: Mapped[str] = mapped_column(String(12), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


class ChatToolCall(Base):
    __tablename__ = 'chat_tool_calls'
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey('chat_sessions.id'), index=True, nullable=False)
    tool_name: Mapped[str] = mapped_column(String(60), nullable=False)
    arguments_json: Mapped[str] = mapped_column(Text, nullable=False, default='{}')
    status: Mapped[str] = mapped_column(String(30), nullable=False, default='pending')
    confirmation_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confirmed_by_user: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    idempotency_key: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    result_text: Mapped[str] = mapped_column(Text, default='', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
