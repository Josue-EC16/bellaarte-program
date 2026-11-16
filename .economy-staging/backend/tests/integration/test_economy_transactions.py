"""Economic invariants on the explicitly validated, isolated PostgreSQL cluster.

Most cases run inside a connection transaction and roll it back, including
immutable ledger rows. Concurrency cases need committed synthetic identities;
those QA_ECON_* records deliberately remain in testing as evidence. No deletes,
trigger bypass, business connection or production credentials are used.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError


def _setup(db):
    from app.models.account import Cuenta
    from app.models.boutique_enums import EstadoCorteCajaEnum, TipoPedidoEnum
    from app.models.boutique_item import ItemBoutique
    from app.models.boutique_type import TipoItemBoutique
    from app.models.client import Cliente
    from app.models.currency import Moneda
    from app.models.economy import CorteCaja
    from app.models.flete import FleteVestido
    from app.models.order import Pedido
    from app.models.receipt import TipoComprobante
    from app.models.role import Rol
    from app.models.user import Usuario
    from app.services.economic_ledger_service import record_fund

    token = uuid4().hex[:16]
    roles = {}
    for code in ("ADMIN", "CAJA"):
        role = db.scalar(select(Rol).where(Rol.codigo == code))
        if role is None:
            role = Rol(codigo=code, nombre="QA_ECON_ROLE_" + code, activo=True)
            db.add(role)
            db.flush()
        roles[code] = role
    actors = []
    for number, code in enumerate(("ADMIN", "CAJA", "CAJA")):
        user = Usuario(nombres="QA_ECON_" + token, apellido_paterno=str(number),
                       ci=f"EC{token}{number}", celular="00000000",
                       correo=f"{token}{number}@example.invalid", zona="SOLO TEST", activo=True)
        db.add(user)
        db.flush()
        actor = Cuenta(usuario_id=user.id, rol_id=roles[code].id,
                       username=f"qa_ec_{token}{number}", password_hash="NOT_A_REAL_LOGIN_HASH",
                       must_change_password=False, is_active=True)
        db.add(actor)
        actors.append(actor)
    db.flush()
    admin, cashier, other = actors
    currency = db.scalar(select(Moneda).where(Moneda.codigo == "BOB"))
    if currency is None:
        currency = Moneda(codigo="BOB", nombre="BOLIVIANO TEST", simbolo="Bs", es_base=True, habilitado=True)
        db.add(currency)
    category = TipoItemBoutique(nombre="QA_ECON_" + token, habilitado=True)
    client = Cliente(codigo="QE" + token, nombres="QA", apellido_paterno="ECON TEST", ci="EC" + token,
                     celular="00000000", habilitado=True)
    db.add_all([category, client])
    db.flush()
    item = ItemBoutique(tipo_item_id=category.id, codigo="QA_ECON_" + token,
                        nombre="SOLO TEST", color_primario="BLANCO", material="TEST",
                        precio_compra=1, precio_venta=1000, stock=4, stock_minimo=0, estado=True)
    db.add(item)
    db.flush()
    flete = FleteVestido(item_id=item.id, usuario_id=cashier.usuario_id,
                         precio_flete_referencial=100, max_salidas=3, salidas_actuales=0, habilitado=True)
    order = Pedido(cliente_id=client.id, codigo="QA_ECON_" + token, tipo=TipoPedidoEnum.OTRO,
                   usuario_encargado_id=cashier.usuario_id, fecha_entrega=date.today() + timedelta(days=30),
                   precio=1000, total_pagado=0, saldo=1000, habilitado=True)
    cuts = []
    for actor in (cashier, other):
        cut = CorteCaja(cajero_id=actor.usuario_id, admin_id=admin.usuario_id,
                        fondo_asignado=500, estado=EstadoCorteCajaEnum.ABIERTO,
                        control_version=1, observaciones_apertura="QA_ECON_" + token)
        db.add(cut)
        db.flush()
        record_fund(db, cut, admin.usuario_id)
        cuts.append(cut)
    db.add_all([flete, order])
    for name in ("VENTA_BOUTIQUE_INTERNO", "PAGO_PEDIDO_INTERNO", "FLETE_INTERNO"):
        if db.scalar(select(TipoComprobante).where(TipoComprobante.nombre == name)) is None:
            db.add(TipoComprobante(nombre=name, es_fiscal=False, habilitado=True))
    db.flush()
    return SimpleNamespace(db=db, admin=admin, cashier=cashier, other=other,
        cut=cuts[0], other_cut=cuts[1], item=item, client=client, currency=currency,
        flete=flete, order=order, token=token)


@pytest.fixture
def econ(pg_cluster):
    with pg_cluster.engine.connect() as connection:
        pg_cluster.assert_identity(connection, pg_cluster.manifest)
        connection.rollback()
        transaction = connection.begin()
        db = Session(connection, autoflush=False, join_transaction_mode="create_savepoint", expire_on_commit=False)
        try:
            state = _setup(db)
            db.commit()  # Release fixture savepoint; the outer rollback remains.
            yield state
        finally:
            db.close()
            transaction.rollback()


def _sale(state, method="qr", actor=None):
    from app.schemas.boutique import BoutiqueSaleCreateRequest
    from app.services.boutique_sale_service import create_boutique_sale
    return create_boutique_sale(state.db, payload=BoutiqueSaleCreateRequest(
        item_id=state.item.id, client_id=state.client.id, currency_id=state.currency.id,
        quantity=1, payment_method=method), created_by=actor or state.cashier,
        ip_address=None, user_agent="QA_ECON")


def _refund(state, origin_type, origin_id, amount, actor=None, method="qr"):
    from app.schemas.economy import RefundFlowRequest
    from app.services.refund_flow_service import apply_refund_flow
    return apply_refund_flow(state.db, payload=RefundFlowRequest(
        origin_type=origin_type, origin_id=origin_id, refund_amount=amount,
        payment_method=method, concepto="DEVOLUCION QA", reason="SOLO PRUEBA ECONOMICA"),
        account=actor or state.cashier, ip_address=None, user_agent="QA_ECON")


def _expense(state, amount=100, method="efectivo"):
    from app.schemas.economy import ExpenseCreateRequest
    from app.services.expense_service import create_expense
    return create_expense(state.db, payload=ExpenseCreateRequest(tipo="otro", concepto="QA GASTO",
        cantidad=1, precio_unidad=amount, metodo_pago=method), created_by=state.cashier,
        ip_address=None, user_agent="QA_ECON")


def _payment(state, amount=500):
    from app.schemas.order import OrderPaymentCreateRequest
    from app.services.order_payment_service import create_order_payment
    return create_order_payment(state.db, order_id=state.order.id,
        payload=OrderPaymentCreateRequest(currency_id=state.currency.id, monto=amount, metodo_pago="qr"),
        created_by=state.cashier, ip_address=None, user_agent="QA_ECON")


def _output(state):
    from app.schemas.flete import SalidaFleteCreateRequest
    from app.services.flete_service import create_flete_output
    return create_flete_output(state.db, payload=SalidaFleteCreateRequest(
        flete_id=state.flete.id, client_id=state.client.id, currency_id=state.currency.id,
        fecha_salida=date.today(), fecha_devolucion_prevista=date.today() + timedelta(days=3),
        precio=100, garantia=200, metodo_pago="qr", estado_entrega="bueno"),
        created_by=state.cashier, ip_address=None, user_agent="QA_ECON")


def test_partial_successive_refunds_preserve_stock_and_original_receipt(econ):
    from app.models.boutique_sale import VentaBoutique
    from app.models.boutique_enums import EstadoComprobanteEnum, EstadoVentaBoutiqueEnum
    from app.services.financial_source_service import source_refund_summary
    sale = _sale(econ)
    first = _refund(econ, "VENTA_BOUTIQUE", sale.id, 200)
    second = _refund(econ, "VENTA_BOUTIQUE", sale.id, 300)
    original = econ.db.get(VentaBoutique, sale.id)
    assert first.constancia_id != second.constancia_id
    assert original.estado == EstadoVentaBoutiqueEnum.ACTIVA
    assert original.comprobante.estado == EstadoComprobanteEnum.EMITIDO
    assert econ.item.stock == 3
    assert source_refund_summary(econ.db, "VENTA_BOUTIQUE", original)["refundable"] == Decimal("500")
    with pytest.raises(HTTPException) as denied:
        _refund(econ, "VENTA_BOUTIQUE", sale.id, 501)
    assert denied.value.status_code == 409


def test_operative_cancel_once_then_refund_remaining_without_restock_again(econ):
    from app.schemas.economy import OperativeCancellationRequest
    from app.services.refund_flow_service import apply_operative_cancellation
    sale = _sale(econ)
    payload = OperativeCancellationRequest(origin_type="VENTA_BOUTIQUE", origin_id=sale.id,
        target_state="CANCELADA", reason="CANCELACION SOLO TEST")
    result = apply_operative_cancellation(econ.db, payload=payload, account=econ.cashier)
    assert result["pending_refund_bob"] == 1000 and econ.item.stock == 4
    _refund(econ, "VENTA_BOUTIQUE", sale.id, 400)
    _refund(econ, "VENTA_BOUTIQUE", sale.id, 600)
    assert econ.item.stock == 4
    with pytest.raises(HTTPException) as denied:
        apply_operative_cancellation(econ.db, payload=payload, account=econ.cashier)
    assert denied.value.status_code == 409


def test_order_payment_refund_reopens_only_effective_debt(econ):
    from app.services.order_service import get_order_detail
    payment = _payment(econ)
    _refund(econ, "PAGO_PEDIDO", payment.id, 200)
    order = get_order_detail(econ.db, econ.order.id)
    assert order.total_pagado == 300 and order.saldo == 700
    assert order.total_cobrado_bruto_bob == 500 and order.total_devuelto_bob == 200


def test_order_payment_report_distinguishes_gross_returns_and_effective_collection(econ):
    from app.services.order_report_service import list_order_payment_report
    payment = _payment(econ)
    _refund(econ, "PAGO_PEDIDO", payment.id, 200)
    report = list_order_payment_report(econ.db)
    # The fixture transaction can observe retained QA-only concurrency records.
    # Narrow to this unique source through the report's returned payment IDs.
    matching = [entry for entry in report["payments"] if entry.id == payment.id]
    assert len(matching) == 1
    assert matching[0].effective_amount_bob == 300
    assert matching[0].refunded_amount_bob == 200
    assert round(sum(entry.effective_amount_bob for entry in report["payments"]), 2) == report["total_bob"]
    assert round(sum(entry.monto_bob for entry in report["payments"]), 2) == report["gross_total_bob"]
    assert round(sum(entry.refunded_amount_bob for entry in report["payments"]), 2) == report["refunded_total_bob"]


def test_cancel_order_preserves_payments_and_exposes_pending_return(econ):
    from app.models.boutique_enums import EstadoComprobanteEnum
    from app.models.order import PagoPedido
    from app.schemas.order import OrderStatusUpdateRequest
    from app.services.order_service import change_order_status
    payment = _payment(econ)
    order = change_order_status(econ.db, order_id=econ.order.id,
        payload=OrderStatusUpdateRequest(target_state="cancelado", reason="CANCELACION TEST"),
        changed_by=econ.admin, ip_address=None, user_agent=None)
    assert order.saldo == 0 and order.devolucion_pendiente_bob == 500
    assert econ.db.get(PagoPedido, payment.id).comprobante.estado == EstadoComprobanteEnum.EMITIDO


def test_delivered_order_refund_blocked_and_source_ownership_enforced(econ):
    from app.models.boutique_enums import EstadoPedidoGeneralEnum
    payment = _payment(econ)
    with pytest.raises(HTTPException) as denied:
        _refund(econ, "PAGO_PEDIDO", payment.id, 10, actor=econ.other)
    assert denied.value.status_code == 403
    econ.order.estado_general = EstadoPedidoGeneralEnum.ENTREGADO
    econ.order.fecha_entrega_final = econ.order.fecha_entrega
    econ.db.commit()
    with pytest.raises(HTTPException) as delivered:
        _refund(econ, "PAGO_PEDIDO", payment.id, 10, actor=econ.admin)
    assert delivered.value.status_code == 409


def test_cash_fund_qr_and_actual_expense_remain_distinct(econ):
    from app.services.economic_ledger_service import get_cut_balances
    _sale(econ, method="qr")
    _expense(econ, 100)
    balances = get_cut_balances(econ.db, econ.cut.id)
    assert balances["commercial_income_bob"] == 1000
    assert balances["operational_total_bob"] == 1400
    assert balances["expected_cash"]["BOB"] == 400
    with pytest.raises(HTTPException) as denied:
        _expense(econ, 401)
    assert denied.value.status_code == 409


def test_guarantee_is_reserved_custody_without_commercial_income(econ):
    from app.schemas.economy import GuaranteeMovementRequest
    from app.services.economic_ledger_service import get_cut_balances
    from app.services.refund_flow_service import apply_guarantee_movement
    output = _output(econ)
    apply_guarantee_movement(econ.db, origin_id=output.id, account=econ.cashier,
        payload=GuaranteeMovementRequest(action="RECEIVE", amount=200, payment_method="efectivo", reason="GARANTIA TEST"))
    balances = get_cut_balances(econ.db, econ.cut.id)
    assert balances["commercial_income_bob"] == 100
    assert balances["expected_cash"]["BOB"] == 700
    assert balances["free_cash_bob"] == 500 and balances["reserved_cash_bob"] == 200
    apply_guarantee_movement(econ.db, origin_id=output.id, account=econ.cashier,
        payload=GuaranteeMovementRequest(action="RETURN", amount=50, payment_method="efectivo", reason="GARANTIA TEST"))
    balances = get_cut_balances(econ.db, econ.cut.id)
    assert balances["expected_cash"]["BOB"] == 650 and balances["reserved_cash_bob"] == 150
    assert balances["free_cash_bob"] == 500


def test_admin_outside_cut_return_releases_only_open_cut_custody_reservation(econ):
    from app.schemas.economy import GuaranteeMovementRequest
    from app.services.economic_ledger_service import get_cut_balances
    from app.services.refund_flow_service import apply_guarantee_movement
    output = _output(econ)
    apply_guarantee_movement(econ.db, origin_id=output.id, account=econ.cashier,
        payload=GuaranteeMovementRequest(action="RECEIVE", amount=200,
            payment_method="efectivo", reason="GARANTIA SOLO TEST"))
    apply_guarantee_movement(econ.db, origin_id=output.id, account=econ.admin,
        payload=GuaranteeMovementRequest(action="RETURN", amount=200,
            payment_method="qr", reason="PAGO ADMIN EXTERNO"))
    balances = get_cut_balances(econ.db, econ.cut.id)
    assert balances["reserved_cash_bob"] == 0
    assert balances["expected_cash"]["BOB"] == 700
    assert balances["free_cash_bob"] == 700
    assert balances["commercial_income_bob"] == 100


def test_closed_guarantee_snapshot_stays_frozen_after_external_admin_return(econ):
    from app.schemas.economy import CashCutCloseRequest, GuaranteeMovementRequest
    from app.services.cash_cut_service import close_cash_cut, get_cash_cut_detail
    from app.services.refund_flow_service import apply_guarantee_movement
    output = _output(econ)
    apply_guarantee_movement(econ.db, origin_id=output.id, account=econ.cashier,
        payload=GuaranteeMovementRequest(action="RECEIVE", amount=200,
            payment_method="efectivo", reason="GARANTIA SOLO TEST"))
    snapshot = close_cash_cut(econ.db, cut_id=econ.cut.id, closed_by=econ.admin,
        payload=CashCutCloseRequest(estado="cerrado", efectivo_recibido={"BOB": 700}),
        ip_address=None, user_agent=None).model_dump(mode="json")
    apply_guarantee_movement(econ.db, origin_id=output.id, account=econ.admin,
        payload=GuaranteeMovementRequest(action="RETURN", amount=200,
            payment_method="qr", reason="PAGO ADMIN POSTERIOR"))
    current = get_cash_cut_detail(econ.db, cut_id=econ.cut.id, account=econ.admin).model_dump(mode="json")
    assert current == snapshot
    assert current["garantias_reservadas_bob"] == 200


def test_product_return_after_guarantee_payout_does_not_require_repaying_or_reversing_money(econ):
    from app.schemas.economy import GuaranteeMovementRequest
    from app.schemas.flete import SalidaFleteDeliverRequest, SalidaFleteReturnRequest
    from app.services.economic_ledger_service import get_guarantee_balance
    from app.services.flete_service import deliver_flete_output, return_flete_output
    from app.services.refund_flow_service import apply_guarantee_movement
    output = _output(econ)
    deliver_flete_output(econ.db, salida_id=output.id, changed_by=econ.cashier,
        payload=SalidaFleteDeliverRequest(), ip_address=None, user_agent=None)
    for action in ("RECEIVE", "RETURN"):
        apply_guarantee_movement(econ.db, origin_id=output.id, account=econ.cashier,
            payload=GuaranteeMovementRequest(action=action, amount=200,
                payment_method="qr", reason="CUSTODIA SOLO TEST"))
    returned = return_flete_output(econ.db, salida_id=output.id, changed_by=econ.cashier,
        payload=SalidaFleteReturnRequest(estado_salida="devuelto", estado_devolucion="bueno",
            fecha_devolucion_real=date.today()), ip_address=None, user_agent=None)
    assert returned.estado_salida.value == "devuelto" and returned.garantia_devuelta == 200
    balance = get_guarantee_balance(econ.db, output.id)
    assert balance["returned_bob"] == 200 and balance["available_return_bob"] == 0


def test_foreign_physical_cash_cannot_fund_bob_outflow(econ):
    from app.models.currency import Moneda
    from app.models.boutique_sale import VentaBoutique
    from app.services.economic_ledger_service import get_cut_balances, record_income
    currency = econ.db.scalar(select(Moneda).where(Moneda.codigo == "USD"))
    if currency is None:
        currency = Moneda(codigo="USD", nombre="DOLAR TEST", simbolo="$", es_base=False, habilitado=True)
        econ.db.add(currency)
        econ.db.flush()
    sale = VentaBoutique(item_id=econ.item.id, usuario_id=econ.cashier.usuario_id,
        corte_id=econ.cut.id, cliente_id=econ.client.id, moneda_id=currency.id,
        cantidad=1, precio_unitario=696, tipo_cambio_usado=Decimal("6.96"),
        total_moneda_original=100, metodo_pago="efectivo")
    econ.db.add(sale)
    econ.db.flush()
    # Exercise physical attribution using a real synthetic source and historical rate.
    record_income(econ.db, account=econ.cashier, cut=econ.cut, origin_type="venta_boutique",
        source=sale, amount_bob=696,
        amount_original=100, currency_code="USD", payment_method="efectivo")
    econ.db.commit()
    balances = get_cut_balances(econ.db, econ.cut.id)
    assert balances["expected_cash"]["USD"] == 100 and balances["free_cash_bob"] == 500
    with pytest.raises(HTTPException) as denied:
        _expense(econ, 501)
    assert denied.value.status_code == 409


def test_rollback_after_receipt_failure_removes_sale_stock_and_ledger(econ, monkeypatch):
    from app.models.boutique_item import ItemBoutique
    from app.models.boutique_sale import VentaBoutique
    from app.models.economy import MovimientoEconomico
    from app.services import boutique_sale_service
    def fault(*args, **kwargs):
        raise RuntimeError("QA injected receipt failure")
    monkeypatch.setattr(boutique_sale_service, "create_sale_receipt", fault)
    with pytest.raises(RuntimeError, match="QA injected"):
        _sale(econ)
    assert econ.db.get(ItemBoutique, econ.item.id).stock == 4
    assert econ.db.scalar(select(func.count()).select_from(VentaBoutique).where(VentaBoutique.usuario_id == econ.cashier.usuario_id)) == 0
    assert econ.db.scalar(select(func.count()).select_from(MovimientoEconomico).where(
        MovimientoEconomico.corte_id == econ.cut.id, MovimientoEconomico.evento == "ingreso")) == 0


def test_closed_snapshot_survives_current_dated_admin_adjustment(econ):
    from app.schemas.economy import CashCutCloseRequest, ExpenseAnnulRequest
    from app.services.cash_cut_service import close_cash_cut, get_cash_cut_detail
    from app.services.expense_service import annul_expense
    expense = _expense(econ)
    closed = close_cash_cut(econ.db, cut_id=econ.cut.id,
        payload=CashCutCloseRequest(estado="cerrado", efectivo_recibido={"BOB":400}),
        closed_by=econ.admin, ip_address=None, user_agent=None)
    before = closed.model_dump(mode="json")
    annul_expense(econ.db, expense_id=expense.id,
        payload=ExpenseAnnulRequest(motivo="RESTITUCION REAL ADMIN", adjustment_method="qr"),
        changed_by=econ.admin, ip_address=None, user_agent=None)
    after = get_cash_cut_detail(econ.db, cut_id=econ.cut.id, account=econ.admin).model_dump(mode="json")
    assert after == before


def test_open_cut_adjustment_has_consistent_rows_buckets_and_aggregate(econ):
    from app.schemas.economy import ExpenseAnnulRequest
    from app.services.cash_cut_service import get_cash_cut_detail
    from app.services.expense_service import annul_expense, list_expenses
    expense = _expense(econ)
    annul_expense(econ.db, expense_id=expense.id,
        payload=ExpenseAnnulRequest(motivo="RESTITUCION REAL ADMIN", adjustment_method="qr"),
        changed_by=econ.admin, ip_address=None, user_agent=None)
    detail = get_cash_cut_detail(econ.db, cut_id=econ.cut.id, account=econ.admin)
    listed = list_expenses(econ.db, account=econ.cashier)
    assert detail.egresos_total_bob == 0 and listed.total_bob == 0
    assert sum(bucket.total_bob for bucket in detail.egresos_por_tipo) == 0
    assert listed.items[0].adjusted_amount_bob == 100
    assert detail.egresos[0].adjusted_amount_bob == 100


@pytest.mark.parametrize("table,action", [
    ("movimiento_economico", "UPDATE"), ("movimiento_economico", "DELETE"),
    ("constancia_devolucion", "UPDATE"), ("constancia_devolucion", "DELETE"),
])
def test_database_rejects_mutation_of_existing_financial_evidence(econ, table, action):
    from app.models.economy import MovimientoEconomico
    sale = _sale(econ)
    refund = _refund(econ, "VENTA_BOUTIQUE", sale.id, 100)
    if table == "movimiento_economico":
        identifier = econ.db.scalar(select(MovimientoEconomico.id).where(
            MovimientoEconomico.corte_id == econ.cut.id, MovimientoEconomico.evento == "fondo"))
        assignment = "motivo='QA MUTATION MUST FAIL'"
    else:
        identifier = refund.constancia_id
        assignment = "snapshot='{}'::jsonb"
    query = (f"UPDATE {table} SET {assignment} WHERE id=:identifier" if action == "UPDATE"
             else f"DELETE FROM {table} WHERE id=:identifier")
    with pytest.raises(IntegrityError) as denied:
        with econ.db.begin_nested():
            econ.db.execute(text(query), {"identifier": identifier})
    assert denied.value.orig.pgcode == "23514"
    assert econ.db.scalar(text(f"SELECT count(*) FROM {table} WHERE id=:identifier"),
                          {"identifier": identifier}) == 1


@pytest.mark.parametrize("assignment", ["control_version=0", "cierre_snapshot='{}'::jsonb",
                                         "cco_fondo_asignado=501"])
def test_database_rejects_rewriting_closed_controlled_cut(econ, assignment):
    from app.schemas.economy import CashCutCloseRequest
    from app.services.cash_cut_service import close_cash_cut
    close_cash_cut(econ.db, cut_id=econ.cut.id, closed_by=econ.admin,
        payload=CashCutCloseRequest(estado="cerrado", efectivo_recibido={"BOB":500}),
        ip_address=None, user_agent=None)
    with pytest.raises(IntegrityError) as denied:
        with econ.db.begin_nested():
            econ.db.execute(text(f"UPDATE corte_caja SET {assignment} WHERE cco_id=:id"),
                            {"id": econ.cut.id})
    assert denied.value.orig.pgcode == "23514"


def test_legacy_cut_requires_explicit_uncertified_closure(econ):
    from app.models.economy import CorteCaja
    from app.schemas.economy import CashCutCloseRequest
    from app.services.cash_cut_service import close_cash_cut
    close_cash_cut(econ.db, cut_id=econ.cut.id, closed_by=econ.admin,
        payload=CashCutCloseRequest(estado="cerrado", efectivo_recibido={"BOB":500}),
        ip_address=None, user_agent=None)
    legacy = CorteCaja(cajero_id=econ.cashier.usuario_id, admin_id=econ.admin.usuario_id,
        fondo_asignado=1000, control_version=0, estado="abierto")
    econ.db.add(legacy)
    econ.db.commit()
    with pytest.raises(HTTPException) as denied:
        close_cash_cut(econ.db, cut_id=legacy.id, closed_by=econ.admin,
            payload=CashCutCloseRequest(estado="cerrado"), ip_address=None, user_agent=None)
    assert denied.value.status_code == 409
    result = close_cash_cut(econ.db, cut_id=legacy.id, closed_by=econ.admin,
        payload=CashCutCloseRequest(estado="cerrado_observado", cierre_legado=True,
            observaciones_cierre="CIERRE LEGADO SIN CERTIFICACION"), ip_address=None, user_agent=None)
    assert not result.certified and result.control_version == 0
    assert result.efectivo_esperado == {} and result.efectivo_recibido == {}


def test_zero_fund_cannot_spend_electronic_collections_as_cash(econ):
    from app.schemas.economy import CashCutCloseRequest, CashCutCreateRequest
    from app.services.cash_cut_service import close_cash_cut, open_cash_cut
    close_cash_cut(econ.db, cut_id=econ.cut.id, closed_by=econ.admin,
        payload=CashCutCloseRequest(estado="cerrado", efectivo_recibido={"BOB":500}),
        ip_address=None, user_agent=None)
    opened = open_cash_cut(econ.db, opened_by=econ.admin,
        payload=CashCutCreateRequest(cajero_id=econ.cashier.usuario_id, fondo_asignado=0),
        ip_address=None, user_agent=None)
    assert opened.efectivo_esperado == {"BOB":0} and opened.fondo_asignado == 0
    _sale(econ, method="qr")
    with pytest.raises(HTTPException) as denied:
        _expense(econ, 1)
    assert denied.value.status_code == 409


def test_income_enum_filters_pagination_and_incomparable_report(econ):
    from app.services.income_service import list_income_rows
    from app.services.expense_service import list_expenses
    from app.services.economy_report_service import get_income_statement_report
    _sale(econ)
    _expense(econ)
    rows = list_income_rows(econ.db, account=econ.admin, source_type="VENTA_BOUTIQUE", search="QA_ECON", page_size=1)
    assert rows.total >= 1 and len(rows.items) == 1
    assert rows.items[0].estado_origen.upper() == "ACTIVA"
    expenses = list_expenses(econ.db, account=econ.cashier, page_size=1)
    assert expenses.total == 1 and expenses.total_bob == 100
    filtered = get_income_statement_report(econ.db, account=econ.admin, source_type="VENTA_BOUTIQUE")
    assert filtered.resultado_bob is None and not filtered.comparable and filtered.comparison_note


def test_real_jwt_idempotency_replay_and_permission_gate(econ):
    import casbin
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.routers.economia import router
    from app.core.database import get_db
    from app.core.security import create_access_token
    from app.deps.auth import get_enforcer
    from app.models.economy import Egreso
    security = Path(__file__).resolve().parents[2] / "app" / "security"
    enforcer = casbin.Enforcer(str(security / "model.conf"), str(security / "policy.csv"))
    enforcer.add_policy("CAJA", "economy_expenses:create", "use")
    application = FastAPI()
    application.include_router(router, prefix="/economia")
    def session():
        yield econ.db
    application.dependency_overrides[get_db] = session
    application.dependency_overrides[get_enforcer] = lambda: enforcer
    token = create_access_token(subject=str(econ.cashier.id), role_code="CAJA")
    headers = {"Authorization":"Bearer " + token, "Idempotency-Key":uuid4().hex}
    payload = {"tipo":"otro", "concepto":"QA API", "cantidad":1, "precio_unidad":100, "metodo_pago":"efectivo"}
    with TestClient(application) as client:
        assert client.post("/economia/egresos", json=payload).status_code == 401
        missing_key = client.post("/economia/egresos", json=payload,
            headers={"Authorization": headers["Authorization"]})
        assert missing_key.status_code == 422
        first = client.post("/economia/egresos", headers=headers, json=payload)
        assert first.status_code == 201, first.text
        replay = client.post("/economia/egresos", headers=headers, json=payload)
        assert replay.status_code == 201 and replay.json() == first.json()
        mismatch = client.post("/economia/egresos", headers=headers, json={**payload,"precio_unidad":101})
        assert mismatch.status_code == 409
        assert econ.db.scalar(select(func.count()).select_from(Egreso).where(Egreso.usuario_id==econ.cashier.usuario_id)) == 1
        denied = client.get("/economia/reportes/estado-resultados", headers=headers)
        assert denied.status_code == 403
        enforcer.remove_policy("CAJA", "economy_expenses:create", "use")
        assert client.post("/economia/egresos", headers=headers, json=payload).status_code == 403


@pytest.fixture
def economy_api(econ):
    """Real JWT/Casbin with explicit test-only session injection; no ERP startup."""
    import casbin
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.routers.economia import router
    from app.api.routers.boutique import router as boutique_router
    from app.core.database import get_db
    from app.core.security import create_access_token
    from app.deps.auth import get_enforcer
    security = Path(__file__).resolve().parents[2] / "app" / "security"
    enforcer = casbin.Enforcer(str(security / "model.conf"), str(security / "policy.csv"))
    app = FastAPI()
    app.include_router(router, prefix="/economia")
    app.include_router(boutique_router, prefix="/boutique")
    def session():
        yield econ.db
    app.dependency_overrides[get_db] = session
    app.dependency_overrides[get_enforcer] = lambda: enforcer
    def headers(actor, key=None):
        token = create_access_token(subject=str(actor.id), role_code=actor.rol.codigo)
        return {"Authorization": "Bearer " + token, "Idempotency-Key": key or uuid4().hex}
    with TestClient(app) as client:
        yield client, headers


@pytest.mark.parametrize("actor_name", ["admin", "cashier"])
def test_authorized_refund_and_operative_cancel_endpoints_preserve_distinct_effects(econ, economy_api, actor_name):
    from app.models.boutique_sale import VentaBoutique
    from app.models.economy import Egreso
    client, headers = economy_api
    actor = getattr(econ, actor_name)
    sale = _sale(econ)
    refund_payload = dict(origin_type="VENTA_BOUTIQUE", origin_id=sale.id, refund_amount=200,
        payment_method="qr", reason="DEVOLUCION API SOLO TEST", concepto="QA DEVOLUCION")
    first = client.post("/economia/devoluciones", headers=headers(actor), json=refund_payload)
    assert first.status_code == 201, first.text
    econ.db.expire_all()
    original = econ.db.get(VentaBoutique, sale.id)
    assert original.estado.value == "activa" and original.comprobante.estado.value == "emitido"
    assert econ.db.get(type(econ.item), econ.item.id).stock == 3
    cancellation = dict(origin_type="VENTA_BOUTIQUE", origin_id=sale.id,
        target_state="CANCELADA", reason="CANCELACION OPERATIVA API")
    cancel_headers = headers(actor)
    result = client.post("/economia/anulaciones-operativas", headers=cancel_headers, json=cancellation)
    assert result.status_code == 200, result.text
    assert result.json()["money_returned_bob"] == 0
    assert result.json()["pending_refund_bob"] == 800
    replay = client.post("/economia/anulaciones-operativas", headers=cancel_headers, json=cancellation)
    assert replay.status_code == 200 and replay.json() == result.json()
    econ.db.expire_all()
    original = econ.db.get(VentaBoutique, sale.id)
    assert original.total == 1000 and original.estado.value == "cancelada"
    assert original.comprobante.estado.value == "anulado"
    assert econ.db.get(type(econ.item), econ.item.id).stock == 4
    assert econ.db.scalar(select(func.sum(Egreso.monto)).where(
        Egreso.tabla_referencia == "venta_boutique", Egreso.id_referencia == sale.id)) == 200


def test_financial_resource_ownership_and_closed_certificate_access(econ, economy_api):
    from app.schemas.economy import CashCutCloseRequest
    from app.services.cash_cut_service import close_cash_cut
    client, headers = economy_api
    sale = _sale(econ)
    refund = _refund(econ, "VENTA_BOUTIQUE", sale.id, 100)
    output = _output(econ)
    for path in (f"/economia/ingresos/VENTA_BOUTIQUE/{sale.id}/refund-context",
                 f"/economia/garantias/{output.id}",
                 f"/economia/constancias-devolucion/{refund.constancia_id}"):
        foreign = client.get(path, headers=headers(econ.other))
        assert foreign.status_code == 403, (path, foreign.text)
    close_cash_cut(econ.db, cut_id=econ.cut.id, closed_by=econ.admin,
        payload=CashCutCloseRequest(estado="cerrado", efectivo_recibido={"BOB":500}),
        ip_address=None, user_agent=None)
    own = client.get(f"/economia/constancias-devolucion/{refund.constancia_id}", headers=headers(econ.cashier))
    assert own.status_code == 200 and own.json()["snapshot"]["expense_id"] == refund.expense_id


def test_legacy_sale_cancellation_wrapper_retries_atomically_without_duplicate_stock(econ, economy_api):
    from app.models.economy import Egreso, SolicitudEconomica
    client, headers = economy_api
    sale = _sale(econ)
    request_headers, payload = headers(econ.cashier), {"reason": "ANULACION WRAPPER QA"}
    path = f"/boutique/sales/{sale.id}/cancel"
    first = client.patch(path, headers=request_headers, json=payload)
    assert first.status_code == 200, first.text
    replay = client.patch(path, headers=request_headers, json=payload)
    assert replay.status_code == 200 and replay.json() == first.json()
    econ.db.expire_all()
    assert econ.item.stock == 4
    assert econ.db.scalar(select(func.count()).select_from(Egreso).where(
        Egreso.tabla_referencia == "venta_boutique", Egreso.id_referencia == sale.id)) == 0
    assert econ.db.scalar(select(func.count()).select_from(SolicitudEconomica).where(
        SolicitudEconomica.actor_id == econ.cashier.usuario_id,
        SolicitudEconomica.clave == request_headers["Idempotency-Key"])) == 1


@pytest.mark.parametrize("first_action,second_action", [("disable", "disable"), ("retire", "retire"),
                                                         ("disable", "retire"), ("retire", "disable")])
def test_flete_terminal_actions_restore_unused_stock_exactly_once(econ, first_action, second_action):
    from app.schemas.flete import FleteDisableRequest, FleteRetireRequest
    from app.services.flete_service import disable_flete, retire_flete
    actions = {"disable": (disable_flete, FleteDisableRequest), "retire": (retire_flete, FleteRetireRequest)}
    initial = econ.item.stock
    for index, action in enumerate((first_action, second_action)):
        operation, schema = actions[action]
        args = dict(flete_id=econ.flete.id, payload=schema(motivo="RETIRO SIN USOS SOLO QA"),
                    changed_by=econ.admin, ip_address=None, user_agent=None)
        if index == 0:
            operation(econ.db, **args)
        else:
            with pytest.raises(HTTPException) as repeated:
                operation(econ.db, **args)
            assert repeated.value.status_code == 409
        econ.db.expire_all()
        assert econ.item.stock == initial + 1


@pytest.fixture
def committed_econ(pg_cluster):
    """Committed QA-only rows are retained because the financial ledger is immutable."""
    with Session(pg_cluster.engine, autoflush=False, expire_on_commit=False) as db:
        state = _setup(db)
        state.item.stock = 1
        db.commit()
        yield SimpleNamespace(engine=pg_cluster.engine, cashier_id=state.cashier.id,
            other_id=state.other.id, admin_id=state.admin.id, item_id=state.item.id,
            client_id=state.client.id, currency_id=state.currency.id, cut_id=state.cut.id,
            order_id=state.order.id, token=state.token)


def test_two_independent_sessions_cannot_oversell_last_unit(committed_econ):
    from app.models.account import Cuenta
    from app.models.boutique_item import ItemBoutique
    from app.schemas.boutique import BoutiqueSaleCreateRequest
    from app.services.boutique_sale_service import create_boutique_sale
    state = committed_econ
    barrier = Barrier(2)
    def sell(account_id):
        with Session(state.engine, autoflush=False) as db:
            actor = db.get(Cuenta, account_id)
            barrier.wait(timeout=10)
            try:
                result = create_boutique_sale(db, payload=BoutiqueSaleCreateRequest(item_id=state.item_id,
                    client_id=state.client_id, currency_id=state.currency_id, quantity=1, payment_method="qr"),
                    created_by=actor, ip_address=None, user_agent="QA CONCURRENCY")
                return (201, result.id)
            except HTTPException as exc:
                return (exc.status_code, None)
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(sell, [state.cashier_id, state.other_id]))
    assert sorted(code for code, _ in outcomes) == [201,409]
    with Session(state.engine, autoflush=False) as db:
        assert db.get(ItemBoutique,state.item_id).stock == 0


def test_simultaneous_identical_idempotency_keys_commit_one_expense_and_one_movement(committed_econ):
    from app.models.account import Cuenta
    from app.models.economy import Egreso, MovimientoEconomico, SolicitudEconomica
    from app.schemas.economy import ExpenseCreateRequest
    from app.services.economic_write_service import economic_write
    from app.services.expense_service import create_expense
    state, key, barrier = committed_econ, uuid4().hex, Barrier(2)
    def spend(_):
        with Session(state.engine, autoflush=False) as db:
            actor = db.get(Cuenta, state.cashier_id)
            payload = ExpenseCreateRequest(tipo="otro", concepto="QA MISMA INTENCION",
                cantidad=1, precio_unidad=100, metodo_pago="efectivo")
            barrier.wait(timeout=10)
            return economic_write(db, account=actor, operation="expense_create", key=key, payload=payload,
                execute=lambda: create_expense(db, payload=payload, created_by=actor,
                    ip_address=None, user_agent="QA SAME KEY", commit=False))
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(spend, (1, 2)))
    assert outcomes[0] == outcomes[1]
    expense_id = outcomes[0]["id"]
    with Session(state.engine, autoflush=False) as observer:
        actor = observer.get(Cuenta, state.cashier_id)
        assert observer.scalar(select(func.count()).select_from(Egreso).where(
            Egreso.usuario_id == actor.usuario_id)) == 1
        assert observer.scalar(select(func.count()).select_from(MovimientoEconomico).where(
            MovimientoEconomico.egreso_id == expense_id, MovimientoEconomico.evento == "egreso")) == 1
        assert observer.scalar(select(func.count()).select_from(SolicitudEconomica).where(
            SolicitudEconomica.actor_id == actor.usuario_id, SolicitudEconomica.clave == key)) == 1


def test_inventory_entry_refreshes_stock_changed_by_a_separate_sale_session(committed_econ):
    from app.models.account import Cuenta
    from app.models.boutique_item import ItemBoutique
    from app.schemas.boutique import BoutiqueEntryCreateRequest, BoutiqueSaleCreateRequest
    from app.services.boutique_entry_service import create_boutique_entry
    from app.services.boutique_sale_service import create_boutique_sale
    state = committed_econ
    with Session(state.engine, autoflush=False, expire_on_commit=False) as entry_session:
        # Keep a real stale ORM instance, as can happen during service composition.
        stale_item = entry_session.get(ItemBoutique, state.item_id)
        assert stale_item.stock == 1
        with Session(state.engine, autoflush=False) as sale_session:
            create_boutique_sale(sale_session,
                payload=BoutiqueSaleCreateRequest(item_id=state.item_id, client_id=state.client_id,
                    currency_id=state.currency_id, quantity=1, payment_method="qr"),
                created_by=sale_session.get(Cuenta, state.cashier_id), ip_address=None, user_agent="QA STOCK")
        create_boutique_entry(entry_session,
            payload=BoutiqueEntryCreateRequest(item_id=state.item_id, quantity=5, unit_cost=1),
            created_by=entry_session.get(Cuenta, state.admin_id), ip_address=None, user_agent="QA STOCK")
    with Session(state.engine, autoflush=False) as observer:
        assert observer.get(ItemBoutique, state.item_id).stock == 5


def test_observer_sees_no_partial_sale_ledger_or_idempotent_success_after_failure(committed_econ, monkeypatch):
    from app.models.account import Cuenta
    from app.models.boutique_item import ItemBoutique
    from app.models.boutique_sale import VentaBoutique
    from app.models.economy import MovimientoEconomico, SolicitudEconomica
    from app.schemas.boutique import BoutiqueSaleCreateRequest
    from app.services import boutique_sale_service
    from app.services.economic_write_service import economic_write
    state, key = committed_econ, uuid4().hex
    def fail_after_flushing_ledger(db, **kwargs):
        db.flush()
        raise RuntimeError("QA failure after real ledger flush")
    monkeypatch.setattr(boutique_sale_service, "create_sale_receipt", fail_after_flushing_ledger)
    with Session(state.engine, autoflush=False) as writer:
        actor = writer.get(Cuenta, state.cashier_id)
        actor_user_id = actor.usuario_id
        payload = BoutiqueSaleCreateRequest(item_id=state.item_id, client_id=state.client_id,
            currency_id=state.currency_id, quantity=1, payment_method="qr")
        with pytest.raises(RuntimeError, match="QA failure after real ledger flush"):
            economic_write(writer, account=actor, operation="sale_create", key=key, payload=payload,
                execute=lambda: boutique_sale_service.create_boutique_sale(writer, payload=payload,
                    created_by=actor, ip_address=None, user_agent="QA ROLLBACK", commit=False))
    with Session(state.engine, autoflush=False) as observer:
        assert observer.get(ItemBoutique, state.item_id).stock == 1
        assert observer.scalar(select(func.count()).select_from(VentaBoutique).where(
            VentaBoutique.usuario_id == actor_user_id)) == 0
        assert observer.scalar(select(func.count()).select_from(MovimientoEconomico).where(
            MovimientoEconomico.corte_id == state.cut_id, MovimientoEconomico.evento == "ingreso")) == 0
        assert observer.scalar(select(func.count()).select_from(SolicitudEconomica).where(
            SolicitudEconomica.actor_id == actor_user_id, SolicitudEconomica.clave == key)) == 0


def test_two_independent_refunds_cannot_exceed_historical_cap(committed_econ):
    from app.models.account import Cuenta
    from app.models.boutique_sale import VentaBoutique
    from app.schemas.boutique import BoutiqueSaleCreateRequest
    from app.schemas.economy import RefundFlowRequest
    from app.services.boutique_sale_service import create_boutique_sale
    from app.services.financial_source_service import refund_totals
    from app.services.refund_flow_service import apply_refund_flow
    state = committed_econ
    with Session(state.engine, autoflush=False) as db:
        actor=db.get(Cuenta,state.cashier_id)
        sale=create_boutique_sale(db,payload=BoutiqueSaleCreateRequest(item_id=state.item_id,
            client_id=state.client_id,currency_id=state.currency_id,quantity=1,payment_method="qr"),
            created_by=actor,ip_address=None,user_agent="QA CONCURRENCY")
        sale_id=sale.id
    barrier=Barrier(2)
    def refund(_):
        with Session(state.engine, autoflush=False) as db:
            actor=db.get(Cuenta,state.cashier_id)
            barrier.wait(timeout=10)
            try:
                apply_refund_flow(db,payload=RefundFlowRequest(origin_type="VENTA_BOUTIQUE",origin_id=sale_id,
                    refund_amount=600,payment_method="qr",concepto="QA CONCURRENT",reason="CONCURRENCIA TEST"),account=actor)
                return 201
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes=list(executor.map(refund,[1,2]))
    assert sorted(outcomes)==[201,409]
    with Session(state.engine, autoflush=False) as db:
        assert refund_totals(db,"VENTA_BOUTIQUE",sale_id)==600
        assert db.get(VentaBoutique,sale_id).total==1000


def test_two_independent_payments_cannot_overpay_order(committed_econ):
    from app.models.account import Cuenta
    from app.schemas.order import OrderPaymentCreateRequest
    from app.services.order_payment_service import create_order_payment
    from app.services.financial_source_service import effective_order_paid
    state=committed_econ
    barrier=Barrier(2)
    def pay(account_id):
        with Session(state.engine, autoflush=False) as db:
            actor=db.get(Cuenta,account_id)
            barrier.wait(timeout=10)
            try:
                create_order_payment(db,order_id=state.order_id,
                    payload=OrderPaymentCreateRequest(currency_id=state.currency_id,monto=600,metodo_pago="qr"),
                    created_by=actor,ip_address=None,user_agent="QA CONCURRENCY")
                return 201
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes=list(executor.map(pay,[state.cashier_id,state.other_id]))
    assert sorted(outcomes)==[201,409]
    with Session(state.engine, autoflush=False) as db:
        assert effective_order_paid(db,state.order_id)==600


def test_cut_close_and_expense_serialize_without_post_close_movement(committed_econ):
    from app.models.account import Cuenta
    from app.models.boutique_enums import EstadoCorteCajaEnum
    from app.models.economy import CorteCaja
    from app.schemas.economy import CashCutCloseRequest, ExpenseCreateRequest
    from app.services.cash_cut_service import close_cash_cut
    from app.services.economic_ledger_service import get_cut_balances
    from app.services.expense_service import create_expense
    state=committed_econ
    barrier=Barrier(2)
    def close():
        with Session(state.engine, autoflush=False) as db:
            actor=db.get(Cuenta,state.admin_id)
            barrier.wait(timeout=10)
            try:
                close_cash_cut(db,cut_id=state.cut_id,payload=CashCutCloseRequest(
                    estado="cerrado",efectivo_recibido={"BOB":500}),closed_by=actor,
                    ip_address=None,user_agent="QA CONCURRENCY")
                return 200
            except HTTPException as exc:
                db.rollback()
                return exc.status_code
    def expense():
        with Session(state.engine, autoflush=False) as db:
            actor=db.get(Cuenta,state.cashier_id)
            barrier.wait(timeout=10)
            try:
                create_expense(db,payload=ExpenseCreateRequest(tipo="otro",concepto="QA CONCURRENT",
                    cantidad=1,precio_unidad=100,metodo_pago="efectivo"),created_by=actor,
                    ip_address=None,user_agent="QA CONCURRENCY")
                return 201
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        closing=executor.submit(close)
        spending=executor.submit(expense)
        outcome=(closing.result(timeout=30),spending.result(timeout=30))
    assert outcome in {(200,409),(422,201)}
    with Session(state.engine, autoflush=False) as db:
        cut=db.get(CorteCaja,state.cut_id)
        balances=get_cut_balances(db,state.cut_id)
        if cut.estado==EstadoCorteCajaEnum.CERRADO:
            assert balances["expected_cash"]["BOB"]==500
            assert cut.cierre_snapshot is not None
        else:
            assert cut.estado==EstadoCorteCajaEnum.ABIERTO
            assert balances["expected_cash"]["BOB"]==400


def test_paginated_cuts_keep_scope_counts_and_own_history_is_numeric(econ):
    from app.schemas.economy import CashCutCloseRequest
    from app.services.cash_cut_service import list_cash_cuts,close_cash_cut,get_my_cut_history_page
    page=list_cash_cuts(econ.db,account=econ.admin,cajero_id=econ.cashier.usuario_id,page_size=1)
    assert page.total==1 and page.open_count==1 and len(page.items)==1
    close_cash_cut(econ.db,cut_id=econ.cut.id,payload=CashCutCloseRequest(
        estado="cerrado",efectivo_recibido={"BOB":500}),closed_by=econ.admin,ip_address=None,user_agent="QA PAGE")
    closed=list_cash_cuts(econ.db,account=econ.admin,cajero_id=econ.cashier.usuario_id,page_size=1)
    assert closed.open_count==0 and closed.closed_count==1
    own=get_my_cut_history_page(econ.db,account=econ.cashier,page_size=1)
    assert own.total==1 and own.items[0].resultado_display=="500.00"
    assert "***" not in own.model_dump_json()
    assert "observaciones_cierre" not in own.model_dump_json()


def test_expense_net_amount_and_reversal_summary_agree(econ):
    from app.schemas.economy import ExpenseAnnulRequest
    from app.services.expense_service import annul_expense,list_expenses
    expense=_expense(econ,100)
    annul_expense(econ.db,expense_id=expense.id,payload=ExpenseAnnulRequest(
        motivo="EL DINERO NUNCA SALIO",money_did_not_leave=True),changed_by=econ.cashier,
        ip_address=None,user_agent="QA NET")
    page=list_expenses(econ.db,account=econ.cashier,cut_id=econ.cut.id)
    assert page.total_bob==0
    assert page.items[0].monto==100 and page.items[0].net_amount_bob==0


def test_open_cut_api_response_and_replay_include_pending_initial_fund_without_autoflush(econ,economy_api):
    from app.schemas.economy import CashCutCloseRequest
    from app.services.cash_cut_service import close_cash_cut
    client,headers=economy_api
    assert econ.db.autoflush is False
    close_cash_cut(econ.db,cut_id=econ.cut.id,payload=CashCutCloseRequest(
        estado="cerrado",efectivo_recibido={"BOB":500}),closed_by=econ.admin,ip_address=None,user_agent="QA OPEN")
    intent=headers(econ.admin)
    payload={"cajero_id":econ.cashier.usuario_id,"fondo_asignado":167.01}
    created=client.post("/economia/cortes-caja",headers=intent,json=payload)
    assert created.status_code==201,created.text
    assert created.json()["resultado_bob"]==167.01
    assert created.json()["efectivo_esperado"]["BOB"]==167.01
    replay=client.post("/economia/cortes-caja",headers=intent,json=payload)
    assert replay.status_code==201 and replay.json()==created.json()


def test_adjustment_api_response_includes_uncommitted_correction_without_autoflush(econ,economy_api):
    client,headers=economy_api
    expense=_expense(econ,100)
    response=client.patch(f"/economia/egresos/{expense.id}/annul",headers=headers(econ.admin),
        json={"motivo":"RESTITUCION REAL SOLO TEST","adjustment_method":"qr"})
    assert response.status_code==200,response.text
    assert response.json()["adjusted_amount_bob"]==100
    assert response.json()["net_amount_bob"]==0


def test_cash_flow_csv_preserves_non_comparability_and_summary_scope(econ,economy_api):
    import csv,io
    client,headers=economy_api
    _sale(econ)
    response=client.get("/economia/reportes/flujo-efectivo",headers=headers(econ.admin),
        params={"format":"csv","cashier_id":econ.cashier.usuario_id,"source_type":"VENTA_BOUTIQUE"})
    assert response.status_code==200,response.text
    rows=list(csv.DictReader(io.StringIO(response.text)))
    assert rows[0]["PERIODO"]=="RESUMEN"
    assert rows[0]["INGRESOS_BOB"]=="1000.0"
    assert rows[0]["RESULTADO_BOB"]==""
    assert all("No comparable" in row["COMPARABILIDAD"] for row in rows)
