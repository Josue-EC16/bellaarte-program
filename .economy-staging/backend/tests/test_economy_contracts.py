from types import SimpleNamespace
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.core.permissions import build_permissions_for_role
from app.models.boutique_enums import EstadoVentaBoutiqueEnum, TipoEgresoEnum
from app.schemas.economy import CashCutCloseRequest, ExpenseCreateRequest, RefundFlowRequest
from app.services.boutique_sale_service import change_boutique_sale_state
from app.services.expense_service import create_expense
from app.services.flete_service import annul_flete_output
from app.services.order_payment_service import annul_order_payment


def test_admin_and_caja_permissions_include_economy_module() -> None:
    admin_permissions = set(build_permissions_for_role("ADMIN"))
    caja_permissions = set(build_permissions_for_role("CAJA"))

    assert {
        "economy_expenses:list",
        "economy_expenses:view",
        "economy_expenses:create",
        "economy_expenses:annul",
        "cash_cuts:list",
        "cash_cuts:view",
        "cash_cuts:open",
        "cash_cuts:close",
        "economy_income:view",
        "economy_income:view_all",
        "economy_refunds:create",
        "economy_reports:view",
        "economy_reports:view_all",
        "economy_reports:export",
    }.issubset(admin_permissions)
    assert {
        "economy_expenses:list",
        "economy_expenses:view",
        "economy_expenses:create",
        "economy_expenses:annul",
        "cash_cuts:view_own",
        "economy_income:view",
        "economy_refunds:create",
        "economy_reports:view",
        "economy_reports:export",
    }.issubset(caja_permissions)


def test_non_economy_roles_do_not_receive_economy_permissions() -> None:
    for role_code in ("INV_BOUTIQUE", "INV_TALLER", "MODISTA"):
        permissions = set(build_permissions_for_role(role_code))
        assert "economy_expenses:list" not in permissions
        assert "cash_cuts:view_own" not in permissions
        assert "economy_income:view" not in permissions
        assert "economy_refunds:create" not in permissions
        assert "economy_reports:view" not in permissions


def test_refund_flow_request_normalizes_uppercase_fields() -> None:
    payload = RefundFlowRequest.model_validate(
        {
            "origin_type": " venta_boutique ",
            "origin_id": 12,
            "payment_method": "efectivo",
            "refund_amount": 150,
            "reason": " devolucion parcial acordada ",
            "concepto": " devolucion de venta ",
            "beneficiario": " maria perez ",
            "observaciones": " cliente solicita devolucion parcial ",
        }
    )
    assert payload.origin_type == "VENTA_BOUTIQUE"
    assert payload.target_state is None
    assert payload.reason == "DEVOLUCION PARCIAL ACORDADA"
    assert payload.concepto == "DEVOLUCION DE VENTA"
    assert payload.beneficiario == "MARIA PEREZ"
    assert payload.observaciones == "CLIENTE SOLICITA DEVOLUCION PARCIAL"


def test_cash_cut_close_request_requires_observation_for_observed_close() -> None:
    with pytest.raises(ValueError):
        CashCutCloseRequest.model_validate({"estado": "cerrado_observado"})


def test_manual_expense_endpoint_rejects_devolucion_type() -> None:
    payload = ExpenseCreateRequest.model_validate(
        {
            "tipo": TipoEgresoEnum.DEVOLUCION,
            "concepto": "DEVOLUCION MANUAL",
            "cantidad": 1,
            "precio_unidad": 100,
            "metodo_pago":"efectivo",
        }
    )
    with pytest.raises(HTTPException) as exc_info:
        create_expense(
            db=Mock(),
            payload=payload,
            created_by=None,  # type: ignore[arg-type]
            ip_address=None,
            user_agent=None,
        )
    assert exc_info.value.status_code == 409
    assert "DEVOLUCIONES" in exc_info.value.detail


