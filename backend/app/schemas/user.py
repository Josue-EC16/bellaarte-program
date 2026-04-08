from datetime import datetime

from app.schemas.common import ORMBaseModel


class UserListItem(ORMBaseModel):
    id: int
    user_id: int
    full_name: str
    username: str
    correo: str
    ci: str
    celular: str
    zona: str
    role_code: str
    role_name: str
    is_active: bool
    must_change_password: bool
    last_login_at: datetime | None


class UserCreateResponse(ORMBaseModel):
    id: int
    user_id: int
    full_name: str
    username: str
    role_code: str
    role_name: str
    is_active: bool
    must_change_password: bool
