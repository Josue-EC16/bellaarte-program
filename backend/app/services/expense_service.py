from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import object_session, Session, joinedload

from app.core.audit import register_audit_event
from app.models.account import Cuenta
from app.models.boutique_enums import EstadoCorteCajaEnum, EstadoEgresoEnum, TipoEgresoEnum, MetodoPagoEnum
from app.models.economy import CorteCaja, Egreso, MovimientoEconomico
from app.models.user import Usuario
from app.services.financial_source_service import money, _lock, lock_financial_source, recalculate_order_amounts, rollback_on_error
from app.services.economic_ledger_service import lock_active_cut, lock_cut, record_expense, record_expense_adjustment
from app.services.economy_query_service import apply_dates
from app.services.notification_service import sync_order_delivery_notifications_for_order
from app.schemas.economy import CashCutMiniSummary, ExpenseCreateRequest, ExpenseDetailResponse, ExpenseListItem, ExpenseAnnulRequest, ExpensePageResponse, UserMiniSummary


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _is_admin(account: Cuenta) -> bool:
    return account.rol.codigo == "ADMIN"


def _active_cut_for_cajero(db: Session, *, cajero_id: int) -> CorteCaja | None:
    return db.execute(
        select(CorteCaja)
        .options(joinedload(CorteCaja.cajero), joinedload(CorteCaja.admin))
        .where(CorteCaja.cajero_id == cajero_id, CorteCaja.estado == EstadoCorteCajaEnum.ABIERTO)
    ).scalar_one_or_none()


def _expense_cut_for_account(db: Session, *, account: Cuenta) -> CorteCaja | None:
    return lock_active_cut(db, account)


def _to_user_summary(user: Usuario | None) -> UserMiniSummary | None:
    if user is None:
        return None
    return UserMiniSummary(
        id=user.id,
        full_name=user.nombre_completo,
        username=user.cuenta.username if user.cuenta else None,
    )


def _to_cut_summary(cut: CorteCaja | None) -> CashCutMiniSummary | None:
    if cut is None:
        return None
    return CashCutMiniSummary(
        id=cut.id,
        estado=cut.estado,
        fecha_apertura=cut.fecha_apertura,
        fecha_cierre=cut.fecha_cierre,
        fondo_asignado=float(cut.fondo_asignado),
    )


def _to_expense_list_item(expense: Egreso) -> ExpenseListItem:
    session=object_session(expense)
    if session is not None:
        session.flush()
    adjusted=session.scalar(select(func.coalesce(func.sum(MovimientoEconomico.monto_bob),0)).where(
        MovimientoEconomico.egreso_id==expense.id,MovimientoEconomico.evento=="ajuste_egreso")) if session else 0
    return ExpenseListItem(
        id=expense.id,
        fecha=expense.fecha,
        tipo=expense.tipo,
        concepto=expense.concepto,
        cantidad=float(expense.cantidad),
        precio_unidad=float(expense.precio_unidad),
        monto=float(expense.monto),
        beneficiario=expense.beneficiario,
        estado=expense.estado,
        usuario=_to_user_summary(expense.usuario),
        corte=_to_cut_summary(expense.corte),
        tabla_referencia=expense.tabla_referencia,
        id_referencia=expense.id_referencia,
        metodo_pago=expense.metodo_pago, adjusted_amount_bob=float(adjusted or 0),
        net_amount_bob=float(expense.monto-(adjusted or 0)) if expense.estado==EstadoEgresoEnum.REGISTRADO else 0,
    )


def _to_expense_detail(expense: Egreso) -> ExpenseDetailResponse:
    session = object_session(expense)
    from app.models.economy import ConstanciaDevolucion
    certificate_id = session.scalar(select(ConstanciaDevolucion.id).where(ConstanciaDevolucion.egreso_id == expense.id)) if session else None
    base = _to_expense_list_item(expense).model_dump()
    return ExpenseDetailResponse(
        **base,constancia_id=certificate_id,
        observaciones_1=expense.observaciones_1,
        observaciones_2=expense.observaciones_2,
        fecha_cambio_estado=expense.fecha_cambio_estado,
        motivo_cambio_estado=expense.motivo_cambio_estado,
    )


def _get_expense_entity(db: Session, *, expense_id: int) -> Egreso:
    expense = db.execute(
        select(Egreso)
        .options(
            joinedload(Egreso.usuario).joinedload(Usuario.cuenta),
            joinedload(Egreso.corte).joinedload(CorteCaja.cajero).joinedload(Usuario.cuenta),
            joinedload(Egreso.corte).joinedload(CorteCaja.admin).joinedload(Usuario.cuenta),
        )
        .where(Egreso.id == expense_id)
    ).scalar_one_or_none()
    if expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Egreso no encontrado.")
    return expense


