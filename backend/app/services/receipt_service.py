from datetime import datetime, timezone
from decimal import Decimal
from html import escape

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session, joinedload

from app.core.audit import register_audit_event
from app.models.account import Cuenta
from app.models.boutique_enums import EstadoComprobanteEnum
from app.models.client import Cliente
from app.models.currency import Moneda
from app.models.order import PagoPedido, Pedido
from app.models.receipt import ComprobanteInterno, DetalleComprobante, TipoComprobante
from app.models.user import Usuario
from app.schemas.receipt import (
    ReceiptClientSnapshot,
    ReceiptCurrencySummary,
    ReceiptCustomerSnapshotPayload,
    ReceiptDetailLine,
    ReceiptDetailResponse,
    ReceiptListItem,
    ReceiptSummary,
    ReceiptTypeCreateRequest,
    ReceiptTypeResponse,
    ReceiptTypeUpdateRequest,
    ReceiptUserSummary,
)


RECEIPT_TYPE_NAMES = {
    "VENTA_BOUTIQUE": "VENTA_BOUTIQUE_INTERNO",
    "PAGO_PEDIDO": "PAGO_PEDIDO_INTERNO",
    "SALIDA_FLETE": "FLETE_INTERNO",
}
RECEIPT_CODE_PREFIXES = {
    "VENTA_BOUTIQUE": "COI-VEB-",
    "PAGO_PEDIDO": "COI-PPD-",
    "SALIDA_FLETE": "COI-SFL-",
}
SYSTEM_RECEIPT_TYPE_NAMES = frozenset(RECEIPT_TYPE_NAMES.values())


def _to_float(value) -> float:
    return float(value or 0)


def _resolve_origin_type(receipt: ComprobanteInterno) -> tuple[str, int]:
    if receipt.venta_boutique_id is not None:
        return "VENTA_BOUTIQUE", receipt.venta_boutique_id
    if receipt.pago_pedido_id is not None:
        return "PAGO_PEDIDO", receipt.pago_pedido_id
    if receipt.salida_flete_id is not None:
        return "SALIDA_FLETE", receipt.salida_flete_id
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="El comprobante no tiene un origen operativo válido.")


def _normalize_upper(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None


def _get_receipt_type_entity(db: Session, type_id: int) -> TipoComprobante:
    entity = db.execute(select(TipoComprobante).where(TipoComprobante.id == type_id)).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de comprobante no encontrado.")
    return entity


def _ensure_unique_receipt_type_name(db: Session, nombre: str, *, exclude_id: int | None = None) -> None:
    stmt = select(TipoComprobante.id).where(func.upper(TipoComprobante.nombre) == nombre.strip().upper())
    if exclude_id is not None:
        stmt = stmt.where(TipoComprobante.id != exclude_id)
    if db.execute(stmt).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un tipo de comprobante con ese nombre.")


def _is_system_receipt_type(entity: TipoComprobante) -> bool:
    return entity.nombre.strip().upper() in SYSTEM_RECEIPT_TYPE_NAMES


def _to_receipt_type_response(entity: TipoComprobante) -> ReceiptTypeResponse:
    return ReceiptTypeResponse.model_validate(entity)


def _get_receipt_type(db: Session, origin_type: str) -> TipoComprobante:
    type_name = RECEIPT_TYPE_NAMES[origin_type]
    receipt_type = db.execute(
        select(TipoComprobante).where(func.upper(TipoComprobante.nombre) == type_name)
    ).scalar_one_or_none()
    if receipt_type is None or not receipt_type.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"No existe un tipo de comprobante habilitado para {origin_type}.")
    return receipt_type


