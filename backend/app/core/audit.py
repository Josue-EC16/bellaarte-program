from __future__ import annotations

import json
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.account import Cuenta
from app.models.audit_log import AuditoriaSistema
from app.models.boutique_enums import TipoAccionAuditoriaEnum
from app.models.user import Usuario


SENSITIVE_FIELD_MARKERS = (
    "PASSWORD",
    "HASH",
    "TOKEN",
    "SECRET",
    "ACCESS_TOKEN",
    "REFRESH_TOKEN",
)

REQUEST_EVENT_ID: ContextVar[str | None] = ContextVar("audit_event_id", default=None)
REQUEST_HTTP_METHOD: ContextVar[str | None] = ContextVar("audit_http_method", default=None)
REQUEST_IP_ADDRESS: ContextVar[str | None] = ContextVar("audit_ip_address", default=None)
REQUEST_USER_AGENT: ContextVar[str | None] = ContextVar("audit_user_agent", default=None)


@dataclass(frozen=True)
class AuditDescriptor:
    module: str
    submodule: str
    table: str
    action: TipoAccionAuditoriaEnum
    functional_action: str


ACTION_DESCRIPTOR_MAP: dict[str, AuditDescriptor] = {
    "ACCESS_DENIED": AuditDescriptor("SEGURIDAD", "CONTROL_ACCESO", "cuentas", TipoAccionAuditoriaEnum.OTRO, "ACCESO DENEGADO"),
    "LOGIN_FAILED": AuditDescriptor("SEGURIDAD", "LOGIN", "cuentas", TipoAccionAuditoriaEnum.LOGIN, "LOGIN FALLIDO"),
    "LOGIN_SUCCESS": AuditDescriptor("SEGURIDAD", "LOGIN", "cuentas", TipoAccionAuditoriaEnum.LOGIN, "LOGIN EXITOSO"),
    "LOGOUT": AuditDescriptor("SEGURIDAD", "LOGOUT", "cuentas", TipoAccionAuditoriaEnum.LOGOUT, "CIERRE DE SESION"),
    "PASSWORD_CHANGED": AuditDescriptor("SEGURIDAD", "CAMBIAR_CLAVE", "cuentas", TipoAccionAuditoriaEnum.OTRO, "CAMBIO DE CONTRASENA"),
    "PASSWORD_CHANGE_FAILED": AuditDescriptor("SEGURIDAD", "CAMBIAR_CLAVE", "cuentas", TipoAccionAuditoriaEnum.OTRO, "INTENTO FALLIDO DE CAMBIO DE CONTRASENA"),
    "PASSWORD_RESET": AuditDescriptor("SEGURIDAD", "RESET_CLAVE", "cuentas", TipoAccionAuditoriaEnum.OTRO, "RESETEO DE CONTRASENA"),
    "ROLE_CREATED": AuditDescriptor("SEGURIDAD", "ROLES", "roles", TipoAccionAuditoriaEnum.INSERT, "CREACION DE ROL"),
    "ROLE_UPDATED": AuditDescriptor("SEGURIDAD", "ROLES", "roles", TipoAccionAuditoriaEnum.UPDATE, "ACTUALIZACION DE ROL"),
    "ROLE_STATUS_CHANGED": AuditDescriptor("SEGURIDAD", "ROLES", "roles", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "CAMBIO DE ESTADO DE ROL"),
    "USER_CREATED": AuditDescriptor("SEGURIDAD", "USUARIOS", "cuentas", TipoAccionAuditoriaEnum.INSERT, "CREACION DE USUARIO INTERNO"),
    "USER_UPDATED": AuditDescriptor("SEGURIDAD", "USUARIOS", "cuentas", TipoAccionAuditoriaEnum.UPDATE, "ACTUALIZACION DE USUARIO INTERNO"),
    "ACCOUNT_STATUS_CHANGED": AuditDescriptor("SEGURIDAD", "CUENTAS", "cuentas", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "CAMBIO DE ESTADO DE CUENTA"),
    "CLIENT_CREATED": AuditDescriptor("CLIENTES", "REGISTRO", "cliente", TipoAccionAuditoriaEnum.INSERT, "CREACION DE CLIENTE"),
    "CLIENT_UPDATED": AuditDescriptor("CLIENTES", "EDICION", "cliente", TipoAccionAuditoriaEnum.UPDATE, "ACTUALIZACION DE CLIENTE"),
    "CLIENT_STATUS_CHANGED": AuditDescriptor("CLIENTES", "ESTADO", "cliente", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "CAMBIO DE ESTADO DE CLIENTE"),
    "BOUTIQUE_PROVIDER_CREATED": AuditDescriptor("PROVEEDORES", "BOUTIQUE", "proveedor", TipoAccionAuditoriaEnum.INSERT, "CREACION DE PROVEEDOR"),
    "BOUTIQUE_PROVIDER_UPDATED": AuditDescriptor("PROVEEDORES", "BOUTIQUE", "proveedor", TipoAccionAuditoriaEnum.UPDATE, "ACTUALIZACION DE PROVEEDOR"),
    "BOUTIQUE_PROVIDER_STATUS_CHANGED": AuditDescriptor("PROVEEDORES", "BOUTIQUE", "proveedor", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "CAMBIO DE ESTADO DE PROVEEDOR"),
    "CURRENCY_CREATED": AuditDescriptor("MONEDAS", "MONEDAS", "moneda", TipoAccionAuditoriaEnum.INSERT, "CREACION DE MONEDA"),
    "CURRENCY_UPDATED": AuditDescriptor("MONEDAS", "MONEDAS", "moneda", TipoAccionAuditoriaEnum.UPDATE, "ACTUALIZACION DE MONEDA"),
    "CURRENCY_STATUS_CHANGED": AuditDescriptor("MONEDAS", "MONEDAS", "moneda", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "CAMBIO DE ESTADO DE MONEDA"),
    "EXCHANGE_RATE_CREATED": AuditDescriptor("TIPO_CAMBIO", "TIPOS_CAMBIO", "tipo_cambio_moneda", TipoAccionAuditoriaEnum.INSERT, "CREACION DE TIPO DE CAMBIO"),
    "EXCHANGE_RATE_UPDATED": AuditDescriptor("TIPO_CAMBIO", "TIPOS_CAMBIO", "tipo_cambio_moneda", TipoAccionAuditoriaEnum.UPDATE, "ACTUALIZACION DE TIPO DE CAMBIO"),
    "EXCHANGE_RATE_STATUS_CHANGED": AuditDescriptor("TIPO_CAMBIO", "TIPOS_CAMBIO", "tipo_cambio_moneda", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "CAMBIO DE ESTADO DE TIPO DE CAMBIO"),
    "BOUTIQUE_TYPE_CREATED": AuditDescriptor("INVENTARIO_BOUTIQUE", "TIPOS", "tipo_item_boutique", TipoAccionAuditoriaEnum.INSERT, "CREACION DE TIPO DE ITEM BOUTIQUE"),
    "BOUTIQUE_TYPE_UPDATED": AuditDescriptor("INVENTARIO_BOUTIQUE", "TIPOS", "tipo_item_boutique", TipoAccionAuditoriaEnum.UPDATE, "ACTUALIZACION DE TIPO DE ITEM BOUTIQUE"),
    "BOUTIQUE_TYPE_STATUS_CHANGED": AuditDescriptor("INVENTARIO_BOUTIQUE", "TIPOS", "tipo_item_boutique", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "CAMBIO DE ESTADO DE TIPO DE ITEM BOUTIQUE"),
    "BOUTIQUE_ITEM_CREATED": AuditDescriptor("INVENTARIO_BOUTIQUE", "ITEMS", "item_boutique", TipoAccionAuditoriaEnum.INSERT, "CREACION DE ITEM BOUTIQUE"),
    "BOUTIQUE_ITEM_UPDATED": AuditDescriptor("INVENTARIO_BOUTIQUE", "ITEMS", "item_boutique", TipoAccionAuditoriaEnum.UPDATE, "ACTUALIZACION DE ITEM BOUTIQUE"),
    "BOUTIQUE_ITEM_STATUS_CHANGED": AuditDescriptor("INVENTARIO_BOUTIQUE", "ITEMS", "item_boutique", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "CAMBIO DE ESTADO DE ITEM BOUTIQUE"),
    "BOUTIQUE_ENTRY_CREATED": AuditDescriptor("INVENTARIO_BOUTIQUE", "ENTRADAS", "entrada_item_boutique", TipoAccionAuditoriaEnum.INSERT, "CREACION DE ENTRADA BOUTIQUE"),
    "BOUTIQUE_ENTRY_STATUS_CHANGED": AuditDescriptor("INVENTARIO_BOUTIQUE", "ENTRADAS", "entrada_item_boutique", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "CAMBIO DE ESTADO DE ENTRADA BOUTIQUE"),
    "BOUTIQUE_SALE_CREATED": AuditDescriptor("VENTAS_BOUTIQUE", "VENTAS", "venta_boutique", TipoAccionAuditoriaEnum.INSERT, "CREACION DE VENTA BOUTIQUE"),
    "BOUTIQUE_SALE_CANCELLED": AuditDescriptor("VENTAS_BOUTIQUE", "ANULAR_VENTA", "venta_boutique", TipoAccionAuditoriaEnum.CANCELACION, "CANCELACION DE VENTA BOUTIQUE"),
    "FLETE_CREATED": AuditDescriptor("FLETES", "VESTIDOS_FLETE", "flete_vestido", TipoAccionAuditoriaEnum.INSERT, "CREACION DE VESTIDO EN FLETE"),
    "FLETE_UPDATED": AuditDescriptor("FLETES", "VESTIDOS_FLETE", "flete_vestido", TipoAccionAuditoriaEnum.UPDATE, "ACTUALIZACION DE VESTIDO EN FLETE"),
    "FLETE_STATUS_CHANGED": AuditDescriptor("FLETES", "VESTIDOS_FLETE", "flete_vestido", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "CAMBIO DE ESTADO DE VESTIDO EN FLETE"),
    "FLETE_PASSED_TO_SALE": AuditDescriptor("FLETES", "VESTIDOS_FLETE", "flete_vestido", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "PASE DE FLETE A VENTA"),
    "FLETE_RETIRED": AuditDescriptor("FLETES", "VESTIDOS_FLETE", "flete_vestido", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "RETIRO DEFINITIVO DE FLETE"),
    "FLETE_OUTPUT_CREATED": AuditDescriptor("FLETES", "SALIDAS_FLETE", "salida_flete", TipoAccionAuditoriaEnum.INSERT, "CREACION DE SALIDA DE FLETE"),
    "FLETE_OUTPUT_DELIVERED": AuditDescriptor("FLETES", "SALIDAS_FLETE", "salida_flete", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "ENTREGA DE SALIDA DE FLETE"),
    "FLETE_OUTPUT_RETURNED": AuditDescriptor("FLETES", "SALIDAS_FLETE", "salida_flete", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "DEVOLUCION DE SALIDA DE FLETE"),
    "FLETE_OUTPUT_ANNULLED": AuditDescriptor("FLETES", "SALIDAS_FLETE", "salida_flete", TipoAccionAuditoriaEnum.ANULACION, "ANULACION DE SALIDA DE FLETE"),
    "FLETE_RECEIPT_CREATED": AuditDescriptor("COMPROBANTES", "FLETES", "comprobante_interno", TipoAccionAuditoriaEnum.INSERT, "CREACION DE COMPROBANTE INTERNO DE FLETE"),
    "FLETE_RECEIPT_ANNULLED": AuditDescriptor("COMPROBANTES", "FLETES", "comprobante_interno", TipoAccionAuditoriaEnum.ANULACION, "ANULACION DE COMPROBANTE INTERNO DE FLETE"),
    "WORKSHOP_TYPE_CREATED": AuditDescriptor("INVENTARIO_TALLER", "TIPOS", "tipo_inventario_taller", TipoAccionAuditoriaEnum.INSERT, "CREACION DE TIPO DE INVENTARIO TALLER"),
    "WORKSHOP_TYPE_UPDATED": AuditDescriptor("INVENTARIO_TALLER", "TIPOS", "tipo_inventario_taller", TipoAccionAuditoriaEnum.UPDATE, "ACTUALIZACION DE TIPO DE INVENTARIO TALLER"),
    "WORKSHOP_TYPE_STATUS_CHANGED": AuditDescriptor("INVENTARIO_TALLER", "TIPOS", "tipo_inventario_taller", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "CAMBIO DE ESTADO DE TIPO DE INVENTARIO TALLER"),
    "WORKSHOP_ITEM_CREATED": AuditDescriptor("INVENTARIO_TALLER", "MATERIALES", "inventario_taller", TipoAccionAuditoriaEnum.INSERT, "CREACION DE MATERIAL DE TALLER"),
    "WORKSHOP_ITEM_UPDATED": AuditDescriptor("INVENTARIO_TALLER", "MATERIALES", "inventario_taller", TipoAccionAuditoriaEnum.UPDATE, "ACTUALIZACION DE MATERIAL DE TALLER"),
    "WORKSHOP_ITEM_STATUS_CHANGED": AuditDescriptor("INVENTARIO_TALLER", "MATERIALES", "inventario_taller", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "CAMBIO DE ESTADO DE MATERIAL DE TALLER"),
    "WORKSHOP_ENTRY_CREATED": AuditDescriptor("INVENTARIO_TALLER", "ENTRADAS", "entrada_inventario_taller", TipoAccionAuditoriaEnum.INSERT, "CREACION DE ENTRADA DE TALLER"),
    "WORKSHOP_ENTRY_STATUS_CHANGED": AuditDescriptor("INVENTARIO_TALLER", "ENTRADAS", "entrada_inventario_taller", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "CAMBIO DE ESTADO DE ENTRADA DE TALLER"),
    "WORKSHOP_OUTPUT_CREATED": AuditDescriptor("INVENTARIO_TALLER", "SALIDAS", "salida_material_taller", TipoAccionAuditoriaEnum.INSERT, "CREACION DE SALIDA DE MATERIAL TALLER"),
    "WORKSHOP_OUTPUT_STATUS_CHANGED": AuditDescriptor("INVENTARIO_TALLER", "SALIDAS", "salida_material_taller", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "CAMBIO DE ESTADO DE SALIDA DE MATERIAL TALLER"),
    "ORDER_CREATED": AuditDescriptor("PEDIDOS", "PEDIDOS", "pedido", TipoAccionAuditoriaEnum.INSERT, "CREACION DE PEDIDO"),
    "ORDER_UPDATED": AuditDescriptor("PEDIDOS", "PEDIDOS", "pedido", TipoAccionAuditoriaEnum.UPDATE, "ACTUALIZACION DE PEDIDO"),
    "ORDER_CANCELLED": AuditDescriptor("PEDIDOS", "PEDIDOS", "pedido", TipoAccionAuditoriaEnum.CANCELACION, "CANCELACION DE PEDIDO"),
    "ORDER_DELIVERED": AuditDescriptor("PEDIDOS", "PEDIDOS", "pedido", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "ENTREGA DE PEDIDO"),
    "ORDER_PAYMENT_CREATED": AuditDescriptor("PAGOS_PEDIDO", "PAGOS", "pago_pedido", TipoAccionAuditoriaEnum.INSERT, "CREACION DE PAGO DE PEDIDO"),
    "ORDER_PAYMENT_ANNULLED": AuditDescriptor("PAGOS_PEDIDO", "PAGOS", "pago_pedido", TipoAccionAuditoriaEnum.ANULACION, "ANULACION DE PAGO DE PEDIDO"),
    "ORDER_TEST_CREATED": AuditDescriptor("PRUEBAS_PEDIDO", "PRUEBAS", "prueba_pedido", TipoAccionAuditoriaEnum.INSERT, "CREACION DE PRUEBA DE PEDIDO"),
    "ORDER_TEST_UPDATED": AuditDescriptor("PRUEBAS_PEDIDO", "PRUEBAS", "prueba_pedido", TipoAccionAuditoriaEnum.UPDATE, "ACTUALIZACION DE PRUEBA DE PEDIDO"),
    "RECEIPT_TYPE_CREATED": AuditDescriptor("COMPROBANTES", "TIPOS", "tipo_comprobante", TipoAccionAuditoriaEnum.INSERT, "CREACION DE TIPO DE COMPROBANTE"),
    "RECEIPT_TYPE_UPDATED": AuditDescriptor("COMPROBANTES", "TIPOS", "tipo_comprobante", TipoAccionAuditoriaEnum.UPDATE, "ACTUALIZACION DE TIPO DE COMPROBANTE"),
    "RECEIPT_TYPE_STATUS_CHANGED": AuditDescriptor("COMPROBANTES", "TIPOS", "tipo_comprobante", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "CAMBIO DE ESTADO DE TIPO DE COMPROBANTE"),
    "ECONOMY_EXPENSE_CREATED": AuditDescriptor("EGRESOS", "EGRESOS", "egreso", TipoAccionAuditoriaEnum.INSERT, "CREACION DE EGRESO"),
    "ECONOMY_EXPENSE_ANNULLED": AuditDescriptor("EGRESOS", "EGRESOS", "egreso", TipoAccionAuditoriaEnum.ANULACION, "ANULACION DE EGRESO"),
    "ECONOMY_REFUND_RECORDED": AuditDescriptor("EGRESOS", "DEVOLUCIONES", "egreso", TipoAccionAuditoriaEnum.INSERT, "REGISTRO DE DEVOLUCION ECONOMICA"),
    "CASH_CUT_OPENED": AuditDescriptor("CORTE_CAJA", "APERTURA", "corte_caja", TipoAccionAuditoriaEnum.INSERT, "APERTURA DE CORTE DE CAJA"),
    "CASH_CUT_CLOSED": AuditDescriptor("CORTE_CAJA", "CIERRE", "corte_caja", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "CIERRE DE CORTE DE CAJA"),
    "NOTIFICATION_RESOLVED": AuditDescriptor("NOTIFICACIONES", "RESOLUCION", "notificacion", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, "RESOLUCION DE NOTIFICACION"),
    "NOTIFICATION_EMAIL_RETRIED": AuditDescriptor("NOTIFICACIONES", "REINTENTO_CORREO", "notificacion", TipoAccionAuditoriaEnum.OTRO, "REINTENTO DE ENVIO DE CORREO"),
    "BACKUP_MANUAL_STARTED": AuditDescriptor("BACKUPS", "GENERACION", "backup_bd", TipoAccionAuditoriaEnum.INSERT, "INICIO DE BACKUP MANUAL"),
    "BACKUP_MANUAL_COMPLETED": AuditDescriptor("BACKUPS", "GENERACION", "backup_bd", TipoAccionAuditoriaEnum.OTRO, "BACKUP MANUAL EXITOSO"),
    "BACKUP_AUTOMATIC_STARTED": AuditDescriptor("BACKUPS", "GENERACION", "backup_bd", TipoAccionAuditoriaEnum.INSERT, "INICIO DE BACKUP AUTOMATICO"),
    "BACKUP_AUTOMATIC_COMPLETED": AuditDescriptor("BACKUPS", "GENERACION", "backup_bd", TipoAccionAuditoriaEnum.OTRO, "BACKUP AUTOMATICO EXITOSO"),
    "BACKUP_FAILED": AuditDescriptor("BACKUPS", "GENERACION", "backup_bd", TipoAccionAuditoriaEnum.OTRO, "BACKUP FALLIDO"),
    "BACKUP_DOWNLOADED": AuditDescriptor("BACKUPS", "DESCARGA", "backup_bd", TipoAccionAuditoriaEnum.OTRO, "DESCARGA DE BACKUP"),
    "BACKUP_DOWNLOAD_FAILED": AuditDescriptor("BACKUPS", "DESCARGA", "backup_bd", TipoAccionAuditoriaEnum.OTRO, "DESCARGA FALLIDA DE BACKUP"),
}


