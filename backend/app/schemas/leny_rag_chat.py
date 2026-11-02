"""Server-issued references; no URLs or filesystem keys are public contracts."""
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SourceReference(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_id: UUID
    available: bool
    citation_id: str = Field(default='S1', pattern=r'^S[1-5]$')
    label: str | None = Field(default=None, max_length=200)
    version: int | None = Field(default=None, ge=1)
    locator: dict | None = None
    source_type: str | None = Field(default=None, max_length=24)
    warnings: list[str] = Field(default_factory=list, max_length=10)


class SourceDetail(SourceReference):
    text: str = Field(max_length=8192)
