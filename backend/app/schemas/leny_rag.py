"""Administrative contextualization requests; provider options are never input."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class ContextualizationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: UUID
    action: Literal['contextualize','recontextualize','retry'] = 'contextualize'
    retry_of: UUID | None = None

    @model_validator(mode='after')
    def retry_matches_action(self):
        if (self.action == 'retry') != (self.retry_of is not None):
            raise ValueError('Reintentar requiere una solicitud anterior.')
        return self


class ContextualizationJob(BaseModel):
    id: UUID
    document_id: UUID | None
    version_id: UUID | None
    source_document_id: UUID
    source_version_id: UUID
    status: Literal['queued','running','completed','failed','cancelled','invalidated']
    stage: str
    progress: dict
    attempts: int
    cancel_requested: bool
    indexation_id: UUID | None
    retry_of: UUID | None
    error_code: str | None
    safe_message: str | None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None
    model: str
    dimension: int
    indexation_status: str | None = None
    chunk_count: int | None = None
    warnings: list = []


class ContextualizationPage(BaseModel):
    items: list[ContextualizationJob]
    total: int
    page: int
    page_size: int
