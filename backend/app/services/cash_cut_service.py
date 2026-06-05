from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.audit import register_audit_event
from app.models.account import Cuenta
from app.models.boutique_enums import EstadoCorteCajaEnum, EstadoEgresoEnum
from app.models.economy import CorteCaja, Egreso
from app.models.user import Usuario
from app.schemas.economy import (
    CashCutCloseRequest,
    CashCutCreateRequest,
    CashCutDetailResponse,
    CashCutListItem,
    CashCutMiniSummary,
    CashCutOwnActiveResponse,
    CashCutOwnHistoryItem,
    ExpenseListItem,
    NamedAmountBucket,
    UserMiniSummary,
)
from app.services.income_service import collect_income_rows_for_period


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _is_admin(account: Cuenta) -> bool:
    return account.rol.codigo == "ADMIN"


def _to_user_summary(user: Usuario) -> UserMiniSummary:
    return UserMiniSummary(
        id=user.id,
        full_name=user.nombre_completo,
        username=user.cuenta.username if user.cuenta else None,
    )


def _to_cut_mini_summary(cut: CorteCaja) -> CashCutMiniSummary:
    return CashCutMiniSummary(
        id=cut.id,
        estado=cut.estado,
        fecha_apertura=cut.fecha_apertura,
        fecha_cierre=cut.fecha_cierre,
        fondo_asignado=_to_float(cut.fondo_asignado),
    )


def _to_expense_list_item(expense: Egreso) -> ExpenseListItem:
    return ExpenseListItem(
        id=expense.id,
        fecha=expense.fecha,
        tipo=expense.tipo,
        concepto=expense.concepto,
        cantidad=_to_float(expense.cantidad),
        precio_unidad=_to_float(expense.precio_unidad),
        monto=_to_float(expense.monto),
        beneficiario=expense.beneficiario,
        estado=expense.estado,
        usuario=_to_user_summary(expense.usuario) if expense.usuario else None,
        corte=_to_cut_mini_summary(expense.corte) if expense.corte else None,
        tabla_referencia=expense.tabla_referencia,
        id_referencia=expense.id_referencia,
    )


