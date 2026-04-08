AUTHENTICATED_PERMISSIONS = (
    "dashboard:view",
    "auth:me",
    "auth:change_password",
    "auth:logout",
)

ADMIN_PERMISSIONS = (
    "users:list",
    "users:create",
    "users:update_status",
    "roles:list",
)


def build_permissions_for_role(role_code: str) -> list[str]:
    permissions = list(AUTHENTICATED_PERMISSIONS)
    if role_code == "ADMIN":
        permissions.extend(ADMIN_PERMISSIONS)
    return sorted(set(permissions))

