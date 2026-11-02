from datetime import date
from typing import Iterable

from fastapi import HTTPException
from sqlalchemy import and_, case, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, joinedload

from app.core.notification_catalog import (
    DELIVERY_NOTIFICATION_TYPES, FLETE_RETURN_NOTIFICATION_TYPES,
    MATERIAL_NOTIFICATION_TYPES, NOTIFICATION_TYPES, STOCK_NOTIFICATION_TYPES,
    TEST_NOTIFICATION_TYPES, business_today, normalize_upper, recipient_roles, utc_now,
)
from app.models.account import Cuenta
from app.models.boutique_enums import EstadoFleteEnum, EstadoPedidoGeneralEnum, EstadoSalidaFleteEnum, PrioridadNotificacionEnum
from app.models.boutique_item import ItemBoutique
from app.models.flete import FleteVestido, SalidaFlete
from app.models.notification import Notificacion
from app.models.order import Pedido, PruebaPedido
from app.models.role import Rol
from app.models.user import Usuario
from app.models.workshop import InventarioTaller


def count_effect(db: Session, name: str, amount: int = 1) -> None:
    counters = db.info.get("notification_counters")
    if counters is not None:
        counters[name] = counters.get(name, 0) + amount


def lock_source(db: Session, model, record_id: int):
    # Services have autoflush=False. Flush their mutations before refreshing the
    # source, and keep this row lock until the business coordinator commits.
    db.flush()
    return db.execute(select(model).where(model.id == record_id).with_for_update()
                      .execution_options(populate_existing=True)).scalar_one_or_none()


def lock_test_source(db: Session, test_id: int):
    db.flush()
    order_id = db.execute(select(PruebaPedido.pedido_id).where(PruebaPedido.id == test_id)).scalar_one_or_none()
    if order_id is None:
        return None
    lock_source(db, Pedido, order_id)
    return lock_source(db, PruebaPedido, test_id)


def _get_active_accounts_for_roles(db: Session, role_codes: Iterable[str]) -> list[Cuenta]:
    return list(db.execute(select(Cuenta).options(joinedload(Cuenta.usuario), joinedload(Cuenta.rol)).join(Cuenta.usuario).join(Cuenta.rol).where(
        Cuenta.is_active.is_(True), Usuario.activo.is_(True), Rol.activo.is_(True),
        Rol.codigo.in_([normalize_upper(code) for code in role_codes]),
    ).order_by(Cuenta.usuario_id).with_for_update(of=Cuenta)
      .execution_options(populate_existing=True)).scalars().all())