def _get_cajero_user(db: Session, *, cajero_id: int) -> Usuario:
    user = db.execute(
        select(Usuario)
        .options(joinedload(Usuario.cuenta).joinedload(Cuenta.rol))
        .where(Usuario.id == cajero_id)
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró el cajero seleccionado.")
    if not user.activo:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El cajero seleccionado está inactivo.")
    if user.cuenta is None or not user.cuenta.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La cuenta del cajero seleccionado está inactiva.")
    if user.cuenta.rol.codigo != "CAJA":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo puedes abrir cortes para usuarios con rol CAJA.")
    return user


def _get_cut_entity(db: Session, *, cut_id: int) -> CorteCaja:
    cut = db.execute(
        select(CorteCaja)
        .options(
            joinedload(CorteCaja.cajero).joinedload(Usuario.cuenta),
            joinedload(CorteCaja.admin).joinedload(Usuario.cuenta),
            joinedload(CorteCaja.egresos).joinedload(Egreso.usuario).joinedload(Usuario.cuenta),
        )
        .where(CorteCaja.id == cut_id)
    ).unique().scalar_one_or_none()
    if cut is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Corte de caja no encontrado.")
    return cut


def _get_active_cut_for_cajero(db: Session, *, cajero_id: int) -> CorteCaja | None:
    return db.execute(
        select(CorteCaja)
        .options(
            joinedload(CorteCaja.cajero).joinedload(Usuario.cuenta),
            joinedload(CorteCaja.admin).joinedload(Usuario.cuenta),
        )
        .where(CorteCaja.cajero_id == cajero_id, CorteCaja.estado == EstadoCorteCajaEnum.ABIERTO)
    ).scalar_one_or_none()


def _sum_registered_expenses(expenses: list[Egreso]) -> float:
    return round(sum(_to_float(expense.monto) for expense in expenses if expense.estado == EstadoEgresoEnum.REGISTRADO), 2)


def _sum_buckets(rows, *, key_getter) -> list[NamedAmountBucket]:
    totals: dict[str, float] = {}
    extra: dict[str, tuple[str | None, str | None]] = {}
    for row in rows:
        label, amount, currency_code, symbol = key_getter(row)
        totals[label] = round(totals.get(label, 0) + amount, 2)
        extra[label] = (currency_code, symbol)
    return [
        NamedAmountBucket(
            label=label,
            total_bob=total,
            currency_code=extra[label][0],
            symbol=extra[label][1],
        )
        for label, total in sorted(totals.items(), key=lambda item: item[0])
    ]


def _build_cut_metrics(db: Session, *, cut: CorteCaja) -> tuple[list, list[Egreso], float, float, float]:
    income_rows = collect_income_rows_for_period(
        db,
        start_at=cut.fecha_apertura,
        end_at=cut.fecha_cierre,
        user_id=cut.cajero_id,
    )
    expenses = db.execute(
        select(Egreso)
        .options(
            joinedload(Egreso.usuario).joinedload(Usuario.cuenta),
            joinedload(Egreso.corte).joinedload(CorteCaja.cajero).joinedload(Usuario.cuenta),
        )
        .where(Egreso.corte_id == cut.id)
        .order_by(Egreso.fecha.desc(), Egreso.id.desc())
    ).unique().scalars().all()
    ingresos_total = round(sum(item.monto_bob for item in income_rows), 2)
    egresos_total = _sum_registered_expenses(expenses)
    resultado = round(ingresos_total + _to_float(cut.fondo_asignado) - egresos_total, 2)
    return income_rows, expenses, ingresos_total, egresos_total, resultado


def _to_cut_list_item(db: Session, *, cut: CorteCaja) -> CashCutListItem:
    _, _, ingresos_total, egresos_total, resultado = _build_cut_metrics(db, cut=cut)
    return CashCutListItem(
        id=cut.id,
        cajero=_to_user_summary(cut.cajero),
        admin=_to_user_summary(cut.admin),
        fecha_apertura=cut.fecha_apertura,
        fecha_cierre=cut.fecha_cierre,
        fondo_asignado=_to_float(cut.fondo_asignado),
        estado=cut.estado,
        ingresos_total_bob=ingresos_total,
        egresos_total_bob=egresos_total,
        resultado_bob=resultado,
    )


def open_cash_cut(
    db: Session,
    *,
    payload: CashCutCreateRequest,
    opened_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> CashCutDetailResponse:
    if not _is_admin(opened_by):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el ADMIN puede abrir cortes de caja.")
    if payload.cajero_id == opened_by.usuario_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El ADMIN no puede abrir un corte a su propio nombre como cajero.")
    cajero = _get_cajero_user(db, cajero_id=payload.cajero_id)
    existing = _get_active_cut_for_cajero(db, cajero_id=cajero.id)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El cajero seleccionado ya tiene un corte de caja abierto.")

    cut = CorteCaja(
        cajero_id=cajero.id,
        admin_id=opened_by.usuario_id,
        fondo_asignado=payload.fondo_asignado,
        observaciones_apertura=payload.observaciones_apertura,
        estado=EstadoCorteCajaEnum.ABIERTO,
    )
    db.add(cut)
    db.flush()
    register_audit_event(
        db,
        action="CASH_CUT_OPENED",
        description=f"SE ABRIÓ EL CORTE DE CAJA '{cut.id}' PARA '{cajero.nombre_completo}'.",
        account=opened_by,
        user=opened_by.usuario,
        reference=str(cut.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_cash_cut_detail(db, cut_id=cut.id, account=opened_by)


def close_cash_cut(
    db: Session,
    *,
    cut_id: int,
    payload: CashCutCloseRequest,
    closed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> CashCutDetailResponse:
    if not _is_admin(closed_by):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el ADMIN puede cerrar cortes de caja.")
    cut = _get_cut_entity(db, cut_id=cut_id)
    if cut.estado != EstadoCorteCajaEnum.ABIERTO:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo puedes cerrar cortes de caja abiertos.")

    cut.estado = payload.estado
    cut.fecha_cierre = _utc_now()
    cut.observaciones_cierre = payload.observaciones_cierre
    register_audit_event(
        db,
        action="CASH_CUT_CLOSED",
        description=f"SE CERRÓ EL CORTE DE CAJA '{cut.id}' CON ESTADO '{payload.estado.value.upper()}'.",
        account=closed_by,
        user=closed_by.usuario,
        reference=str(cut.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_cash_cut_detail(db, cut_id=cut.id, account=closed_by)


def list_cash_cuts(
    db: Session,
    *,
    account: Cuenta,
    cajero_id: int | None = None,
    state: EstadoCorteCajaEnum | None = None,
    date_from=None,
    date_to=None,
) -> list[CashCutListItem]:
    if not _is_admin(account):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el ADMIN puede listar cortes de caja globales.")
    stmt = (
        select(CorteCaja)
        .options(
            joinedload(CorteCaja.cajero).joinedload(Usuario.cuenta),
            joinedload(CorteCaja.admin).joinedload(Usuario.cuenta),
        )
        .order_by(CorteCaja.fecha_apertura.desc(), CorteCaja.id.desc())
    )
    if cajero_id is not None:
        stmt = stmt.where(CorteCaja.cajero_id == cajero_id)
    if state is not None:
        stmt = stmt.where(CorteCaja.estado == state)
    if date_from is not None:
        stmt = stmt.where(func.date(CorteCaja.fecha_apertura) >= date_from)
    if date_to is not None:
        stmt = stmt.where(func.date(CorteCaja.fecha_apertura) <= date_to)
    return [_to_cut_list_item(db, cut=cut) for cut in db.execute(stmt).unique().scalars().all()]


def get_cash_cut_detail(
    db: Session,
    *,
    cut_id: int,
    account: Cuenta,
) -> CashCutDetailResponse:
    if not _is_admin(account):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el ADMIN puede ver el detalle global del corte de caja.")
    cut = _get_cut_entity(db, cut_id=cut_id)
    income_rows, expenses, ingresos_total, egresos_total, resultado = _build_cut_metrics(db, cut=cut)
    ingresos_por_fuente = _sum_buckets(
        income_rows,
        key_getter=lambda row: (row.source_type.replace("_", " "), row.monto_bob, None, None),
    )
    ingresos_por_metodo = _sum_buckets(
        income_rows,
        key_getter=lambda row: (row.metodo_pago or "SIN METODO", row.monto_bob, None, None),
    )
    ingresos_por_moneda = _sum_buckets(
        income_rows,
        key_getter=lambda row: (row.moneda or "SIN MONEDA", row.monto_bob, row.moneda, row.simbolo_moneda),
    )
    egresos_por_tipo = _sum_buckets(
        [expense for expense in expenses if expense.estado == EstadoEgresoEnum.REGISTRADO],
        key_getter=lambda expense: (expense.tipo.value.upper(), _to_float(expense.monto), None, None),
    )
    return CashCutDetailResponse(
        id=cut.id,
        cajero=_to_user_summary(cut.cajero),
        admin=_to_user_summary(cut.admin),
        fecha_apertura=cut.fecha_apertura,
        fecha_cierre=cut.fecha_cierre,
        fondo_asignado=_to_float(cut.fondo_asignado),
        estado=cut.estado,
        ingresos_total_bob=ingresos_total,
        egresos_total_bob=egresos_total,
        resultado_bob=resultado,
        observaciones_apertura=cut.observaciones_apertura,
        observaciones_cierre=cut.observaciones_cierre,
        ingresos_por_fuente=ingresos_por_fuente,
        ingresos_por_metodo_pago=ingresos_por_metodo,
        ingresos_por_moneda=ingresos_por_moneda,
        egresos_por_tipo=egresos_por_tipo,
        egresos=[_to_expense_list_item(expense) for expense in expenses],
    )


def get_my_active_cut(
    db: Session,
    *,
    account: Cuenta,
) -> CashCutOwnActiveResponse:
    cut = _get_active_cut_for_cajero(db, cajero_id=account.usuario_id)
    if cut is None:
        return CashCutOwnActiveResponse(has_active_cut=False, cut=None)
    return CashCutOwnActiveResponse(
        has_active_cut=True,
        cut=_to_cut_list_item(db, cut=cut),
    )


def get_my_cut_history(
    db: Session,
    *,
    account: Cuenta,
) -> list[CashCutOwnHistoryItem]:
    cuts = db.execute(
        select(CorteCaja)
        .options(
            joinedload(CorteCaja.cajero).joinedload(Usuario.cuenta),
            joinedload(CorteCaja.admin).joinedload(Usuario.cuenta),
        )
        .where(CorteCaja.cajero_id == account.usuario_id, CorteCaja.estado != EstadoCorteCajaEnum.ABIERTO)
        .order_by(CorteCaja.fecha_apertura.desc(), CorteCaja.id.desc())
    ).unique().scalars().all()
    items: list[CashCutOwnHistoryItem] = []
    for cut in cuts:
        income_rows, expenses, _, egresos_total, _ = _build_cut_metrics(db, cut=cut)
        by_source: dict[str, float] = {}
        by_method: dict[str, float] = {}
        for income in income_rows:
            by_source[income.source_type] = round(by_source.get(income.source_type, 0) + income.monto_bob, 2)
            by_method[income.metodo_pago or "SIN METODO"] = round(by_method.get(income.metodo_pago or "SIN METODO", 0) + income.monto_bob, 2)
        items.append(
            CashCutOwnHistoryItem(
                id=cut.id,
                fecha_apertura=cut.fecha_apertura,
                fecha_cierre=cut.fecha_cierre,
                fondo_asignado=_to_float(cut.fondo_asignado),
                estado=cut.estado,
                ingresos_display="***",
                ventas_display="***" if by_source.get("VENTA_BOUTIQUE") else "0",
                pagos_display="***" if by_source.get("PAGO_PEDIDO") else "0",
                fletes_display="***" if by_source.get("SALIDA_FLETE") else "0",
                metodos_display="***" if by_method else "0",
                resultado_display="***",
                egresos_total_bob=egresos_total,
                has_observation=bool(cut.observaciones_cierre),
            )
        )
    return items
