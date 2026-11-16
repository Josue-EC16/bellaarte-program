from app.core.permissions import build_permissions_for_role
from app.schemas.notification import NotificationQueryFilters, NotificationResolveRequest
from app.services.notification_service import build_notification_action_path


def test_admin_permissions_include_full_notification_module() -> None:
    permissions = build_permissions_for_role("ADMIN")
    assert "notifications:list" in permissions
    assert "notifications:view" in permissions
    assert "notifications:mark_read" in permissions
    assert "notifications:mark_all_read" in permissions
    assert "notifications:resolve" in permissions
    assert "notifications:retry_email" in permissions
    assert "notifications:report" in permissions
    assert "notifications:list_all" in permissions


def test_operational_roles_receive_only_their_notification_permissions() -> None:
    expected_permissions = {
        "notifications:list",
        "notifications:view",
        "notifications:mark_read",
        "notifications:mark_all_read",
    }
    for role_code in ("INV_BOUTIQUE", "INV_TALLER", "MODISTA", "CAJA"):
        permissions = set(build_permissions_for_role(role_code))
        assert expected_permissions.issubset(permissions)
        assert "notifications:resolve" not in permissions
        assert "notifications:retry_email" not in permissions
        assert "notifications:report" not in permissions
        assert "notifications:list_all" not in permissions


def test_notification_resolve_request_normalizes_uppercase_reason() -> None:
    payload = NotificationResolveRequest.model_validate({"motivo": "  stock repuesto correctamente  "})
    assert payload.motivo == "STOCK REPUESTO CORRECTAMENTE"


def test_notification_query_filters_normalize_catalog_values() -> None:
    filters = NotificationQueryFilters.model_validate(
        {
            "role_code": " inv_boutique ",
            "module": " pedidos ",
            "type": " entrega_pedido_hoy ",
            "table_ref": " pedido ",
        }
    )
    assert filters.role_code == "INV_BOUTIQUE"
    assert filters.module == "PEDIDOS"
    assert filters.type == "ENTREGA_PEDIDO_HOY"
    assert filters.table_ref == "PEDIDO"


def test_notification_action_path_maps_supported_origins() -> None:
    assert build_notification_action_path("pedido", 10) == "/app/pedidos?order_id=10"
    assert build_notification_action_path("prueba_pedido", 7) == "/app/pedidos/pruebas?test_id=7"
    assert build_notification_action_path("usuarios", 2) == "/app/seguridad/usuarios?user_id=2"
