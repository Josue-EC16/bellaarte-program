from datetime import date, timedelta

from app.core.permissions import build_permissions_for_role
from app.schemas.auth import ResetPasswordRequest, UpdateUserRequest
from app.schemas.client import ClienteCreateRequest
from app.schemas.order import OrderBasePayload, OrderPaymentCreateRequest, OrderTestCreateRequest, PedidoVestidoPayload
from app.schemas.role import RoleCreateRequest
from app.services.client_service import CLIENT_CODE_PATTERN


def test_admin_permissions_include_security_and_client_crud() -> None:
    permissions = build_permissions_for_role("ADMIN")
    assert "roles:create" in permissions
    assert "users:reset_password" in permissions
    assert "clients:update_status" in permissions
    assert "currencies:create" in permissions
    assert "exchange_rates:update" in permissions


def test_modista_permissions_include_clients_only() -> None:
    permissions = build_permissions_for_role("MODISTA")
    assert "clients:create" in permissions
    assert "clients:update" in permissions
    assert "users:create" not in permissions


def test_role_request_accepts_code_and_name() -> None:
    payload = RoleCreateRequest(codigo="ASESORA", nombre="ASESORA COMERCIAL", descripcion="VENTAS")
    assert payload.codigo == "ASESORA"
    assert payload.nombre == "ASESORA COMERCIAL"


def test_update_user_request_accepts_dual_status() -> None:
    payload = UpdateUserRequest(
        nombres="ANA",
        apellido_paterno="LOPEZ",
        apellido_materno=None,
        ci="12345",
        celular="70000000",
        correo="ana@example.com",
        zona="CENTRO",
        direccion="CALLE 1",
        username="ana.lopez",
        role_code="MODISTA",
        user_is_active=True,
        account_is_active=False,
    )
    assert payload.account_is_active is False


def test_reset_password_request_requires_temporary_password() -> None:
    payload = ResetPasswordRequest(temporary_password="Temporal123!")
    assert payload.temporary_password == "Temporal123!"


def test_client_create_request_accepts_optional_code() -> None:
    payload = ClienteCreateRequest(
        nombres="MARIA",
        apellido_paterno="LOPEZ",
        celular="70000000",
        fecha_nacimiento="1998-03-15",
        pais="Bolivia",
        ciudad="La Paz",
    )
    assert payload.codigo is None
    assert str(payload.fecha_nacimiento) == "1998-03-15"
    assert payload.pais == "Bolivia"
    assert payload.ciudad == "La Paz"


def test_client_code_pattern_matches_expected_format() -> None:
    assert CLIENT_CODE_PATTERN.match("CLI-00001")
    assert not CLIENT_CODE_PATTERN.match("CLIENTE-1")


def test_order_permissions_follow_role_matrix() -> None:
    admin_permissions = build_permissions_for_role("ADMIN")
    modista_permissions = build_permissions_for_role("MODISTA")
    caja_permissions = build_permissions_for_role("CAJA")
    inv_taller_permissions = build_permissions_for_role("INV_TALLER")
    inv_boutique_permissions = build_permissions_for_role("INV_BOUTIQUE")

    assert "orders:create" in admin_permissions
    assert "order_payments:annul" in admin_permissions
    assert "orders:create" in modista_permissions
    assert "order_payments:annul" not in modista_permissions
    assert "order_payments:create" in caja_permissions
    assert "orders:update" not in caja_permissions
    assert not any(permission.startswith("orders:") for permission in inv_taller_permissions)
    assert not any(permission.startswith("order_") for permission in inv_boutique_permissions)


def test_order_base_payload_requires_discount_reason() -> None:
    try:
        OrderBasePayload.model_validate(
            {
                "client_id": 1,
                "tipo": "vestido",
                "fecha_entrega": "2026-06-20",
                "precio": 1000,
                "descuento": 100,
            }
        )
    except ValueError as exc:
        assert "motivo" in str(exc).lower()
    else:
        raise AssertionError("OrderBasePayload should reject discount without reason")


def test_order_payment_create_accepts_multicurrency_payload() -> None:
    payload = OrderPaymentCreateRequest.model_validate(
        {
            "currency_id": 2,
            "monto": 100,
            "metodo_pago": "qr",
            "observaciones": "PAGO A CUENTA",
        }
    )
    assert payload.currency_id == 2
    assert payload.metodo_pago.value == "qr"


def test_order_base_payload_rejects_past_delivery_date() -> None:
    try:
        OrderBasePayload.model_validate(
            {
                "client_id": 1,
                "tipo": "vestido",
                "fecha_entrega": str(date.today() - timedelta(days=1)),
                "precio": 1000,
            }
        )
    except ValueError as exc:
        assert "día de hoy" in str(exc).lower()
    else:
        raise AssertionError("OrderBasePayload should reject past delivery dates")


def test_order_base_payload_normalizes_uppercase_business_text() -> None:
    payload = OrderBasePayload.model_validate(
        {
            "codigo": " ped-009 ",
            "client_id": 1,
            "tipo": "vestido",
            "fecha_entrega": str(date.today() + timedelta(days=10)),
            "viaje": True,
            "pais_destino": " bolivia ",
            "ciudad_destino": " la paz ",
            "precio": 1500,
            "observaciones": " cliente vip ",
        }
    )
    assert payload.codigo == "PED-009"
    assert payload.pais_destino == "BOLIVIA"
    assert payload.ciudad_destino == "LA PAZ"
    assert payload.observaciones == "CLIENTE VIP"


def test_pedido_vestido_payload_accepts_new_measurements_and_uppercases_text() -> None:
    payload = PedidoVestidoPayload.model_validate(
        {
            "tipo_vestido": "vestido_de_novia",
            "color_principal": " blanco ",
            "descripcion_material": " satin y encaje ",
            "descripcion_diseno": " linea a ",
            "sisa": 18.5,
            "ancho_busto": 42,
            "separacion_busto": 19,
            "talle_busto": 28,
            "talle_costado": 24,
            "observaciones": " primera prueba ",
        }
    )
    assert payload.color_principal == "BLANCO"
    assert payload.descripcion_material == "SATIN Y ENCAJE"
    assert payload.sisa == 18.5
    assert payload.ancho_busto == 42
    assert payload.separacion_busto == 19
    assert payload.talle_busto == 28
    assert payload.talle_costado == 24


def test_order_test_create_request_uppercases_observaciones() -> None:
    payload = OrderTestCreateRequest.model_validate(
        {
            "numero": 1,
            "fecha": str(date.today() + timedelta(days=3)),
            "estado": "listo",
            "observaciones": " llevar encaje nuevo ",
        }
    )
    assert payload.observaciones == "LLEVAR ENCAJE NUEVO"
