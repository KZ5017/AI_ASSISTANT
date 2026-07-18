from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base

json_type = JSON().with_variant(JSONB, 'postgresql')


class AssistantChatModel(Base):
    __tablename__ = 'assistant_chats'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False, default='Új beszélgetés')
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='active', index=True)
    reasoning_mode: Mapped[str] = mapped_column(String(30), nullable=False, default='normal')
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    chat_metadata: Mapped[dict[str, Any]] = mapped_column(
        'metadata',
        MutableDict.as_mutable(json_type),
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    messages: Mapped[list['AssistantMessageModel']] = relationship(
        back_populates='chat',
        cascade='all, delete-orphan',
        order_by='AssistantMessageModel.sequence_index',
    )


class AssistantMessageModel(Base):
    __tablename__ = 'assistant_messages'
    __table_args__ = (UniqueConstraint('chat_id', 'sequence_index', name='uq_assistant_message_sequence'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey('assistant_chats.id', ondelete='CASCADE'), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_activity_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reasoning_mode: Mapped[str | None] = mapped_column(String(30), nullable=True)
    message_metadata: Mapped[dict[str, Any]] = mapped_column(
        'metadata',
        MutableDict.as_mutable(json_type),
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chat: Mapped[AssistantChatModel] = relationship(back_populates='messages')