def create_notification_for_user(db: Session, *, user: Usuario, tipo: str,
    prioridad: PrioridadNotificacionEnum, titulo: str, mensaje: str, modulo: str | None,
    tabla_referencia: str | None, id_referencia: int | None, force_recreate: bool = False,
    stock_zero: bool = False) -> Notificacion:
    notification_type, table_ref = normalize_upper(tipo), normalize_upper(tabla_referencia)
    if notification_type not in NOTIFICATION_TYPES:
        raise HTTPException(status_code=409, detail="El tipo de notificación no está soportado.")
    if not user.activo or user.cuenta is None or not user.cuenta.is_active or not user.cuenta.rol.activo:
        raise HTTPException(status_code=409, detail="La notificación no tiene un destinatario operativo válido.")
    if force_recreate:
        if notification_type not in MATERIAL_NOTIFICATION_TYPES:
            raise ValueError("Solo las tareas de preparación pueden generar una nueva programación.")
        resolve_notifications_by_reference(db, notification_types=(notification_type,), tabla_referencia=table_ref,
                                           id_referencia=id_referencia, reason="REPROGRAMADA", user_id=user.id)
    now = utc_now()
    values = dict(usuario_id=user.id, tipo=notification_type, prioridad=prioridad,
                  titulo=normalize_upper(titulo), mensaje=normalize_upper(mensaje), modulo=normalize_upper(modulo),
                  tabla_referencia=table_ref, id_referencia=id_referencia, leida=False, resuelta=False,
                  fecha=now, revision=1, revision_fecha=now, stock_cero_detectado=stock_zero,
                  escritorio_revision_reclamada=0)
    columns = {key: getattr(Notificacion, key).property.columns[0] for key in values}
    key = (
        Notificacion.usuario_id == user.id, Notificacion.tipo == notification_type,
        Notificacion.tabla_referencia.is_not_distinct_from(table_ref),
        Notificacion.id_referencia.is_not_distinct_from(id_referencia), Notificacion.resuelta.is_(False),
    )
    escalation = and_(notification_type in STOCK_NOTIFICATION_TYPES, stock_zero,
                      Notificacion.stock_cero_detectado.is_(False))
    updates = {getattr(Notificacion, key).property.columns[0]: values[key]
               for key in ("prioridad", "titulo", "mensaje", "modulo")}
    updates.update({
        columns["revision"]: case((escalation, Notificacion.revision + 1), else_=Notificacion.revision),
        columns["revision_fecha"]: case((escalation, now), else_=Notificacion.revision_fecha),
        columns["stock_cero_detectado"]: or_(Notificacion.stock_cero_detectado, stock_zero),
        columns["leida"]: case((escalation, False), else_=Notificacion.leida),
        Notificacion.fecha_leida.property.columns[0]: case((escalation, None), else_=Notificacion.fecha_leida),
    })
    changed = or_(escalation, *[getattr(Notificacion, key).is_distinct_from(values[key])
                              for key in ("prioridad", "titulo", "mensaje", "modulo")])
    # Return exact created/updated/unchanged metrics without relying on PostgreSQL
    # system columns. The unique index arbitrates races; a concurrent close can
    # make the row disappear from the active key, so retry the insert boundedly.
    for _attempt in range(3):
        stmt = insert(Notificacion).values({columns[key]: value for key, value in values.items()})
        stmt = stmt.on_conflict_do_nothing(
            index_elements=[Notificacion.usuario_id, Notificacion.tipo, Notificacion.tabla_referencia, Notificacion.id_referencia],
            index_where=text("not_resuelta = false"),
        ).returning(Notificacion)
        entity = db.execute(stmt, execution_options={"populate_existing": True}).scalar_one_or_none()
        if entity is not None:
            count_effect(db, "created")
            return entity
        entity = db.execute(update(Notificacion).where(*key, changed).values(updates).returning(Notificacion),
                            execution_options={"populate_existing": True, "synchronize_session": False}).scalar_one_or_none()
        if entity is not None:
            count_effect(db, "updated")
            return entity
        entity = db.execute(select(Notificacion).where(*key).execution_options(populate_existing=True)).scalar_one_or_none()
        if entity is not None:
            count_effect(db, "unchanged")
            return entity
    raise RuntimeError("La incidencia cambió concurrentemente; reintente la operación.")


def create_notifications_for_roles(db: Session, *, role_codes: Iterable[str], **kwargs) -> list[Notificacion]:
    return [create_notification_for_user(db, user=account.usuario, **kwargs)
            for account in _get_active_accounts_for_roles(db, role_codes)]


def resolve_notifications_by_reference(db: Session, *, notification_types: Iterable[str],
    tabla_referencia: str | None, id_referencia: int | None, reason: str = "CONDICION_CORREGIDA", user_id: int | None = None) -> int:
    stmt = update(Notificacion).where(
        Notificacion.tipo.in_([normalize_upper(value) for value in notification_types]),
        Notificacion.tabla_referencia.is_not_distinct_from(normalize_upper(tabla_referencia)),
        Notificacion.id_referencia.is_not_distinct_from(id_referencia), Notificacion.resuelta.is_(False),
    )
    if user_id is not None:
        stmt = stmt.where(Notificacion.usuario_id == user_id)
    result = db.execute(stmt.values(resuelta=True, fecha_resuelta=utc_now(), motivo_cierre=reason))
    count_effect(db, "resolved", result.rowcount)
    return result.rowcount


def _sync_role_notifications_for_reference(db: Session, *, role_codes: Iterable[str], active_type: str,
    candidate_types: Iterable[str], prioridad: PrioridadNotificacionEnum, titulo: str, mensaje: str,
    modulo: str | None, tabla_referencia: str, id_referencia: int, stock_zero: bool = False) -> None:
    accounts = _get_active_accounts_for_roles(db, role_codes)
    eligible = [account.usuario_id for account in accounts]
    result = db.execute(update(Notificacion).where(
        Notificacion.tipo.in_(list(candidate_types)), Notificacion.tabla_referencia == normalize_upper(tabla_referencia),
        Notificacion.id_referencia == id_referencia, Notificacion.resuelta.is_(False),
        or_(Notificacion.tipo != active_type, Notificacion.usuario_id.not_in(eligible)),
    ).values(resuelta=True, fecha_resuelta=utc_now(), motivo_cierre="VIGENCIA_O_DESTINATARIO"))
    count_effect(db, "resolved", result.rowcount)
    for account in accounts:
        create_notification_for_user(db, user=account.usuario, tipo=active_type, prioridad=prioridad,
            titulo=titulo, mensaje=mensaje, modulo=modulo, tabla_referencia=tabla_referencia,
            id_referencia=id_referencia, stock_zero=stock_zero)


