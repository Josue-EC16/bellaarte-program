from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.audit import register_audit_event
from app.models.account import Cuenta
from app.models.boutique_enums import EstadoCorteCajaEnum, EstadoEgresoEnum, TipoEgresoEnum
from app.models.economy import CorteCaja, Egreso
from app.models.user import Usuario
from app.schemas.economy import CashCutMiniSummary, ExpenseCreateRequest, ExpenseDetailResponse, ExpenseListItem, ExpenseAnnulRequest, UserMiniSummary


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _is_admin(account: Cuenta) -> bool:
    return account.rol.codigo == "ADMIN"


def _active_cut_for_cajero(db: Session, *, cajero_id: int) -> CorteCaja | None:
    return db.execute(
        select(CorteCaja)
        .options(joinedload(CorteCaja.cajero), joinedload(CorteCaja.admin))
        .where(CorteCaja.cajero_id == cajero_id, CorteCaja.estado == EstadoCorteCajaEnum.ABIERTO)
    ).scalar_one_or_none()


def _expense_cut_for_account(db: Session, *, account: Cuenta) -> CorteCaja | None:
    if _is_admin(account):
        return None
    if account.rol.codigo != "CAJA":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para registrar egresos.")
    cut = _active_cut_for_cajero(db, cajero_id=account.usuario_id)
    if cut is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="NO TIENES UN CORTE DE CAJA ABIERTO. CONTACTA AL ADMINISTRADOR.")
    return cut


def _to_user_summary(user: Usuario | None) -> UserMiniSummary | None:
    if user is None:
        return None
    return UserMiniSummary(
        id=user.id,
        full_name=user.nombre_completo,
        username=user.cuenta.username if user.cuenta else None,
    )


def _to_cut_summary(cut: CorteCaja | None) -> CashCutMiniSummary | None:
    if cut is None:
        return None
    return CashCutMiniSummary(
        id=cut.id,
        estado=cut.estado,
        fecha_apertura=cut.fecha_apertura,
        fecha_cierre=cut.fecha_cierre,
        fondo_asignado=float(cut.fondo_asignado),
    )


def _to_expense_list_item(expense: Egreso) -> ExpenseListItem:
    return ExpenseListItem(
        id=expense.id,
        fecha=expense.fecha,
        tipo=expense.tipo,
        concepto=expense.concepto,
        cantidad=float(expense.cantidad),
        precio_unidad=float(expense.precio_unidad),
        monto=float(expense.monto),
        beneficiario=expense.beneficiario,
        estado=expense.estado,
        usuario=_to_user_summary(expense.usuario),
        corte=_to_cut_summary(expense.corte),
        tabla_referencia=expense.tabla_referencia,
        id_referencia=expense.id_referencia,
    )


def _to_expense_detail(expense: Egreso) -> ExpenseDetailResponse:
    base = _to_expense_list_item(expense).model_dump()
    return ExpenseDetailResponse(
        **base,
        observaciones_1=expense.observaciones_1,
        observaciones_2=expense.observaciones_2,
        fecha_cambio_estado=expense.fecha_cambio_estado,
        motivo_cambio_estado=expense.motivo_cambio_estado,
    )


def _get_expense_entity(db: Session, *, expense_id: int) -> Egreso:
    expense = db.execute(
        select(Egreso)
        .options(
            joinedload(Egreso.usuario).joinedload(Usuario.cuenta),
            joinedload(Egreso.corte).joinedload(CorteCaja.cajero).joinedload(Usuario.cuenta),
            joinedload(Egreso.corte).joinedload(CorteCaja.admin).joinedload(Usuario.cuenta),
        )
        .where(Egreso.id == expense_id)
    ).scalar_one_or_none()
    if expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Egreso no encontrado.")
    return expense


def create_expense_record(
    db: Session,
    *,
    account: Cuenta,
    tipo: TipoEgresoEnum,
    concepto: str,
    cantidad: float,
    precio_unidad: float,
    beneficiario: str | None,
    observaciones_1: str | None,
    observaciones_2: str | None,
    tabla_referencia: str | None = None,
    id_referencia: int | None = None,
) -> Egreso:
    cut = _expense_cut_for_account(db, account=account)
    expense = Egreso(
        usuario_id=account.usuario_id,
        corte_id=cut.id if cut else None,
        tipo=tipo,
        concepto=concepto,
        cantidad=cantidad,
        precio_unidad=precio_unidad,
        beneficiario=beneficiario,
        observaciones_1=observaciones_1,
        observaciones_2=observaciones_2,
        estado=EstadoEgresoEnum.REGISTRADO,
        tabla_referencia=tabla_referencia,
        id_referencia=id_referencia,
    )
    db.add(expense)
    db.flush()
    db.refresh(expense)
    return expense


