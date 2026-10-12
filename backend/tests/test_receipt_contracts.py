from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.permissions import build_permissions_for_role
from app.models.boutique_enums import MetodoPagoEnum, MotivoDescFleteEnum, MotivoDescVentaBoutiqueEnum
from app.schemas.boutique import BoutiqueSaleCreateRequest
from app.schemas.flete import SalidaFleteCreateRequest
from app.schemas.order import OrderPaymentCreateRequest
from app.schemas.receipt import ReceiptCustomerSnapshotPayload, ReceiptTypeCreateRequest, ReceiptTypeUpdateRequest
from app.services.receipt_service import resolve_customer_snapshot


def test_admin_and_caja_permissions_include_receipt_module() -> None:
    assert "receipt_types:list" in build_permissions_for_role("ADMIN")
    assert "receipt_types:view" in build_permissions_for_role("ADMIN")
    assert "receipt_types:create" in build_permissions_for_role("ADMIN")
    assert "receipt_types:update" in build_permissions_for_role("ADMIN")
    assert "receipt_types:update_status" in build_permissions_for_role("ADMIN")
    assert "receipts:list" in build_permissions_for_role("ADMIN")
    assert "receipts:view" in build_permissions_for_role("ADMIN")
    assert "receipts:print" in build_permissions_for_role("ADMIN")
    assert "receipt_types:list" in build_permissions_for_role("CAJA")
    assert "receipt_types:view" in build_permissions_for_role("CAJA")
    assert "receipts:list" in build_permissions_for_role("CAJA")
    assert "receipts:view" in build_permissions_for_role("CAJA")
    assert "receipts:print" in build_permissions_for_role("CAJA")


def test_non_receipt_roles_do_not_receive_receipt_permissions_by_default() -> None:
    for role_code in ("MODISTA", "INV_TALLER", "INV_BOUTIQUE"):
        permissions = build_permissions_for_role(role_code)
        assert "receipt_types:list" not in permissions
        assert "receipt_types:view" not in permissions
        assert "receipt_types:create" not in permissions
        assert "receipt_types:update" not in permissions
        assert "receipt_types:update_status" not in permissions
        assert "receipts:list" not in permissions
        assert "receipts:view" not in permissions
        assert "receipts:print" not in permissions


def test_receipt_type_create_request_normalizes_uppercase() -> None:
    payload = ReceiptTypeCreateRequest.model_validate(
        {
            "nombre": "  control_manual  ",
            "descripcion": "  uso interno del área administrativa  ",
            "es_fiscal": False,
        }
    )
    assert payload.nombre == "CONTROL_MANUAL"
    assert payload.descripcion == "USO INTERNO DEL ÁREA ADMINISTRATIVA"


def test_receipt_type_update_request_normalizes_description_uppercase() -> None:
    payload = ReceiptTypeUpdateRequest.model_validate(
        {
            "descripcion": "  respaldo comercial del cierre diario  ",
            "es_fiscal": True,
        }
    )
    assert payload.descripcion == "RESPALDO COMERCIAL DEL CIERRE DIARIO"
    assert payload.es_fiscal is True


def test_receipt_snapshot_payload_normalizes_uppercase() -> None:
    payload = ReceiptCustomerSnapshotPayload.model_validate(
        {
            "full_name": "  maria perez  ",
            "ci_nit": " 123456 lp ",
            "cellphone": " 70000000 ",
        }
    )
    assert payload.full_name == "MARIA PEREZ"
    assert payload.ci_nit == "123456 LP"
    assert payload.cellphone == "70000000"


def test_resolve_customer_snapshot_requires_complete_manual_snapshot_without_client() -> None:
    with pytest.raises(HTTPException) as exc_info:
        resolve_customer_snapshot(
            client=None,
            snapshot_payload=ReceiptCustomerSnapshotPayload.model_validate({"full_name": "MARIA"}),
        )
    assert exc_info.value.status_code == 409


def test_resolve_customer_snapshot_uses_existing_client_fields_and_completes_missing_ones() -> None:
    client = SimpleNamespace(
        id=1,
        nombre_completo="MARIA PEREZ",
        ci=None,
        celular="70000000",
    )
    full_name, ci_nit, cellphone = resolve_customer_snapshot(
        client=client,
        snapshot_payload=ReceiptCustomerSnapshotPayload.model_validate({"ci_nit": "123456 LP"}),
    )
    assert full_name == "MARIA PEREZ"
    assert ci_nit == "123456 LP"
    assert cellphone == "70000000"


def test_boutique_sale_request_accepts_receipt_snapshot() -> None:
    payload = BoutiqueSaleCreateRequest.model_validate(
        {
            "item_id": 10,
            "currency_id": 1,
            "quantity": 1,
            "discount": 10,
            "discount_reason": MotivoDescVentaBoutiqueEnum.REBAJA,
            "payment_method": MetodoPagoEnum.QR,
            "receipt_customer_snapshot": {
                "full_name": "MARIA PEREZ",
                "ci_nit": "123456 LP",
                "cellphone": "70000000",
            },
        }
    )
    assert payload.receipt_customer_snapshot is not None
    assert payload.receipt_customer_snapshot.full_name == "MARIA PEREZ"


def test_order_payment_request_accepts_receipt_snapshot() -> None:
    payload = OrderPaymentCreateRequest.model_validate(
        {
            "currency_id": 2,
            "monto": 250,
            "metodo_pago": MetodoPagoEnum.EFECTIVO,
            "receipt_customer_snapshot": {
                "full_name": "MARIA PEREZ",
                "ci_nit": "123456 LP",
                "cellphone": "70000000",
            },
        }
    )
    assert payload.receipt_customer_snapshot is not None
    assert payload.receipt_customer_snapshot.ci_nit == "123456 LP"


def test_flete_output_request_accepts_receipt_snapshot() -> None:
    payload = SalidaFleteCreateRequest.model_validate(
        {
            "flete_id": 4,
            "client_id": 2,
            "currency_id": 1,
            "fecha_salida": "2026-05-25",
            "fecha_devolucion_prevista": "2026-05-28",
            "precio": 300,
            "descuento": 20,
            "motivo_desc": MotivoDescFleteEnum.REBAJA,
            "metodo_pago": MetodoPagoEnum.TRANSACCION,
            "garantia": 150,
            "estado_entrega": "bueno",
            "receipt_customer_snapshot": {
                "full_name": "MARIA PEREZ",
                "ci_nit": "123456 LP",
                "cellphone": "70000000",
            },
        }
    )
    assert payload.receipt_customer_snapshot is not None
    assert payload.receipt_customer_snapshot.cellphone == "70000000"
