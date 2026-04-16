from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMBaseModel


class ClienteCreateRequest(BaseModel):
    codigo: str | None = Field(default=None, max_length=20)
    nombres: str = Field(min_length=2, max_length=100)
    apellido_paterno: str = Field(min_length=2, max_length=100)
    apellido_materno: str | None = Field(default=None, max_length=100)
    celular: str = Field(min_length=6, max_length=30)
    celular_referencia: str | None = Field(default=None, max_length=30)
    nombre_referencia: str | None = Field(default=None, max_length=120)
    correo: EmailStr | None = None
    ci: str | None = Field(default=None, max_length=30)
    nacionalidad: str | None = Field(default=None, max_length=100)
    zona: str | None = Field(default=None, max_length=100)
    calle: str | None = Field(default=None, max_length=100)
    observaciones: str | None = None


class ClienteUpdateRequest(ClienteCreateRequest):
    pass


class ClienteStatusUpdateRequest(BaseModel):
    habilitado: bool


class ClienteListItem(ORMBaseModel):
    id: int
    codigo: str
    full_name: str
    celular: str
    correo: str | None
    ci: str | None
    zona: str | None
    is_active: bool
    created_at: datetime


class ClienteDetailResponse(ORMBaseModel):
    id: int
    codigo: str
    nombres: str
    apellido_paterno: str
    apellido_materno: str | None
    full_name: str
    celular: str
    celular_referencia: str | None
    nombre_referencia: str | None
    correo: str | None
    ci: str | None
    nacionalidad: str | None
    zona: str | None
    calle: str | None
    observaciones: str | None
    is_active: bool
    created_at: datetime
