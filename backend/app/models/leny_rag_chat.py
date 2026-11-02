"""Revocable message references and the durable local inference quarantine."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LenyRagMessageSource(Base):
    __tablename__ = 'rag_fuentes_mensaje'
    __table_args__ = (
        UniqueConstraint('message_id', 'ordinal', name='uq_leny_rag_source_ordinal'),
        UniqueConstraint('message_id', 'fragment_id', name='uq_leny_rag_source_fragment'),
        CheckConstraint('ordinal BETWEEN 1 AND 5', name='ck_leny_rag_source_ordinal'),
        Index('ix_leny_rag_source_fragment', 'fragment_id'),
        {'schema': 'leny'},
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    message_id: Mapped[UUID] = mapped_column(ForeignKey('leny.mensajes.id', ondelete='CASCADE'), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    fragment_id: Mapped[UUID | None] = mapped_column(ForeignKey('leny.rag_fragmentos.id', ondelete='SET NULL'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LenyInferenceState(Base):
    __tablename__ = 'inferencia_estado'
    __table_args__ = (
        CheckConstraint('id = 1', name='ck_leny_inference_singleton'),
        CheckConstraint("state IN ('idle','inflight','uncertain')", name='ck_leny_inference_state'),
        CheckConstraint("phase IS NULL OR phase IN ('classifier','query_embedding','generation')", name='ck_leny_inference_phase'),
        CheckConstraint("(state = 'idle' AND request_id IS NULL AND model IS NULL AND phase IS NULL) OR "
                        "(state IN ('inflight','uncertain') AND request_id IS NOT NULL AND "
                        "model IS NOT NULL AND length(trim(model)) BETWEEN 1 AND 120 AND phase IS NOT NULL)",
                        name='ck_leny_inference_metadata'),
        {'schema': 'leny'},
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1, autoincrement=False)
    state: Mapped[str] = mapped_column(String(16), default='idle', server_default='idle', nullable=False)
    # No FK: an unresolved provider call outlives conversation retention.
    request_id: Mapped[UUID | None] = mapped_column(Uuid)
    model: Mapped[str | None] = mapped_column(String(120))
    phase: Mapped[str | None] = mapped_column(String(24))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