def _generate_receipt_code(db: Session, origin_type: str) -> str:
    prefix = RECEIPT_CODE_PREFIXES[origin_type]
    if db.bind and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"), {"lock_key": prefix})
    latest_code = db.execute(
        select(ComprobanteInterno.codigo)
        .where(ComprobanteInterno.codigo.like(f"{prefix}%"))
        .order_by(ComprobanteInterno.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    next_number = int(latest_code.removeprefix(prefix)) + 1 if latest_code else 1
    return f"{prefix}{next_number:05d}"


def _ensure_origin_receipt_absent(
    db: Session,
    *,
    venta_boutique_id: int | None = None,
    pago_pedido_id: int | None = None,
    salida_flete_id: int | None = None,
) -> None:
    conditions = []
    if venta_boutique_id is not None:
        conditions.append(ComprobanteInterno.venta_boutique_id == venta_boutique_id)
    if pago_pedido_id is not None:
        conditions.append(ComprobanteInterno.pago_pedido_id == pago_pedido_id)
    if salida_flete_id is not None:
        conditions.append(ComprobanteInterno.salida_flete_id == salida_flete_id)
    if not conditions:
        return
    existing = db.execute(select(ComprobanteInterno.id).where(or_(*conditions))).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El movimiento ya tiene un comprobante interno emitido.")


def resolve_customer_snapshot(
    *,
    client: Cliente | None,
    snapshot_payload: ReceiptCustomerSnapshotPayload | None,
) -> tuple[str, str, str]:
    payload_name = snapshot_payload.full_name if snapshot_payload else None
    payload_ci = snapshot_payload.ci_nit if snapshot_payload else None
    payload_cell = snapshot_payload.cellphone if snapshot_payload else None

    if client is None:
        if not payload_name or not payload_ci or not payload_cell:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Debes completar NOMBRE, CI/NIT y CELULAR para emitir el comprobante interno.",
            )
        return payload_name, payload_ci, payload_cell

    resolved_name = client.nombre_completo or payload_name
    resolved_ci = client.ci or payload_ci
    resolved_cell = client.celular or payload_cell
    if not resolved_name or not resolved_ci or not resolved_cell:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El cliente no tiene datos documentales completos. Completa NOMBRE, CI/NIT y CELULAR para emitir el comprobante interno.",
        )
    return resolved_name, resolved_ci, resolved_cell


def _to_receipt_summary(receipt: ComprobanteInterno | None) -> ReceiptSummary | None:
    if receipt is None:
        return None
    return ReceiptSummary(
        id=receipt.id,
        codigo=receipt.codigo,
        estado=receipt.estado,
        total=_to_float(receipt.total),
        total_moneda_original=_to_float(receipt.total_moneda_original),
    )


def list_receipt_types(db: Session) -> list[ReceiptTypeResponse]:
    entities = db.execute(select(TipoComprobante).order_by(TipoComprobante.nombre.asc())).scalars().all()
    return [_to_receipt_type_response(entity) for entity in entities]


def get_receipt_type(db: Session, type_id: int) -> ReceiptTypeResponse:
    return _to_receipt_type_response(_get_receipt_type_entity(db, type_id))


