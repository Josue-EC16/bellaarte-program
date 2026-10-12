import pytest
from pydantic import ValidationError

from app.core.permissions import build_permissions_for_role
from app.schemas.boutique import BoutiqueItemCreateRequest, BoutiqueSaleCreateRequest
from app.schemas.flete import FleteCreateRequest, SalidaFleteCreateRequest, SalidaFleteReturnRequest
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
    assert "fletes:create" in permissions
    assert "flete_outputs:return" in permissions


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


def test_admin_permissions_include_full_flete_module() -> None:
    permissions = build_permissions_for_role("ADMIN")
    assert "fletes:create" in permissions
    assert "fletes:pass_to_sale" in permissions
    assert "flete_outputs:deliver" in permissions
    assert "flete_outputs:annul" in permissions


def test_flete_create_request_accepts_valid_payload() -> None:
    payload = FleteCreateRequest.model_validate(
        {
            "item_id": 10,
            "precio_flete_ref": 180,
            "max_salidas": 3,
            "observaciones": "HABILITACION INICIAL",
        }
    )
    assert payload.max_salidas == 3


def test_flete_output_create_requires_discount_reason() -> None:
    with pytest.raises(ValidationError):
        SalidaFleteCreateRequest.model_validate(
            {
                "flete_id": 2,
                "client_id": 3,
                "currency_id": 1,
                "fecha_salida": "2026-05-15",
                "fecha_devolucion_prevista": "2026-05-18",
                "precio": 220,
                "descuento": 20,
                "metodo_pago": "efectivo",
                "garantia": 100,
                "estado_entrega": "bueno",
            }
        )


def test_flete_output_create_rejects_invalid_return_date_order() -> None:
    with pytest.raises(ValidationError):
        SalidaFleteCreateRequest.model_validate(
            {
                "flete_id": 2,
                "client_id": 3,
                "currency_id": 1,
                "fecha_salida": "2026-05-15",
                "fecha_devolucion_prevista": "2026-05-14",
                "precio": 220,
                "metodo_pago": "efectivo",
                "garantia": 100,
                "estado_entrega": "regular",
            }
        )


def test_flete_return_requires_arreglo_description_when_needed() -> None:
    with pytest.raises(ValidationError):
        SalidaFleteReturnRequest.model_validate(
            {
                "estado_salida": "devuelto_con_arreglo",
                "estado_devolucion": "dañado",
                "fecha_devolucion_real": "2026-05-18",
                "requiere_arreglo": True,
                "monto_arreglo": 60,
                "garantia_devuelta": 40,
            }
        )


def test_flete_return_accepts_complete_arreglo_payload() -> None:
    payload = SalidaFleteReturnRequest.model_validate(
        {
            "estado_salida": "devuelto_con_arreglo",
            "estado_devolucion": "dañado",
            "fecha_devolucion_real": "2026-05-18",
            "requiere_arreglo": True,
            "monto_arreglo": 60,
            "descripcion_arreglo": "ROTURA EN LA FALDA",
            "garantia_devuelta": 40,
            "observaciones_devolucion": "SE RETIENE PARTE DE GARANTIA",
        }
    )
    assert payload.requiere_arreglo is True
