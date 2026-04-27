AUTHENTICATED_PERMISSIONS = (
    "dashboard:view",
    "auth:me",
    "auth:change_password",
    "auth:logout",
)

ADMIN_PERMISSIONS = (
    "users:list",
    "users:view",
    "users:create",
    "users:update",
    "users:update_status",
    "users:reset_password",
    "roles:list",
    "roles:view",
    "roles:create",
    "roles:update",
    "roles:update_status",
    "clients:list",
    "clients:view",
    "clients:create",
    "clients:update",
    "clients:update_status",
    "boutique_types:list",
    "boutique_types:create",
    "boutique_types:update",
    "boutique_types:update_status",
    "boutique_items:list",
    "boutique_items:view",
    "boutique_items:create",
    "boutique_items:update",
    "boutique_items:update_status",
    "boutique_sales:list",
    "boutique_sales:view",
    "boutique_sales:create",
    "boutique_sales:cancel",
    "boutique_sales:annul",
)

INV_BOUTIQUE_PERMISSIONS = (
    "boutique_types:list",
    "boutique_types:create",
    "boutique_types:update",
    "boutique_types:update_status",
    "boutique_items:list",
    "boutique_items:view",
    "boutique_items:create",
    "boutique_items:update",
    "boutique_items:update_status",
    "boutique_sales:list",
    "boutique_sales:view",
)

CAJA_PERMISSIONS = (
    "clients:list",
    "clients:view",
    "boutique_types:list",
    "boutique_items:list",
    "boutique_items:view",
    "boutique_sales:list",
    "boutique_sales:view",
    "boutique_sales:create",
    "boutique_sales:cancel",
    "boutique_sales:annul",
)

MODISTA_PERMISSIONS = (
    "clients:list",
    "clients:view",
    "clients:create",
    "clients:update",
    "clients:update_status",
)


def build_permissions_for_role(role_code: str) -> list[str]:
    permissions = list(AUTHENTICATED_PERMISSIONS)
    if role_code == "ADMIN":
        permissions.extend(ADMIN_PERMISSIONS)
    if role_code == "INV_BOUTIQUE":
        permissions.extend(INV_BOUTIQUE_PERMISSIONS)
    if role_code == "CAJA":
        permissions.extend(CAJA_PERMISSIONS)
    if role_code == "MODISTA":
        permissions.extend(MODISTA_PERMISSIONS)
    return sorted(set(permissions))
