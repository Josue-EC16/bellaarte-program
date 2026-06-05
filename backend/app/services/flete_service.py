from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.audit import register_audit_event
from app.models.account import Cuenta
from app.models.boutique_details import DetalleVestidoBoutique
from app.models.boutique_enums import EstadoFleteEnum, EstadoSalidaFleteEnum, TipoVestidoEnum
from app.models.boutique_item import ItemBoutique
from app.models.client import Cliente
from app.models.currency import Moneda
from app.models.flete import FleteVestido, SalidaFlete
from app.models.user import Usuario
from app.schemas.flete import (
    ComprobanteSummary,
    FleteClientSummary,
    FleteCreateRequest,
    FleteCurrencySummary,
    FleteDetailResponse,
    FleteDisableRequest,
    FleteEligibleItemSummary,
    FleteItemSummary,
    FleteListItem,
    FletePassToSaleRequest,
    FletePassToSaleResponse,
    FleteResolveReviewRequest,
    FleteRetireRequest,
    FleteSalidaHistoryItem,
    FleteUpdateRequest,
    FleteUserSummary,
    SalidaFleteAnnulRequest,
    SalidaFleteCreateRequest,
    SalidaFleteDeliverRequest,
    SalidaFleteDetailResponse,
    SalidaFleteListItem,
    SalidaFleteReturnRequest,
)
from app.services.currency_service import get_active_exchange_rate_for_currency
from app.services.notification_service import sync_flete_max_outputs_notification, sync_flete_return_notifications_for_output
from app.services.receipt_service import annul_receipt, create_flete_output_receipt


COUNTED_OUTPUT_STATES = {
    EstadoSalidaFleteEnum.DEVUELTO,
    EstadoSalidaFleteEnum.DEVUELTO_CON_OBSERVACION,
    EstadoSalidaFleteEnum.DEVUELTO_CON_ARREGLO,
}
BLOCKING_OUTPUT_STATES = {
    EstadoSalidaFleteEnum.RESERVADO,
    EstadoSalidaFleteEnum.EN_FLETE,
}


def _to_float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _ensure_operating_account(account: Cuenta) -> None:
    if not account.is_active or not account.usuario.activo or not account.rol.activo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="La cuenta usada para operar Fletes no está habilitada.")


