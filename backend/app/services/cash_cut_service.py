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
    CashCutCloseRequest, CashCutPageResponse, CashCutOwnHistoryPageResponse,
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
from app.services.economic_ledger_service import lock_cut, record_fund, get_cut_balances
from app.services.economy_query_service import apply_dates


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
    from app.services.expense_service import _to_expense_list_item as serialize
    return serialize(expense)


def _expense_net(expense):
    item=_to_expense_list_item(expense)
    return item.monto-item.adjusted_amount_bob if item.estado==EstadoEgresoEnum.REGISTRADO else 0


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
    return round(sum(_expense_net(expense) for expense in expenses), 2)


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
    filters = {"cut_id": cut.id} if cut.control_version else {
        "start_at":cut.fecha_apertura,"end_at":cut.fecha_cierre,"user_id":cut.cajero_id}
    income_rows = collect_income_rows_for_period(db, **filters)
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
    if cut.control_version:
        balances = get_cut_balances(db,cut.id)
        ingresos_total = float(balances["commercial_income_bob"])
        egresos_total = float(balances["expenses_bob"])
        resultado = float(balances["operational_total_bob"])
    return income_rows, expenses, ingresos_total, egresos_total, resultado


def _to_cut_list_item(db: Session, *, cut: CorteCaja) -> CashCutListItem:
    if cut.cierre_snapshot:
        return CashCutListItem.model_validate(cut.cierre_snapshot)
    _, _, ingresos_total, egresos_total, resultado = _build_cut_metrics(db, cut=cut)
    balances = get_cut_balances(db,cut.id) if cut.control_version else {}
    return CashCutListItem(
        control_version=cut.control_version, certified=False,
        efectivo_esperado=balances.get("expected_cash",{}),
        efectivo_libre_bob=balances.get("free_cash_bob"),garantias_reservadas_bob=balances.get("reserved_cash_bob"),
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
    commit: bool = True,
) -> CashCutDetailResponse:
    if not _is_admin(opened_by):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el ADMIN puede abrir cortes de caja.")
    if payload.cajero_id == opened_by.usuario_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El ADMIN no puede abrir un corte a su propio nombre como cajero.")
    cajero = _get_cajero_user(db, cajero_id=payload.cajero_id)
    # Serialize simultaneous openings even when there is no cut row yet.
    db.execute(select(Usuario.id).where(Usuario.id == cajero.id).with_for_update()).scalar_one()
    existing = _get_active_cut_for_cajero(db, cajero_id=cajero.id)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El cajero seleccionado ya tiene un corte de caja abierto.")

    cut = CorteCaja(
        control_version=1,
        cajero_id=cajero.id,
        admin_id=opened_by.usuario_id,
        fondo_asignado=payload.fondo_asignado,
        observaciones_apertura=payload.observaciones_apertura,
        estado=EstadoCorteCajaEnum.ABIERTO,
    )
    db.add(cut)
    db.flush()
    record_fund(db,cut,opened_by.usuario_id)
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
    if commit:
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
    commit: bool = True,
) -> CashCutDetailResponse:
    if not _is_admin(closed_by):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el ADMIN puede cerrar cortes de caja.")
    cut = lock_cut(db,cut_id,require_open=True)
    if not cut.control_version:
        if not payload.cierre_legado or not payload.observaciones_cierre:
            raise HTTPException(409,"El corte legado requiere cierre explícito y observación; sus cifras no se certifican.")
        if payload.efectivo_recibido:
            raise HTTPException(422,"No se certifica efectivo histórico sin trazabilidad de medios de pago.")
        snapshot = None
    else:
        if payload.cierre_legado:
            raise HTTPException(422,"Este corte tiene control económico y requiere conteo de efectivo.")
        balances = get_cut_balances(db,cut.id)
        expected = {code:Decimal(str(amount)) for code,amount in balances["expected_cash"].items()}
        received = payload.efectivo_recibido
        if set(expected) != set(received):
            raise HTTPException(422,"Debes declarar efectivo recibido para cada moneda física esperada, incluido BOB.")
        differences = {code:received[code]-amount for code,amount in expected.items()}
        if any(differences.values()) and (payload.estado != EstadoCorteCajaEnum.CERRADO_OBSERVADO or not payload.observaciones_cierre):
            raise HTTPException(422,"Las diferencias de efectivo exigen cierre observado y explicación.")
        snapshot = get_cash_cut_detail(db,cut_id=cut.id,account=closed_by).model_dump(mode="json")
        snapshot.update(certified=True,efectivo_recibido={k:float(v) for k,v in received.items()},
                        diferencias_efectivo={k:float(v) for k,v in differences.items()})
    cut.estado = payload.estado
    cut.fecha_cierre = _utc_now()
    cut.observaciones_cierre = payload.observaciones_cierre
    if snapshot is not None:
        snapshot.update(estado=cut.estado.value,fecha_cierre=cut.fecha_cierre.isoformat(),
                        observaciones_cierre=cut.observaciones_cierre)
        cut.cierre_snapshot = snapshot
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
    if commit:
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
    page=1,page_size=25,
) -> CashCutPageResponse:
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
    stmt = apply_dates(stmt,CorteCaja.fecha_apertura,date_from=date_from,date_to=date_to)
    if page<1 or not 1<=page_size<=100:
        raise HTTPException(422,"La paginación exige página positiva y tamaño entre 1 y 100.")
    scope=stmt.with_only_columns(CorteCaja.id.label("id"),CorteCaja.estado.label("state")).order_by(None).subquery()
    count,opened,closed,observed=db.execute(select(func.count(),
        func.count().filter(scope.c.state==EstadoCorteCajaEnum.ABIERTO),
        func.count().filter(scope.c.state==EstadoCorteCajaEnum.CERRADO),
        func.count().filter(scope.c.state==EstadoCorteCajaEnum.CERRADO_OBSERVADO)).select_from(scope)).one()
    cuts=db.execute(stmt.offset((page-1)*page_size).limit(page_size)).unique().scalars().all()
    return CashCutPageResponse(items=[_to_cut_list_item(db,cut=cut) for cut in cuts],total=count,
        page=page,page_size=page_size,open_count=opened,closed_count=closed,observed_count=observed)