def create_expense_record(
    db: Session,
    *,
    account: Cuenta,
    tipo: TipoEgresoEnum,
    concepto: str,
    cantidad: float,
    precio_unidad: float,
    metodo_pago: MetodoPagoEnum,
    beneficiario: str | None,
    observaciones_1: str | None,
    observaciones_2: str | None,
    tabla_referencia: str | None = None,
    id_referencia: int | None = None,
) -> Egreso:
    cut = _expense_cut_for_account(db, account=account)
    quantity, unit_price = money(cantidad), money(precio_unidad)
    if quantity <= 0 or unit_price <= 0 or money(quantity * unit_price) <= 0:
        raise HTTPException(status_code=422, detail="Cantidad, precio e importe deben ser positivos a la precisión de almacenamiento.")
    expense = Egreso(
        usuario_id=account.usuario_id,
        corte_id=cut.id if cut else None,
        tipo=tipo,
        concepto=concepto,
        cantidad=quantity,
        precio_unidad=unit_price,
        metodo_pago=metodo_pago,
        beneficiario=beneficiario,
        observaciones_1=observaciones_1,
        observaciones_2=observaciones_2,
        estado=EstadoEgresoEnum.REGISTRADO,
        tabla_referencia=tabla_referencia,
        id_referencia=id_referencia,
    )
    db.add(expense)
    db.flush()
    db.refresh(expense)
    record_expense(db, account=account, cut=cut, expense=expense)
    return expense


