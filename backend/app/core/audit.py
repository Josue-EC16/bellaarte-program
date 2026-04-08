from sqlalchemy.orm import Session

from app.models.audit_log import AuditoriaSistema
from app.models.account import Cuenta
from app.models.user import Usuario


def register_audit_event(
    db: Session,
    *,
    action: str,
    description: str,
    account: Cuenta | None = None,
    user: Usuario | None = None,
    reference: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditoriaSistema:
    audit = AuditoriaSistema(
        cuenta_id=account.id if account else None,
        usuario_id=user.id if user else None,
        accion=action,
        descripcion=description,
        referencia=reference,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(audit)
    return audit
