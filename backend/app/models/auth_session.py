"""Durable, individually revocable sessions; never stores bearer credentials."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuthSession(Base):
    __tablename__ = "sesion_cuenta"
    __table_args__ = (
        CheckConstraint("auth_version >= 0", name="ck_sesion_cuenta_auth_version"),
        CheckConstraint("expires_at > created_at", name="ck_sesion_cuenta_expiration"),
        Index("ix_sesion_cuenta_account", "cuenta_id", "revoked_at"),
        Index("ix_sesion_cuenta_expiry", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="RESTRICT"), nullable=False)
    auth_version: Mapped[int] = mapped_column(Integer, nullable=False)
    refresh_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revocation_reason: Mapped[str | None] = mapped_column(String(40))


class LoginBucket(Base):
    __tablename__ = "auth_login_bucket"
    __table_args__ = (CheckConstraint("failures >= 0", name="ck_auth_login_bucket_failures"),
                      Index("ix_auth_login_bucket_expires", "expires_at"))
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