def reconcile_user_notification_eligibility(db: Session, *, user_ids: Iterable[int]) -> None:
    """Revoke obsolete recipient copies without changing the source incident."""
    db.flush()
    for user_id in sorted(set(user_ids)):
        account = db.execute(select(Cuenta).where(Cuenta.usuario_id == user_id)
                             .with_for_update().execution_options(populate_existing=True)).scalar_one_or_none()
        rows = db.execute(select(Notificacion).where(Notificacion.usuario_id == user_id,
                                                     Notificacion.resuelta.is_(False))).scalars().all()
        active = account and account.is_active and account.usuario.activo and account.rol.activo
        for row in rows:
            cashier_eligible = False
            if row.tipo in DELIVERY_NOTIFICATION_TYPES:
                order = db.get(Pedido, row.id_referencia, populate_existing=True) if row.id_referencia else None
                cashier_eligible = bool(order and order.habilitado and order.estado_general == EstadoPedidoGeneralEnum.ACTIVO and order.saldo > 0)
            elif row.tipo in FLETE_RETURN_NOTIFICATION_TYPES:
                output = db.get(SalidaFlete, row.id_referencia, populate_existing=True) if row.id_referencia else None
                cashier_eligible = bool(output and output.habilitado and output.estado_salida in {EstadoSalidaFleteEnum.RESERVADO, EstadoSalidaFleteEnum.EN_FLETE}
                                        and (output.garantia > output.garantia_devuelta or output.monto_arreglo > 0))
            allowed = recipient_roles(row.tipo, cashier_eligible=cashier_eligible)
            if row.tipo == "SISTEMA" and active:
                allowed = {account.rol.codigo}
            if not active or account.rol.codigo not in allowed:
                row.resuelta, row.fecha_resuelta, row.motivo_cierre = True, utc_now(), "DESTINATARIO_NO_ELEGIBLE"
                count_effect(db, "resolved")


def sync_boutique_stock_notification(db: Session, *, item_id: int) -> None:
    item = lock_source(db, ItemBoutique, item_id)
    if item is None:
        return
    if not item.estado or not item.tipo_item.habilitado or item.stock > item.stock_minimo:
        resolve_notifications_by_reference(db, notification_types=("STOCK_BAJO_BOUTIQUE",), tabla_referencia="item_boutique", id_referencia=item_id)
        return
    priority = PrioridadNotificacionEnum.URGENTE if item.stock == 0 else PrioridadNotificacionEnum.ALTA
    _sync_role_notifications_for_reference(
        db,
        role_codes=recipient_roles("STOCK_BAJO_BOUTIQUE"),
        active_type="STOCK_BAJO_BOUTIQUE",
        candidate_types=("STOCK_BAJO_BOUTIQUE",),
        stock_zero=item.stock == 0,
        prioridad=priority,
        titulo="STOCK BAJO EN BOUTIQUE",
        mensaje=f'EL PRODUCTO "{item.nombre}" TIENE STOCK ACTUAL DE {item.stock} UNIDADES Y SU STOCK MÍNIMO ES {item.stock_minimo}. SE RECOMIENDA REVISAR REPOSICIÓN.',
        modulo="BOUTIQUE",
        tabla_referencia="item_boutique",
        id_referencia=item.id,
    )


def sync_workshop_stock_notification(db: Session, *, item_id: int) -> None:
    item = lock_source(db, InventarioTaller, item_id)
    if item is None:
        return
    if not item.estado or not item.tipo.habilitado or item.stock > item.stock_minimo:
        resolve_notifications_by_reference(db, notification_types=("STOCK_BAJO_TALLER",), tabla_referencia="inventario_taller", id_referencia=item_id)
        return
    priority = PrioridadNotificacionEnum.URGENTE if float(item.stock) == 0 else PrioridadNotificacionEnum.ALTA
    _sync_role_notifications_for_reference(
        db,
        role_codes=recipient_roles("STOCK_BAJO_TALLER"),
        active_type="STOCK_BAJO_TALLER",
        candidate_types=("STOCK_BAJO_TALLER",),
        stock_zero=item.stock == 0,
        prioridad=priority,
        titulo="STOCK BAJO EN TALLER",
        mensaje=f'EL MATERIAL "{item.nombre}" TIENE STOCK ACTUAL DE {float(item.stock):.2f} {item.unidad_medida.value.upper()} Y SU STOCK MÍNIMO ES {float(item.stock_minimo):.2f}. SE RECOMIENDA REVISAR REPOSICIÓN.',
        modulo="TALLER",
        tabla_referencia="inventario_taller",
        id_referencia=item.id,
    )


