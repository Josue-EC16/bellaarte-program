from __future__ import annotations

import html
from datetime import datetime, time
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.account import Cuenta
from app.models.audit_log import AuditoriaSistema
from app.models.user import Usuario
from app.schemas.audit import AuditDetailResponse, AuditEventResponse, AuditListItem, AuditQueryFilters, AuditUserSummary


def _ensure_admin(account: Cuenta) -> None:
    if account.rol.codigo != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el ADMIN puede acceder a auditoría.")


def _user_summary(user: Usuario | None) -> AuditUserSummary | None:
    if user is None:
        return None
    cuenta = user.cuenta
    return AuditUserSummary(
        user_id=user.id,
        full_name=user.nombre_completo,
        username=cuenta.username if cuenta else None,
        email=user.correo,
    )


def _to_list_item(audit: AuditoriaSistema) -> AuditListItem:
    return AuditListItem(
        id=audit.id,
        fecha=audit.fecha,
        modulo=audit.modulo,
        submodulo=audit.submodulo,
        tabla=audit.tabla,
        id_registro=audit.id_registro,
        accion=audit.accion,
        accion_funcional=audit.accion_funcional,
        descripcion=audit.descripcion,
        campo=audit.campo,
        valor_anterior=audit.valor_anterior,
        valor_nuevo=audit.valor_nuevo,
        metodo_http=audit.metodo_http,
        ip=audit.ip,
        user_agent=audit.user_agent,
        dispositivo=audit.dispositivo,
        navegador=audit.navegador,
        sistema_operativo=audit.sistema_operativo,
        id_evento=audit.id_evento,
        usuario=_user_summary(audit.usuario),
    )


def _base_stmt():
    return select(AuditoriaSistema).options(joinedload(AuditoriaSistema.usuario).joinedload(Usuario.cuenta))


def _apply_filters(stmt, filters: AuditQueryFilters):
    if filters.user_id is not None:
        stmt = stmt.where(AuditoriaSistema.usuario_id == filters.user_id)
    if filters.module:
        stmt = stmt.where(func.upper(AuditoriaSistema.modulo) == filters.module)
    if filters.submodule:
        stmt = stmt.where(func.upper(func.coalesce(AuditoriaSistema.submodulo, "")) == filters.submodule)
    if filters.table:
        stmt = stmt.where(func.upper(AuditoriaSistema.tabla) == filters.table)
    if filters.record_id:
        stmt = stmt.where(func.upper(AuditoriaSistema.id_registro).like(f"%{filters.record_id.upper()}%"))
    if filters.action is not None:
        stmt = stmt.where(AuditoriaSistema.accion == filters.action)
    if filters.functional_action:
        stmt = stmt.where(func.upper(func.coalesce(AuditoriaSistema.accion_funcional, "")).like(f"%{filters.functional_action}%"))
    if filters.date_from is not None:
        stmt = stmt.where(AuditoriaSistema.fecha >= datetime.combine(filters.date_from, time.min))
    if filters.date_to is not None:
        stmt = stmt.where(AuditoriaSistema.fecha <= datetime.combine(filters.date_to, time.max))
    if filters.ip:
        stmt = stmt.where(func.coalesce(AuditoriaSistema.ip, "").like(f"%{filters.ip}%"))
    if filters.device:
        stmt = stmt.where(func.upper(func.coalesce(AuditoriaSistema.dispositivo, "")).like(f"%{filters.device}%"))
    if filters.browser:
        stmt = stmt.where(func.upper(func.coalesce(AuditoriaSistema.navegador, "")).like(f"%{filters.browser}%"))
    if filters.operating_system:
        stmt = stmt.where(func.upper(func.coalesce(AuditoriaSistema.sistema_operativo, "")).like(f"%{filters.operating_system}%"))
    if filters.http_method:
        stmt = stmt.where(func.upper(func.coalesce(AuditoriaSistema.metodo_http, "")) == filters.http_method)
    if filters.event_id is not None:
        stmt = stmt.where(AuditoriaSistema.id_evento == filters.event_id)
    if filters.search_description:
        stmt = stmt.where(func.upper(func.coalesce(AuditoriaSistema.descripcion, "")).like(f"%{filters.search_description}%"))
    if filters.search_old_value:
        stmt = stmt.where(func.upper(func.coalesce(AuditoriaSistema.valor_anterior, "")).like(f"%{filters.search_old_value}%"))
    if filters.search_new_value:
        stmt = stmt.where(func.upper(func.coalesce(AuditoriaSistema.valor_nuevo, "")).like(f"%{filters.search_new_value}%"))
    if filters.search_field:
        stmt = stmt.where(func.upper(func.coalesce(AuditoriaSistema.campo, "")).like(f"%{filters.search_field}%"))
    return stmt


def list_audits(
    db: Session,
    *,
    account: Cuenta,
    filters: AuditQueryFilters,
) -> list[AuditListItem]:
    _ensure_admin(account)
    stmt = _apply_filters(_base_stmt(), filters).order_by(AuditoriaSistema.fecha.desc(), AuditoriaSistema.id.desc())
    return [_to_list_item(row) for row in db.execute(stmt).scalars().all()]


