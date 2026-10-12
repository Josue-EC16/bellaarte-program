from types import SimpleNamespace

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
            "target_state": " cancelada ",
            "refund_amount": 150,
            "reason": " devolucion parcial acordada ",
            "concepto": " devolucion de venta ",
            "beneficiario": " maria perez ",
            "observaciones": " cliente solicita devolucion parcial ",
        }
    )
    assert payload.origin_type == "VENTA_BOUTIQUE"
    assert payload.target_state == "CANCELADA"
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
        }
    )
    with pytest.raises(HTTPException) as exc_info:
        create_expense(
            db=None,  # type: ignore[arg-type]
            payload=payload,
            created_by=None,  # type: ignore[arg-type]
            ip_address=None,
            user_agent=None,
        )
    assert exc_info.value.status_code == 409
    assert "DEVOLUCIONES" in exc_info.value.detail


def test_public_sale_state_change_requires_economy_refund_flow() -> None:
    with pytest.raises(HTTPException) as exc_info:
        change_boutique_sale_state(
            db=None,  # type: ignore[arg-type]
            sale_id=1,
            target_state=EstadoVentaBoutiqueEnum.CANCELADA,
            reason="PRUEBA",
            changed_by=None,  # type: ignore[arg-type]
            ip_address=None,
            user_agent=None,
        )
    assert exc_info.value.status_code == 409
    assert "ECONOMÍA" in exc_info.value.detail


def test_public_order_payment_annul_requires_economy_refund_flow() -> None:
    with pytest.raises(HTTPException) as exc_info:
        annul_order_payment(
            db=None,  # type: ignore[arg-type]
            payment_id=1,
            payload=SimpleNamespace(reason="PRUEBA"),
            annulled_by=None,  # type: ignore[arg-type]
            ip_address=None,
            user_agent=None,
        )
    assert exc_info.value.status_code == 409
    assert "ECONOMÍA" in exc_info.value.detail


def test_public_flete_annul_requires_economy_refund_flow() -> None:
    with pytest.raises(HTTPException) as exc_info:
        annul_flete_output(
            db=None,  # type: ignore[arg-type]
            salida_id=1,
            payload=SimpleNamespace(motivo="PRUEBA"),
            changed_by=None,  # type: ignore[arg-type]
            ip_address=None,
            user_agent=None,
        )
    assert exc_info.value.status_code == 409
    assert "ECONOMÍA" in exc_info.value.detail
