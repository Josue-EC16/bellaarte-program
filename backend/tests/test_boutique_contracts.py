import pytest
from pydantic import ValidationError

from app.core.permissions import build_permissions_for_role
from app.schemas.boutique import BoutiqueItemCreateRequest


def test_inv_boutique_permissions_include_crud_actions() -> None:
    permissions = build_permissions_for_role("INV_BOUTIQUE")
    assert "boutique_items:create" in permissions
    assert "boutique_items:update" in permissions
    assert "boutique_types:update_status" in permissions


def test_caja_permissions_are_read_only_for_boutique() -> None:
    permissions = build_permissions_for_role("CAJA")
    assert "boutique_items:list" in permissions
    assert "boutique_items:view" in permissions
    assert "boutique_items:create" not in permissions


def test_boutique_item_request_requires_specialized_detail() -> None:
    with pytest.raises(ValidationError):
        BoutiqueItemCreateRequest.model_validate(
            {
                "type_id": 1,
                "detail_kind": "VESTIDO",
                "item": {
                    "code": "VBT-001",
                    "name": "VESTIDO AURORA",
                    "color": "BLANCO",
                    "material": "SATEN",
                    "purchase_price": 100,
                    "sale_price": 200,
                    "stock": 1,
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
                "detail": {"size": "GRANDE"},
                "item": {
                    "code": "OTR-001",
                    "name": "PERCHA",
                    "color": "DORADO",
                    "material": "METAL",
                    "purchase_price": 5,
                    "sale_price": 10,
                    "stock": 10,
                    "stock_min": 2,
                },
            }
        )