def start_audit_event(
    *,
    method: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    force_new: bool = False,
) -> str:
    current_event_id = REQUEST_EVENT_ID.get()
    if current_event_id and not force_new:
        if method:
            REQUEST_HTTP_METHOD.set(method)
        if ip_address is not None:
            REQUEST_IP_ADDRESS.set(ip_address)
        if user_agent is not None:
            REQUEST_USER_AGENT.set(user_agent)
        return current_event_id

    event_id = str(uuid4())
    REQUEST_EVENT_ID.set(event_id)
    REQUEST_HTTP_METHOD.set(method)
    REQUEST_IP_ADDRESS.set(ip_address)
    REQUEST_USER_AGENT.set(user_agent)
    return event_id


def prime_audit_request_context(
    *,
    method: str | None,
    ip_address: str | None,
    user_agent: str | None,
) -> dict[str, Token]:
    return {
        "event": REQUEST_EVENT_ID.set(str(uuid4())),
        "method": REQUEST_HTTP_METHOD.set(method),
        "ip": REQUEST_IP_ADDRESS.set(ip_address),
        "user_agent": REQUEST_USER_AGENT.set(user_agent),
    }


def reset_audit_request_context(tokens: dict[str, Token]) -> None:
    REQUEST_USER_AGENT.reset(tokens["user_agent"])
    REQUEST_IP_ADDRESS.reset(tokens["ip"])
    REQUEST_HTTP_METHOD.reset(tokens["method"])
    REQUEST_EVENT_ID.reset(tokens["event"])


