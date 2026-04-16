from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMBaseModel


class UserSummary(ORMBaseModel):
    id: int
    full_name: str
    role_code: str
    role_name: str
    username: str
    must_change_password: bool
    permissions: list[str]


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSummary


class MeResponse(BaseModel):
    user: UserSummary


class CreateUserRequest(BaseModel):
    nombres: str = Field(min_length=2, max_length=120)
    apellido_paterno: str = Field(min_length=2, max_length=120)
    apellido_materno: str | None = Field(default=None, max_length=120)
    ci: str = Field(min_length=3, max_length=30)
    celular: str = Field(min_length=6, max_length=30)
    correo: EmailStr
    zona: str = Field(min_length=2, max_length=120)
    direccion: str | None = Field(default=None, max_length=500)
    username: str = Field(min_length=3, max_length=50)
    password_temporal: str = Field(min_length=8, max_length=128)
    role_code: str = Field(min_length=2, max_length=50)


class StatusUpdateRequest(BaseModel):
    is_active: bool


class UpdateUserRequest(BaseModel):
    nombres: str = Field(min_length=2, max_length=120)
    apellido_paterno: str = Field(min_length=2, max_length=120)
    apellido_materno: str | None = Field(default=None, max_length=120)
    ci: str = Field(min_length=3, max_length=30)
    celular: str = Field(min_length=6, max_length=30)
    correo: EmailStr
    zona: str = Field(min_length=2, max_length=120)
    direccion: str | None = Field(default=None, max_length=500)
    username: str = Field(min_length=3, max_length=50)
    role_code: str = Field(min_length=2, max_length=50)
    user_is_active: bool = True
    account_is_active: bool = True


class ResetPasswordRequest(BaseModel):
    temporary_password: str = Field(min_length=8, max_length=128)