def sync_order_delivery_notifications_for_order(db: Session, *, order_id: int, today: date | None = None) -> None:
    order = lock_source(db, Pedido, order_id)
    if order is None:
        return
    if order.estado_general != EstadoPedidoGeneralEnum.ACTIVO or not order.habilitado:
        resolve_notifications_by_reference(db, notification_types=DELIVERY_NOTIFICATION_TYPES, tabla_referencia="pedido", id_referencia=order.id)
        return
    base_date = today or business_today()
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
    role_codes = recipient_roles(notification_type, cashier_eligible=order.saldo > 0)
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
    test = lock_test_source(db, test_id)
    if test is None:
        return
    if test.pedido.estado_general != EstadoPedidoGeneralEnum.ACTIVO or not test.pedido.habilitado:
        resolve_notifications_by_reference(db, notification_types=TEST_NOTIFICATION_TYPES, tabla_referencia="prueba_pedido", id_referencia=test.id)
        return
    base_date = today or business_today()
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
        role_codes=recipient_roles(notification_type),
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
    test = lock_test_source(db, test_id)
    if test is None or test.numero not in {1, 2}:
        return
    if test.pedido.estado_general != EstadoPedidoGeneralEnum.ACTIVO or not test.pedido.habilitado:
        resolve_notifications_by_reference(db, notification_types=MATERIAL_NOTIFICATION_TYPES,
                                           tabla_referencia="PRUEBA_PEDIDO", id_referencia=test.id)
        return
    notification_type = "PRUEBA_1_ALISTAR_MATERIAL" if test.numero == 1 else "PRUEBA_2_ALISTAR_MATERIAL"
    resolve_notifications_by_reference(db, notification_types=(notification_type,), tabla_referencia="prueba_pedido", id_referencia=test.id, reason="REPROGRAMADA")
    create_notifications_for_roles(
        db,
        role_codes=recipient_roles(notification_type),
        tipo=notification_type,
        prioridad=PrioridadNotificacionEnum.ALTA,
        titulo=f"ALISTAR MATERIAL PARA PRUEBA {test.numero}",
        mensaje=f'SE REGISTRÓ O REPROGRAMÓ LA PRUEBA N°{test.numero} DEL PEDIDO {test.pedido.codigo} DE LA CLIENTA {test.pedido.cliente.nombre_completo}. ALISTE EL MATERIAL CORRESPONDIENTE.',
        modulo="PRUEBAS",
        tabla_referencia="prueba_pedido",
        id_referencia=test.id,
        force_recreate=True,
    )


