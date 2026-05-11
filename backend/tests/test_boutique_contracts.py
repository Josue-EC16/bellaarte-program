import pytest
from pydantic import ValidationError

from app.core.permissions import build_permissions_for_role
from app.schemas.boutique import BoutiqueItemCreateRequest, BoutiqueSaleCreateRequest
from app.schemas.workshop import TallerEntryCreateRequest, TallerOutputCreateRequest


def test_inv_boutique_permissions_include_crud_actions() -> None:
    permissions = build_permissions_for_role("INV_BOUTIQUE")
    assert "boutique_items:create" in permissions
    assert "boutique_items:update" in permissions
    assert "boutique_types:update_status" in permissions
    assert "boutique_providers:create" in permissions
    assert "boutique_entries:create" in permissions
    assert "currencies:view" in permissions
    assert "exchange_rates:view" in permissions
    assert "boutique_sales:list" in permissions
    assert "boutique_sales:create" not in permissions


def test_caja_permissions_are_sales_enabled_but_inventory_read_only() -> None:
    permissions = build_permissions_for_role("CAJA")
    assert "boutique_items:list" in permissions
    assert "boutique_items:view" in permissions
    assert "boutique_items:create" not in permissions
    assert "currencies:list" in permissions
    assert "exchange_rates:list" in permissions
    assert "boutique_sales:create" in permissions
    assert "boutique_sales:annul" in permissions


def test_inv_taller_permissions_include_full_workshop_module() -> None:
    permissions = build_permissions_for_role("INV_TALLER")
    assert "workshop_types:create" in permissions
    assert "workshop_inventory:update" in permissions
    assert "workshop_entries:create" in permissions
    assert "workshop_outputs:update_status" in permissions


def test_modista_permissions_allow_outputs_and_inventory_read_only() -> None:
    permissions = build_permissions_for_role("MODISTA")
    assert "workshop_inventory:list" in permissions
    assert "workshop_inventory:view" in permissions
    assert "workshop_outputs:create" in permissions
    assert "workshop_outputs:update_status" in permissions
    assert "workshop_entries:create" not in permissions


def test_boutique_item_request_requires_specialized_detail() -> None:
    with pytest.raises(ValidationError):
        BoutiqueItemCreateRequest.model_validate(
            {
                "type_id": 1,
                "detail_kind": "VESTIDO",
                "item": {
                    "code": "VBT-001",
                    "name": "VESTIDO AURORA",
                    "color_primary": "BLANCO",
                    "material": "SATEN",
                    "purchase_price": 100,
                    "sale_price": 200,
                    "stock": 1,
                    "stock_min": 1,
                },
            }
        )


def test_boutique_item_request_accepts_brassier_detail() -> None:
    payload = BoutiqueItemCreateRequest.model_validate(
        {
            "type_id": 5,
            "detail_kind": "BRASIER",
            "detail": {
                "cup_size": "COPA B",
                "has_lace": True,
                "brand": "BELLA",
            },
            "item": {
                "code": "BRA-001",
                "name": "BRASSIER CLASICO",
                "color_primary": "BLANCO",
                "material": "ENCAJE",
                "purchase_price": 30,
                "sale_price": 55,
                "stock": 3,
                "stock_min": 1,
            },
        }
    )
    assert payload.detail_kind == "BRASIER"


def test_boutique_item_request_rejects_brassier_without_cup_size() -> None:
    with pytest.raises(ValidationError):
        BoutiqueItemCreateRequest.model_validate(
            {
                "type_id": 5,
                "detail_kind": "BRASIER",
                "detail": {
                    "brand": "BELLA",
                },
                "item": {
                    "code": "BRA-002",
                    "name": "BRASSIER ENCAJE",
                    "color_primary": "MARFIL",
                    "material": "ENCAJE",
                    "purchase_price": 25,
                    "sale_price": 50,
                    "stock": 2,
                    "stock_min": 1,
                },
            }
        )


def test_boutique_item_request_rejects_detail_for_otro() -> None:
    with pytest.raises(ValidationError):
        BoutiqueItemCreateRequest.model_validate(
            {
                "type_id": 4,
                "detail_kind": "OTRO",
                "detail": {"shape": "REDONDO"},
                "item": {
                    "code": "OTR-001",
                    "name": "PERCHA",
                    "color_primary": "DORADO",
                    "material": "METAL",
                    "purchase_price": 5,
                    "sale_price": 10,
                    "stock": 10,
                    "stock_min": 2,
                },
            }
        )


def test_boutique_sale_request_rejects_removed_mixed_payment_value() -> None:
    with pytest.raises(ValidationError):
        BoutiqueSaleCreateRequest.model_validate(
            {
                "item_id": 1,
                "currency_id": 1,
                "quantity": 1,
                "payment_method": "mixto",
            }
        )


def test_boutique_sale_request_requires_discount_reason() -> None:
    with pytest.raises(ValidationError):
        BoutiqueSaleCreateRequest.model_validate(
            {
                "item_id": 1,
                "currency_id": 1,
                "quantity": 1,
                "discount": 10,
                "payment_method": "qr",
            }
        )


def test_boutique_sale_request_accepts_lowercase_payment_and_reason() -> None:
    payload = BoutiqueSaleCreateRequest.model_validate(
        {
            "item_id": 1,
            "currency_id": 1,
            "quantity": 2,
            "discount": 15,
            "discount_reason": "rebaja",
            "payment_method": "efectivo",
        }
    )
    assert payload.payment_method.value == "efectivo"


def test_workshop_entry_request_accepts_valid_unit_measure() -> None:
    payload = TallerEntryCreateRequest.model_validate(
        {
            "item_id": 10,
            "quantity": 2.5,
            "unit_measure": "metro",
            "unit_cost": 18.5,
            "reason": "entrada_stock",
        }
    )
    assert payload.unit_measure.value == "metro"


def test_workshop_output_request_accepts_valid_payload() -> None:
    payload = TallerOutputCreateRequest.model_validate(
        {
            "item_id": 8,
            "quantity": 1,
            "unit_measure": "unidad",
            "destination": "PRUEBA DE MUESTRA",
        }
    )
    assert payload.destination == "PRUEBA DE MUESTRA"
