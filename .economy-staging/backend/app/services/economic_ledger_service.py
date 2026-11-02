"""Cut/cash attribution without commits or commercial-income duplication.

Coordinators lock: idempotency -> cut -> parent/item -> source, before mutation.
Every helper participates in that same transaction; no implicit commits occur.
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import case, func, select

from app.models.boutique_enums import EstadoCorteCajaEnum, MetodoPagoEnum
from app.models.economy import CorteCaja, MovimientoEconomico


ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def money(value) -> Decimal:
    try:
        result = Decimal(str(value))
        if not result.is_finite():
            raise ValueError("Non-finite money")
        result = result.quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise HTTPException(status_code=422, detail="Importe monetario inválido.") from None
    if abs(result) >= Decimal("10000000000"):
        raise HTTPException(status_code=422, detail="El importe supera la precisión admitida.")
    return result


def _is_admin(account) -> bool:
    return account.rol.codigo == "ADMIN"


def _method(value) -> MetodoPagoEnum:
    try:
        return MetodoPagoEnum(value)
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="Método de pago inválido.") from None


def lock_cut(db, cut_id: int, *, require_open: bool = True) -> CorteCaja:
    with db.no_autoflush:
        cut = db.scalar(select(CorteCaja).where(CorteCaja.id == cut_id).with_for_update().execution_options(populate_existing=True))
    if cut is None:
        raise HTTPException(status_code=404, detail="Corte de caja no encontrado.")
    if require_open and cut.estado != EstadoCorteCajaEnum.ABIERTO:
        raise HTTPException(status_code=409, detail="El corte de caja ya está cerrado.")
    return cut


def lock_active_cut(db, account, *, required: bool = True) -> CorteCaja | None:
    """ADMIN acts outside cashier cuts; a cashier must lock their own v1 cut."""
    if _is_admin(account):
        return None
    if account.rol.codigo != "CAJA":
        if not required:
            return None
        raise HTTPException(status_code=403, detail="La operación requiere ADMIN o CAJA.")
    with db.no_autoflush:
        cut = db.scalar(select(CorteCaja).where(
            CorteCaja.cajero_id == account.usuario_id,
            CorteCaja.estado == EstadoCorteCajaEnum.ABIERTO,
        ).with_for_update().execution_options(populate_existing=True))
    if cut is None:
        if not required:
            return None
        raise HTTPException(status_code=409, detail="Debe tener un corte de caja abierto para registrar la operación.")
    if cut.control_version != 1:
        raise HTTPException(status_code=409, detail="El corte legado debe cerrarse explícitamente antes de registrar movimientos controlados.")
    return cut


def assert_source_cut(account, cut: CorteCaja | None, source) -> None:
    if _is_admin(account):
        return
    if cut is None or account.rol.codigo != "CAJA" or source.usuario_id != account.usuario_id or source.corte_id != cut.id:
        raise HTTPException(status_code=403, detail="Solo puede operar sobre sus propios registros del corte abierto actual.")


def _validate_cut(account, cut):
    if cut is None:
        if not _is_admin(account):
            raise HTTPException(status_code=409, detail="La operación requiere su corte abierto.")
        return
    if cut.estado != EstadoCorteCajaEnum.ABIERTO or cut.control_version != 1:
        raise HTTPException(status_code=409, detail="El corte no admite movimientos controlados.")
    if not _is_admin(account) and cut.cajero_id != account.usuario_id:
        raise HTTPException(status_code=403, detail="El corte pertenece a otro cajero.")


def _append(db, *, account, cut, event, direction, amount, original=None, currency="BOB", method, origin_type, origin_id, expense_id=None, output_id=None, sequence=1, reason=None):
    _validate_cut(account, cut)
    amount = money(amount)
    original = money(original if original is not None else amount)
    if amount <= ZERO or original <= ZERO:
        raise HTTPException(status_code=422, detail="El importe debe ser mayor a cero después del redondeo monetario.")
    row = MovimientoEconomico(
        corte_id=cut.id if cut is not None else None, actor_id=account.usuario_id,
        evento=event, direccion=direction, monto_bob=amount, monto_original=original,
        moneda_codigo=currency.strip().upper(), metodo_pago=_method(method),
        origen_tipo=origin_type, origen_id=origin_id, egreso_id=expense_id,
        salida_flete_id=output_id, secuencia=sequence, motivo=reason,
    )
    db.add(row)
    return row


def record_fund(db, cut: CorteCaja, actor_id: int):
    """Initial operational advance, never commercial income; zero is allowed."""
    amount = money(cut.fondo_asignado)
    if amount < ZERO or cut.control_version != 1 or cut.estado != EstadoCorteCajaEnum.ABIERTO:
        raise HTTPException(status_code=409, detail="Fondo o corte inválido.")
    if amount == ZERO:
        return None
    row = MovimientoEconomico(corte_id=cut.id, actor_id=actor_id, evento="fondo", direccion=1,
        monto_bob=amount, monto_original=amount, moneda_codigo="BOB", metodo_pago=MetodoPagoEnum.EFECTIVO,
        origen_tipo="corte_caja", origen_id=cut.id, secuencia=1)
    db.add(row)
    return row


def record_income(db, *, account, cut, origin_type: str, source, amount_bob, amount_original, currency_code: str, payment_method):
    if origin_type not in {"venta_boutique", "pago_pedido", "salida_flete"}:
        raise ValueError("Invalid commercial income source")
    _validate_cut(account, cut)
    source.corte_id = cut.id if cut is not None else None
    return _append(db, account=account, cut=cut, event="ingreso", direction=1, amount=amount_bob,
        original=amount_original, currency=currency_code, method=payment_method,
        origin_type=origin_type, origin_id=source.id,
        output_id=source.id if origin_type == "salida_flete" else None)


def get_cut_balances(db, cut_id: int) -> dict:
    """Aggregate only attributed rows; no time-window guessing for controlled cuts."""
    # The application Session disables autoflush. Coordinators already hold the
    # cut/source locks here; include pending movements before reading balances.
    db.flush()
    rows = db.execute(select(
        MovimientoEconomico.evento, MovimientoEconomico.moneda_codigo, MovimientoEconomico.metodo_pago,
        func.sum(MovimientoEconomico.monto_bob * MovimientoEconomico.direccion),
        func.sum(MovimientoEconomico.monto_original * MovimientoEconomico.direccion),
    ).where(MovimientoEconomico.corte_id == cut_id).group_by(
        MovimientoEconomico.evento, MovimientoEconomico.moneda_codigo, MovimientoEconomico.metodo_pago,
    )).all()
    cash = {}
    funds = incomes = expenses = ZERO
    for event, currency, method, amount, original in rows:
        amount, original = money(amount), money(original)
        if method == MetodoPagoEnum.EFECTIVO:
            cash[currency] = money(cash.get(currency, ZERO) + original)
        if event == "fondo":
            funds += amount
        elif event == "ingreso":
            incomes += amount
        elif event in {"egreso", "ajuste_egreso"}:
            expenses -= amount
    # A cash guarantee remains reserved even after ADMIN retention. Returning it
    # through any method discharges its liability, without inventing cash.
    custody_sources=select(MovimientoEconomico.salida_flete_id).where(
        MovimientoEconomico.corte_id==cut_id,MovimientoEconomico.evento=="garantia_recibida")
    custody = db.execute(select(
        MovimientoEconomico.salida_flete_id,
        func.sum(case((
            (MovimientoEconomico.evento == "garantia_recibida") & (MovimientoEconomico.metodo_pago == MetodoPagoEnum.EFECTIVO) & (MovimientoEconomico.corte_id == cut_id),
            MovimientoEconomico.monto_bob), else_=0)),
        func.sum(case((MovimientoEconomico.evento == "garantia_devuelta", MovimientoEconomico.monto_bob), else_=0)),
    ).where(MovimientoEconomico.salida_flete_id.in_(custody_sources), MovimientoEconomico.evento.in_(["garantia_recibida", "garantia_devuelta", "garantia_retenida"]))
        .group_by(MovimientoEconomico.salida_flete_id)).all()
    reserved = sum((max(ZERO, money(received) - money(returned)) for _, received, returned in custody), ZERO)
    cash.setdefault("BOB", ZERO)
    physical_bob = cash["BOB"]
    return {
        "expected_cash": {currency: money(amount) for currency, amount in cash.items()},
        "free_cash_bob": money(physical_bob - reserved), "reserved_cash_bob": money(reserved),
        "commercial_income_bob": money(incomes), "expenses_bob": money(expenses),
        "fund_bob": money(funds), "operational_total_bob": money(funds + incomes - expenses),
    }


def _assert_cash(db, cut, amount, method, *, release_reserved=ZERO):
    if cut is None or _method(method) != MetodoPagoEnum.EFECTIVO:
        return
    balances = get_cut_balances(db, cut.id)
    available = money(balances["free_cash_bob"] + release_reserved)
    if money(amount) > available:
        raise HTTPException(status_code=409, detail="Efectivo BOB libre insuficiente; no se pueden usar cobros electrónicos, moneda extranjera ni garantías reservadas.")


def record_expense(db, *, account, cut, expense):
    _validate_cut(account, cut)
    if expense.corte_id != (cut.id if cut else None):
        raise ValueError("Expense attribution does not match locked cut")
    if expense.metodo_pago is None:
        raise HTTPException(status_code=422, detail="Indique el método real del egreso.")
    _assert_cash(db, cut, expense.monto, expense.metodo_pago)
    return _append(db, account=account, cut=cut, event="egreso", direction=-1, amount=expense.monto,
        method=expense.metodo_pago, origin_type="egreso", origin_id=expense.id, expense_id=expense.id)


def record_expense_adjustment(db, *, account, cut, expense, payment_method, reason):
    """Current-dated cash correction; the original expense and closed cut survive."""
    if not _is_admin(account):
        assert_source_cut(account, cut, expense)
    if not reason or len(reason.strip()) < 5:
        raise HTTPException(status_code=422, detail="Se requiere el motivo de la corrección.")
    if expense.metodo_pago is None:
        raise HTTPException(status_code=409, detail="El egreso legado carece de método certificado y requiere revisión manual.")
    prior = db.scalar(select(MovimientoEconomico.id).where(
        MovimientoEconomico.evento == "ajuste_egreso", MovimientoEconomico.egreso_id == expense.id))
    if prior is not None:
        raise HTTPException(status_code=409, detail="El egreso ya tiene una corrección económica.")
    return _append(db, account=account, cut=cut, event="ajuste_egreso", direction=1, amount=expense.monto,
        method=payment_method, origin_type="egreso", origin_id=expense.id, expense_id=expense.id, reason=reason.strip().upper())


def get_guarantee_balance(db, source_id: int) -> dict:
    rows = db.execute(select(MovimientoEconomico.evento, func.sum(MovimientoEconomico.monto_bob)).where(
        MovimientoEconomico.salida_flete_id == source_id,
        MovimientoEconomico.evento.in_(["garantia_recibida", "garantia_devuelta", "garantia_retenida"]),
    ).group_by(MovimientoEconomico.evento)).all()
    totals = {event: money(amount) for event, amount in rows}
    received = totals.get("garantia_recibida", ZERO)
    returned = totals.get("garantia_devuelta", ZERO)
    retained = totals.get("garantia_retenida", ZERO)
    return {"received_bob": received, "returned_bob": returned, "retained_pending_bob": retained,
            "available_return_bob": money(received - returned - retained)}


def record_guarantee(db, *, account, cut, source, action: str, amount, payment_method, reason=None):
    """The coordinator must lock parent and output before invoking custody."""
    _validate_cut(account, cut)
    assert_source_cut(account, cut, source)
    events = {"receive": "garantia_recibida", "return": "garantia_devuelta", "retain": "garantia_retenida"}
    action = {"recibir": "receive", "devolver": "return", "retener": "retain"}.get(action, action)
    if action not in events:
        raise HTTPException(status_code=422, detail="Acción de garantía inválida.")
    amount = money(amount)
    balance = get_guarantee_balance(db, source.id)
    if action == "receive":
        if balance["received_bob"] != ZERO or amount != money(source.garantia):
            raise HTTPException(status_code=409, detail="La recepción debe corresponder exactamente a la garantía BOB y registrarse una sola vez.")
    else:
        if amount > balance["available_return_bob"]:
            raise HTTPException(status_code=409, detail="El importe supera la garantía disponible en custodia.")
        if action == "retain":
            if not _is_admin(account):
                raise HTTPException(status_code=403, detail="Solo ADMIN puede autorizar una retención de garantía.")
            if not reason or len(reason.strip()) < 5:
                raise HTTPException(status_code=422, detail="La retención requiere un motivo explícito.")
        else:
            cash_received = db.scalar(select(func.coalesce(func.sum(MovimientoEconomico.monto_bob), 0)).where(
                MovimientoEconomico.salida_flete_id == source.id, MovimientoEconomico.corte_id == (cut.id if cut else None),
                MovimientoEconomico.evento == "garantia_recibida", MovimientoEconomico.metodo_pago == MetodoPagoEnum.EFECTIVO))
            released = min(amount, max(ZERO, money(cash_received) - balance["returned_bob"]))
            _assert_cash(db, cut, amount, payment_method, release_reserved=released)
    count = db.scalar(select(func.count()).select_from(MovimientoEconomico).where(
        MovimientoEconomico.salida_flete_id == source.id, MovimientoEconomico.evento == events[action]))
    return _append(db, account=account, cut=cut, event=events[action], direction={"receive": 1, "return": -1, "retain": 0}[action],
        amount=amount, method=payment_method, origin_type="salida_flete", origin_id=source.id,
        output_id=source.id, sequence=int(count or 0) + 1, reason=reason)
