from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AuditoriaSistema(Base):
    __tablename__ = "auditoria_sistema"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    cuenta_id: Mapped[int | None] = mapped_column(ForeignKey("cuentas.id", ondelete="SET NULL"))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    accion: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    descripcion: Mapped[str] = mapped_column(Text(), nullable=False)
    referencia: Mapped[str | None] = mapped_column(String(120))
    ip_address: Mapped[str | None] = mapped_column(String(60))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    cuenta = relationship("Cuenta")
    usuario = relationship("Usuario")