@rollback_on_error
def create_expense(
    db: Session,
    *,
    payload: ExpenseCreateRequest,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
    commit: bool = True,
) -> ExpenseDetailResponse:
    if payload.tipo == TipoEgresoEnum.DEVOLUCION:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Las DEVOLUCIONES deben registrarse desde el flujo económico obligatorio de anulación.",
        )
    expense = create_expense_record(
        db,
        account=created_by,
        tipo=payload.tipo,
        concepto=payload.concepto,
        cantidad=payload.cantidad,
        precio_unidad=payload.precio_unidad,
        metodo_pago=payload.metodo_pago,
        beneficiario=payload.beneficiario,
        observaciones_1=payload.observaciones_1,
        observaciones_2=payload.observaciones_2,
    )
    register_audit_event(
        db,
        action="ECONOMY_EXPENSE_CREATED",
        description=f"SE REGISTRÓ EL EGRESO '{expense.id}' DE TIPO '{expense.tipo.value.upper()}'.",
        account=created_by,
        user=created_by.usuario,
        reference=str(expense.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if commit:
        db.commit()
    return get_expense_detail(db, expense_id=expense.id, account=created_by)


def list_expenses(
    db: Session,
    *,
    account: Cuenta,
    search: str | None = None,
    expense_type: TipoEgresoEnum | None = None,
    state: EstadoEgresoEnum | None = None,
    cut_id: int | None = None,
    date_from=None,
    date_to=None,
    page: int = 1,
    page_size: int = 25,
) -> ExpensePageResponse:
    if page < 1 or not 1 <= page_size <= 100:
        raise HTTPException(status_code=422, detail="La paginación exige página positiva y tamaño entre 1 y 100.")
    stmt = (
        select(Egreso)
        .options(
            joinedload(Egreso.usuario).joinedload(Usuario.cuenta),
            joinedload(Egreso.corte).joinedload(CorteCaja.cajero).joinedload(Usuario.cuenta),
            joinedload(Egreso.corte).joinedload(CorteCaja.admin).joinedload(Usuario.cuenta),
        )
        .order_by(Egreso.fecha.desc(), Egreso.id.desc())
    )
    if not _is_admin(account):
        stmt = stmt.join(Egreso.corte).where(CorteCaja.cajero_id == account.usuario_id)
        if cut_id is not None:
            stmt = stmt.where(Egreso.corte_id == cut_id)
    elif cut_id is not None:
        stmt = stmt.where(Egreso.corte_id == cut_id)
    if expense_type is not None:
        stmt = stmt.where(Egreso.tipo == expense_type)
    if state is not None:
        stmt = stmt.where(Egreso.estado == state)
    stmt = apply_dates(stmt, Egreso.fecha, date_from=date_from, date_to=date_to)
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.where(
            or_(
                func.upper(Egreso.concepto).like(term),
                func.upper(func.coalesce(Egreso.beneficiario, "")).like(term),
                func.upper(func.coalesce(Egreso.observaciones_1, "")).like(term),
            )
        )
    scope = stmt.with_only_columns(Egreso.id.label("expense_id"), Egreso.monto.label("amount"),
                                   Egreso.estado.label("state")).order_by(None).subquery()
    total, total_amount = db.execute(select(func.count(), func.coalesce(func.sum(case(
        (scope.c.state == EstadoEgresoEnum.REGISTRADO, scope.c.amount), else_=0)), 0)).select_from(scope)).one()
    corrections = db.execute(select(func.coalesce(func.sum(MovimientoEconomico.monto_bob), 0))
        .join(scope, scope.c.expense_id == MovimientoEconomico.egreso_id).where(
            MovimientoEconomico.evento == "ajuste_egreso",
            scope.c.state == EstadoEgresoEnum.REGISTRADO,
        )).scalar_one()
    items = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).unique().scalars().all()
    return ExpensePageResponse(items=[_to_expense_list_item(item) for item in items], total=total,
        page=page, page_size=page_size, total_bob=money(total_amount) - money(corrections))


def get_expense_detail(
    db: Session,
    *,
    expense_id: int,
    account: Cuenta,
) -> ExpenseDetailResponse:
    expense = _get_expense_entity(db, expense_id=expense_id)
    if not _is_admin(account):
        if expense.corte is None or expense.corte.cajero_id != account.usuario_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a ese egreso.")
    return _to_expense_detail(expense)


@rollback_on_error
def annul_expense(
    db: Session,
    *,
    expense_id: int,
    payload: ExpenseAnnulRequest,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
    commit: bool = True,
) -> ExpenseDetailResponse:
    # Discover identifiers first; acquire cut, business source and expense in that
    # order so closure, refund and correction cannot race each other.
    with db.no_autoflush:
        reference = db.execute(select(Egreso.corte_id, Egreso.tipo, Egreso.tabla_referencia,
                                      Egreso.id_referencia).where(Egreso.id == expense_id)).one_or_none()
    if reference is None:
        raise HTTPException(status_code=404, detail="Egreso no encontrado.")
    cut = None
    if _is_admin(changed_by):
        if reference.corte_id is not None:
            cut = lock_cut(db, reference.corte_id, require_open=False)
    else:
        cut = lock_active_cut(db, changed_by)
        if reference.corte_id != cut.id:
            raise HTTPException(status_code=403, detail="Solo puedes corregir egresos de tu corte activo.")
    source = None
    if reference.tipo == TipoEgresoEnum.DEVOLUCION:
        source = lock_financial_source(db, origin_type=reference.tabla_referencia.upper(),
                                      origin_id=reference.id_referencia, account=changed_by, cut=cut)
    _lock(db, Egreso, expense_id)
    expense = _get_expense_entity(db, expense_id=expense_id)
    if expense.estado != EstadoEgresoEnum.REGISTRADO:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo puedes anular egresos registrados.")
    historical = cut is not None and cut.estado != EstadoCorteCajaEnum.ABIERTO
    actual_adjustment = historical or payload.adjustment_method is not None
    if actual_adjustment:
        if not _is_admin(changed_by):
            raise HTTPException(status_code=403, detail="Solo ADMIN registra ajustes económicos reales o históricos.")
        if payload.adjustment_method is None:
            raise HTTPException(status_code=422, detail="El ajuste exige declarar el medio real de restitución.")
        adjustment_cut = None if historical else cut
        method = payload.adjustment_method
    else:
        if not payload.money_did_not_leave:
            raise HTTPException(status_code=409, detail="Confirma que el dinero no salió. Una devolución real exige un ajuste ADMIN.")
        if expense.metodo_pago is None:
            raise HTTPException(status_code=409, detail="El egreso legado no tiene medio verificable; requiere ajuste ADMIN explícito.")
        adjustment_cut = cut
        method = expense.metodo_pago
    record_expense_adjustment(db, account=changed_by, cut=adjustment_cut, expense=expense,
                              payment_method=method, reason=payload.motivo)
    if not actual_adjustment:
        expense.estado = EstadoEgresoEnum.ANULADO
        expense.fecha_cambio_estado = _utc_now()
        expense.motivo_cambio_estado = payload.motivo
    if source is not None and reference.tabla_referencia.upper() == "PAGO_PEDIDO":
        recalculate_order_amounts(db, source.pedido)
        sync_order_delivery_notifications_for_order(db, order_id=source.pedido_id)
    register_audit_event(
        db,
        action="ECONOMY_EXPENSE_ADJUSTED" if actual_adjustment else "ECONOMY_EXPENSE_ANNULLED",
        description=f"SE REGISTRÓ {'AJUSTE ECONÓMICO' if actual_adjustment else 'ANULACIÓN SIN SALIDA DE DINERO'} DEL EGRESO '{expense.id}'.",
        account=changed_by,
        user=changed_by.usuario,
        reference=str(expense.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if commit:
        db.commit()
    return get_expense_detail(db, expense_id=expense.id, account=changed_by)