def create_receipt_type(
    db: Session,
    *,
    payload: ReceiptTypeCreateRequest,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> ReceiptTypeResponse:
    _ensure_unique_receipt_type_name(db, payload.nombre)
    entity = TipoComprobante(
        nombre=payload.nombre,
        descripcion=payload.descripcion,
        es_fiscal=payload.es_fiscal,
        habilitado=True,
    )
    db.add(entity)
    db.flush()
    register_audit_event(
        db,
        action="RECEIPT_TYPE_CREATED",
        description=f"Se creó el tipo de comprobante '{entity.nombre}'.",
        account=created_by,
        user=created_by.usuario,
        reference=str(entity.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(entity)
    return _to_receipt_type_response(entity)


def update_receipt_type(
    db: Session,
    *,
    type_id: int,
    payload: ReceiptTypeUpdateRequest,
    updated_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> ReceiptTypeResponse:
    entity = _get_receipt_type_entity(db, type_id)
    entity.descripcion = payload.descripcion
    entity.es_fiscal = payload.es_fiscal
    register_audit_event(
        db,
        action="RECEIPT_TYPE_UPDATED",
        description=f"Se actualizó el tipo de comprobante '{entity.nombre}'.",
        account=updated_by,
        user=updated_by.usuario,
        reference=str(entity.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(entity)
    return _to_receipt_type_response(entity)


def set_receipt_type_status(
    db: Session,
    *,
    type_id: int,
    enabled: bool,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> ReceiptTypeResponse:
    entity = _get_receipt_type_entity(db, type_id)
    if not enabled and _is_system_receipt_type(entity):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No puedes deshabilitar un tipo de comprobante base del sistema porque se usa para la emisión automática.",
        )
    entity.habilitado = enabled
    register_audit_event(
        db,
        action="RECEIPT_TYPE_STATUS_CHANGED",
        description=f"Se actualizó el estado del tipo de comprobante '{entity.nombre}' a {'ACTIVO' if enabled else 'INACTIVO'}.",
        account=changed_by,
        user=changed_by.usuario,
        reference=str(entity.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(entity)
    return _to_receipt_type_response(entity)


def create_sale_receipt(
    db: Session,
    *,
    sale,
    client: Cliente | None,
    snapshot_payload: ReceiptCustomerSnapshotPayload | None,
) -> ComprobanteInterno:
    _ensure_origin_receipt_absent(db, venta_boutique_id=sale.id)
    receipt_type = _get_receipt_type(db, "VENTA_BOUTIQUE")
    snapshot_name, snapshot_ci, snapshot_cell = resolve_customer_snapshot(client=client, snapshot_payload=snapshot_payload)
    subtotal = Decimal(sale.cantidad) * Decimal(str(sale.precio_unitario))
    receipt = ComprobanteInterno(
        tipo_comprobante_id=receipt_type.id,
        cliente_id=client.id if client else None,
        usuario_id=sale.usuario_id,
        venta_boutique_id=sale.id,
        moneda_id=sale.moneda_id,
        codigo=_generate_receipt_code(db, "VENTA_BOUTIQUE"),
        nombre_cliente=snapshot_name,
        ci_nit_cliente=snapshot_ci,
        celular_cliente=snapshot_cell,
        subtotal=subtotal,
        descuento=sale.descuento or 0,
        total=sale.total,
        total_moneda_original=sale.total_moneda_original,
        saldo_posterior=0,
        garantia=0,
        tipo_cambio_usado=sale.tipo_cambio_usado,
        metodo_pago=sale.metodo_pago,
        estado=EstadoComprobanteEnum.EMITIDO,
        habilitado=True,
    )
    db.add(receipt)
    db.flush()
    db.add(
        DetalleComprobante(
            comprobante_id=receipt.id,
            concepto=f"VENTA BOUTIQUE {sale.item.codigo} - {sale.item.nombre}",
            cantidad=sale.cantidad,
            precio_unidad=sale.precio_unitario,
            descuento=sale.descuento or 0,
            subtotal=sale.total,
            observaciones=sale.observaciones,
        )
    )
    return receipt


def create_order_payment_receipt(
    db: Session,
    *,
    payment: PagoPedido,
    order: Pedido,
    snapshot_payload: ReceiptCustomerSnapshotPayload | None,
) -> ComprobanteInterno:
    _ensure_origin_receipt_absent(db, pago_pedido_id=payment.id)
    receipt_type = _get_receipt_type(db, "PAGO_PEDIDO")
    snapshot_name, snapshot_ci, snapshot_cell = resolve_customer_snapshot(client=order.cliente, snapshot_payload=snapshot_payload)
    receipt = ComprobanteInterno(
        tipo_comprobante_id=receipt_type.id,
        cliente_id=order.cliente_id,
        usuario_id=payment.usuario_id,
        pago_pedido_id=payment.id,
        moneda_id=payment.moneda_id,
        codigo=_generate_receipt_code(db, "PAGO_PEDIDO"),
        nombre_cliente=snapshot_name,
        ci_nit_cliente=snapshot_ci,
        celular_cliente=snapshot_cell,
        subtotal=payment.monto_bob,
        descuento=0,
        total=payment.monto_bob,
        total_moneda_original=payment.monto,
        saldo_posterior=order.saldo,
        garantia=0,
        tipo_cambio_usado=payment.tipo_cambio_usado,
        metodo_pago=payment.metodo_pago,
        estado=EstadoComprobanteEnum.EMITIDO,
        habilitado=True,
    )
    db.add(receipt)
    db.flush()
    db.add(
        DetalleComprobante(
            comprobante_id=receipt.id,
            concepto=f"PAGO DE PEDIDO {order.codigo}",
            cantidad=1,
            precio_unidad=payment.monto_bob,
            descuento=0,
            subtotal=payment.monto_bob,
            observaciones=payment.observaciones,
        )
    )
    return receipt


def create_flete_output_receipt(
    db: Session,
    *,
    salida,
    client: Cliente,
    snapshot_payload: ReceiptCustomerSnapshotPayload | None,
) -> ComprobanteInterno:
    _ensure_origin_receipt_absent(db, salida_flete_id=salida.id)
    receipt_type = _get_receipt_type(db, "SALIDA_FLETE")
    snapshot_name, snapshot_ci, snapshot_cell = resolve_customer_snapshot(client=client, snapshot_payload=snapshot_payload)
    receipt = ComprobanteInterno(
        tipo_comprobante_id=receipt_type.id,
        cliente_id=client.id,
        usuario_id=salida.usuario_id,
        salida_flete_id=salida.id,
        moneda_id=salida.moneda_id,
        codigo=_generate_receipt_code(db, "SALIDA_FLETE"),
        nombre_cliente=snapshot_name,
        ci_nit_cliente=snapshot_ci,
        celular_cliente=snapshot_cell,
        subtotal=salida.precio,
        descuento=salida.descuento or 0,
        total=salida.total_flete,
        total_moneda_original=salida.total_flete_moneda_original,
        saldo_posterior=0,
        garantia=salida.garantia,
        tipo_cambio_usado=salida.tipo_cambio_usado,
        metodo_pago=salida.metodo_pago,
        estado=EstadoComprobanteEnum.EMITIDO,
        habilitado=True,
    )
    db.add(receipt)
    db.flush()
    db.add(
        DetalleComprobante(
            comprobante_id=receipt.id,
            concepto=f"SERVICIO DE FLETE {salida.flete.item.codigo} - {salida.flete.item.nombre}",
            cantidad=1,
            precio_unidad=salida.precio,
            descuento=salida.descuento or 0,
            subtotal=salida.total_flete,
            observaciones="LA GARANTIA SE REGISTRA COMO CONTROL Y NO COMO INGRESO REAL",
        )
    )
    return receipt


def annul_receipt(receipt: ComprobanteInterno | None, *, reason: str) -> None:
    if receipt is None or receipt.estado == EstadoComprobanteEnum.ANULADO:
        return
    receipt.estado = EstadoComprobanteEnum.ANULADO
    receipt.fecha_cambio_estado = datetime.now(timezone.utc)
    receipt.motivo_cambio_estado = reason
    receipt.habilitado = False


def _receipt_list_query():
    return (
        select(ComprobanteInterno)
        .options(
            joinedload(ComprobanteInterno.tipo_comprobante),
            joinedload(ComprobanteInterno.usuario).joinedload(Usuario.cuenta),
            joinedload(ComprobanteInterno.moneda),
            joinedload(ComprobanteInterno.detalles),
            joinedload(ComprobanteInterno.venta_boutique),
            joinedload(ComprobanteInterno.pago_pedido).joinedload(PagoPedido.pedido),
            joinedload(ComprobanteInterno.salida_flete),
        )
        .order_by(ComprobanteInterno.fecha.desc(), ComprobanteInterno.id.desc())
    )


def _to_receipt_list_item(receipt: ComprobanteInterno) -> ReceiptListItem:
    origin_type, origin_id = _resolve_origin_type(receipt)
    return ReceiptListItem(
        id=receipt.id,
        codigo=receipt.codigo,
        fecha=receipt.fecha,
        estado=receipt.estado,
        origin_type=origin_type,
        origin_id=origin_id,
        tipo_comprobante=receipt.tipo_comprobante.nombre,
        client_name=receipt.nombre_cliente or "SIN CLIENTE",
        client_ci_nit=receipt.ci_nit_cliente or "SIN CI/NIT",
        client_cellphone=receipt.celular_cliente or "SIN CELULAR",
        currency_code=receipt.moneda.codigo if receipt.moneda else None,
        payment_method=receipt.metodo_pago,
        subtotal=_to_float(receipt.subtotal),
        descuento=_to_float(receipt.descuento),
        total=_to_float(receipt.total),
        total_moneda_original=_to_float(receipt.total_moneda_original),
        saldo_posterior=_to_float(receipt.saldo_posterior),
        garantia=_to_float(receipt.garantia),
        registered_by=receipt.usuario.nombre_completo,
    )


def list_receipts(
    db: Session,
    *,
    search: str | None = None,
    origin_type: str | None = None,
    state: EstadoComprobanteEnum | None = None,
    currency_id: int | None = None,
    payment_method=None,
    client_id: int | None = None,
    user_id: int | None = None,
    date_from=None,
    date_to=None,
) -> list[ReceiptListItem]:
    stmt = _receipt_list_query()
    if origin_type == "VENTA_BOUTIQUE":
        stmt = stmt.where(ComprobanteInterno.venta_boutique_id.is_not(None))
    if origin_type == "PAGO_PEDIDO":
        stmt = stmt.where(ComprobanteInterno.pago_pedido_id.is_not(None))
    if origin_type == "SALIDA_FLETE":
        stmt = stmt.where(ComprobanteInterno.salida_flete_id.is_not(None))
    if state is not None:
        stmt = stmt.where(ComprobanteInterno.estado == state)
    if currency_id is not None:
        stmt = stmt.where(ComprobanteInterno.moneda_id == currency_id)
    if payment_method is not None:
        stmt = stmt.where(ComprobanteInterno.metodo_pago == payment_method)
    if client_id is not None:
        stmt = stmt.where(ComprobanteInterno.cliente_id == client_id)
    if user_id is not None:
        stmt = stmt.where(ComprobanteInterno.usuario_id == user_id)
    if date_from is not None:
        stmt = stmt.where(func.date(ComprobanteInterno.fecha) >= date_from)
    if date_to is not None:
        stmt = stmt.where(func.date(ComprobanteInterno.fecha) <= date_to)
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.where(
            or_(
                func.upper(ComprobanteInterno.codigo).like(term),
                func.upper(func.coalesce(ComprobanteInterno.nombre_cliente, "")).like(term),
                func.upper(func.coalesce(ComprobanteInterno.ci_nit_cliente, "")).like(term),
                func.upper(func.coalesce(ComprobanteInterno.celular_cliente, "")).like(term),
            )
        )
    return [_to_receipt_list_item(receipt) for receipt in db.execute(stmt).unique().scalars().all()]


def get_receipt_entity(db: Session, receipt_id: int) -> ComprobanteInterno:
    receipt = db.execute(_receipt_list_query().where(ComprobanteInterno.id == receipt_id)).unique().scalar_one_or_none()
    if receipt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comprobante interno no encontrado.")
    return receipt


def get_receipt_detail(db: Session, receipt_id: int) -> ReceiptDetailResponse:
    receipt = get_receipt_entity(db, receipt_id)
    origin_type, origin_id = _resolve_origin_type(receipt)
    return ReceiptDetailResponse(
        id=receipt.id,
        codigo=receipt.codigo,
        fecha=receipt.fecha,
        estado=receipt.estado,
        origin_type=origin_type,
        origin_id=origin_id,
        tipo_comprobante=receipt.tipo_comprobante.nombre,
        client=ReceiptClientSnapshot(
            id=receipt.cliente_id,
            full_name=receipt.nombre_cliente or "SIN CLIENTE",
            ci_nit=receipt.ci_nit_cliente or "SIN CI/NIT",
            cellphone=receipt.celular_cliente or "SIN CELULAR",
        ),
        registered_by=ReceiptUserSummary(
            id=receipt.usuario.id,
            full_name=receipt.usuario.nombre_completo,
            username=receipt.usuario.cuenta.username if receipt.usuario.cuenta else None,
        ),
        currency=ReceiptCurrencySummary(
            id=receipt.moneda.id if receipt.moneda else None,
            codigo=receipt.moneda.codigo if receipt.moneda else None,
            nombre=receipt.moneda.nombre if receipt.moneda else None,
            simbolo=receipt.moneda.simbolo if receipt.moneda else None,
            es_base=receipt.moneda.es_base if receipt.moneda else None,
        )
        if receipt.moneda
        else None,
        subtotal=_to_float(receipt.subtotal),
        descuento=_to_float(receipt.descuento),
        total=_to_float(receipt.total),
        total_moneda_original=_to_float(receipt.total_moneda_original),
        saldo_posterior=_to_float(receipt.saldo_posterior),
        garantia=_to_float(receipt.garantia),
        tipo_cambio_usado=_to_float(receipt.tipo_cambio_usado),
        payment_method=receipt.metodo_pago,
        changed_at=receipt.fecha_cambio_estado,
        state_change_reason=receipt.motivo_cambio_estado,
        details=[
            ReceiptDetailLine(
                id=detail.id,
                concepto=detail.concepto,
                cantidad=_to_float(detail.cantidad),
                precio_unidad=_to_float(detail.precio_unidad),
                descuento=_to_float(detail.descuento),
                subtotal=_to_float(detail.subtotal),
                observaciones=detail.observaciones,
            )
            for detail in receipt.detalles
        ],
    )


def build_receipt_printable_html(db: Session, receipt_id: int) -> str:
    receipt = get_receipt_detail(db, receipt_id)
    detail_rows = "".join(
        f"<tr>"
        f"<td>{escape(line.concepto)}</td>"
        f"<td class='right'>{line.cantidad:.2f}</td>"
        f"<td class='right'>Bs {line.precio_unidad:.2f}</td>"
        f"<td class='right'>Bs {line.descuento:.2f}</td>"
        f"<td class='right'>Bs {line.subtotal:.2f}</td>"
        f"</tr>"
        for line in receipt.details
    )
    observation_rows = "".join(
        f"<li>{escape(line.observaciones)}</li>"
        for line in receipt.details
        if line.observaciones
    )
    watermark = (
        "<div class='watermark'>ANULADO</div>"
        if receipt.estado == EstadoComprobanteEnum.ANULADO
        else ""
    )
    guarantee_block = (
        f"<div class='metric'><span>GARANTIA</span><strong>Bs {receipt.garantia:.2f}</strong></div>"
        if receipt.garantia > 0
        else ""
    )
    saldo_block = (
        f"<div class='metric'><span>SALDO POSTERIOR</span><strong>Bs {receipt.saldo_posterior:.2f}</strong></div>"
        if receipt.saldo_posterior > 0
        else ""
    )
    state_note = (
        f"<p class='state-note'>COMPROBANTE ANULADO EL {receipt.changed_at:%d/%m/%Y %H:%M} POR: {escape(receipt.state_change_reason or 'SIN MOTIVO REGISTRADO')}</p>"
        if receipt.estado == EstadoComprobanteEnum.ANULADO and receipt.changed_at
        else ""
    )
    return f"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>Comprobante interno {escape(receipt.codigo)}</title>
  <style>
    :root {{
      --ink: #2d1a16;
      --accent: #8f3d2e;
      --line: #d8c5bd;
      --soft: #fff7f1;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 20px;
      font-family: "Trebuchet MS", "Segoe UI", sans-serif;
      color: var(--ink);
      background: #f7f1ed;
    }}
    .actions {{ margin-bottom: 12px; }}
    .actions button {{
      border: 0;
      background: var(--accent);
      color: #fff;
      padding: 10px 18px;
      border-radius: 999px;
      cursor: pointer;
      font-weight: 700;
    }}
    .sheet {{
      position: relative;
      width: 210mm;
      min-height: 297mm;
      margin: 0 auto;
      background: white;
      padding: 18mm 16mm;
      box-shadow: 0 18px 60px rgba(45, 26, 22, 0.12);
      overflow: hidden;
    }}
    .watermark {{
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 68px;
      font-weight: 900;
      color: rgba(143, 61, 46, 0.12);
      transform: rotate(-24deg);
      pointer-events: none;
      letter-spacing: 6px;
    }}
    header {{
      display: grid;
      grid-template-columns: 110px 1fr auto;
      gap: 18px;
      align-items: center;
      border-bottom: 2px solid var(--accent);
      padding-bottom: 16px;
      margin-bottom: 18px;
    }}
    .brand img {{ width: 100%; height: auto; display: block; }}
    .brand-copy h1 {{
      margin: 0;
      font-size: 28px;
      letter-spacing: 0.04em;
    }}
    .brand-copy p {{
      margin: 6px 0 0;
      color: #6e5148;
      font-size: 13px;
    }}
    .doc-tag {{
      text-align: right;
    }}
    .doc-tag strong {{
      display: block;
      font-size: 13px;
      color: #6e5148;
    }}
    .doc-tag h2 {{
      margin: 4px 0 0;
      font-size: 20px;
      color: var(--accent);
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}
    .panel {{
      border: 1px solid var(--line);
      background: linear-gradient(180deg, #fff, var(--soft));
      border-radius: 16px;
      padding: 14px;
    }}
    .panel h3 {{
      margin: 0 0 10px;
      font-size: 13px;
      color: var(--accent);
      letter-spacing: 0.08em;
    }}
    .kv {{
      display: grid;
      grid-template-columns: 145px 1fr;
      gap: 8px;
      font-size: 13px;
      margin-bottom: 6px;
    }}
    .kv span:first-child {{
      color: #6e5148;
      font-weight: 700;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0 18px;
    }}
    thead th {{
      background: var(--accent);
      color: white;
      font-size: 12px;
      letter-spacing: 0.04em;
      padding: 10px 8px;
      text-align: left;
    }}
    tbody td {{
      border: 1px solid var(--line);
      padding: 10px 8px;
      font-size: 12px;
      vertical-align: top;
    }}
    .right {{ text-align: right; }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 12px;
      background: #fffaf7;
    }}
    .metric span {{
      display: block;
      font-size: 12px;
      color: #6e5148;
      margin-bottom: 6px;
    }}
    .metric strong {{
      font-size: 20px;
      color: var(--ink);
    }}
    .legal {{
      margin-top: 18px;
      padding-top: 12px;
      border-top: 1px dashed var(--line);
      font-size: 12px;
      color: #6e5148;
    }}
    .state-note {{
      margin-top: 12px;
      color: #a03322;
      font-weight: 700;
    }}
    ul {{
      margin: 8px 0 0 18px;
      padding: 0;
      font-size: 12px;
    }}
    @media print {{
      body {{ background: white; padding: 0; }}
      .actions {{ display: none; }}
      .sheet {{
        width: auto;
        min-height: auto;
        margin: 0;
        padding: 10mm;
        box-shadow: none;
      }}
    }}
  </style>
</head>
<body>
  <div class="actions">
    <button onclick="window.print()">IMPRIMIR / GUARDAR PDF</button>
  </div>
  <div class="sheet">
    {watermark}
    <header>
      <div class="brand">
        <img src="/logo_bellaarte2.png" alt="BELLAARTE BOUTIQUE" />
      </div>
      <div class="brand-copy">
        <h1>BELLAARTE BOUTIQUE</h1>
        <p>COMPROBANTE INTERNO NO FISCAL</p>
        <p>DOCUMENTO DE CONTROL COMERCIAL Y ADMINISTRATIVO</p>
      </div>
      <div class="doc-tag">
        <strong>{escape(receipt.tipo_comprobante)}</strong>
        <h2>{escape(receipt.codigo)}</h2>
      </div>
    </header>

    <section class="meta-grid">
      <div class="panel">
        <h3>DATOS DEL CLIENTE</h3>
        <div class="kv"><span>NOMBRE</span><span>{escape(receipt.client.full_name)}</span></div>
        <div class="kv"><span>CI / NIT</span><span>{escape(receipt.client.ci_nit)}</span></div>
        <div class="kv"><span>CELULAR</span><span>{escape(receipt.client.cellphone)}</span></div>
      </div>
      <div class="panel">
        <h3>CONTROL OPERATIVO</h3>
        <div class="kv"><span>FECHA / HORA</span><span>{receipt.fecha:%d/%m/%Y %H:%M}</span></div>
        <div class="kv"><span>REGISTRADO POR</span><span>{escape(receipt.registered_by.full_name)}</span></div>
        <div class="kv"><span>USUARIO</span><span>{escape(receipt.registered_by.username or 'SIN USUARIO')}</span></div>
        <div class="kv"><span>ORIGEN</span><span>{escape(receipt.origin_type)} #{receipt.origin_id}</span></div>
        <div class="kv"><span>ESTADO</span><span>{escape(receipt.estado.value.upper())}</span></div>
      </div>
    </section>

    <table>
      <thead>
        <tr>
          <th>CONCEPTO</th>
          <th class="right">CANTIDAD</th>
          <th class="right">PRECIO UNIDAD</th>
          <th class="right">DESCUENTO</th>
          <th class="right">SUBTOTAL</th>
        </tr>
      </thead>
      <tbody>{detail_rows}</tbody>
    </table>

    <section class="summary">
      <div class="metric"><span>SUBTOTAL</span><strong>Bs {receipt.subtotal:.2f}</strong></div>
      <div class="metric"><span>DESCUENTO</span><strong>Bs {receipt.descuento:.2f}</strong></div>
      <div class="metric"><span>TOTAL</span><strong>Bs {receipt.total:.2f}</strong></div>
      <div class="metric"><span>TOTAL MONEDA ORIGEN</span><strong>{escape(receipt.currency.simbolo or receipt.currency.codigo or '')} {receipt.total_moneda_original:.2f}</strong></div>
      <div class="metric"><span>TIPO DE CAMBIO USADO</span><strong>{receipt.tipo_cambio_usado:.4f}</strong></div>
      <div class="metric"><span>METODO DE PAGO</span><strong>{escape(receipt.payment_method.value.upper() if receipt.payment_method else 'SIN REGISTRO')}</strong></div>
      {saldo_block}
      {guarantee_block}
    </section>

    {f"<div class='panel'><h3>OBSERVACIONES</h3><ul>{observation_rows}</ul></div>" if observation_rows else ""}
    {state_note}

    <div class="legal">
      ESTE DOCUMENTO ES UN COMPROBANTE INTERNO NO FISCAL Y NO SUSTITUYE FACTURA.
    </div>
  </div>
</body>
</html>
"""
