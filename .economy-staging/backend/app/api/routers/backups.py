from datetime import date

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps.auth import require_permission
from app.models.account import Cuenta
from app.models.boutique_enums import EstadoBackupBdEnum, TipoBackupBdEnum
from app.schemas.backup import (
    BackupActiveStatusResponse,
    BackupCheckFileResponse,
    BackupDetailResponse,
    BackupListItem,
    BackupQueryFilters,
    BackupRunResponse,
)
from app.services.backup_service import (
    check_backup_file,
    get_active_backup_status,
    get_backup_detail,
    get_downloadable_backup_path,
    list_backups,
    run_backup_process,
)


router = APIRouter()


def _filters_from_query(
    *,
    tipo: TipoBackupBdEnum | None,
    estado: EstadoBackupBdEnum | None,
    origen: str | None,
    usuario_id: int | None,
    date_from: date | None,
    date_to: date | None,
    search: str | None,
) -> BackupQueryFilters:
    return BackupQueryFilters(
        tipo=tipo,
        estado=estado,
        origen=origen,
        usuario_id=usuario_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )


@router.get("", response_model=list[BackupListItem])
def get_backups(
    tipo: TipoBackupBdEnum | None = Query(default=None),
    estado: EstadoBackupBdEnum | None = Query(default=None),
    origen: str | None = Query(default=None),
    usuario_id: int | None = Query(default=None, gt=0),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1),
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("backups:list")),
) -> list[BackupListItem]:
    return list_backups(
        db,
        account=account,
        filters=_filters_from_query(
            tipo=tipo,
            estado=estado,
            origen=origen,
            usuario_id=usuario_id,
            date_from=date_from,
            date_to=date_to,
            search=search,
        ),
    )


@router.get("/status/active", response_model=BackupActiveStatusResponse)
def get_backup_active_status(
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("backups:view")),
) -> BackupActiveStatusResponse:
    return get_active_backup_status(db, account=account)


@router.get("/{backup_id}", response_model=BackupDetailResponse)
def get_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("backups:view")),
) -> BackupDetailResponse:
    return get_backup_detail(db, backup_id=backup_id, account=account)


@router.post("/run", response_model=BackupRunResponse, status_code=status.HTTP_201_CREATED)
def run_backup_now(
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("backups:create")),
) -> BackupRunResponse:
    return run_backup_process(
        db,
        backup_type=TipoBackupBdEnum.MANUAL,
        origin="MANUAL",
        requested_by=account,
        observation="BACKUP MANUAL SOLICITADO DESDE EL PANEL ADMIN.",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/{backup_id}/check-file", response_model=BackupCheckFileResponse)
def check_backup_storage_file(
    backup_id: int,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("backups:view")),
) -> BackupCheckFileResponse:
    return check_backup_file(db, backup_id=backup_id, account=account)


@router.get("/{backup_id}/download")
def download_backup_file(
    backup_id: int,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("backups:download")),
):
    entity, file_path = get_downloadable_backup_path(
        db,
        backup_id=backup_id,
        account=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return FileResponse(
        path=file_path,
        media_type="application/octet-stream",
        filename=entity.nombre_archivo,
    )
