import re
from pydantic import BaseModel, EmailStr, Field, field_validator

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

    @field_validator("new_password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        if not re.search(r"[a-z]", v):
            raise ValueError("La contraseña debe contener al menos una letra minúscula.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("La contraseña debe contener al menos una letra mayúscula.")
        if not re.search(r"\d", v):
            raise ValueError("La contraseña debe contener al menos un número.")
        if not re.search(r"[^A-Za-z0-9]", v):
            raise ValueError("La contraseña debe contener al menos un carácter especial.")
        return v

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
    role_code: str = Field(min_length=2, max_length=50)
    user_is_active: bool = True
    account_is_active: bool = True


class ResetPasswordRequest(BaseModel):
    pass
