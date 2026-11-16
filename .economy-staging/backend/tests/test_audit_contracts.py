from types import SimpleNamespace

from app.core.audit import parse_user_agent, register_audit_event, start_audit_event
from app.core.permissions import build_permissions_for_role
from app.models.boutique_enums import TipoAccionAuditoriaEnum
from app.schemas.audit import AuditQueryFilters


class DummySession:
    def __init__(self) -> None:
        self.added = []
        self.executed = []

    def add(self, value) -> None:
        self.added.append(value)

    def execute(self, statement, params=None):
        self.executed.append((statement, params))
        return None


def test_admin_permissions_include_audit_module() -> None:
    permissions = build_permissions_for_role("ADMIN")
    assert "audit:list" in permissions
    assert "audit:view" in permissions
    assert "audit:view_event" in permissions
    assert "audit:export" in permissions


def test_non_admin_roles_do_not_receive_audit_permissions() -> None:
    for role_code in ("CAJA", "MODISTA", "INV_BOUTIQUE", "INV_TALLER"):
        permissions = build_permissions_for_role(role_code)
        assert "audit:list" not in permissions
        assert "audit:view" not in permissions
        assert "audit:view_event" not in permissions
        assert "audit:export" not in permissions


def test_audit_query_filters_normalize_catalog_text() -> None:
    filters = AuditQueryFilters.model_validate(
        {
            "module": " ventas_boutique ",
            "submodule": " anular_venta ",
            "table": " venta_boutique ",
            "functional_action": " anulacion de venta boutique ",
            "browser": " chrome ",
            "device": " laptop ",
            "operating_system": " windows ",
            "http_method": " patch ",
            "search_description": " error operativo ",
        }
    )
    assert filters.module == "VENTAS_BOUTIQUE"
    assert filters.submodule == "ANULAR_VENTA"
    assert filters.table == "VENTA_BOUTIQUE"
    assert filters.functional_action == "ANULACION DE VENTA BOUTIQUE"
    assert filters.browser == "CHROME"
    assert filters.device == "LAPTOP"
    assert filters.operating_system == "WINDOWS"
    assert filters.http_method == "PATCH"
    assert filters.search_description == "ERROR OPERATIVO"


def test_parse_user_agent_extracts_basic_metadata() -> None:
    device, browser, operating_system = parse_user_agent(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/136.0.0.0 Safari/537.36"
    )
    assert device in {"PC ESCRITORIO", "LAPTOP"}
    assert browser == "CHROME"
    assert operating_system == "WINDOWS"


def test_register_audit_event_builds_rich_summary_record() -> None:
    session = DummySession()
    user = SimpleNamespace(id=7)
    account = SimpleNamespace(id=4, usuario=user)

    event_id = start_audit_event(method="PATCH", ip_address="127.0.0.1", user_agent="Chrome/136")
    record = register_audit_event(
        session,
        action="CLIENT_UPDATED",
        description="Se actualizó el cliente 'CLI-00001'.",
        account=account,
        user=user,
        reference="CLI-00001",
        ip_address="127.0.0.1",
        user_agent="Chrome/136",
        http_method="PATCH",
        event_id=event_id,
    )

    assert session.added
    assert record.modulo == "CLIENTES"
    assert record.tabla == "cliente"
    assert record.id_registro == "CLI-00001"
    assert record.accion == TipoAccionAuditoriaEnum.UPDATE
    assert str(record.id_evento) == event_id
    assert session.executed
