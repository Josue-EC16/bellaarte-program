"""Private conversational history; no commercial data or agent tools."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid, false, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class LenyConversation(TimestampMixin, Base):
    __tablename__ = "conversaciones"
    __table_args__ = (Index("ix_leny_conversation_owner_updated", "user_id", "updated_at"), {"schema": "leny"})

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(120), default="Nueva conversación", nullable=False)


class LenyMessage(TimestampMixin, Base):
    __tablename__ = "mensajes"
    __table_args__ = (
        UniqueConstraint("conversation_id", "sequence", name="uq_leny_message_sequence"),
        UniqueConstraint("request_id", "role", name="uq_leny_request_role"),
        CheckConstraint("sequence > 0", name="ck_leny_sequence_positive"),
        CheckConstraint("role IN ('user', 'assistant')", name="ck_leny_message_role"),
        CheckConstraint("status IN ('generating', 'completed', 'interrupted', 'failed')", name="ck_leny_message_status"),
        Index("ix_leny_message_conversation_created", "conversation_id", "created_at"),
        {"schema": "leny"},
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("leny.conversaciones.id", ondelete="CASCADE"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    request_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="completed")
    model: Mapped[str | None] = mapped_column(String(120))
    category: Mapped[str | None] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(String(120))
    policy_version: Mapped[str | None] = mapped_column(String(32))
    context_eligible: Mapped[bool] = mapped_column(Boolean, server_default=false(), default=False, nullable=False)


class LenyRateUser(Base):
    __tablename__ = "rate_users"
    __table_args__ = {"schema": "leny"}

    user_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), primary_key=True)
    last_quota_audit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LenyAdmission(Base):
    __tablename__ = "admissions"
    __table_args__ = (
        Index("ix_leny_admission_user_time", "user_id", "admitted_at"),
        {"schema": "leny"},
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), primary_key=True)
    request_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    admitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False, default="admitted")
