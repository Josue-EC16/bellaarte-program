from __future__ import annotations

from datetime import datetime, time
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.audit import register_audit_event, register_audit_failure
from app.core.backup_runtime import (
    BACKUP_BLOCKED_MESSAGE,
    backup_lock,
    is_backup_lock_active,
    read_backup_lock,
    release_stale_lock_if_safe,
    update_backup_lock,
)
from app.models.account import Cuenta
from app.models.backup import BackupBd
from app.models.boutique_enums import EstadoBackupBdEnum, TipoBackupBdEnum
from app.models.user import Usuario
from app.schemas.backup import (
    BackupActiveStatusResponse,
    BackupCheckFileResponse,
    BackupDetailResponse,
    BackupListItem,
    BackupQueryFilters,
    BackupRunResponse,
    BackupUserSummary,
)
from scripts.backup_manager import BackupResult, generate_backup


def _ensure_admin(account: Cuenta) -> None:
    if account.rol.codigo != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="SOLO EL ADMIN PUEDE ACCEDER AL MÓDULO DE BACKUPS.")


def _user_summary(user: Usuario | None) -> BackupUserSummary | None:
    if user is None:
        return None
    cuenta = user.cuenta
    return BackupUserSummary(
        id=user.id,
        full_name=user.nombre_completo,
        username=cuenta.username if cuenta else None,
    )


def _file_exists(path_value: str) -> bool:
    return Path(path_value).exists()


def _to_list_item(entity: BackupBd) -> BackupListItem:
    return BackupListItem(
        id=entity.id,
        tipo=entity.tipo,
        estado=entity.estado,
        origen=entity.origen,
        nombre_archivo=entity.nombre_archivo,
        tamano_bytes=entity.tamano_bytes,
        hash_sha256=entity.hash_sha256,
        fecha_inicio=entity.fecha_inicio,
        fecha_fin=entity.fecha_fin,
        pg_dump_version=entity.pg_dump_version,
        db_nombre=entity.db_nombre,
        usuario=_user_summary(entity.usuario),
        file_exists=_file_exists(entity.ruta_archivo),
    )


def _to_detail_response(entity: BackupBd) -> BackupDetailResponse:
    base = _to_list_item(entity)
    return BackupDetailResponse(
        **base.model_dump(),
        ruta_archivo=entity.ruta_archivo,
        observacion=entity.observacion,
        error=entity.error,
    )


def _base_stmt():
    return select(BackupBd).options(joinedload(BackupBd.usuario).joinedload(Usuario.cuenta))


def _apply_filters(stmt, filters: BackupQueryFilters):
    if filters.tipo is not None:
        stmt = stmt.where(BackupBd.tipo == filters.tipo)
    if filters.estado is not None:
        stmt = stmt.where(BackupBd.estado == filters.estado)
    if filters.origen:
        stmt = stmt.where(func.upper(BackupBd.origen) == filters.origen)
    if filters.usuario_id is not None:
        stmt = stmt.where(BackupBd.usuario_id == filters.usuario_id)
    if filters.date_from is not None:
        stmt = stmt.where(BackupBd.fecha_inicio >= datetime.combine(filters.date_from, time.min))
    if filters.date_to is not None:
        stmt = stmt.where(BackupBd.fecha_inicio <= datetime.combine(filters.date_to, time.max))
    if filters.search:
        search_term = f"%{filters.search}%"
        stmt = stmt.where(
            or_(
                func.upper(BackupBd.nombre_archivo).like(search_term),
                func.upper(BackupBd.ruta_archivo).like(search_term),
                func.upper(func.coalesce(BackupBd.hash_sha256, "")).like(search_term),
                func.upper(func.coalesce(BackupBd.db_nombre, "")).like(search_term),
                func.upper(func.coalesce(BackupBd.error, "")).like(search_term),
            )
        )
    return stmt


def list_backups(
    db: Session,
    *,
    account: Cuenta,
    filters: BackupQueryFilters,
) -> list[BackupListItem]:
    _ensure_admin(account)
    stmt = _apply_filters(_base_stmt(), filters).order_by(BackupBd.fecha_inicio.desc(), BackupBd.id.desc())
    return [_to_list_item(item) for item in db.execute(stmt).scalars().all()]


def get_backup_detail(
    db: Session,
    *,
    backup_id: int,
    account: Cuenta,
) -> BackupDetailResponse:
    _ensure_admin(account)
    entity = db.execute(_base_stmt().where(BackupBd.id == backup_id)).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BACKUP NO ENCONTRADO.")
    return _to_detail_response(entity)