def current_audit_event_id() -> str | None:
    return REQUEST_EVENT_ID.get()


def parse_user_agent(user_agent: str | None) -> tuple[str | None, str | None, str | None]:
    if not user_agent:
        return None, None, None
    try:
        from user_agents import parse as parse_ua  # type: ignore

        parsed = parse_ua(user_agent)
        if parsed.is_mobile:
            device = "MOVIL"
        elif parsed.is_tablet:
            device = "TABLET"
        elif parsed.is_pc:
            device = "PC ESCRITORIO"
        elif parsed.is_bot:
            device = "BOT"
        else:
            device = "DISPOSITIVO DESCONOCIDO"
        browser = parsed.browser.family.upper() if parsed.browser.family else "NAVEGADOR DESCONOCIDO"
        os_name = parsed.os.family.upper() if parsed.os.family else "SISTEMA OPERATIVO DESCONOCIDO"
        return device, browser, os_name
    except Exception:
        normalized = user_agent.upper()
        browser = "CHROME" if "CHROME" in normalized else "EDGE" if "EDG/" in normalized else "FIREFOX" if "FIREFOX" in normalized else "SAFARI" if "SAFARI" in normalized and "CHROME" not in normalized else "NAVEGADOR DESCONOCIDO"
        if "ANDROID" in normalized:
            os_name = "ANDROID"
        elif "IPHONE" in normalized or "IPAD" in normalized:
            os_name = "IOS"
        elif "WINDOWS" in normalized:
            os_name = "WINDOWS"
        elif "MAC OS" in normalized or "MACINTOSH" in normalized:
            os_name = "MACOS"
        elif "LINUX" in normalized:
            os_name = "LINUX"
        else:
            os_name = "SISTEMA OPERATIVO DESCONOCIDO"
        if "MOBILE" in normalized or "ANDROID" in normalized or "IPHONE" in normalized:
            device = "MOVIL"
        elif "IPAD" in normalized or "TABLET" in normalized:
            device = "TABLET"
        elif "LAPTOP" in normalized:
            device = "LAPTOP"
        else:
            device = "PC ESCRITORIO"
        return device, browser, os_name


