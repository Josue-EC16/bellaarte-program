"""Public LENY contracts. The browser supplies no model/system instructions."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.services.leny_guard import validate_input
from app.schemas.leny_rag_chat import SourceReference


class LenyChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: UUID
    request_id: UUID
    message: str = Field(min_length=1, max_length=10000)

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        return validate_input(value)


class ConversationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal['ollama', 'gemini'] = 'ollama'
    quality_profile: Literal['baseline', 'spec03'] | None = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    llm_provider: Literal['ollama', 'gemini'] = 'ollama'
    llm_model: str = 'qwen3.5:4b-q4_K_M'
    quality_profile: Literal['baseline', 'spec03'] = 'baseline'


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    status: Literal["generating", "completed", "interrupted", "failed"]
    request_id: UUID
    created_at: datetime
    category: str | None = None
    reason: str | None = None
    context_eligible: bool = False
    sources: list[SourceReference] = Field(default_factory=list, max_length=5)


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    total: int
    page: int
    page_size: int


class ConversationDetailResponse(BaseModel):
    conversation: ConversationResponse
    items: list[MessageResponse]
    total: int
    page: int
    page_size: int


class ProviderStatus(BaseModel):
    provider: Literal['ollama', 'gemini']
    model: str
    available: bool
    code: str
    request_timeout_seconds: float


class LenyStatusResponse(BaseModel):
    quality_evaluation_enabled: bool = False
    available: bool
    code: str
    model: str
    max_message_chars: int
    request_timeout_seconds: float
    providers: list[ProviderStatus] = Field(default_factory=list)


class StartEvent(BaseModel):
    type: Literal["start"] = "start"
    conversation_id: UUID
    request_id: UUID
    assistant_message_id: UUID
    provider: Literal['ollama', 'gemini'] | None = None
    model: str | None = None


class DeltaEvent(BaseModel):
    type: Literal["delta"] = "delta"
    text: str


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"
    status: Literal["completed", "interrupted"]
    finish_reason: str
    outcome: Literal["answered", "refused", "clarification"] = "answered"
    reason_code: str | None = None
    response_scope: Literal['documented', 'partial', 'general'] | None = None
    provider: Literal['ollama', 'gemini'] | None = None
    model: str | None = None
    sources: list[SourceReference] = Field(default_factory=list, max_length=5)


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str