def get_cash_cut_detail(
    db: Session,
    *,
    cut_id: int,
    account: Cuenta,
) -> CashCutDetailResponse:
    if not _is_admin(account):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el ADMIN puede ver el detalle global del corte de caja.")
    cut = _get_cut_entity(db, cut_id=cut_id)
    if cut.cierre_snapshot:
        return CashCutDetailResponse.model_validate(cut.cierre_snapshot)
    income_rows, expenses, ingresos_total, egresos_total, resultado = _build_cut_metrics(db, cut=cut)
    balances = get_cut_balances(db,cut.id) if cut.control_version else {}
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
        key_getter=lambda expense: (expense.tipo.value.upper(), _expense_net(expense), None, None),
    )
    return CashCutDetailResponse(
        control_version=cut.control_version,certified=False,
        efectivo_esperado=balances.get("expected_cash",{}),
        efectivo_libre_bob=balances.get("free_cash_bob"),garantias_reservadas_bob=balances.get("reserved_cash_bob"),
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
    page: int | None = None,page_size: int = 25,
) -> list[CashCutOwnHistoryItem]:
    history_stmt = (
        select(CorteCaja)
        .options(
            joinedload(CorteCaja.cajero).joinedload(Usuario.cuenta),
            joinedload(CorteCaja.admin).joinedload(Usuario.cuenta),
        )
        .where(CorteCaja.cajero_id == account.usuario_id, CorteCaja.estado != EstadoCorteCajaEnum.ABIERTO)
        .order_by(CorteCaja.fecha_apertura.desc(), CorteCaja.id.desc())
    )
    if page is not None:
        history_stmt=history_stmt.offset((page-1)*page_size).limit(page_size)
    cuts=db.execute(history_stmt).unique().scalars().all()
    items: list[CashCutOwnHistoryItem] = []
    for cut in cuts:
        item = _to_cut_list_item(db,cut=cut)
        if cut.cierre_snapshot:
            source_buckets = cut.cierre_snapshot.get("ingresos_por_fuente",[])
            by_source = {b["label"].replace(" ","_"):b["total_bob"] for b in source_buckets}
            by_method = {b["label"]:b["total_bob"] for b in cut.cierre_snapshot.get("ingresos_por_metodo_pago",[])}
        else:
            income_rows = collect_income_rows_for_period(db,start_at=cut.fecha_apertura,end_at=cut.fecha_cierre,user_id=cut.cajero_id)
            by_source, by_method = {}, {}
            for income in income_rows:
                by_source[income.source_type] = by_source.get(income.source_type,0)+income.monto_bob
                by_method[income.metodo_pago] = by_method.get(income.metodo_pago,0)+income.monto_bob
        egresos_total = item.egresos_total_bob
        items.append(
            CashCutOwnHistoryItem(
                control_version=cut.control_version,certified=bool(cut.cierre_snapshot),
                id=cut.id,
                fecha_apertura=cut.fecha_apertura,
                fecha_cierre=cut.fecha_cierre,
                fondo_asignado=_to_float(cut.fondo_asignado),
                estado=cut.estado,
                ingresos_display=f"{item.ingresos_total_bob:.2f}",
                ventas_display=f"{by_source.get('VENTA_BOUTIQUE',0):.2f}",
                pagos_display=f"{by_source.get('PAGO_PEDIDO',0):.2f}",
                fletes_display=f"{by_source.get('SALIDA_FLETE',0):.2f}",
                metodos_display="; ".join(f"{key}: {value:.2f}" for key,value in sorted(by_method.items())),
                resultado_display=f"{item.resultado_bob:.2f}",
                egresos_total_bob=egresos_total,
                has_observation=bool(cut.observaciones_cierre),
            )
        )
    return items


def get_my_cut_history_page(db,*,account,page=1,page_size=25):
    if page<1 or not 1<=page_size<=100:
        raise HTTPException(422,"La paginación exige página positiva y tamaño entre 1 y 100.")
    # The own history serializer contains no ADMIN notes or other users' cuts.
    total=db.scalar(select(func.count()).select_from(CorteCaja).where(CorteCaja.cajero_id==account.usuario_id,
        CorteCaja.estado!=EstadoCorteCajaEnum.ABIERTO))
    items=get_my_cut_history(db,account=account,page=page,page_size=page_size)
    return CashCutOwnHistoryPageResponse(items=items,total=total,page=page,page_size=page_size)
