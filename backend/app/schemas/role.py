from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMBaseModel
from app.core.user_validation import clean_user_text, meaningful_user_text


class RoleResponse(ORMBaseModel):
    id: int
    codigo: str
    nombre: str
    descripcion: str | None
    activo: bool
    created_at: datetime | None = None


class RoleCreateRequest(BaseModel):
    codigo: str = Field(min_length=2, max_length=50)
    nombre: str = Field(min_length=2, max_length=120)
    descripcion: str | None = Field(default=None, max_length=500)

    @field_validator("codigo", "nombre", mode="before")
    @classmethod
    def required_content(cls, value):
        return meaningful_user_text(value).upper() if isinstance(value, str) else value

    @field_validator("descripcion", mode="before")
    @classmethod
    def optional_content(cls, value):
        return clean_user_text(value) or None if isinstance(value, str) else value


class RoleUpdateRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    descripcion: str | None = Field(default=None, max_length=500)

    @field_validator("nombre", mode="before")
    @classmethod
    def required_content(cls, value):
        return meaningful_user_text(value).upper() if isinstance(value, str) else value

    @field_validator("descripcion", mode="before")
    @classmethod
    def optional_content(cls, value):
        return clean_user_text(value) or None if isinstance(value, str) else value


class RoleStatusUpdateRequest(BaseModel):
    activo: bool
