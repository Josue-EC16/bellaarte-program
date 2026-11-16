from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMBaseModel


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


class RoleUpdateRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    descripcion: str | None = Field(default=None, max_length=500)


class RoleStatusUpdateRequest(BaseModel):
    activo: bool
