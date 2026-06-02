from datetime import date, datetime, timezone
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.audit import register_audit_event
from app.core.security import hash_password
from app.models.account import Cuenta
from app.models.boutique_enums import (
    EstadoFleteEnum,
    EstadoPedidoGeneralEnum,
    EstadoSalidaFleteEnum,
    PrioridadNotificacionEnum,
)
from app.models.boutique_item import ItemBoutique
from app.models.flete import FleteVestido, SalidaFlete
from app.models.notification import Notificacion
from app.models.order import Pedido, PruebaPedido
from app.models.role import Rol
from app.models.user import Usuario
from app.models.workshop import InventarioTaller
from app.schemas.notification import (
    NotificationDetailResponse,
    NotificationListItem,
    NotificationQueryFilters,
    NotificationRecipientSummary,
    NotificationReportBucket,
    NotificationReportSummary,
    NotificationSummaryResponse,
)
from app.services.email_service import send_welcome_email


ADMIN_ROLE_CODE = "ADMIN"
NOTIFICATION_TYPES = frozenset(
    {
        "STOCK_BAJO_BOUTIQUE",
        "STOCK_BAJO_TALLER",
        "ENTREGA_PEDIDO_2_DIAS",
        "ENTREGA_PEDIDO_1_DIA",
        "ENTREGA_PEDIDO_HOY",
        "PRUEBA_PEDIDO_2_DIAS",
        "PRUEBA_PEDIDO_1_DIA",
        "PRUEBA_PEDIDO_HOY",
        "PRUEBA_1_ALISTAR_MATERIAL",
        "PRUEBA_2_ALISTAR_MATERIAL",
        "DEVOLUCION_FLETE_2_DIAS",
        "DEVOLUCION_FLETE_1_DIA",
        "DEVOLUCION_FLETE_HOY",
        "DEVOLUCION_FLETE_VENCIDA",
        "FLETE_MAX_SALIDAS",
        "ERROR_ENVIO_CORREO",
        "SISTEMA",
    }
)
DELIVERY_NOTIFICATION_TYPES = frozenset({"ENTREGA_PEDIDO_2_DIAS", "ENTREGA_PEDIDO_1_DIA", "ENTREGA_PEDIDO_HOY"})
TEST_NOTIFICATION_TYPES = frozenset({"PRUEBA_PEDIDO_2_DIAS", "PRUEBA_PEDIDO_1_DIA", "PRUEBA_PEDIDO_HOY"})
FLETE_RETURN_NOTIFICATION_TYPES = frozenset(
    {"DEVOLUCION_FLETE_2_DIAS", "DEVOLUCION_FLETE_1_DIA", "DEVOLUCION_FLETE_HOY", "DEVOLUCION_FLETE_VENCIDA"}
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _is_admin(account: Cuenta) -> bool:
    return account.rol.codigo == ADMIN_ROLE_CODE


def _normalize_upper(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None


def _notification_query():
    return select(Notificacion).options(
        joinedload(Notificacion.usuario).joinedload(Usuario.cuenta).joinedload(Cuenta.rol)
    )


def _ensure_notification_access(notification: Notificacion, account: Cuenta) -> None:
    if _is_admin(account):
        return
    if notification.usuario_id != account.usuario_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a esa notificación.")


def _to_recipient_summary(user: Usuario) -> NotificationRecipientSummary:
    return NotificationRecipientSummary(
        user_id=user.id,
        full_name=user.nombre_completo,
        role_code=user.cuenta.rol.codigo if user.cuenta and user.cuenta.rol else None,
        role_name=user.cuenta.rol.nombre if user.cuenta and user.cuenta.rol else None,
        username=user.cuenta.username if user.cuenta else None,
    )


def build_notification_action_path(table_ref: str | None, record_id_ref: int | None) -> str | None:
    if not table_ref:
        return None
    normalized = table_ref.lower()
    if normalized == "item_boutique":
        return f"/app/boutique/inventario?item_id={record_id_ref}" if record_id_ref else "/app/boutique/inventario"
    if normalized == "inventario_taller":
        return f"/app/taller/inventario?item_id={record_id_ref}" if record_id_ref else "/app/taller/inventario"
    if normalized == "pedido":
        return f"/app/pedidos?order_id={record_id_ref}" if record_id_ref else "/app/pedidos"
    if normalized == "prueba_pedido":
        return f"/app/pedidos/pruebas?test_id={record_id_ref}" if record_id_ref else "/app/pedidos/pruebas"
    if normalized == "salida_flete":
        return f"/app/fletes/salidas?output_id={record_id_ref}" if record_id_ref else "/app/fletes/salidas"
    if normalized == "flete_vestido":
        return f"/app/fletes?flete_id={record_id_ref}" if record_id_ref else "/app/fletes"
    if normalized == "usuarios":
        return f"/app/seguridad/usuarios?user_id={record_id_ref}" if record_id_ref else "/app/seguridad/usuarios"
    return None


def _to_list_item(notification: Notificacion) -> NotificationListItem:
    return NotificationListItem(
        id=notification.id,
        tipo=notification.tipo,
        prioridad=notification.prioridad,
        titulo=notification.titulo,
        mensaje=notification.mensaje,
        modulo=notification.modulo,
        leida=notification.leida,
        resuelta=notification.resuelta,
        fecha=notification.fecha,
        fecha_leida=notification.fecha_leida,
        fecha_resuelta=notification.fecha_resuelta,
        tabla_referencia=notification.tabla_referencia,
        id_referencia=notification.id_referencia,
        recipient=_to_recipient_summary(notification.usuario),
    )


def _to_detail_response(notification: Notificacion) -> NotificationDetailResponse:
    return NotificationDetailResponse(
        **_to_list_item(notification).model_dump(),
        action_path=build_notification_action_path(notification.tabla_referencia, notification.id_referencia),
    )


def _base_notification_search(stmt, search: str | None):
    if not search:
        return stmt
    term = f"%{search.strip().upper()}%"
    return stmt.where(
        or_(
            func.upper(Notificacion.titulo).like(term),
            func.upper(Notificacion.mensaje).like(term),
            func.upper(Notificacion.tipo).like(term),
            func.upper(func.coalesce(Notificacion.modulo, "")).like(term),
            func.upper(Usuario.nombres).like(term),
            func.upper(Usuario.apellido_paterno).like(term),
        )
    )


def list_notifications(
    db: Session,
    *,
    account: Cuenta,
    search: str | None = None,
    filters: NotificationQueryFilters,
) -> list[NotificationListItem]:
    stmt = _notification_query().join(Notificacion.usuario).join(Usuario.cuenta).join(Cuenta.rol).order_by(Notificacion.fecha.desc(), Notificacion.id.desc())
    if not _is_admin(account):
        stmt = stmt.where(Notificacion.usuario_id == account.usuario_id)
    elif filters.user_id is not None:
        stmt = stmt.where(Notificacion.usuario_id == filters.user_id)
    if _is_admin(account) and filters.role_code:
        stmt = stmt.where(func.upper(Rol.codigo) == filters.role_code)
    if filters.module:
        stmt = stmt.where(func.upper(func.coalesce(Notificacion.modulo, "")) == filters.module)
    if filters.type:
        stmt = stmt.where(func.upper(Notificacion.tipo) == filters.type)
    if filters.priority is not None:
        stmt = stmt.where(Notificacion.prioridad == filters.priority)
    if filters.is_read is not None:
        stmt = stmt.where(Notificacion.leida.is_(filters.is_read))
    if filters.is_resolved is not None:
        stmt = stmt.where(Notificacion.resuelta.is_(filters.is_resolved))
    if filters.date_from is not None:
        stmt = stmt.where(func.date(Notificacion.fecha) >= filters.date_from)
    if filters.date_to is not None:
        stmt = stmt.where(func.date(Notificacion.fecha) <= filters.date_to)
    if filters.table_ref:
        stmt = stmt.where(func.upper(func.coalesce(Notificacion.tabla_referencia, "")) == filters.table_ref)
    if filters.record_id_ref is not None:
        stmt = stmt.where(Notificacion.id_referencia == filters.record_id_ref)
    stmt = _base_notification_search(stmt, search)
    return [_to_list_item(item) for item in db.execute(stmt).unique().scalars().all()]


def get_notification_detail(db: Session, *, notification_id: int, account: Cuenta) -> NotificationDetailResponse:
    entity = db.execute(_notification_query().where(Notificacion.id == notification_id)).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada.")
    _ensure_notification_access(entity, account)
    return _to_detail_response(entity)


def get_notification_summary(db: Session, *, account: Cuenta, limit: int = 8) -> NotificationSummaryResponse:
    unread_stmt = select(func.count()).select_from(Notificacion)
    unresolved_stmt = select(func.count()).select_from(Notificacion)
    urgent_stmt = select(func.count()).select_from(Notificacion).where(
        Notificacion.resuelta.is_(False), Notificacion.prioridad == PrioridadNotificacionEnum.URGENTE
    )
    priority_stmt = select(Notificacion.prioridad, func.count()).group_by(Notificacion.prioridad)
    latest_stmt = _notification_query()
    if not _is_admin(account):
        unread_stmt = unread_stmt.where(Notificacion.usuario_id == account.usuario_id, Notificacion.leida.is_(False))
        unresolved_stmt = unresolved_stmt.where(Notificacion.usuario_id == account.usuario_id, Notificacion.resuelta.is_(False))
        urgent_stmt = urgent_stmt.where(Notificacion.usuario_id == account.usuario_id)
        priority_stmt = priority_stmt.where(Notificacion.usuario_id == account.usuario_id)
        latest_stmt = latest_stmt.where(Notificacion.usuario_id == account.usuario_id)
    else:
        unread_stmt = unread_stmt.where(Notificacion.leida.is_(False))
        unresolved_stmt = unresolved_stmt.where(Notificacion.resuelta.is_(False))

    unread_count = db.execute(unread_stmt).scalar_one()
    unresolved_count = db.execute(unresolved_stmt).scalar_one()
    urgent_count = db.execute(urgent_stmt).scalar_one()
    priority_counts = {row[0].value.upper(): row[1] for row in db.execute(priority_stmt).all()}
    latest_stmt = latest_stmt.order_by(Notificacion.fecha.desc(), Notificacion.id.desc()).limit(limit)
    latest = [_to_list_item(item) for item in db.execute(latest_stmt).unique().scalars().all()]
    return NotificationSummaryResponse(
        unread_count=int(unread_count or 0),
        unresolved_count=int(unresolved_count or 0),
        urgent_count=int(urgent_count or 0),
        priority_counts=priority_counts,
        latest=latest,
    )


def mark_notification_read(db: Session, *, notification_id: int, account: Cuenta) -> NotificationDetailResponse:
    entity = db.execute(_notification_query().where(Notificacion.id == notification_id)).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada.")
    _ensure_notification_access(entity, account)
    if not entity.leida:
        entity.leida = True
        entity.fecha_leida = utc_now()
        db.commit()
        db.refresh(entity)
    return _to_detail_response(entity)


def mark_all_notifications_read(db: Session, *, account: Cuenta) -> dict[str, int]:
    stmt = select(Notificacion).where(Notificacion.leida.is_(False))
    if not _is_admin(account):
        stmt = stmt.where(Notificacion.usuario_id == account.usuario_id)
    notifications = db.execute(stmt).scalars().all()
    now = utc_now()
    for entity in notifications:
        entity.leida = True
        entity.fecha_leida = now
    db.commit()
    return {"updated": len(notifications)}


def resolve_notification(
    db: Session,
    *,
    notification_id: int,
    reason: str,
    resolved_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> NotificationDetailResponse:
    entity = db.execute(_notification_query().where(Notificacion.id == notification_id)).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada.")
    if not entity.resuelta:
        entity.resuelta = True
        entity.fecha_resuelta = utc_now()
        if not entity.leida:
            entity.leida = True
            entity.fecha_leida = entity.fecha_resuelta
        register_audit_event(
            db,
            action="NOTIFICATION_RESOLVED",
            description=f"Se resolvió manualmente la notificación '{entity.tipo}' para '{entity.usuario.nombre_completo}'. Motivo: {reason}.",
            account=resolved_by,
            user=resolved_by.usuario,
            reference=str(entity.id),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.commit()
        db.refresh(entity)
    return _to_detail_response(entity)


def get_notification_report_summary(db: Session) -> NotificationReportSummary:
    total = db.execute(select(func.count()).select_from(Notificacion)).scalar_one()
    unread = db.execute(select(func.count()).select_from(Notificacion).where(Notificacion.leida.is_(False))).scalar_one()
    unresolved = db.execute(select(func.count()).select_from(Notificacion).where(Notificacion.resuelta.is_(False))).scalar_one()
    urgent_unresolved = db.execute(
        select(func.count()).select_from(Notificacion).where(
            Notificacion.resuelta.is_(False), Notificacion.prioridad == PrioridadNotificacionEnum.URGENTE
        )
    ).scalar_one()

    def collect(stmt, label_transform=lambda value: value):
        return [NotificationReportBucket(label=label_transform(row[0] or "SIN_DATO"), count=row[1]) for row in db.execute(stmt).all()]

    by_module = collect(select(Notificacion.modulo, func.count()).group_by(Notificacion.modulo).order_by(func.count().desc()))
    by_priority = collect(
        select(Notificacion.prioridad, func.count()).group_by(Notificacion.prioridad).order_by(func.count().desc()),
        label_transform=lambda value: value.value.upper() if hasattr(value, "value") else str(value).upper(),
    )
    by_role = collect(
        select(Rol.codigo, func.count())
        .select_from(Notificacion)
        .join(Notificacion.usuario)
        .join(Usuario.cuenta)
        .join(Cuenta.rol)
        .group_by(Rol.codigo)
        .order_by(func.count().desc())
    )
    by_type = collect(select(Notificacion.tipo, func.count()).group_by(Notificacion.tipo).order_by(func.count().desc()))

    return NotificationReportSummary(
        total=int(total or 0),
        unread=int(unread or 0),
        unresolved=int(unresolved or 0),
        urgent_unresolved=int(urgent_unresolved or 0),
        by_module=by_module,
        by_priority=by_priority,
        by_role=by_role,
        by_type=by_type,
    )


def _get_active_accounts_for_roles(db: Session, role_codes: Iterable[str]) -> list[Cuenta]:
    normalized_codes = [code.strip().upper() for code in role_codes]
    stmt = (
        select(Cuenta)
        .options(joinedload(Cuenta.usuario), joinedload(Cuenta.rol))
        .join(Cuenta.usuario)
        .join(Cuenta.rol)
        .where(
            Cuenta.is_active.is_(True),
            Usuario.activo.is_(True),
            Rol.activo.is_(True),
            func.upper(Rol.codigo).in_(normalized_codes),
        )
    )
    return list(db.execute(stmt).unique().scalars().all())


def create_notification_for_user(
    db: Session,
    *,
    user: Usuario,
    tipo: str,
    prioridad: PrioridadNotificacionEnum,
    titulo: str,
    mensaje: str,
    modulo: str | None,
    tabla_referencia: str | None,
    id_referencia: int | None,
    force_recreate: bool = False,
) -> Notificacion:
    normalized_type = _normalize_upper(tipo)
    if normalized_type not in NOTIFICATION_TYPES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El tipo de notificación no está soportado.")
    if user.cuenta is None or not user.cuenta.is_active or not user.activo:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La notificación no tiene un destinatario operativo válido.")

    normalized_table = _normalize_upper(tabla_referencia or "")
    existing = db.execute(
        select(Notificacion).where(
            Notificacion.usuario_id == user.id,
            func.upper(Notificacion.tipo) == normalized_type,
            func.upper(func.coalesce(Notificacion.tabla_referencia, "")) == normalized_table,
            Notificacion.id_referencia == id_referencia,
            Notificacion.resuelta.is_(False),
        )
    ).scalar_one_or_none()
    if existing is not None and not force_recreate:
        return existing
    if existing is not None and force_recreate:
        existing.resuelta = True
        existing.fecha_resuelta = utc_now()

    notification = Notificacion(
        usuario_id=user.id,
        tipo=normalized_type,
        prioridad=prioridad,
        titulo=titulo,
        mensaje=mensaje,
        modulo=modulo,
        leida=False,
        fecha=utc_now(),
        tabla_referencia=tabla_referencia,
        id_referencia=id_referencia,
        resuelta=False,
    )
    db.add(notification)
    db.flush()
    return notification


def create_notifications_for_roles(
    db: Session,
    *,
    role_codes: Iterable[str],
    tipo: str,
    prioridad: PrioridadNotificacionEnum,
    titulo: str,
    mensaje: str,
    modulo: str | None,
    tabla_referencia: str | None,
    id_referencia: int | None,
    force_recreate: bool = False,
) -> list[Notificacion]:
    notifications: list[Notificacion] = []
    seen_user_ids: set[int] = set()
    for account in _get_active_accounts_for_roles(db, role_codes):
        if account.usuario_id in seen_user_ids:
            continue
        seen_user_ids.add(account.usuario_id)
        notifications.append(
            create_notification_for_user(
                db,
                user=account.usuario,
                tipo=tipo,
                prioridad=prioridad,
                titulo=titulo,
                mensaje=mensaje,
                modulo=modulo,
                tabla_referencia=tabla_referencia,
                id_referencia=id_referencia,
                force_recreate=force_recreate,
            )
        )
    return notifications


def resolve_notifications_by_reference(
    db: Session,
    *,
    notification_types: Iterable[str],
    tabla_referencia: str,
    id_referencia: int,
) -> int:
    normalized_types = [_normalize_upper(notification_type) for notification_type in notification_types]
    notifications = db.execute(
        select(Notificacion).where(
            func.upper(Notificacion.tipo).in_(normalized_types),
            func.upper(func.coalesce(Notificacion.tabla_referencia, "")) == _normalize_upper(tabla_referencia),
            Notificacion.id_referencia == id_referencia,
            Notificacion.resuelta.is_(False),
        )
    ).scalars().all()
    now = utc_now()
    for entity in notifications:
        entity.resuelta = True
        entity.fecha_resuelta = now
    return len(notifications)


def _sync_role_notifications_for_reference(
    db: Session,
    *,
    role_codes: Iterable[str],
    active_type: str,
    candidate_types: Iterable[str],
    prioridad: PrioridadNotificacionEnum,
    titulo: str,
    mensaje: str,
    modulo: str | None,
    tabla_referencia: str,
    id_referencia: int,
) -> None:
    accounts = _get_active_accounts_for_roles(db, role_codes)
    expected_accounts = {account.usuario_id: account for account in accounts}
    existing = db.execute(
        select(Notificacion).where(
            func.upper(Notificacion.tipo).in_([_normalize_upper(value) for value in candidate_types]),
            func.upper(func.coalesce(Notificacion.tabla_referencia, "")) == _normalize_upper(tabla_referencia),
            Notificacion.id_referencia == id_referencia,
            Notificacion.resuelta.is_(False),
        )
    ).scalars().all()
    now = utc_now()
    for entity in existing:
        if entity.tipo != _normalize_upper(active_type) or entity.usuario_id not in expected_accounts:
            entity.resuelta = True
            entity.fecha_resuelta = now
            continue
        expected_accounts.pop(entity.usuario_id, None)
    for account in expected_accounts.values():
        create_notification_for_user(
            db,
            user=account.usuario,
            tipo=active_type,
            prioridad=prioridad,
            titulo=titulo,
            mensaje=mensaje,
            modulo=modulo,
            tabla_referencia=tabla_referencia,
            id_referencia=id_referencia,
        )


def sync_boutique_stock_notification(db: Session, *, item_id: int) -> None:
    item = db.execute(select(ItemBoutique).where(ItemBoutique.id == item_id)).scalar_one_or_none()
    if item is None:
        return
    if not item.estado or item.stock > item.stock_minimo:
        resolve_notifications_by_reference(db, notification_types=("STOCK_BAJO_BOUTIQUE",), tabla_referencia="item_boutique", id_referencia=item_id)
        return
    priority = PrioridadNotificacionEnum.URGENTE if item.stock == 0 else PrioridadNotificacionEnum.ALTA
    create_notifications_for_roles(
        db,
        role_codes=(ADMIN_ROLE_CODE, "INV_BOUTIQUE"),
        tipo="STOCK_BAJO_BOUTIQUE",
        prioridad=priority,
        titulo="STOCK BAJO EN BOUTIQUE",
        mensaje=f'EL PRODUCTO "{item.nombre}" TIENE STOCK ACTUAL DE {item.stock} UNIDADES Y SU STOCK MÍNIMO ES {item.stock_minimo}. SE RECOMIENDA REVISAR REPOSICIÓN.',
        modulo="BOUTIQUE",
        tabla_referencia="item_boutique",
        id_referencia=item.id,
    )


def sync_workshop_stock_notification(db: Session, *, item_id: int) -> None:
    item = db.execute(select(InventarioTaller).where(InventarioTaller.id == item_id)).scalar_one_or_none()
    if item is None:
        return
    if not item.estado or float(item.stock) > float(item.stock_minimo):
        resolve_notifications_by_reference(db, notification_types=("STOCK_BAJO_TALLER",), tabla_referencia="inventario_taller", id_referencia=item_id)
        return
    priority = PrioridadNotificacionEnum.URGENTE if float(item.stock) == 0 else PrioridadNotificacionEnum.ALTA
    create_notifications_for_roles(
        db,
        role_codes=(ADMIN_ROLE_CODE, "INV_TALLER"),
        tipo="STOCK_BAJO_TALLER",
        prioridad=priority,
        titulo="STOCK BAJO EN TALLER",
        mensaje=f'EL MATERIAL "{item.nombre}" TIENE STOCK ACTUAL DE {float(item.stock):.2f} {item.unidad_medida.value.upper()} Y SU STOCK MÍNIMO ES {float(item.stock_minimo):.2f}. SE RECOMIENDA REVISAR REPOSICIÓN.',
        modulo="TALLER",
        tabla_referencia="inventario_taller",
        id_referencia=item.id,
    )


def sync_order_delivery_notifications_for_order(db: Session, *, order_id: int, today: date | None = None) -> None:
    order = db.execute(select(Pedido).options(joinedload(Pedido.cliente)).where(Pedido.id == order_id)).scalar_one_or_none()
    if order is None:
        return
    if order.estado_general != EstadoPedidoGeneralEnum.ACTIVO or not order.habilitado:
        resolve_notifications_by_reference(db, notification_types=DELIVERY_NOTIFICATION_TYPES, tabla_referencia="pedido", id_referencia=order.id)
        return
    base_date = today or date.today()
    days_left = (order.fecha_entrega - base_date).days
    if days_left not in {0, 1, 2}:
        resolve_notifications_by_reference(db, notification_types=DELIVERY_NOTIFICATION_TYPES, tabla_referencia="pedido", id_referencia=order.id)
        return
    type_map = {
        2: ("ENTREGA_PEDIDO_2_DIAS", PrioridadNotificacionEnum.MEDIA, "ENTREGA DE PEDIDO DENTRO DE 2 DÍAS"),
        1: ("ENTREGA_PEDIDO_1_DIA", PrioridadNotificacionEnum.ALTA, "ENTREGA DE PEDIDO PARA MAÑANA"),
        0: ("ENTREGA_PEDIDO_HOY", PrioridadNotificacionEnum.URGENTE, "ENTREGA DE PEDIDO PARA HOY"),
    }
    notification_type, priority, title = type_map[days_left]
    role_codes = [ADMIN_ROLE_CODE, "MODISTA", "INV_BOUTIQUE"]
    if float(order.saldo) > 0:
        role_codes.append("CAJA")
    _sync_role_notifications_for_reference(
        db,
        role_codes=role_codes,
        active_type=notification_type,
        candidate_types=DELIVERY_NOTIFICATION_TYPES,
        prioridad=priority,
        titulo=title,
        mensaje=f'EL PEDIDO {order.codigo} DE LA CLIENTA {order.cliente.nombre_completo} TIENE ENTREGA PROGRAMADA PARA {order.fecha_entrega.strftime("%d/%m/%Y")}.',
        modulo="PEDIDOS",
        tabla_referencia="pedido",
        id_referencia=order.id,
    )


def sync_test_schedule_notifications_for_test(db: Session, *, test_id: int, today: date | None = None) -> None:
    test = db.execute(
        select(PruebaPedido).options(joinedload(PruebaPedido.pedido).joinedload(Pedido.cliente)).where(PruebaPedido.id == test_id)
    ).scalar_one_or_none()
    if test is None:
        return
    if test.pedido.estado_general != EstadoPedidoGeneralEnum.ACTIVO or not test.pedido.habilitado:
        resolve_notifications_by_reference(db, notification_types=TEST_NOTIFICATION_TYPES, tabla_referencia="prueba_pedido", id_referencia=test.id)
        return
    base_date = today or date.today()
    days_left = (test.fecha - base_date).days
    if days_left not in {0, 1, 2}:
        resolve_notifications_by_reference(db, notification_types=TEST_NOTIFICATION_TYPES, tabla_referencia="prueba_pedido", id_referencia=test.id)
        return
    type_map = {
        2: ("PRUEBA_PEDIDO_2_DIAS", PrioridadNotificacionEnum.MEDIA, "PRUEBA DE PEDIDO DENTRO DE 2 DÍAS"),
        1: ("PRUEBA_PEDIDO_1_DIA", PrioridadNotificacionEnum.ALTA, "PRUEBA DE PEDIDO PARA MAÑANA"),
        0: ("PRUEBA_PEDIDO_HOY", PrioridadNotificacionEnum.URGENTE, "PRUEBA DE PEDIDO PARA HOY"),
    }
    notification_type, priority, title = type_map[days_left]
    hour_text = test.hora.strftime("%H:%M") if test.hora else "SIN HORA DEFINIDA"
    _sync_role_notifications_for_reference(
        db,
        role_codes=(ADMIN_ROLE_CODE, "MODISTA", "INV_BOUTIQUE"),
        active_type=notification_type,
        candidate_types=TEST_NOTIFICATION_TYPES,
        prioridad=priority,
        titulo=title,
        mensaje=f'LA PRUEBA N°{test.numero} DEL PEDIDO {test.pedido.codigo} DE LA CLIENTA {test.pedido.cliente.nombre_completo} ESTÁ PROGRAMADA PARA EL {test.fecha.strftime("%d/%m/%Y")} A HORAS {hour_text}.',
        modulo="PRUEBAS",
        tabla_referencia="prueba_pedido",
        id_referencia=test.id,
    )


def sync_material_preparation_notification_for_test(db: Session, *, test_id: int) -> None:
    test = db.execute(
        select(PruebaPedido).options(joinedload(PruebaPedido.pedido).joinedload(Pedido.cliente)).where(PruebaPedido.id == test_id)
    ).scalar_one_or_none()
    if test is None or test.numero not in {1, 2}:
        return
    if test.pedido.estado_general != EstadoPedidoGeneralEnum.ACTIVO or not test.pedido.habilitado:
        return
    notification_type = "PRUEBA_1_ALISTAR_MATERIAL" if test.numero == 1 else "PRUEBA_2_ALISTAR_MATERIAL"
    resolve_notifications_by_reference(db, notification_types=(notification_type,), tabla_referencia="prueba_pedido", id_referencia=test.id)
    create_notifications_for_roles(
        db,
        role_codes=(ADMIN_ROLE_CODE, "MODISTA", "CAJA"),
        tipo=notification_type,
        prioridad=PrioridadNotificacionEnum.ALTA,
        titulo=f"ALISTAR MATERIAL PARA PRUEBA {test.numero}",
        mensaje=f'SE REGISTRÓ O REPROGRAMÓ LA PRUEBA N°{test.numero} DEL PEDIDO {test.pedido.codigo} DE LA CLIENTA {test.pedido.cliente.nombre_completo}. ALISTE EL MATERIAL CORRESPONDIENTE.',
        modulo="PRUEBAS",
        tabla_referencia="prueba_pedido",
        id_referencia=test.id,
        force_recreate=True,
    )


def sync_flete_return_notifications_for_output(db: Session, *, output_id: int, today: date | None = None) -> None:
    salida = db.execute(
        select(SalidaFlete)
        .options(joinedload(SalidaFlete.cliente), joinedload(SalidaFlete.flete).joinedload(FleteVestido.item))
        .where(SalidaFlete.id == output_id)
    ).scalar_one_or_none()
    if salida is None:
        return
    if salida.estado_salida not in {EstadoSalidaFleteEnum.RESERVADO, EstadoSalidaFleteEnum.EN_FLETE} or not salida.habilitado:
        resolve_notifications_by_reference(db, notification_types=FLETE_RETURN_NOTIFICATION_TYPES, tabla_referencia="salida_flete", id_referencia=salida.id)
        return
    base_date = today or date.today()
    days_left = (salida.fecha_devolucion_prevista - base_date).days
    if days_left not in {0, 1, 2} and days_left >= 0:
        resolve_notifications_by_reference(db, notification_types=FLETE_RETURN_NOTIFICATION_TYPES, tabla_referencia="salida_flete", id_referencia=salida.id)
        return
    if days_left == 2:
        notification_type, priority, title = "DEVOLUCION_FLETE_2_DIAS", PrioridadNotificacionEnum.MEDIA, "DEVOLUCIÓN DE FLETE DENTRO DE 2 DÍAS"
    elif days_left == 1:
        notification_type, priority, title = "DEVOLUCION_FLETE_1_DIA", PrioridadNotificacionEnum.ALTA, "DEVOLUCIÓN DE FLETE PARA MAÑANA"
    elif days_left == 0:
        notification_type, priority, title = "DEVOLUCION_FLETE_HOY", PrioridadNotificacionEnum.URGENTE, "DEVOLUCIÓN DE FLETE PARA HOY"
    else:
        notification_type, priority, title = "DEVOLUCION_FLETE_VENCIDA", PrioridadNotificacionEnum.URGENTE, "DEVOLUCIÓN DE FLETE VENCIDA"
    role_codes = [ADMIN_ROLE_CODE, "INV_BOUTIQUE"]
    if float(salida.garantia) > float(salida.garantia_devuelta) or float(salida.monto_arreglo) > 0:
        role_codes.append("CAJA")
    _sync_role_notifications_for_reference(
        db,
        role_codes=role_codes,
        active_type=notification_type,
        candidate_types=FLETE_RETURN_NOTIFICATION_TYPES,
        prioridad=priority,
        titulo=title,
        mensaje=f'LA SALIDA DE FLETE DE LA CLIENTA {salida.cliente.nombre_completo} TIENE DEVOLUCIÓN PREVISTA PARA {salida.fecha_devolucion_prevista.strftime("%d/%m/%Y")}.',
        modulo="FLETES",
        tabla_referencia="salida_flete",
        id_referencia=salida.id,
    )


def sync_flete_max_outputs_notification(db: Session, *, flete_id: int) -> None:
    flete = db.execute(select(FleteVestido).options(joinedload(FleteVestido.item)).where(FleteVestido.id == flete_id)).scalar_one_or_none()
    if flete is None:
        return
    if flete.estado in {EstadoFleteEnum.PASADO_PARA_VENTA, EstadoFleteEnum.RETIRADO} or flete.salidas_actuales < flete.max_salidas:
        resolve_notifications_by_reference(db, notification_types=("FLETE_MAX_SALIDAS",), tabla_referencia="flete_vestido", id_referencia=flete.id)
        return
    create_notifications_for_roles(
        db,
        role_codes=(ADMIN_ROLE_CODE, "INV_BOUTIQUE"),
        tipo="FLETE_MAX_SALIDAS",
        prioridad=PrioridadNotificacionEnum.ALTA,
        titulo="FLETE CON MÁXIMO DE SALIDAS ALCANZADO",
        mensaje=f'EL VESTIDO "{flete.item.nombre}" ALCANZÓ {flete.salidas_actuales} SALIDAS VÁLIDAS DE UN MÁXIMO DE {flete.max_salidas}. REVISE SI PASA A VENTA, SE RETIRA O CONTINÚA EN REVISIÓN.',
        modulo="FLETES",
        tabla_referencia="flete_vestido",
        id_referencia=flete.id,
    )


def create_email_failure_notification(db: Session, *, user_id: int, recipient_email: str, error_message: str) -> None:
    create_notifications_for_roles(
        db,
        role_codes=(ADMIN_ROLE_CODE,),
        tipo="ERROR_ENVIO_CORREO",
        prioridad=PrioridadNotificacionEnum.URGENTE,
        titulo="ERROR AL ENVIAR CREDENCIALES",
        mensaje=f'NO SE PUDO ENVIAR EL CORREO DE CREDENCIALES AL DESTINATARIO {recipient_email.upper()} PARA EL USUARIO #{user_id}. DETALLE TÉCNICO: {error_message.upper()[:220]}.',
        modulo="SEGURIDAD",
        tabla_referencia="usuarios",
        id_referencia=user_id,
    )


def resolve_email_failure_notifications(db: Session, *, user_id: int) -> None:
    resolve_notifications_by_reference(db, notification_types=("ERROR_ENVIO_CORREO",), tabla_referencia="usuarios", id_referencia=user_id)


def send_welcome_email_with_tracking(
    *,
    user_id: int,
    recipient_email: str,
    full_name: str,
    username: str,
    initial_password: str,
) -> None:
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        success, error_message = send_welcome_email(
            recipient_email=recipient_email,
            full_name=full_name,
            username=username,
            initial_password=initial_password,
        )
        if success:
            resolve_email_failure_notifications(db, user_id=user_id)
        else:
            create_email_failure_notification(
                db,
                user_id=user_id,
                recipient_email=recipient_email,
                error_message=error_message or "ERROR DESCONOCIDO",
            )
        db.commit()
    finally:
        db.close()


def retry_email_notification(
    db: Session,
    *,
    notification_id: int,
    retried_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> NotificationDetailResponse:
    notification = db.execute(_notification_query().where(Notificacion.id == notification_id)).scalar_one_or_none()
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada.")
    if notification.tipo != "ERROR_ENVIO_CORREO":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo puedes reintentar notificaciones de error de correo.")
    if notification.tabla_referencia != "USUARIOS" or notification.id_referencia is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La notificación no tiene una referencia de usuario válida.")
    user = db.execute(
        select(Usuario).options(joinedload(Usuario.cuenta).joinedload(Cuenta.rol)).where(Usuario.id == notification.id_referencia)
    ).scalar_one_or_none()
    if user is None or user.cuenta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El usuario asociado a la notificación ya no existe.")
    if user.cuenta.last_login_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La cuenta ya inició sesión y no admite reenvío de credenciales de bienvenida.")
    initial_password = user.ci.upper()
    success, error_message = send_welcome_email(
        recipient_email=user.correo,
        full_name=user.nombre_completo,
        username=user.cuenta.username,
        initial_password=initial_password,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se pudo reenviar el correo. Detalle técnico: {(error_message or 'ERROR DESCONOCIDO').upper()}",
        )
    user.cuenta.password_hash = hash_password(initial_password)
    user.cuenta.must_change_password = True
    notification.resuelta = True
    notification.fecha_resuelta = utc_now()
    notification.leida = True
    notification.fecha_leida = notification.fecha_resuelta
    register_audit_event(
        db,
        action="NOTIFICATION_EMAIL_RETRIED",
        description=f"Se reintentó el envío de credenciales para la cuenta '{user.cuenta.username}'.",
        account=retried_by,
        user=retried_by.usuario,
        reference=str(notification.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(notification)
    return _to_detail_response(notification)