def check_backup_file(
    db: Session,
    *,
    backup_id: int,
    account: Cuenta,
) -> BackupCheckFileResponse:
    detail = get_backup_detail(db, backup_id=backup_id, account=account)
    path = Path(detail.ruta_archivo)
    return BackupCheckFileResponse(
        id=detail.id,
        exists=path.exists(),
        nombre_archivo=detail.nombre_archivo,
        ruta_archivo=detail.ruta_archivo,
        tamano_registrado_bytes=detail.tamano_bytes,
        tamano_actual_bytes=path.stat().st_size if path.exists() else None,
    )


def _backup_in_progress_exists(db: Session) -> bool:
    count = db.execute(
        select(func.count(BackupBd.id)).where(BackupBd.estado == EstadoBackupBdEnum.EN_PROCESO)
    ).scalar_one()
    return bool(count)


def _cleanup_stale_runtime_lock(db: Session) -> None:
    release_stale_lock_if_safe(_backup_in_progress_exists(db))


def cleanup_stale_backup_lock(db: Session) -> None:
    _cleanup_stale_runtime_lock(db)


def get_active_backup_status(db: Session, *, account: Cuenta) -> BackupActiveStatusResponse:
    _ensure_admin(account)
    lock_payload = read_backup_lock()
    active_row = db.execute(
        select(BackupBd).where(BackupBd.estado == EstadoBackupBdEnum.EN_PROCESO).order_by(BackupBd.fecha_inicio.desc(), BackupBd.id.desc())
    ).scalar_one_or_none()
    if not lock_payload and active_row is None:
        return BackupActiveStatusResponse(active=False)
    return BackupActiveStatusResponse(
        active=True,
        message=(lock_payload or {}).get("message") or BACKUP_BLOCKED_MESSAGE,
        backup_id=active_row.id if active_row else (lock_payload or {}).get("backup_id"),
        tipo=active_row.tipo.value if active_row else (lock_payload or {}).get("tipo"),
        origen=active_row.origen if active_row else (lock_payload or {}).get("origen"),
        created_at=(lock_payload or {}).get("created_at"),
    )


def _create_in_progress_record(
    db: Session,
    *,
    requested_by: Cuenta | None,
    backup_type: TipoBackupBdEnum,
    origin: str,
    observation: str | None,
    ip_address: str | None,
    user_agent: str | None,
    action_name: str,
) -> BackupBd:
    entity = BackupBd(
        usuario_id=requested_by.usuario_id if requested_by else None,
        tipo=backup_type,
        estado=EstadoBackupBdEnum.EN_PROCESO,
        origen=origin,
        nombre_archivo="PENDIENTE",
        ruta_archivo="PENDIENTE",
        observacion=observation,
    )
    db.add(entity)
    db.flush()
    register_audit_event(
        db,
        action=action_name,
        description=f"SE INICIÓ UN BACKUP {origin} DE TIPO {backup_type.value}.",
        account=requested_by,
        user=requested_by.usuario if requested_by else None,
        reference=str(entity.id),
        ip_address=ip_address,
        user_agent=user_agent,
        module="BACKUPS",
        submodule="GENERACION",
        table="backup_bd",
        functional_action="INICIO DE BACKUP",
    )
    db.commit()
    db.refresh(entity)
    return entity


def _mark_backup_success(
    db: Session,
    *,
    entity: BackupBd,
    result: BackupResult,
    requested_by: Cuenta | None,
    ip_address: str | None,
    user_agent: str | None,
    action_name: str,
) -> BackupRunResponse:
    entity.nombre_archivo = result.file_name
    entity.ruta_archivo = result.file_path
    entity.tamano_bytes = result.file_size_bytes
    entity.hash_sha256 = result.sha256_hash
    entity.pg_dump_version = result.pg_dump_version
    entity.db_nombre = result.database_name
    entity.fecha_fin = result.finished_at
    entity.estado = EstadoBackupBdEnum.EXITOSO
    entity.error = None
    db.add(entity)
    register_audit_event(
        db,
        action=action_name,
        description=f"EL BACKUP '{result.file_name}' SE GENERÓ CORRECTAMENTE.",
        account=requested_by,
        user=requested_by.usuario if requested_by else None,
        reference=str(entity.id),
        ip_address=ip_address,
        user_agent=user_agent,
        module="BACKUPS",
        submodule="GENERACION",
        table="backup_bd",
        functional_action="BACKUP EXITOSO",
    )
    db.commit()
    db.refresh(entity)
    return BackupRunResponse(
        **_to_detail_response(entity).model_dump(),
        message="BACKUP GENERADO CORRECTAMENTE.",
    )


