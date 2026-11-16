"""Inference boundary only; authorization and RAG remain owned by LENY."""
from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from app.core.config import Settings


class LenyError(Exception):
    def __init__(self, code: str, message: str, status: int = 503):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


class Capability(str, Enum):
    SUPPORTED = 'supported'
    UNSUPPORTED = 'unsupported'
    DISABLED = 'prepared_disabled'


@dataclass(frozen=True)
class ProviderCapabilities:
    text_generation: Capability
    streaming: Capability
    structured_outputs: Capability
    token_usage: Capability
    reasoning: Capability
    context_measurement: Capability


@runtime_checkable
class ChatProvider(Protocol):
    config: Settings
    capabilities: ProviderCapabilities
    finish_reason: str
    response_complete: bool
    inference_started: bool
    metrics: dict

    async def available(self) -> None: ...
    def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]: ...
    async def classify(self, messages, schema) -> str: ...
    async def structured(self, messages, schema) -> str: ...
    async def measure_prompt(self, messages, schema=None) -> int: ...
