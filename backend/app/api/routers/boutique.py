from datetime import date

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps.auth import require_permission
from app.models.account import Cuenta
from app.models.boutique_enums import EstadoVentaBoutiqueEnum, MetodoPagoEnum
from app.schemas.boutique import (
    BoutiqueEntryCreateRequest,
    BoutiqueEntryDetailResponse,
    BoutiqueEntryListItem,
    BoutiqueEntryStatusUpdateRequest,
    BoutiqueItemCreateRequest,
    BoutiqueItemDetailResponse,
    BoutiqueItemListItem,
    BoutiqueItemStatusUpdateRequest,
    BoutiqueItemUpdateRequest,
    BoutiqueSaleCreateRequest,
    BoutiqueSaleDetailResponse,
    BoutiqueSaleListItem,
    BoutiqueSaleStateChangeRequest,
    ProveedorCreateRequest,
    ProveedorDetailResponse,
    ProveedorListItem,
    ProveedorStatusUpdateRequest,
    ProveedorUpdateRequest,
    TipoItemBoutiqueCreate,
    TipoItemBoutiqueResponse,
    TipoItemBoutiqueStatusUpdate,
    TipoItemBoutiqueUpdate,
)
from app.services.boutique_entry_service import create_boutique_entry, get_boutique_entry_detail, list_boutique_entries, set_boutique_entry_status
from app.services.boutique_sale_service import change_boutique_sale_state, create_boutique_sale, get_boutique_sale_detail, list_boutique_sales
from app.services.boutique_service import (
    create_boutique_item,
    create_boutique_type,
    get_boutique_item_detail,
    get_boutique_type,
    list_boutique_items,
    list_boutique_types,
    set_boutique_item_status,
    set_boutique_type_status,
    update_boutique_item,
    update_boutique_type,
)
from app.services.provider_service import create_provider, get_provider, list_providers, set_provider_status, update_provider


router = APIRouter()


@router.get("/types", response_model=list[TipoItemBoutiqueResponse])
def get_types(
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("boutique_types:list")),
) -> list[TipoItemBoutiqueResponse]:
    return [TipoItemBoutiqueResponse.model_validate(item) for item in list_boutique_types(db)]


@router.get("/types/{type_id}", response_model=TipoItemBoutiqueResponse)
def get_type(
    type_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("boutique_types:list")),
) -> TipoItemBoutiqueResponse:
    return TipoItemBoutiqueResponse.model_validate(get_boutique_type(db, type_id))


@router.post("/types", response_model=TipoItemBoutiqueResponse, status_code=status.HTTP_201_CREATED)
def create_type(
    payload: TipoItemBoutiqueCreate,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("boutique_types:create")),
) -> TipoItemBoutiqueResponse:
    created = create_boutique_type(
        db,
        payload=payload,
        created_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return TipoItemBoutiqueResponse.model_validate(created)


@router.patch("/types/{type_id}", response_model=TipoItemBoutiqueResponse)
def update_type(
    type_id: int,
    payload: TipoItemBoutiqueUpdate,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("boutique_types:update")),
) -> TipoItemBoutiqueResponse:
    updated = update_boutique_type(
        db,
        type_id=type_id,
        payload=payload,
        updated_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return TipoItemBoutiqueResponse.model_validate(updated)


@router.patch("/types/{type_id}/status", response_model=TipoItemBoutiqueResponse)
def update_type_status(
    type_id: int,
    payload: TipoItemBoutiqueStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("boutique_types:update_status")),
) -> TipoItemBoutiqueResponse:
    updated = set_boutique_type_status(
        db,
        type_id=type_id,
        enabled=payload.habilitado,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return TipoItemBoutiqueResponse.model_validate(updated)


@router.get("/proveedores", response_model=list[ProveedorListItem])
def get_providers(
    search: str | None = Query(default=None, min_length=1),
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("boutique_providers:list")),
) -> list[ProveedorListItem]:
    return list_providers(db, search=search, is_active=is_active)


@router.get("/proveedores/{provider_id}", response_model=ProveedorDetailResponse)
def get_provider_detail(
    provider_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("boutique_providers:view")),
) -> ProveedorDetailResponse:
    return get_provider(db, provider_id)


@router.post("/proveedores", response_model=ProveedorDetailResponse, status_code=status.HTTP_201_CREATED)
def create_provider_record(
    payload: ProveedorCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("boutique_providers:create")),
) -> ProveedorDetailResponse:
    return create_provider(
        db,
        payload=payload,
        created_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/proveedores/{provider_id}", response_model=ProveedorDetailResponse)
def update_provider_record(
    provider_id: int,
    payload: ProveedorUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("boutique_providers:update")),
) -> ProveedorDetailResponse:
    return update_provider(
        db,
        provider_id=provider_id,
        payload=payload,
        updated_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/proveedores/{provider_id}/status", response_model=ProveedorDetailResponse)
def update_provider_record_status(
    provider_id: int,
    payload: ProveedorStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("boutique_providers:update_status")),
) -> ProveedorDetailResponse:
    return set_provider_status(
        db,
        provider_id=provider_id,
        enabled=payload.habilitado,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/entries", response_model=list[BoutiqueEntryListItem])
def get_entries(
    search: str | None = Query(default=None, min_length=1),
    item_id: int | None = Query(default=None, gt=0),
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("boutique_entries:list")),
) -> list[BoutiqueEntryListItem]:
    return list_boutique_entries(db, search=search, item_id=item_id, is_active=is_active)