@pytest.mark.parametrize("source", ["sale", "payment", "flete"])
def test_legacy_annulment_endpoints_use_operative_coordinator_without_refund(monkeypatch, source):
    from app.services import boutique_sale_service, order_payment_service, flete_service, refund_flow_service
    coordinator = Mock(return_value={"money_returned_bob": 0})
    monetary_refund = Mock(side_effect=AssertionError("Operative cancellation must not return money"))
    monkeypatch.setattr(refund_flow_service, "apply_operative_cancellation", coordinator)
    monkeypatch.setattr(refund_flow_service, "apply_refund_flow", monetary_refund)
    detail = object()
    for module, name in ((boutique_sale_service, "get_boutique_sale_detail"),
                         (order_payment_service, "get_payment_detail"),
                         (flete_service, "get_flete_output_detail")):
        monkeypatch.setattr(module, name, Mock(return_value=detail))
    db, actor = Mock(), object()
    common = dict(db=db, ip_address=None, user_agent=None, commit=False)
    if source == "sale":
        result = change_boutique_sale_state(**common, sale_id=1,
            target_state=EstadoVentaBoutiqueEnum.CANCELADA, reason="PRUEBA", changed_by=actor)
        expected = ("VENTA_BOUTIQUE", "CANCELADA")
    elif source == "payment":
        result = annul_order_payment(**common, payment_id=1,
            payload=SimpleNamespace(reason="PRUEBA"), annulled_by=actor)
        expected = ("PAGO_PEDIDO", "ANULADA")
    else:
        result = annul_flete_output(**common, salida_id=1,
            payload=SimpleNamespace(motivo="PRUEBA"), changed_by=actor)
        expected = ("SALIDA_FLETE", "ANULADA")
    assert result is detail
    coordinator.assert_called_once()
    call = coordinator.call_args.kwargs
    assert (call["payload"].origin_type, call["payload"].target_state) == expected
    assert call["payload"].origin_id == 1 and call["account"] is actor
    assert call["commit"] is False
    monetary_refund.assert_not_called()


@pytest.mark.parametrize("change", [{"payment_method": None}, {"refund_amount": "0.001"},
    {"refund_amount": 0}, {"refund_amount": "NaN"}, {"origin_type": "OTHER"},
    {"target_state": "CANCELADA"}])
def test_monetary_refund_rejects_ambiguous_or_operative_payload(change):
    payload = dict(origin_type="VENTA_BOUTIQUE", origin_id=1, refund_amount="10.00",
        payment_method="qr", reason="PRUEBA SEGURA", concepto="DEVOLUCION TEST")
    payload.update(change)
    with pytest.raises(ValueError):
        RefundFlowRequest.model_validate(payload)


@pytest.mark.parametrize("change", [{"metodo_pago": None}, {"cantidad": "0.001"},
    {"precio_unidad": "10.005"}, {"precio_unidad": "Infinity"}])
def test_expense_requires_actual_method_and_storage_precision(change):
    payload = dict(tipo="otro", concepto="GASTO TEST", cantidad=1, precio_unidad=10, metodo_pago="qr")
    payload.update(change)
    with pytest.raises(ValueError):
        ExpenseCreateRequest.model_validate(payload)


def test_cut_close_cannot_leave_open_or_accept_invalid_cash_counts():
    for payload in ({"estado": "abierto"}, {"estado": "cerrado", "efectivo_recibido": {"bob": 10}},
                    {"estado": "cerrado", "efectivo_recibido": {"BOB": "1.001"}},
                    {"estado": "cerrado", "efectivo_recibido": {"BOB": -1}}):
        with pytest.raises(ValueError):
            CashCutCloseRequest.model_validate(payload)


def test_economic_calendar_bounds_use_local_day_and_exclusive_next_midnight():
    from app.services.economy_query_service import date_bounds
    start, end = date_bounds(date(2026, 10, 18), date(2026, 10, 18))
    assert start == datetime(2026, 10, 18, 4, tzinfo=timezone.utc)
    assert end == datetime(2026, 10, 19, 4, tzinfo=timezone.utc)
    with pytest.raises(HTTPException) as error:
        date_bounds(date(2026, 10, 19), date(2026, 10, 18))
    assert error.value.status_code == 422


def test_economic_money_rounding_matches_postgresql_half_up():
    from app.services.economic_ledger_service import money
    assert money("1.005") == Decimal("1.01")
    assert money("-1.005") == Decimal("-1.01")
    for amount in ("NaN", "Infinity", "10000000000"):
        with pytest.raises(HTTPException) as error:
            money(amount)
        assert error.value.status_code == 422


def test_unknown_income_source_rejected_before_database_query():
    from app.services.economy_query_service import income_scope
    with pytest.raises(HTTPException) as error:
        income_scope(source_type="NOT_A_SOURCE")
    assert error.value.status_code == 422