def reconcile_material_preparation_recipients(db: Session, *, test_id: int) -> None:
    """Deliver an existing task to new eligible recipients without reprogramming it.

    A recipient's completed task is never reopened by the daily job. The most
    recent reprogramming boundary separates it from an earlier completed task.
    """
    test = lock_test_source(db, test_id)
    if test is None:
        return
    if not test.pedido.habilitado or test.pedido.estado_general != EstadoPedidoGeneralEnum.ACTIVO:
        resolve_notifications_by_reference(db, notification_types=MATERIAL_NOTIFICATION_TYPES,
                                           tabla_referencia="PRUEBA_PEDIDO", id_referencia=test_id)
        return
    if test.numero not in {1, 2}:
        return
    kind = f"PRUEBA_{test.numero}_ALISTAR_MATERIAL"
    reference = (Notificacion.tipo == kind, Notificacion.tabla_referencia == "PRUEBA_PEDIDO",
                 Notificacion.id_referencia == test_id)
    boundary = db.execute(select(func.max(Notificacion.fecha_resuelta)).where(
        *reference, Notificacion.motivo_cierre == "REPROGRAMADA")).scalar_one()
    template_query = select(Notificacion).where(*reference, or_(
        Notificacion.resuelta.is_(False), Notificacion.motivo_cierre == "DESTINATARIO_NO_ELEGIBLE"))
    if boundary is not None:
        template_query = template_query.where(Notificacion.fecha >= boundary)
    template = db.execute(template_query.order_by(Notificacion.fecha.desc(), Notificacion.id.desc()).limit(1)).scalar_one_or_none()
    if template is None:
        return
    accounts = _get_active_accounts_for_roles(db, recipient_roles(kind))
    eligible = [account.usuario_id for account in accounts]
    result = db.execute(update(Notificacion).where(*reference, Notificacion.resuelta.is_(False),
        Notificacion.usuario_id.not_in(eligible)).values(resuelta=True, fecha_resuelta=utc_now(),
                                                       motivo_cierre="DESTINATARIO_NO_ELEGIBLE"))
    count_effect(db, "resolved", result.rowcount)
    for account in accounts:
        previous_query = select(Notificacion).where(*reference, Notificacion.usuario_id == account.usuario_id)
        if boundary is not None:
            previous_query = previous_query.where(Notificacion.fecha >= boundary)
        previous = db.execute(previous_query.order_by(Notificacion.fecha.desc(), Notificacion.id.desc()).limit(1)).scalar_one_or_none()
        if previous is not None and (not previous.resuelta or previous.motivo_cierre != "DESTINATARIO_NO_ELEGIBLE"):
            continue
        create_notification_for_user(db, user=account.usuario, tipo=kind, prioridad=template.prioridad,
            titulo=template.titulo, mensaje=template.mensaje, modulo=template.modulo,
            tabla_referencia="PRUEBA_PEDIDO", id_referencia=test_id)


def sync_order_test_notifications_for_order(db: Session, *, order_id: int) -> None:
    order = lock_source(db, Pedido, order_id)
    if order is None:
        return
    test_ids = db.execute(select(PruebaPedido.id).where(PruebaPedido.pedido_id == order_id)
                          .order_by(PruebaPedido.id)).scalars().all()
    for test_id in test_ids:
        sync_test_schedule_notifications_for_test(db, test_id=test_id)
        if not order.habilitado or order.estado_general != EstadoPedidoGeneralEnum.ACTIVO:
            resolve_notifications_by_reference(db, notification_types=MATERIAL_NOTIFICATION_TYPES,
                                               tabla_referencia="PRUEBA_PEDIDO", id_referencia=test_id)


def sync_flete_return_notifications_for_output(db: Session, *, output_id: int, today: date | None = None) -> None:
    salida = lock_source(db, SalidaFlete, output_id)
    if salida is None:
        return
    if salida.estado_salida not in {EstadoSalidaFleteEnum.RESERVADO, EstadoSalidaFleteEnum.EN_FLETE} or not salida.habilitado:
        resolve_notifications_by_reference(db, notification_types=FLETE_RETURN_NOTIFICATION_TYPES, tabla_referencia="salida_flete", id_referencia=salida.id)
        return
    base_date = today or business_today()
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
    role_codes = recipient_roles(notification_type, cashier_eligible=salida.garantia > salida.garantia_devuelta or salida.monto_arreglo > 0)
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
    flete = lock_source(db, FleteVestido, flete_id)
    if flete is None:
        return
    if not flete.habilitado or flete.estado in {EstadoFleteEnum.PASADO_PARA_VENTA, EstadoFleteEnum.RETIRADO} or flete.salidas_actuales < flete.max_salidas:
        resolve_notifications_by_reference(db, notification_types=("FLETE_MAX_SALIDAS",), tabla_referencia="flete_vestido", id_referencia=flete.id)
        return
    _sync_role_notifications_for_reference(
        db,
        role_codes=recipient_roles("FLETE_MAX_SALIDAS"),
        active_type="FLETE_MAX_SALIDAS",
        candidate_types=("FLETE_MAX_SALIDAS",),
        prioridad=PrioridadNotificacionEnum.ALTA,
        titulo="FLETE CON MÁXIMO DE SALIDAS ALCANZADO",
        mensaje=f'EL VESTIDO "{flete.item.nombre}" ALCANZÓ {flete.salidas_actuales} SALIDAS VÁLIDAS DE UN MÁXIMO DE {flete.max_salidas}. REVISE SI PASA A VENTA, SE RETIRA O CONTINÚA EN REVISIÓN.',
        modulo="FLETES",
        tabla_referencia="flete_vestido",
        id_referencia=flete.id,
    )


