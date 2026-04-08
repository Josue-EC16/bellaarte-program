from app.schemas.common import ORMBaseModel


class RoleResponse(ORMBaseModel):
    id: int
    codigo: str
    nombre: str
    descripcion: str | None
    activo: bool

