from datetime import date

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps.auth import require_permission
from app.models.account import Cuenta
from app.models.boutique_enums import EstadoFleteEnum, EstadoSalidaFleteEnum
from app.schemas.flete import (
    FleteCreateRequest,
    FleteDetailResponse,
    FleteDisableRequest,
    FleteEligibleItemSummary,
    FleteListItem,
    FletePassToSaleRequest,
    FletePassToSaleResponse,
    FleteResolveReviewRequest,
    FleteRetireRequest,
    FleteUpdateRequest,
    SalidaFleteAnnulRequest,
    SalidaFleteCreateRequest,
    SalidaFleteDeliverRequest,
    SalidaFleteDetailResponse,
    SalidaFleteListItem,
    SalidaFleteReturnRequest,
)
from app.services.flete_service import (
    annul_flete_output,
    create_flete,
    create_flete_output,
    deliver_flete_output,
    disable_flete,
    get_flete_detail,
    get_flete_output_detail,
    list_eligible_flete_items,
    list_flete_outputs,
    list_fletes,
    pass_flete_to_sale,
    resolve_flete_review,
    retire_flete,
    return_flete_output,
    update_flete,
)


router = APIRouter()


@router.get("", response_model=list[FleteListItem])
def get_fletes(
    search: str | None = Query(default=None, min_length=1),
    state: EstadoFleteEnum | None = Query(default=None),
    is_enabled: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("fletes:list")),
) -> list[FleteListItem]:
    return list_fletes(db, search=search, state=state, is_enabled=is_enabled)


@router.get("/eligible-items", response_model=list[FleteEligibleItemSummary])
def get_eligible_items(
    search: str | None = Query(default=None, min_length=1),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("fletes:list")),
) -> list[FleteEligibleItemSummary]:
    return list_eligible_flete_items(db, search=search)


@router.get("/salidas", response_model=list[SalidaFleteListItem])
def get_outputs(
    search: str | None = Query(default=None, min_length=1),
    flete_id: int | None = Query(default=None, gt=0),
    client_id: int | None = Query(default=None, gt=0),
    currency_id: int | None = Query(default=None, gt=0),
    state: EstadoSalidaFleteEnum | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("flete_outputs:list")),
) -> list[SalidaFleteListItem]:
    return list_flete_outputs(
        db,
        search=search,
        flete_id=flete_id,
        client_id=client_id,
        currency_id=currency_id,
        state=state,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/salidas/{salida_id}", response_model=SalidaFleteDetailResponse)
def get_output(
    salida_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("flete_outputs:view")),
) -> SalidaFleteDetailResponse:
    return get_flete_output_detail(db, salida_id)


@router.post("/salidas", response_model=SalidaFleteDetailResponse, status_code=status.HTTP_201_CREATED)
def create_output(
    payload: SalidaFleteCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("flete_outputs:create")),
) -> SalidaFleteDetailResponse:
    return create_flete_output(
        db,
        payload=payload,
        created_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/salidas/{salida_id}/deliver", response_model=SalidaFleteDetailResponse)
def deliver_output(
    salida_id: int,
    payload: SalidaFleteDeliverRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("flete_outputs:deliver")),
) -> SalidaFleteDetailResponse:
    return deliver_flete_output(
        db,
        salida_id=salida_id,
        payload=payload,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/salidas/{salida_id}/return", response_model=SalidaFleteDetailResponse)
def return_output(
    salida_id: int,
    payload: SalidaFleteReturnRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("flete_outputs:return")),
) -> SalidaFleteDetailResponse:
    return return_flete_output(
        db,
        salida_id=salida_id,
        payload=payload,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/salidas/{salida_id}/annul", response_model=SalidaFleteDetailResponse)
def annul_output(
    salida_id: int,
    payload: SalidaFleteAnnulRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("flete_outputs:annul")),
) -> SalidaFleteDetailResponse:
    return annul_flete_output(
        db,
        salida_id=salida_id,
        payload=payload,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/{flete_id}", response_model=FleteDetailResponse)
def get_flete(
    flete_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("fletes:view")),
) -> FleteDetailResponse:
    return get_flete_detail(db, flete_id)


@router.post("", response_model=FleteDetailResponse, status_code=status.HTTP_201_CREATED)
def create_flete_record(
    payload: FleteCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("fletes:create")),
) -> FleteDetailResponse:
    return create_flete(
        db,
        payload=payload,
        created_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/{flete_id}", response_model=FleteDetailResponse)
def update_flete_record(
    flete_id: int,
    payload: FleteUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("fletes:update")),
) -> FleteDetailResponse:
    return update_flete(
        db,
        flete_id=flete_id,
        payload=payload,
        updated_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/{flete_id}/disable", response_model=FleteDetailResponse)
def disable_flete_record(
    flete_id: int,
    payload: FleteDisableRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("fletes:disable")),
) -> FleteDetailResponse:
    return disable_flete(
        db,
        flete_id=flete_id,
        payload=payload,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/{flete_id}/resolve-review", response_model=FleteDetailResponse)
def resolve_review(
    flete_id: int,
    payload: FleteResolveReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("fletes:resolve_review")),
) -> FleteDetailResponse:
    return resolve_flete_review(
        db,
        flete_id=flete_id,
        payload=payload,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/{flete_id}/pass-to-sale", response_model=FletePassToSaleResponse)
def pass_to_sale(
    flete_id: int,
    payload: FletePassToSaleRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("fletes:pass_to_sale")),
) -> FletePassToSaleResponse:
    return pass_flete_to_sale(
        db,
        flete_id=flete_id,
        payload=payload,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/{flete_id}/retire", response_model=FleteDetailResponse)
def retire_flete_record(
    flete_id: int,
    payload: FleteRetireRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("fletes:retire")),
) -> FleteDetailResponse:
    return retire_flete(
        db,
        flete_id=flete_id,
        payload=payload,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