def _mark_backup_failed(
    db: Session,
    *,
    entity: BackupBd,
    result: BackupResult,
    requested_by: Cuenta | None,
    ip_address: str | None,
    user_agent: str | None,
) -> BackupRunResponse:
    entity.nombre_archivo = result.file_name
    entity.ruta_archivo = result.file_path
    entity.fecha_fin = result.finished_at
    entity.estado = EstadoBackupBdEnum.FALLIDO
    entity.error = result.error or "NO FUE POSIBLE GENERAR EL BACKUP."
    db.add(entity)
    register_audit_failure(
        db,
        action="BACKUP_FAILED",
        description=f"FALLÓ LA GENERACIÓN DEL BACKUP {entity.origen}. {entity.error}",
        account=requested_by,
        user=requested_by.usuario if requested_by else None,
        reference=str(entity.id),
        ip_address=ip_address,
        user_agent=user_agent,
        http_method="POST" if requested_by else "CLI",
    )
    db.commit()
    db.refresh(entity)
    return BackupRunResponse(
        **_to_detail_response(entity).model_dump(),
        message="EL BACKUP FALLÓ.",
    )


def run_backup_process(
    db: Session,
    *,
    backup_type: TipoBackupBdEnum,
    origin: str,
    requested_by: Cuenta | None = None,
    observation: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> BackupRunResponse:
    if requested_by is not None:
        _ensure_admin(requested_by)
    _cleanup_stale_runtime_lock(db)
    if _backup_in_progress_exists(db) or is_backup_lock_active():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="YA EXISTE UN BACKUP EN PROCESO. ESPERE A QUE FINALICE ANTES DE INICIAR OTRO.")

    start_action = "BACKUP_MANUAL_STARTED" if origin == "MANUAL" else "BACKUP_AUTOMATIC_STARTED"
    end_action = "BACKUP_MANUAL_COMPLETED" if origin == "MANUAL" else "BACKUP_AUTOMATIC_COMPLETED"

    with backup_lock({"origin": origin, "tipo": backup_type.value}):
        entity = _create_in_progress_record(
            db,
            requested_by=requested_by,
            backup_type=backup_type,
            origin=origin,
            observation=observation,
            ip_address=ip_address,
            user_agent=user_agent,
            action_name=start_action,
        )
        update_backup_lock({"backup_id": entity.id})
        result = generate_backup()
        if result.success:
            return _mark_backup_success(
                db,
                entity=entity,
                result=result,
                requested_by=requested_by,
                ip_address=ip_address,
                user_agent=user_agent,
                action_name=end_action,
            )
        return _mark_backup_failed(
            db,
            entity=entity,
            result=result,
            requested_by=requested_by,
            ip_address=ip_address,
            user_agent=user_agent,
        )


def get_downloadable_backup_path(
    db: Session,
    *,
    backup_id: int,
    account: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> tuple[BackupBd, Path]:
    _ensure_admin(account)
    entity = db.execute(_base_stmt().where(BackupBd.id == backup_id)).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BACKUP NO ENCONTRADO.")
    if entity.estado != EstadoBackupBdEnum.EXITOSO:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SOLO SE PUEDEN DESCARGAR BACKUPS EXITOSOS.")

    file_path = Path(entity.ruta_archivo)
    if not file_path.exists():
        register_audit_failure(
            db,
            action="BACKUP_DOWNLOAD_FAILED",
            description=f"SE INTENTÓ DESCARGAR EL BACKUP '{entity.nombre_archivo}', PERO EL ARCHIVO NO EXISTE.",
            account=account,
            user=account.usuario,
            reference=str(entity.id),
            ip_address=ip_address,
            user_agent=user_agent,
            http_method="GET",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="EL ARCHIVO DEL BACKUP YA NO EXISTE EN EL ALMACENAMIENTO.")

    register_audit_event(
        db,
        action="BACKUP_DOWNLOADED",
        description=f"SE DESCARGÓ EL BACKUP '{entity.nombre_archivo}'.",
        account=account,
        user=account.usuario,
        reference=str(entity.id),
        ip_address=ip_address,
        user_agent=user_agent,
        http_method="GET",
        module="BACKUPS",
        submodule="DESCARGA",
        table="backup_bd",
        functional_action="DESCARGA DE BACKUP",
    )
    db.commit()
    return entity, file_path