def create_expense(
    db: Session,
    *,
    payload: ExpenseCreateRequest,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> ExpenseDetailResponse:
    if payload.tipo == TipoEgresoEnum.DEVOLUCION:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Las DEVOLUCIONES deben registrarse desde el flujo económico obligatorio de anulación.",
        )
    expense = create_expense_record(
        db,
        account=created_by,
        tipo=payload.tipo,
        concepto=payload.concepto,
        cantidad=payload.cantidad,
        precio_unidad=payload.precio_unidad,
        beneficiario=payload.beneficiario,
        observaciones_1=payload.observaciones_1,
        observaciones_2=payload.observaciones_2,
    )
    register_audit_event(
        db,
        action="ECONOMY_EXPENSE_CREATED",
        description=f"SE REGISTRÓ EL EGRESO '{expense.id}' DE TIPO '{expense.tipo.value.upper()}'.",
        account=created_by,
        user=created_by.usuario,
        reference=str(expense.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_expense_detail(db, expense_id=expense.id, account=created_by)


def list_expenses(
    db: Session,
    *,
    account: Cuenta,
    search: str | None = None,
    expense_type: TipoEgresoEnum | None = None,
    state: EstadoEgresoEnum | None = None,
    cut_id: int | None = None,
    date_from=None,
    date_to=None,
) -> list[ExpenseListItem]:
    stmt = (
        select(Egreso)
        .options(
            joinedload(Egreso.usuario).joinedload(Usuario.cuenta),
            joinedload(Egreso.corte).joinedload(CorteCaja.cajero).joinedload(Usuario.cuenta),
            joinedload(Egreso.corte).joinedload(CorteCaja.admin).joinedload(Usuario.cuenta),
        )
        .order_by(Egreso.fecha.desc(), Egreso.id.desc())
    )
    if not _is_admin(account):
        stmt = stmt.join(Egreso.corte).where(CorteCaja.cajero_id == account.usuario_id)
        if cut_id is not None:
            stmt = stmt.where(Egreso.corte_id == cut_id)
    elif cut_id is not None:
        stmt = stmt.where(Egreso.corte_id == cut_id)
    if expense_type is not None:
        stmt = stmt.where(Egreso.tipo == expense_type)
    if state is not None:
        stmt = stmt.where(Egreso.estado == state)
    if date_from is not None:
        stmt = stmt.where(func.date(Egreso.fecha) >= date_from)
    if date_to is not None:
        stmt = stmt.where(func.date(Egreso.fecha) <= date_to)
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.where(
            or_(
                func.upper(Egreso.concepto).like(term),
                func.upper(func.coalesce(Egreso.beneficiario, "")).like(term),
                func.upper(func.coalesce(Egreso.observaciones_1, "")).like(term),
            )
        )
    return [_to_expense_list_item(item) for item in db.execute(stmt).unique().scalars().all()]


def get_expense_detail(
    db: Session,
    *,
    expense_id: int,
    account: Cuenta,
) -> ExpenseDetailResponse:
    expense = _get_expense_entity(db, expense_id=expense_id)
    if not _is_admin(account):
        if expense.corte is None or expense.corte.cajero_id != account.usuario_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a ese egreso.")
    return _to_expense_detail(expense)


def annul_expense(
    db: Session,
    *,
    expense_id: int,
    payload: ExpenseAnnulRequest,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> ExpenseDetailResponse:
    expense = _get_expense_entity(db, expense_id=expense_id)
    if expense.estado != EstadoEgresoEnum.REGISTRADO:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo puedes anular egresos registrados.")
    if not _is_admin(changed_by):
        active_cut = _active_cut_for_cajero(db, cajero_id=changed_by.usuario_id)
        if active_cut is None or expense.corte_id != active_cut.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo puedes anular egresos de tu corte activo.")
    expense.estado = EstadoEgresoEnum.ANULADO
    expense.fecha_cambio_estado = _utc_now()
    expense.motivo_cambio_estado = payload.motivo
    register_audit_event(
        db,
        action="ECONOMY_EXPENSE_ANNULLED",
        description=f"SE ANULÓ EL EGRESO '{expense.id}'.",
        account=changed_by,
        user=changed_by.usuario,
        reference=str(expense.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_expense_detail(db, expense_id=expense.id, account=changed_by)