def get_audit_detail(
    db: Session,
    *,
    audit_id: int,
    account: Cuenta,
) -> AuditDetailResponse:
    _ensure_admin(account)
    audit = db.execute(
        _base_stmt().where(AuditoriaSistema.id == audit_id)
    ).scalar_one_or_none()
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro de auditoría no encontrado.")
    event_count = 0
    if audit.id_evento is not None:
        event_count = db.execute(
            select(func.count(AuditoriaSistema.id)).where(AuditoriaSistema.id_evento == audit.id_evento)
        ).scalar_one()
    item = _to_list_item(audit)
    return AuditDetailResponse(**item.model_dump(), event_records_count=event_count)


def get_audit_event(
    db: Session,
    *,
    event_id: UUID,
    account: Cuenta,
) -> AuditEventResponse:
    _ensure_admin(account)
    records = db.execute(
        _base_stmt()
        .where(AuditoriaSistema.id_evento == event_id)
        .order_by(AuditoriaSistema.fecha.asc(), AuditoriaSistema.id.asc())
    ).scalars().all()
    if not records:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontraron auditorías para ese evento.")
    items = [_to_list_item(row) for row in records]
    return AuditEventResponse(event_id=event_id, total_records=len(items), records=items)


def export_audit_rows_for_csv(
    db: Session,
    *,
    account: Cuenta,
    filters: AuditQueryFilters,
) -> list[list[object]]:
    audits = list_audits(db, account=account, filters=filters)
    rows: list[list[object]] = []
    for audit in audits:
        rows.append(
            [
                audit.id,
                audit.fecha.isoformat(),
                audit.usuario.full_name if audit.usuario else "SISTEMA",
                audit.usuario.username if audit.usuario else "",
                audit.modulo,
                audit.submodulo or "",
                audit.tabla,
                audit.id_registro,
                audit.accion.value.upper(),
                audit.accion_funcional or "",
                audit.descripcion or "",
                audit.campo or "",
                audit.valor_anterior or "",
                audit.valor_nuevo or "",
                audit.metodo_http or "",
                audit.ip or "",
                audit.dispositivo or "",
                audit.navegador or "",
                audit.sistema_operativo or "",
                str(audit.id_evento or ""),
            ]
        )
    return rows


def build_audit_printable_html(
    db: Session,
    *,
    account: Cuenta,
    filters: AuditQueryFilters | None = None,
    event_id: UUID | None = None,
) -> str:
    _ensure_admin(account)
    if event_id is not None:
        event = get_audit_event(db, event_id=event_id, account=account)
        records = event.records
        title = f"EVENTO DE AUDITORÍA {event_id}"
    else:
        records = list_audits(db, account=account, filters=filters or AuditQueryFilters())
        title = "AUDITORÍA DEL SISTEMA"

    rows = []
    for record in records:
        rows.append(
            f"""
            <tr>
              <td>{html.escape(record.fecha.strftime("%d/%m/%Y %H:%M:%S"))}</td>
              <td>{html.escape(record.usuario.full_name if record.usuario else "SISTEMA")}</td>
              <td>{html.escape(record.modulo)}</td>
              <td>{html.escape(record.submodulo or "-")}</td>
              <td>{html.escape(record.tabla)}</td>
              <td>{html.escape(record.id_registro)}</td>
              <td>{html.escape(record.accion.value.upper())}</td>
              <td>{html.escape(record.campo or "-")}</td>
              <td>{html.escape(record.valor_anterior or "-")}</td>
              <td>{html.escape(record.valor_nuevo or "-")}</td>
              <td>{html.escape(record.ip or "-")}</td>
              <td>{html.escape(str(record.id_evento or "-"))}</td>
            </tr>
            """
        )

    return f"""
    <!doctype html>
    <html lang="es">
      <head>
        <meta charset="utf-8" />
        <title>{html.escape(title)}</title>
        <style>
          body {{
            font-family: "Georgia", "Times New Roman", serif;
            margin: 24px;
            color: #36231d;
            background: #fffdf8;
          }}
          .sheet {{
            border: 1px solid #d8c9ba;
            border-radius: 18px;
            padding: 24px;
          }}
          h1 {{
            margin: 0 0 4px;
            font-size: 24px;
            letter-spacing: 0.08em;
          }}
          .meta {{
            color: #7b5c4c;
            margin-bottom: 18px;
            font-size: 13px;
          }}
          table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
          }}
          th, td {{
            border: 1px solid #e3d7ca;
            padding: 8px;
            vertical-align: top;
          }}
          th {{
            background: #f6ede4;
            text-align: left;
          }}
          @media print {{
            body {{ margin: 0; background: white; }}
            .sheet {{ border: none; border-radius: 0; padding: 0; }}
          }}
        </style>
      </head>
      <body>
        <div class="sheet">
          <h1>BELLAARTE BOUTIQUE</h1>
          <div class="meta">
            {html.escape(title)}<br />
            GENERADO: {html.escape(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))}
          </div>
          <table>
            <thead>
              <tr>
                <th>FECHA</th>
                <th>USUARIO</th>
                <th>MÓDULO</th>
                <th>SUBMÓDULO</th>
                <th>TABLA</th>
                <th>ID REGISTRO</th>
                <th>ACCIÓN</th>
                <th>CAMPO</th>
                <th>VALOR ANTERIOR</th>
                <th>VALOR NUEVO</th>
                <th>IP</th>
                <th>ID EVENTO</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows) or '<tr><td colspan="12">SIN REGISTROS</td></tr>'}
            </tbody>
          </table>
        </div>
        <script>window.onload = () => window.print();</script>
      </body>
    </html>
    """
