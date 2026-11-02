"""Shared notification semantics; persistence and HTTP use the same catalogue."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


ADMIN_ROLE_CODE = "ADMIN"
STOCK_NOTIFICATION_TYPES = frozenset({"STOCK_BAJO_BOUTIQUE", "STOCK_BAJO_TALLER"})
DELIVERY_NOTIFICATION_TYPES = frozenset({"ENTREGA_PEDIDO_2_DIAS", "ENTREGA_PEDIDO_1_DIA", "ENTREGA_PEDIDO_HOY"})
TEST_NOTIFICATION_TYPES = frozenset({"PRUEBA_PEDIDO_2_DIAS", "PRUEBA_PEDIDO_1_DIA", "PRUEBA_PEDIDO_HOY"})
MATERIAL_NOTIFICATION_TYPES = frozenset({"PRUEBA_1_ALISTAR_MATERIAL", "PRUEBA_2_ALISTAR_MATERIAL"})
FLETE_RETURN_NOTIFICATION_TYPES = frozenset({
    "DEVOLUCION_FLETE_2_DIAS", "DEVOLUCION_FLETE_1_DIA", "DEVOLUCION_FLETE_HOY", "DEVOLUCION_FLETE_VENCIDA",
})
MANUAL_NOTIFICATION_TYPES = MATERIAL_NOTIFICATION_TYPES | {"SISTEMA"}
NOTIFICATION_TYPES = (
    STOCK_NOTIFICATION_TYPES | DELIVERY_NOTIFICATION_TYPES | TEST_NOTIFICATION_TYPES
    | MATERIAL_NOTIFICATION_TYPES | FLETE_RETURN_NOTIFICATION_TYPES
    | {"FLETE_MAX_SALIDAS", "ERROR_ENVIO_CORREO", "SISTEMA"}
)
RECIPIENT_ROLES = {
    "STOCK_BAJO_BOUTIQUE": frozenset({"ADMIN", "INV_BOUTIQUE"}),
    "STOCK_BAJO_TALLER": frozenset({"ADMIN", "INV_TALLER"}),
    "FLETE_MAX_SALIDAS": frozenset({"ADMIN", "INV_BOUTIQUE"}),
    "ERROR_ENVIO_CORREO": frozenset({"ADMIN"}),
    **{kind: frozenset({"ADMIN", "MODISTA", "INV_BOUTIQUE"}) for kind in DELIVERY_NOTIFICATION_TYPES | TEST_NOTIFICATION_TYPES},
    **{kind: frozenset({"ADMIN", "MODISTA", "CAJA"}) for kind in MATERIAL_NOTIFICATION_TYPES},
    **{kind: frozenset({"ADMIN", "INV_BOUTIQUE"}) for kind in FLETE_RETURN_NOTIFICATION_TYPES},
}


def recipient_roles(notification_type: str, *, cashier_eligible: bool = False) -> frozenset[str]:
    kind = normalize_upper(notification_type)
    roles = RECIPIENT_ROLES.get(kind, frozenset())
    if cashier_eligible and kind in DELIVERY_NOTIFICATION_TYPES | FLETE_RETURN_NOTIFICATION_TYPES:
        return roles | {"CAJA"}
    return roles


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def business_today():
    return datetime.now(ZoneInfo("America/La_Paz")).date()


def normalize_upper(value: str | None) -> str | None:
    return (value.strip().upper() or None) if value is not None else None


def build_notification_action_path(table_ref: str | None, record_id_ref: int | None) -> str | None:
    paths = {
        "ITEM_BOUTIQUE": ("/app/boutique/inventario", "item_id"),
        "INVENTARIO_TALLER": ("/app/taller/inventario", "item_id"),
        "PEDIDO": ("/app/pedidos", "order_id"),
        "PRUEBA_PEDIDO": ("/app/pedidos/pruebas", "test_id"),
        "SALIDA_FLETE": ("/app/fletes/salidas", "output_id"),
        "FLETE_VESTIDO": ("/app/fletes", "flete_id"),
        "USUARIOS": ("/app/seguridad/usuarios", "user_id"),
    }
    target = paths.get(normalize_upper(table_ref))
    if target is None:
        return None
    path, parameter = target
    return f"{path}?{parameter}={record_id_ref}" if record_id_ref else path


def can_resolve_manually(notification_type: str) -> bool:
    return normalize_upper(notification_type) in MANUAL_NOTIFICATION_TYPES
