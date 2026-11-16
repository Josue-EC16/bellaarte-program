"""Library contracts; no model/system/tool parameters accepted from the browser."""
from datetime import date, datetime
from typing import Literal
import unicodedata
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

BASE_DOCUMENT_ROLES = frozenset({'ADMIN', 'CAJA', 'INV_BOUTIQUE', 'INV_TALLER', 'MODISTA'})


class DocumentContract(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

    @field_validator('*', mode='before')
    @classmethod
    def safe_text(cls, value):
        if isinstance(value, str) and any(unicodedata.category(c) in {'Cc', 'Cs'} and c not in '\n\r\t' for c in value):
            raise ValueError('El texto contiene caracteres no permitidos.')
        return value


class FolderCreate(DocumentContract):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=2000)
    parent_id: UUID | None = None
    role_codes: list[str] = Field(default_factory=list, max_length=5)

    @field_validator('role_codes')
    @classmethod
    def roles(cls, value):
        if not set(value) <= BASE_DOCUMENT_ROLES or len(value) != len(set(value)):
            raise ValueError('Selecciona roles base válidos sin duplicarlos.')
        return value


class FolderUpdate(FolderCreate):
    pass


class DocumentUpload(DocumentContract):
    request_id: UUID
    sha256: str = Field(pattern=r'^[a-fA-F0-9]{64}$')
    folder_id: UUID
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default='', max_length=4000)


class VersionUpload(DocumentContract):
    request_id: UUID
    sha256: str = Field(pattern=r'^[a-fA-F0-9]{64}$')
    revision: int = Field(ge=1)


class PublicationRequest(DocumentContract):
    request_id: UUID
    version_id: UUID
    indexation_id: UUID
    expected_revision: int = Field(ge=1)
    confirm: Literal[True]


class UnpublicationRequest(DocumentContract):
    request_id: UUID
    expected_revision: int = Field(ge=1)
    confirm: Literal[True]


class DocumentChange(DocumentContract):
    revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    folder_id: UUID | None = None
    role_codes: list[str] | None = Field(default=None, max_length=5)
    confirmation: UUID | None = None

    @field_validator('role_codes')
    @classmethod
    def roles(cls, value):
        if value is not None:
            return FolderCreate.roles(value)
        return value


class PurgePreview(DocumentContract):
    ids: list[UUID] = Field(default_factory=list, max_length=1000)
    all: bool = False


class PurgeConfirm(DocumentContract):
    confirmation: UUID
    request_id: UUID


class DocumentFilters(DocumentContract):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    folder_id: UUID | None = None
    search: str | None = Field(default=None, max_length=200)
    format: str | None = Field(default=None, pattern=r'^(pdf|docx|jpg|jpeg|png)$')
    date_from: date | None = None
    date_to: date | None = None
    creator_id: int | None = Field(default=None, ge=1)


class FolderItem(BaseModel):
    id: UUID
    parent_id: UUID | None
    name: str
    description: str
    role_codes: list[str]


class FolderList(BaseModel):
    items: list[FolderItem]


class VersionItem(BaseModel):
    id: UUID
    document_id: UUID
    number: int
    sha256: str
    size_bytes: int
    media_type: str
    original_name: str
    created_at: datetime
    created_by: int
    status: Literal['pending_contextualization','contextualizing','contextualization_error','pending_publication']
    validated_indexation_id: UUID | None = None
    publication_ready: bool = False
    preview_available: bool


class DocumentItem(BaseModel):
    id: UUID
    folder_id: UUID
    title: str
    description: str
    state: Literal['active','trash','purging']
    created_by: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    purge_after: datetime | None
    revision: int
    published_version_id: UUID | None = None
    published_indexation_id: UUID | None = None
    published_at: datetime | None = None
    published_by: int | None = None
    role_codes: list[str]
    version_count: int
    latest_version_number: int | None
    latest_media_type: str | None = None
    latest_size_bytes: int | None = None
    status: Literal['pending_contextualization','contextualizing','contextualization_error','pending_publication']


class DocumentPage(BaseModel):
    items: list[DocumentItem]
    total: int
    page: int
    page_size: int


class DocumentDetail(DocumentItem):
    versions: list[VersionItem]


class VersionPage(BaseModel):
    items: list[VersionItem]
    total: int
    page: int
    page_size: int
