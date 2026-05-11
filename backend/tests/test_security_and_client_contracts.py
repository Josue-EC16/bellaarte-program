from app.core.permissions import build_permissions_for_role
from app.schemas.auth import ResetPasswordRequest, UpdateUserRequest
from app.schemas.client import ClienteCreateRequest
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
