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
    user_is_active: bool
    account_is_active: bool
    must_change_password: bool
    last_login_at: datetime | None


class UserCreateResponse(ORMBaseModel):
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
    user_is_active: bool
    account_is_active: bool
    must_change_password: bool
    last_login_at: datetime | None = None


class UserDetailResponse(UserCreateResponse):
    nombres: str
    apellido_paterno: str
    apellido_materno: str | None
    direccion: str | None