def _normalize_upper(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None


def _normalize_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _mask_sensitive_value(field_name: str | None, value: Any) -> str | None:
    if value is None:
        return None
    field_upper = (field_name or "").upper()
    if any(marker in field_upper for marker in SENSITIVE_FIELD_MARKERS):
        return "[OCULTO]"
    if isinstance(value, (dict, list, tuple)):
        serialized = json.dumps(value, ensure_ascii=True, default=str)
    else:
        serialized = str(value)
    serialized = serialized.strip()
    return serialized or None


def _descriptor_for_action(action: str, description: str | None = None) -> AuditDescriptor:
    action_upper = action.strip().upper()
    descriptor = ACTION_DESCRIPTOR_MAP.get(action_upper)
    if descriptor is not None:
        return descriptor
    if action_upper.endswith("_CREATED"):
        return AuditDescriptor("SISTEMA", "GENERAL", "sistema", TipoAccionAuditoriaEnum.INSERT, _normalize_upper(action_upper.replace("_", " ")) or "CREACION")
    if action_upper.endswith("_UPDATED"):
        return AuditDescriptor("SISTEMA", "GENERAL", "sistema", TipoAccionAuditoriaEnum.UPDATE, _normalize_upper(action_upper.replace("_", " ")) or "ACTUALIZACION")
    if action_upper.endswith("_STATUS_CHANGED"):
        return AuditDescriptor("SISTEMA", "GENERAL", "sistema", TipoAccionAuditoriaEnum.CAMBIO_ESTADO, _normalize_upper(action_upper.replace("_", " ")) or "CAMBIO DE ESTADO")
    if action_upper.endswith("_ANNULLED"):
        return AuditDescriptor("SISTEMA", "GENERAL", "sistema", TipoAccionAuditoriaEnum.ANULACION, _normalize_upper(action_upper.replace("_", " ")) or "ANULACION")
    if action_upper.endswith("_CANCELLED"):
        return AuditDescriptor("SISTEMA", "GENERAL", "sistema", TipoAccionAuditoriaEnum.CANCELACION, _normalize_upper(action_upper.replace("_", " ")) or "CANCELACION")
    return AuditDescriptor("SISTEMA", "GENERAL", "sistema", TipoAccionAuditoriaEnum.OTRO, _normalize_upper(description) or _normalize_upper(action_upper.replace("_", " ")) or "EVENTO")


def _resolve_audit_user(user: Usuario | None, account: Cuenta | None) -> Usuario | None:
    if user is not None:
        return user
    if account is not None:
        return account.usuario
    return None


def _resolve_record_reference(reference: str | None, *, account: Cuenta | None, user: Usuario | None) -> str:
    if reference:
        return reference.strip()
    if user is not None:
        return str(user.id)
    if account is not None:
        return str(account.id)
    return "SISTEMA"


def _set_db_audit_context(
    db: Session,
    *,
    event_id: str,
    user_id: int | None,
    module: str,
    submodule: str | None,
    action: TipoAccionAuditoriaEnum,
    functional_action: str | None,
    http_method: str | None,
    ip_address: str | None,
    user_agent: str | None,
) -> None:
    settings = {
        "app.audit_event_id": event_id,
        "app.audit_user_id": str(user_id) if user_id is not None else "",
        "app.audit_modulo": module,
        "app.audit_submodulo": submodule or "",
        "app.audit_action": action.value,
        "app.audit_functional": functional_action or "",
        "app.audit_http_method": http_method or "",
        "app.audit_ip": ip_address or "",
        "app.audit_user_agent": user_agent or "",
    }
    for key, value in settings.items():
        db.execute(text("select set_config(:key, :value, true)"), {"key": key, "value": value})


def register_audit_summary(
    db: Session,
    *,
    descriptor: AuditDescriptor,
    description: str,
    account: Cuenta | None = None,
    user: Usuario | None = None,
    reference: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    http_method: str | None = None,
    event_id: str | None = None,
    module: str | None = None,
    submodule: str | None = None,
    table: str | None = None,
    functional_action: str | None = None,
) -> AuditoriaSistema:
    resolved_user = _resolve_audit_user(user, account)
    resolved_event_id = event_id or current_audit_event_id() or start_audit_event(
        method=http_method,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    resolved_http_method = http_method or REQUEST_HTTP_METHOD.get()
    resolved_ip = ip_address or REQUEST_IP_ADDRESS.get()
    resolved_user_agent = user_agent or REQUEST_USER_AGENT.get()
    resolved_module = _normalize_upper(module) or descriptor.module
    resolved_submodule = _normalize_upper(submodule) or descriptor.submodule
    resolved_functional = _normalize_upper(functional_action) or descriptor.functional_action
    resolved_table = _normalize_identifier(table) or descriptor.table
    audit_device, audit_browser, audit_os = parse_user_agent(resolved_user_agent)

    _set_db_audit_context(
        db,
        event_id=resolved_event_id,
        user_id=resolved_user.id if resolved_user else None,
        module=resolved_module,
        submodule=resolved_submodule,
        action=descriptor.action,
        functional_action=resolved_functional,
        http_method=resolved_http_method,
        ip_address=resolved_ip,
        user_agent=resolved_user_agent,
    )

    audit = AuditoriaSistema(
        usuario_id=resolved_user.id if resolved_user else None,
        modulo=resolved_module,
        submodulo=resolved_submodule,
        tabla=resolved_table,
        id_registro=_resolve_record_reference(reference, account=account, user=resolved_user),
        accion=descriptor.action,
        accion_funcional=resolved_functional,
        descripcion=_normalize_upper(description),
        metodo_http=_normalize_upper(resolved_http_method),
        ip=resolved_ip,
        user_agent=resolved_user_agent,
        dispositivo=audit_device,
        navegador=audit_browser,
        sistema_operativo=audit_os,
        id_evento=UUID(resolved_event_id),
    )
    db.add(audit)
    return audit


def register_audit_field_change(
    db: Session,
    *,
    descriptor: AuditDescriptor,
    field_name: str,
    old_value: Any,
    new_value: Any,
    description: str | None = None,
    account: Cuenta | None = None,
    user: Usuario | None = None,
    reference: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    http_method: str | None = None,
    event_id: str | None = None,
    module: str | None = None,
    submodule: str | None = None,
    table: str | None = None,
    functional_action: str | None = None,
) -> AuditoriaSistema:
    resolved_user = _resolve_audit_user(user, account)
    resolved_event_id = event_id or current_audit_event_id() or start_audit_event(
        method=http_method,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    resolved_http_method = http_method or REQUEST_HTTP_METHOD.get()
    resolved_ip = ip_address or REQUEST_IP_ADDRESS.get()
    resolved_user_agent = user_agent or REQUEST_USER_AGENT.get()
    audit_device, audit_browser, audit_os = parse_user_agent(resolved_user_agent)
    audit = AuditoriaSistema(
        usuario_id=resolved_user.id if resolved_user else None,
        modulo=_normalize_upper(module) or descriptor.module,
        submodulo=_normalize_upper(submodule) or descriptor.submodule,
        tabla=_normalize_identifier(table) or descriptor.table,
        id_registro=_resolve_record_reference(reference, account=account, user=resolved_user),
        accion=descriptor.action,
        accion_funcional=_normalize_upper(functional_action) or descriptor.functional_action,
        descripcion=_normalize_upper(description) or f"CAMBIO DE CAMPO {field_name.upper()}",
        campo=_normalize_identifier(field_name),
        valor_anterior=_mask_sensitive_value(field_name, old_value),
        valor_nuevo=_mask_sensitive_value(field_name, new_value),
        metodo_http=_normalize_upper(resolved_http_method),
        ip=resolved_ip,
        user_agent=resolved_user_agent,
        dispositivo=audit_device,
        navegador=audit_browser,
        sistema_operativo=audit_os,
        id_evento=UUID(resolved_event_id),
    )
    db.add(audit)
    return audit


def register_audit_failure(
    db: Session,
    *,
    action: str,
    description: str,
    account: Cuenta | None = None,
    user: Usuario | None = None,
    reference: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    http_method: str | None = None,
) -> AuditoriaSistema:
    descriptor = _descriptor_for_action(action, description)
    return register_audit_summary(
        db,
        descriptor=descriptor,
        description=description,
        account=account,
        user=user,
        reference=reference,
        ip_address=ip_address,
        user_agent=user_agent,
        http_method=http_method,
    )


def register_audit_event(
    db: Session,
    *,
    action: str,
    description: str,
    account: Cuenta | None = None,
    user: Usuario | None = None,
    reference: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    http_method: str | None = None,
    module: str | None = None,
    submodule: str | None = None,
    table: str | None = None,
    functional_action: str | None = None,
    field_name: str | None = None,
    old_value: Any | None = None,
    new_value: Any | None = None,
    event_id: str | None = None,
) -> AuditoriaSistema:
    descriptor = _descriptor_for_action(action, description)
    summary = register_audit_summary(
        db,
        descriptor=descriptor,
        description=description,
        account=account,
        user=user,
        reference=reference,
        ip_address=ip_address,
        user_agent=user_agent,
        http_method=http_method,
        event_id=event_id,
        module=module,
        submodule=submodule,
        table=table,
        functional_action=functional_action,
    )
    if field_name is not None:
        register_audit_field_change(
            db,
            descriptor=descriptor,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            description=description,
            account=account,
            user=user,
            reference=reference,
            ip_address=ip_address,
            user_agent=user_agent,
            http_method=http_method,
            event_id=event_id,
            module=module,
            submodule=submodule,
            table=table,
            functional_action=functional_action,
        )
    return summary