@router.get("/entries/{entry_id}", response_model=BoutiqueEntryDetailResponse)
def get_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("boutique_entries:view")),
) -> BoutiqueEntryDetailResponse:
    return get_boutique_entry_detail(db, entry_id)


@router.post("/entries", response_model=BoutiqueEntryDetailResponse, status_code=status.HTTP_201_CREATED)
def create_entry(
    payload: BoutiqueEntryCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("boutique_entries:create")),
) -> BoutiqueEntryDetailResponse:
    return create_boutique_entry(
        db,
        payload=payload,
        created_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/entries/{entry_id}/status", response_model=BoutiqueEntryDetailResponse)
def update_entry_status(
    entry_id: int,
    payload: BoutiqueEntryStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("boutique_entries:update_status")),
) -> BoutiqueEntryDetailResponse:
    return set_boutique_entry_status(
        db,
        entry_id=entry_id,
        is_active=payload.is_active,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/items", response_model=list[BoutiqueItemListItem])
def get_items(
    type_id: int | None = Query(default=None, gt=0),
    search: str | None = Query(default=None, min_length=1),
    is_active: bool | None = Query(default=None),
    low_stock: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("boutique_items:list")),
) -> list[BoutiqueItemListItem]:
    return list_boutique_items(db, type_id=type_id, search=search, is_active=is_active, low_stock=low_stock)


@router.get("/items/{item_id}", response_model=BoutiqueItemDetailResponse)
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("boutique_items:view")),
) -> BoutiqueItemDetailResponse:
    return get_boutique_item_detail(db, item_id)


@router.post("/items", response_model=BoutiqueItemDetailResponse, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: BoutiqueItemCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("boutique_items:create")),
) -> BoutiqueItemDetailResponse:
    return create_boutique_item(
        db,
        payload=payload,
        created_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/items/{item_id}", response_model=BoutiqueItemDetailResponse)
def update_item(
    item_id: int,
    payload: BoutiqueItemUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("boutique_items:update")),
) -> BoutiqueItemDetailResponse:
    return update_boutique_item(
        db,
        item_id=item_id,
        payload=payload,
        updated_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/items/{item_id}/status", response_model=BoutiqueItemDetailResponse)
def update_item_status(
    item_id: int,
    payload: BoutiqueItemStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("boutique_items:update_status")),
) -> BoutiqueItemDetailResponse:
    return set_boutique_item_status(
        db,
        item_id=item_id,
        is_active=payload.is_active,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/sales", response_model=list[BoutiqueSaleListItem])
def get_sales(
    search: str | None = Query(default=None, min_length=1),
    item_id: int | None = Query(default=None, gt=0),
    client_id: int | None = Query(default=None, gt=0),
    currency_id: int | None = Query(default=None, gt=0),
    payment_method: MetodoPagoEnum | None = Query(default=None),
    state: EstadoVentaBoutiqueEnum | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("boutique_sales:list")),
) -> list[BoutiqueSaleListItem]:
    return list_boutique_sales(
        db,
        search=search,
        item_id=item_id,
        client_id=client_id,
        currency_id=currency_id,
        payment_method=payment_method,
        state=state,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/sales/{sale_id}", response_model=BoutiqueSaleDetailResponse)
def get_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("boutique_sales:view")),
) -> BoutiqueSaleDetailResponse:
    return get_boutique_sale_detail(db, sale_id)


@router.post("/sales", response_model=BoutiqueSaleDetailResponse, status_code=status.HTTP_201_CREATED)
def create_sale(
    payload: BoutiqueSaleCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("boutique_sales:create")),
) -> BoutiqueSaleDetailResponse:
    return create_boutique_sale(
        db,
        payload=payload,
        created_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/sales/{sale_id}/cancel", response_model=BoutiqueSaleDetailResponse)
def cancel_sale(
    sale_id: int,
    payload: BoutiqueSaleStateChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("boutique_sales:cancel")),
) -> BoutiqueSaleDetailResponse:
    return change_boutique_sale_state(
        db,
        sale_id=sale_id,
        target_state=EstadoVentaBoutiqueEnum.CANCELADA,
        reason=payload.reason,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/sales/{sale_id}/annul", response_model=BoutiqueSaleDetailResponse)
def annul_sale(
    sale_id: int,
    payload: BoutiqueSaleStateChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("boutique_sales:annul")),
) -> BoutiqueSaleDetailResponse:
    return change_boutique_sale_state(
        db,
        sale_id=sale_id,
        target_state=EstadoVentaBoutiqueEnum.ANULADA,
        reason=payload.reason,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
