import re
import unicodedata
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.common import ORMBaseModel
from app.core.user_validation import clean_user_text, collaborator_ci, meaningful_user_text, user_name


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

    @field_validator("username", mode="before")
    @classmethod
    def validate_login_name(cls, value):
        return meaningful_user_text(value) if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def validate_nonblank_password(cls, value):
        if not value.strip():
            raise ValueError("Debe ingresar su contraseña.")
        return value


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        if any(unicodedata.category(char) == "Cc" for char in v):
            raise ValueError("La contraseña no puede contener caracteres de control.")
        if len(v.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede superar 72 bytes UTF-8.")
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
    ci: str = Field(min_length=7, max_length=30)
    celular: str = Field(min_length=8, max_length=30)
    correo: EmailStr
    zona: str = Field(min_length=2, max_length=120)
    direccion: str | None = Field(default=None, max_length=500)
    role_code: str = Field(min_length=2, max_length=50)

    @field_validator("nombres", "apellido_paterno", mode="before")
    @classmethod
    def validate_names(cls, value):
        if isinstance(value, str):
            value = user_name(value)
            if sum(char.isalpha() for char in value) < 2:
                raise ValueError("Debe ingresar al menos dos letras; los espacios no cuentan.")
        return value

    @field_validator("apellido_materno", mode="before")
    @classmethod
    def validate_optional_name(cls, value):
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return user_name(value) if isinstance(value, str) else value

    @field_validator("ci")
    @classmethod
    def validate_ci(cls, value):
        return collaborator_ci(value)

    @field_validator("celular", mode="before")
    @classmethod
    def validate_cellphone(cls, value):
        if isinstance(value, str) and not re.fullmatch(r"[0-9]{8,30}", value):
            raise ValueError("El celular debe contener entre 8 y 30 dígitos, sin espacios.")
        return value

    @field_validator("zona", mode="before")
    @classmethod
    def validate_required_text(cls, value):
        if isinstance(value, str):
            value = meaningful_user_text(value).upper()
            if sum(char.isalnum() for char in value) < 2:
                raise ValueError("Debe ingresar al menos dos letras o números; los espacios no cuentan.")
        return value

    @field_validator("role_code", mode="before")
    @classmethod
    def validate_role_code(cls, value):
        return meaningful_user_text(value).upper() if isinstance(value, str) else value

    @field_validator("correo", mode="before")
    @classmethod
    def validate_email_text(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("direccion", mode="before")
    @classmethod
    def validate_optional_text(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            return clean_user_text(value).upper() or None
        return value


class StatusUpdateRequest(BaseModel):
    is_active: bool


class UpdateUserRequest(CreateUserRequest):
    user_is_active: bool = True
    account_is_active: bool = True


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