def _get_item(db: Session, item_id: int) -> ItemBoutique:
    item = db.execute(
        select(ItemBoutique)
        .options(
            joinedload(ItemBoutique.tipo_item),
            joinedload(ItemBoutique.detalle_vestido),
            joinedload(ItemBoutique.proveedor_rel),
        )
        .where(ItemBoutique.id == item_id)
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto boutique no encontrado.")
    return item


def _is_vestido_item(item: ItemBoutique) -> bool:
    return item.tipo_item.nombre == "VESTIDO" and item.detalle_vestido is not None


def _get_flete_entity(db: Session, flete_id: int) -> FleteVestido:
    flete = db.execute(
        select(FleteVestido)
        .options(
            joinedload(FleteVestido.item).joinedload(ItemBoutique.tipo_item),
            joinedload(FleteVestido.item).joinedload(ItemBoutique.detalle_vestido),
            joinedload(FleteVestido.usuario).joinedload(Usuario.cuenta),
            selectinload(FleteVestido.salidas).joinedload(SalidaFlete.cliente),
        )
        .where(FleteVestido.id == flete_id)
    ).scalar_one_or_none()
    if flete is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro de flete no encontrado.")
    return flete


def _get_output_entity(db: Session, salida_id: int) -> SalidaFlete:
    salida = db.execute(
        select(SalidaFlete)
        .options(
            joinedload(SalidaFlete.flete).joinedload(FleteVestido.item).joinedload(ItemBoutique.tipo_item),
            joinedload(SalidaFlete.flete).joinedload(FleteVestido.usuario).joinedload(Usuario.cuenta),
            joinedload(SalidaFlete.cliente),
            joinedload(SalidaFlete.usuario).joinedload(Usuario.cuenta),
            joinedload(SalidaFlete.moneda),
            joinedload(SalidaFlete.comprobante),
        )
        .where(SalidaFlete.id == salida_id)
    ).scalar_one_or_none()
    if salida is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salida de flete no encontrada.")
    return salida


def _get_active_output(flete: FleteVestido) -> SalidaFlete | None:
    return next(
        (
            salida
            for salida in flete.salidas
            if salida.habilitado and salida.estado_salida in BLOCKING_OUTPUT_STATES
        ),
        None,
    )


def _get_client(db: Session, client_id: int) -> Cliente:
    client = db.execute(select(Cliente).where(Cliente.id == client_id)).scalar_one_or_none()
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")
    if not client.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El cliente está inactivo.")
    return client


def _get_currency(db: Session, currency_id: int) -> Moneda:
    currency = db.execute(select(Moneda).where(Moneda.id == currency_id)).scalar_one_or_none()
    if currency is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Moneda no encontrada.")
    if not currency.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La moneda seleccionada está inactiva.")
    return currency


def _generate_used_item_code(db: Session, base_code: str) -> str:
    suffix = 1
    while True:
        candidate = f"{base_code}-USADO-{suffix:02d}"
        exists = db.execute(select(ItemBoutique.id).where(ItemBoutique.codigo == candidate)).scalar_one_or_none()
        if exists is None:
            return candidate
        suffix += 1

def _recalculate_flete_state(flete: FleteVestido) -> None:
    if not flete.habilitado and flete.estado in {EstadoFleteEnum.PASADO_PARA_VENTA, EstadoFleteEnum.RETIRADO}:
        return
    if any(salida.habilitado and salida.estado_salida == EstadoSalidaFleteEnum.EN_FLETE for salida in flete.salidas):
        flete.estado = EstadoFleteEnum.EN_FLETE
        return
    if flete.salidas_actuales >= flete.max_salidas:
        flete.estado = EstadoFleteEnum.AGOTADO
        return
    flete.estado = EstadoFleteEnum.DISPONIBLE


def _to_item_summary(item: ItemBoutique) -> FleteItemSummary:
    return FleteItemSummary(
        id=item.id,
        code=item.codigo,
        name=item.nombre,
        color_primary=item.color_primario,
        color_secondary=item.color_secundario,
        material=item.material,
        sale_price=float(item.precio_venta),
        stock=item.stock,
    )


def _to_user_summary(user: Usuario) -> FleteUserSummary:
    return FleteUserSummary(
        id=user.id,
        full_name=user.nombre_completo,
        username=user.cuenta.username if user.cuenta else "",
    )


def _to_flete_list_item(flete: FleteVestido) -> FleteListItem:
    return FleteListItem(
        id=flete.id,
        item=_to_item_summary(flete.item),
        precio_flete_ref=float(flete.precio_flete_referencial),
        max_salidas=flete.max_salidas,
        salidas_actuales=flete.salidas_actuales,
        estado=flete.estado,
        habilitado=flete.habilitado,
        fecha_habilitacion=flete.fecha_habilitacion,
        tiene_salida_activa=_get_active_output(flete) is not None,
    )


def _to_flete_detail(flete: FleteVestido) -> FleteDetailResponse:
    active_output = _get_active_output(flete)
    history = sorted(flete.salidas, key=lambda salida: (salida.numero_salida, salida.id))
    return FleteDetailResponse(
        id=flete.id,
        item=_to_item_summary(flete.item),
        registered_by=_to_user_summary(flete.usuario),
        precio_flete_ref=float(flete.precio_flete_referencial),
        max_salidas=flete.max_salidas,
        salidas_actuales=flete.salidas_actuales,
        estado=flete.estado,
        fecha_habilitacion=flete.fecha_habilitacion,
        observaciones=flete.observaciones,
        habilitado=flete.habilitado,
        tiene_salida_activa=active_output is not None,
        active_output_id=active_output.id if active_output else None,
        salidas=[
            FleteSalidaHistoryItem(
                id=salida.id,
                numero_salida=salida.numero_salida,
                fecha_salida=salida.fecha_salida,
                fecha_devolucion_prevista=salida.fecha_devolucion_prevista,
                client_name=salida.cliente.nombre_completo,
                estado_salida=salida.estado_salida,
                total_flete=float(salida.total_flete),
            )
            for salida in history
        ],
    )


def _to_output_list_item(salida: SalidaFlete) -> SalidaFleteListItem:
    return SalidaFleteListItem(
        id=salida.id,
        flete_id=salida.flete_id,
        item_code=salida.flete.item.codigo,
        item_name=salida.flete.item.nombre,
        client_id=salida.cliente.id,
        client_name=salida.cliente.nombre_completo,
        currency_code=salida.moneda.codigo,
        numero_salida=salida.numero_salida,
        fecha_salida=salida.fecha_salida,
        fecha_devolucion_prevista=salida.fecha_devolucion_prevista,
        estado_salida=salida.estado_salida,
        total_flete=float(salida.total_flete),
        garantia=float(salida.garantia),
        registered_by=salida.usuario.nombre_completo,
    )


def _to_output_detail(salida: SalidaFlete) -> SalidaFleteDetailResponse:
    comprobante = salida.comprobante
    return SalidaFleteDetailResponse(
        id=salida.id,
        flete_id=salida.flete_id,
        item=_to_item_summary(salida.flete.item),
        client=FleteClientSummary(
            id=salida.cliente.id,
            codigo=salida.cliente.codigo,
            full_name=salida.cliente.nombre_completo,
        ),
        currency=FleteCurrencySummary(
            id=salida.moneda.id,
            codigo=salida.moneda.codigo,
            nombre=salida.moneda.nombre,
            simbolo=salida.moneda.simbolo,
            es_base=salida.moneda.es_base,
        ),
        registered_by=_to_user_summary(salida.usuario),
        numero_salida=salida.numero_salida,
        fecha_registro=salida.fecha_registro,
        fecha_salida=salida.fecha_salida,
        fecha_devolucion_prevista=salida.fecha_devolucion_prevista,
        fecha_devolucion_real=salida.fecha_devolucion_real,
        precio=float(salida.precio),
        descuento=_to_float(salida.descuento),
        motivo_desc=salida.motivo_descuento,
        metodo_pago=salida.metodo_pago,
        tipo_cambio_usado=float(salida.tipo_cambio_usado),
        total_flete=float(salida.total_flete),
        total_flete_moneda_origen=float(salida.total_flete_moneda_original),
        garantia=float(salida.garantia),
        garantia_devuelta=float(salida.garantia_devuelta),
        estado_salida=salida.estado_salida,
        estado_entrega=salida.estado_entrega,
        estado_devolucion=salida.estado_devolucion,
        requiere_arreglo=salida.requiere_arreglo,
        monto_arreglo=float(salida.monto_arreglo),
        descripcion_arreglo=salida.descripcion_arreglo,
        observaciones_entrega=salida.observaciones_entrega,
        observaciones_devolucion=salida.observaciones_devolucion,
        habilitado=salida.habilitado,
        comprobante=ComprobanteSummary(
            id=comprobante.id,
            codigo=comprobante.codigo,
            total=float(comprobante.total),
            total_moneda_original=float(comprobante.total_moneda_original),
            garantia=float(comprobante.garantia),
            estado=comprobante.estado.value,
        )
        if comprobante
        else None,
    )


def list_fletes(
    db: Session,
    *,
    search: str | None = None,
    state: EstadoFleteEnum | None = None,
    is_enabled: bool | None = None,
) -> list[FleteListItem]:
    stmt = (
        select(FleteVestido)
        .options(
            joinedload(FleteVestido.item),
            selectinload(FleteVestido.salidas),
        )
        .order_by(FleteVestido.fecha_habilitacion.desc())
    )
    if state is not None:
        stmt = stmt.where(FleteVestido.estado == state)
    if is_enabled is not None:
        stmt = stmt.where(FleteVestido.habilitado.is_(is_enabled))
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.join(FleteVestido.item).where(
            or_(
                func.upper(ItemBoutique.codigo).like(term),
                func.upper(ItemBoutique.nombre).like(term),
                func.upper(ItemBoutique.color_primario).like(term),
            )
        )
    return [_to_flete_list_item(flete) for flete in db.execute(stmt).unique().scalars().all()]


def list_eligible_flete_items(db: Session, *, search: str | None = None) -> list[FleteEligibleItemSummary]:
    stmt = (
        select(ItemBoutique)
        .options(joinedload(ItemBoutique.tipo_item), joinedload(ItemBoutique.detalle_vestido), joinedload(ItemBoutique.flete))
        .where(ItemBoutique.estado.is_(True), ItemBoutique.stock > 0)
        .order_by(ItemBoutique.nombre.asc())
    )
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.where(or_(func.upper(ItemBoutique.codigo).like(term), func.upper(ItemBoutique.nombre).like(term)))

    items = []
    for item in db.execute(stmt).unique().scalars().all():
        if not _is_vestido_item(item):
            continue
        if item.flete is not None:
            continue
        items.append(
            FleteEligibleItemSummary(
                id=item.id,
                code=item.codigo,
                name=item.nombre,
                color_primary=item.color_primario,
                sale_price=float(item.precio_venta),
                stock=item.stock,
                detail_kind="VESTIDO",
            )
        )
    return items


def get_flete_detail(db: Session, flete_id: int) -> FleteDetailResponse:
    return _to_flete_detail(_get_flete_entity(db, flete_id))


def create_flete(
    db: Session,
    *,
    payload: FleteCreateRequest,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> FleteDetailResponse:
    _ensure_operating_account(created_by)
    item = _get_item(db, payload.item_id)
    if not item.estado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El producto boutique está inactivo.")
    if not item.tipo_item.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El tipo boutique del producto está deshabilitado.")
    if item.stock <= 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El producto boutique no tiene stock disponible para habilitarse en flete.")
    if not _is_vestido_item(item):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo puedes habilitar para flete productos boutique del tipo VESTIDO.")
    existing = db.execute(select(FleteVestido).where(FleteVestido.item_id == item.id)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El producto boutique ya está relacionado con un registro de flete.")

    flete = FleteVestido(
        item_id=item.id,
        usuario_id=created_by.usuario_id,
        precio_flete_referencial=payload.precio_flete_ref,
        max_salidas=payload.max_salidas,
        salidas_actuales=0,
        estado=EstadoFleteEnum.DISPONIBLE,
        observaciones=payload.observaciones,
        habilitado=True,
    )
    item.stock -= 1
    db.add(flete)
    db.flush()
    register_audit_event(
        db,
        action="FLETE_CREATED",
        description=f"Se habilitó el vestido '{item.codigo}' para modalidad de flete.",
        account=created_by,
        user=created_by.usuario,
        reference=str(flete.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_flete_detail(db, flete.id)


def update_flete(
    db: Session,
    *,
    flete_id: int,
    payload: FleteUpdateRequest,
    updated_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> FleteDetailResponse:
    flete = _get_flete_entity(db, flete_id)
    if not flete.habilitado or flete.estado in {EstadoFleteEnum.PASADO_PARA_VENTA, EstadoFleteEnum.RETIRADO}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes editar un flete cerrado.")
    if payload.max_salidas < flete.salidas_actuales:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El máximo de salidas no puede ser menor a las salidas válidas ya acumuladas.")

    flete.precio_flete_referencial = payload.precio_flete_ref
    flete.max_salidas = payload.max_salidas
    flete.observaciones = payload.observaciones
    _recalculate_flete_state(flete)
    register_audit_event(
        db,
        action="FLETE_UPDATED",
        description=f"Se actualizó la configuración del flete '{flete.id}'.",
        account=updated_by,
        user=updated_by.usuario,
        reference=str(flete.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_flete_detail(db, flete.id)


def disable_flete(
    db: Session,
    *,
    flete_id: int,
    payload: FleteDisableRequest,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> FleteDetailResponse:
    flete = _get_flete_entity(db, flete_id)
    if _get_active_output(flete) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes deshabilitar un flete con una salida activa o reservada.")
    if flete.salidas_actuales > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El vestido ya tiene salidas válidas. Usa 'pasar a venta' o 'retirar' en lugar de deshabilitar.",
        )
    flete.item.stock += 1
    flete.habilitado = False
    flete.estado = EstadoFleteEnum.RETIRADO
    flete.observaciones = payload.motivo
    register_audit_event(
        db,
        action="FLETE_STATUS_CHANGED",
        description=f"Se deshabilitó el flete '{flete.id}' sin salidas válidas y se devolvió stock al item original.",
        account=changed_by,
        user=changed_by.usuario,
        reference=str(flete.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    sync_flete_max_outputs_notification(db, flete_id=flete.id)
    db.commit()
    return get_flete_detail(db, flete.id)


def resolve_flete_review(
    db: Session,
    *,
    flete_id: int,
    payload: FleteResolveReviewRequest,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> FleteDetailResponse:
    flete = _get_flete_entity(db, flete_id)
    if flete.estado != EstadoFleteEnum.EN_REVISION:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo puedes resolver fletes en revisión.")
    if payload.resolution == "disponible" and flete.salidas_actuales >= flete.max_salidas:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes volver a disponible un flete que ya alcanzó el máximo de salidas.")
    flete.estado = EstadoFleteEnum.DISPONIBLE if payload.resolution == "disponible" else EstadoFleteEnum.AGOTADO
    flete.observaciones = payload.motivo
    register_audit_event(
        db,
        action="FLETE_STATUS_CHANGED",
        description=f"Se resolvió la revisión del flete '{flete.id}' al estado '{flete.estado.value}'.",
        account=changed_by,
        user=changed_by.usuario,
        reference=str(flete.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_flete_detail(db, flete.id)


def pass_flete_to_sale(
    db: Session,
    *,
    flete_id: int,
    payload: FletePassToSaleRequest,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> FletePassToSaleResponse:
    flete = _get_flete_entity(db, flete_id)
    if _get_active_output(flete) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes pasar a venta un vestido con salida activa o reservada.")
    if flete.salidas_actuales < 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El vestido debe tener al menos una salida válida antes de pasar a venta.")
    original_item = flete.item
    new_code = _generate_used_item_code(db, original_item.codigo)
    detail_text = (original_item.detalle or "").strip()
    if detail_text:
        detail_text = f"{detail_text} | PRODUCTO USADO PROVENIENTE DE FLETE"
    else:
        detail_text = "PRODUCTO USADO PROVENIENTE DE FLETE"

    new_item = ItemBoutique(
        tipo_item_id=original_item.tipo_item_id,
        proveedor_id=original_item.proveedor_id,
        codigo=new_code,
        nombre=f"{original_item.nombre} USADO",
        color_primario=original_item.color_primario,
        color_secundario=original_item.color_secundario,
        material=original_item.material,
        largo=original_item.largo,
        ancho=original_item.ancho,
        precio_compra=original_item.precio_compra,
        precio_venta=payload.new_sale_price,
        stock=1,
        stock_minimo=1,
        detalle=payload.observaciones.strip().upper() if payload.observaciones else detail_text,
        estado=True,
    )
    db.add(new_item)
    db.flush()
    if original_item.detalle_vestido is not None:
        original_detail = original_item.detalle_vestido
        db.add(
            DetalleVestidoBoutique(
                item_id=new_item.id,
                tipo_vestido=original_detail.tipo_vestido,
                corte_falda=original_detail.corte_falda,
                tipo_escote=original_detail.tipo_escote,
                tiene_cola=original_detail.tiene_cola,
                tiene_manga=original_detail.tiene_manga,
                tiene_pedreria=original_detail.tiene_pedreria,
                copa_talla=original_detail.copa_talla,
                talla=original_detail.talla,
                largo_falda=original_detail.largo_falda,
                observaciones=original_detail.observaciones,
            )
        )
    flete.estado = EstadoFleteEnum.PASADO_PARA_VENTA
    flete.habilitado = False
    register_audit_event(
        db,
        action="FLETE_PASSED_TO_SALE",
        description=f"Se pasó a venta el flete '{flete.id}' y se creó el item boutique usado '{new_code}'.",
        account=changed_by,
        user=changed_by.usuario,
        reference=str(flete.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    sync_flete_max_outputs_notification(db, flete_id=flete.id)
    db.commit()
    return FletePassToSaleResponse(flete=get_flete_detail(db, flete.id), new_item_id=new_item.id, new_item_code=new_code)


def retire_flete(
    db: Session,
    *,
    flete_id: int,
    payload: FleteRetireRequest,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> FleteDetailResponse:
    flete = _get_flete_entity(db, flete_id)
    if _get_active_output(flete) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes retirar un vestido con salida activa o reservada.")
    if flete.salidas_actuales == 0:
        flete.item.stock += 1
    flete.estado = EstadoFleteEnum.RETIRADO
    flete.habilitado = False
    flete.observaciones = payload.motivo
    register_audit_event(
        db,
        action="FLETE_RETIRED",
        description=f"Se retiró el flete '{flete.id}' del circuito operativo.",
        account=changed_by,
        user=changed_by.usuario,
        reference=str(flete.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    sync_flete_max_outputs_notification(db, flete_id=flete.id)
    db.commit()
    return get_flete_detail(db, flete.id)


def list_flete_outputs(
    db: Session,
    *,
    search: str | None = None,
    flete_id: int | None = None,
    client_id: int | None = None,
    currency_id: int | None = None,
    state: EstadoSalidaFleteEnum | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[SalidaFleteListItem]:
    stmt = (
        select(SalidaFlete)
        .options(
            joinedload(SalidaFlete.flete).joinedload(FleteVestido.item),
            joinedload(SalidaFlete.cliente),
            joinedload(SalidaFlete.usuario),
            joinedload(SalidaFlete.moneda),
        )
        .order_by(SalidaFlete.fecha_registro.desc())
    )
    if flete_id is not None:
        stmt = stmt.where(SalidaFlete.flete_id == flete_id)
    if client_id is not None:
        stmt = stmt.where(SalidaFlete.cliente_id == client_id)
    if currency_id is not None:
        stmt = stmt.where(SalidaFlete.moneda_id == currency_id)
    if state is not None:
        stmt = stmt.where(SalidaFlete.estado_salida == state)
    if date_from is not None:
        stmt = stmt.where(SalidaFlete.fecha_salida >= date_from)
    if date_to is not None:
        stmt = stmt.where(SalidaFlete.fecha_salida <= date_to)
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = (
            stmt.join(SalidaFlete.flete)
            .join(FleteVestido.item)
            .join(SalidaFlete.cliente)
            .where(
                or_(
                    func.upper(ItemBoutique.codigo).like(term),
                    func.upper(ItemBoutique.nombre).like(term),
                    func.upper(Cliente.codigo).like(term),
                    func.upper(Cliente.nombres).like(term),
                    func.upper(Cliente.apellido_paterno).like(term),
                )
            )
        )
    return [_to_output_list_item(salida) for salida in db.execute(stmt).unique().scalars().all()]


def get_flete_output_detail(db: Session, salida_id: int) -> SalidaFleteDetailResponse:
    return _to_output_detail(_get_output_entity(db, salida_id))


def create_flete_output(
    db: Session,
    *,
    payload: SalidaFleteCreateRequest,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> SalidaFleteDetailResponse:
    _ensure_operating_account(created_by)
    flete = _get_flete_entity(db, payload.flete_id)
    if not flete.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El flete seleccionado está inactivo.")
    if flete.estado in {EstadoFleteEnum.AGOTADO, EstadoFleteEnum.PASADO_PARA_VENTA, EstadoFleteEnum.RETIRADO, EstadoFleteEnum.EN_REVISION}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El vestido no está disponible para registrar una nueva salida de flete.")
    if _get_active_output(flete) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El vestido ya tiene una salida activa o reservada.")

    next_num = (db.execute(select(func.max(SalidaFlete.numero_salida)).where(SalidaFlete.flete_id == flete.id)).scalar_one() or 0) + 1
    if next_num > flete.max_salidas:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes superar el máximo de salidas permitido para este vestido.")

    client = _get_client(db, payload.client_id)
    currency = _get_currency(db, payload.currency_id)

    subtotal = Decimal(str(payload.precio))
    discount = Decimal(str(payload.descuento or 0))
    total_bob = subtotal - discount
    if total_bob <= 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El total del flete debe ser mayor a cero.")

    if currency.es_base:
        exchange_rate_used = Decimal("1")
        total_currency_origin = total_bob
    else:
        exchange_rate = get_active_exchange_rate_for_currency(db, currency.id)
        if exchange_rate is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La moneda seleccionada no tiene un tipo de cambio activo.")
        exchange_rate_used = Decimal(exchange_rate.valor_bob)
        total_currency_origin = (total_bob / exchange_rate_used).quantize(Decimal("0.01"))

    salida = SalidaFlete(
        flete_id=flete.id,
        cliente_id=client.id,
        usuario_id=created_by.usuario_id,
        moneda_id=currency.id,
        numero_salida=next_num,
        fecha_salida=payload.fecha_salida,
        fecha_devolucion_prevista=payload.fecha_devolucion_prevista,
        precio=subtotal,
        descuento=discount if discount > 0 else None,
        motivo_descuento=payload.motivo_desc if discount > 0 else None,
        metodo_pago=payload.metodo_pago,
        tipo_cambio_usado=exchange_rate_used,
        total_flete_moneda_original=total_currency_origin,
        garantia=payload.garantia,
        garantia_devuelta=0,
        estado_salida=EstadoSalidaFleteEnum.RESERVADO,
        estado_entrega=payload.estado_entrega,
        observaciones_entrega=payload.observaciones_entrega,
        habilitado=True,
    )
    db.add(salida)
    db.flush()
    db.refresh(salida)
    salida.cliente = client
    salida.moneda = currency
    salida.flete = flete
    create_flete_output_receipt(
        db,
        salida=salida,
        client=client,
        snapshot_payload=payload.receipt_customer_snapshot,
    )
    register_audit_event(
        db,
        action="FLETE_OUTPUT_CREATED",
        description=f"Se registró la salida de flete '{salida.id}' para el vestido '{flete.item.codigo}'.",
        account=created_by,
        user=created_by.usuario,
        reference=str(salida.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    register_audit_event(
        db,
        action="FLETE_RECEIPT_CREATED",
        description=f"Se emitió el comprobante interno de la salida de flete '{salida.id}'.",
        account=created_by,
        user=created_by.usuario,
        reference=str(salida.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    sync_flete_return_notifications_for_output(db, output_id=salida.id)
    sync_flete_max_outputs_notification(db, flete_id=flete.id)
    db.commit()
    return get_flete_output_detail(db, salida.id)


def deliver_flete_output(
    db: Session,
    *,
    salida_id: int,
    payload: SalidaFleteDeliverRequest,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> SalidaFleteDetailResponse:
    salida = _get_output_entity(db, salida_id)
    if salida.estado_salida != EstadoSalidaFleteEnum.RESERVADO:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo puedes entregar salidas en estado RESERVADO.")
    salida.estado_salida = EstadoSalidaFleteEnum.EN_FLETE
    if payload.observaciones_entrega:
        salida.observaciones_entrega = payload.observaciones_entrega
    salida.flete.estado = EstadoFleteEnum.EN_FLETE
    register_audit_event(
        db,
        action="FLETE_OUTPUT_DELIVERED",
        description=f"Se marcó como entregada la salida de flete '{salida.id}'.",
        account=changed_by,
        user=changed_by.usuario,
        reference=str(salida.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_flete_output_detail(db, salida.id)


def return_flete_output(
    db: Session,
    *,
    salida_id: int,
    payload: SalidaFleteReturnRequest,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> SalidaFleteDetailResponse:
    salida = _get_output_entity(db, salida_id)
    if salida.estado_salida != EstadoSalidaFleteEnum.EN_FLETE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo puedes registrar devoluciones de salidas que están EN_FLETE.")
    if payload.fecha_devolucion_real < salida.fecha_salida:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La fecha real de devolución no puede ser anterior a la fecha de salida.")
    if payload.garantia_devuelta > float(salida.garantia):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La garantía devuelta no puede ser mayor a la garantía recibida.")

    new_state = EstadoSalidaFleteEnum(payload.estado_salida)
    salida.estado_salida = new_state
    salida.fecha_devolucion_real = payload.fecha_devolucion_real
    salida.estado_devolucion = payload.estado_devolucion
    salida.requiere_arreglo = payload.requiere_arreglo
    salida.monto_arreglo = payload.monto_arreglo
    salida.descripcion_arreglo = payload.descripcion_arreglo
    salida.garantia_devuelta = payload.garantia_devuelta
    salida.observaciones_devolucion = payload.observaciones_devolucion
    salida.flete.salidas_actuales += 1

    if new_state == EstadoSalidaFleteEnum.DEVUELTO:
        salida.flete.estado = EstadoFleteEnum.AGOTADO if salida.flete.salidas_actuales >= salida.flete.max_salidas else EstadoFleteEnum.DISPONIBLE
    else:
        salida.flete.estado = EstadoFleteEnum.EN_REVISION

    register_audit_event(
        db,
        action="FLETE_OUTPUT_RETURNED",
        description=f"Se registró la devolución de la salida de flete '{salida.id}' en estado '{new_state.value}'.",
        account=changed_by,
        user=changed_by.usuario,
        reference=str(salida.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    sync_flete_return_notifications_for_output(db, output_id=salida.id)
    sync_flete_max_outputs_notification(db, flete_id=salida.flete_id)
    db.commit()
    return get_flete_output_detail(db, salida.id)


def _apply_flete_output_annulment(
    db: Session,
    *,
    salida: SalidaFlete,
    motivo: str,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> None:
    if salida.estado_salida == EstadoSalidaFleteEnum.ANULADO:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La salida de flete ya fue anulada.")

    counted_before = salida.estado_salida in COUNTED_OUTPUT_STATES
    salida.estado_salida = EstadoSalidaFleteEnum.ANULADO
    salida.fecha_cambio_estado = datetime.now(timezone.utc)
    salida.motivo_cambio_estado = motivo
    salida.habilitado = False
    if counted_before and salida.flete.salidas_actuales > 0:
        salida.flete.salidas_actuales -= 1
    annul_receipt(salida.comprobante, reason=motivo)
    _recalculate_flete_state(salida.flete)
    register_audit_event(
        db,
        action="FLETE_OUTPUT_ANNULLED",
        description=f"Se anuló la salida de flete '{salida.id}'.",
        account=changed_by,
        user=changed_by.usuario,
        reference=str(salida.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    register_audit_event(
        db,
        action="FLETE_RECEIPT_ANNULLED",
        description=f"Se anuló el comprobante interno asociado a la salida de flete '{salida.id}'.",
        account=changed_by,
        user=changed_by.usuario,
        reference=str(salida.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    sync_flete_return_notifications_for_output(db, output_id=salida.id)
    sync_flete_max_outputs_notification(db, flete_id=salida.flete_id)


def annul_flete_output(
    db: Session,
    *,
    salida_id: int,
    payload: SalidaFleteAnnulRequest,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> SalidaFleteDetailResponse:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Debes registrar la DEVOLUCIÓN desde ECONOMÍA antes de anular la salida de flete.",
    )
