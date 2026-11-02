"""Local-only Ollama HTTP adapter; never executes tools or model output."""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Protocol

import httpx
import anyio

from app.core.config import Settings


class LenyError(Exception):
    def __init__(self, code: str, message: str, status: int = 503):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


class ChatProvider(Protocol):
    async def available(self) -> None: ...
    def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]: ...


class OllamaProvider:
    def __init__(self, config: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.config = config
        self.transport = transport
        self.finish_reason = "stop"
        self.response_complete = False
        self.inference_started = False
        self.metrics = {}

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.config.leny_ollama_url, trust_env=False, follow_redirects=False,
            transport=self.transport,
            timeout=httpx.Timeout(self.config.leny_connect_timeout),
        )

    @asynccontextmanager
    async def session(self):
        client = self.client()
        try:
            yield client
        finally:
            with anyio.CancelScope(shield=True):
                await client.aclose()

    async def available(self) -> None:
        if not self.config.leny_enabled:
            raise LenyError("LENY_DISABLED", "LENY está deshabilitado.")
        try:
            async with self.session() as client:
                response = await client.get("/api/tags")
                response.raise_for_status()
                if not any(m.get("name") == self.config.leny_model for m in response.json().get("models", [])):
                    raise LenyError("LENY_MODEL_MISSING", "El modelo configurado no está instalado en Ollama.")
                response = await client.post("/api/show", json={"model": self.config.leny_model})
                response.raise_for_status()
                data = response.json()
                if data.get("remote_host") or data.get("remote_model"):
                    raise LenyError("LENY_REMOTE_MODEL", "LENY requiere un modelo ejecutado localmente.")
        except LenyError:
            raise
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            raise LenyError("LENY_UNAVAILABLE", "No se pudo verificar el servicio local de LENY.") from None

    async def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        async for text in self._stream(messages):
            yield text

    async def classify(self, messages, schema) -> str:
        chunks = []
        try:
            async def collect():
                async for chunk in self._stream(messages, classification=schema):
                    chunks.append(chunk)
            await asyncio.wait_for(collect(), self.config.leny_classifier_timeout)
            return "".join(chunks)
        except asyncio.TimeoutError:
            # An inconclusive semantic decision may only request clarification.
            return "{}"
        except LenyError as error:
            if error.code in {"LENY_EMPTY_RESPONSE", "LENY_BAD_RESPONSE", "LENY_INCOMPLETE"}:
                return "{}"
            raise

    async def measure_prompt(self, messages) -> int:
        """Discard a one-token prefill probe; never return generated content.

        Experimental candidate only, cold requests to rule out cached-only
        counters. The caller must hold the normal inference lease and deadline.
        Missing counters or cache evidence fails closed; it is not a tokenizer.
        """
        if (getattr(self.config, 'leny_rag_profile', 'legacy') != 'rag4_v1'
                or self.config.leny_keep_alive != '0'):
            raise LenyError('LENY_RAG_PROBE_UNAVAILABLE', 'La medición de contexto no está habilitada.', 503)
        async with self.session() as client:
            response = await client.get('/api/ps')
            response.raise_for_status()
            if any(row.get('name') == self.config.leny_model for row in response.json().get('models', [])):
                raise LenyError('LENY_RAG_PROBE_UNAVAILABLE', 'La medición necesita que el modelo finalice su uso anterior.', 503)
        async for _discarded in self._stream(messages, measurement=True):
            pass
        value = self.metrics.get('prompt_eval_count')
        cached = self.metrics.get('prompt_eval_cached_count', 0)
        if type(value) is not int or value <= 0 or cached != 0:
            raise LenyError('LENY_RAG_PROBE_UNAVAILABLE', 'Ollama no confirmó una medición de contexto utilizable.', 502)
        return value

    async def _stream(self, messages, classification=None, measurement=False) -> AsyncIterator[str]:
        config = self.config
        self.response_complete = False
        self.inference_started = False
        self.metrics = {}
        payload = {
            "model": config.leny_model, "messages": messages, "stream": True, "think": False,
            "keep_alive": config.leny_keep_alive,
            "options": {"num_ctx": config.leny_num_ctx, "num_predict": config.leny_num_predict,
                        "temperature": config.leny_temperature},
        }
        if getattr(config, 'leny_rag_profile', 'legacy') == 'rag4_v1':
            # Native Ollama API: reject over-context input instead of silently
            # dropping a system message or evidence. Kept profile-specific.
            payload.update(truncate=False, shift=False)
        if classification:
            payload["format"] = classification
            payload["options"].update(num_predict=96, temperature=0)
        if measurement:
            payload['options'].update(num_predict=1, temperature=0)
        started = asyncio.get_running_loop().time()
        last_content_at = started
        first = False
        total_bytes = 0
        try:
            async with self.session() as client:
                # Explicit total/first-token/idle deadlines include headers and load time.
                stream_timeout = httpx.Timeout(connect=config.leny_connect_timeout, read=None,
                                               write=config.leny_connect_timeout, pool=config.leny_connect_timeout)
                self.inference_started = True
                opening = client.send(client.build_request("POST", "/api/chat", json=payload, timeout=stream_timeout), stream=True)
                response = await asyncio.wait_for(opening, min(config.leny_first_token_timeout, config.leny_total_timeout))
                try:
                    if measurement and response.status_code == 400:
                        # A complete native400 rejects this probe. Do not read or
                        # log the provider's diagnostic body, retry generation or
                        # pretend a token count was obtained. Bound draining.
                        size = 0
                        async for chunk in response.aiter_bytes():
                            size += len(chunk)
                            if size > 65536:
                                raise LenyError('LENY_BAD_RESPONSE', 'Ollama devolvió una respuesta inválida.', 502)
                        self.response_complete = True
                        raise LenyError('LENY_RAG_PROBE_UNAVAILABLE', 'No se pudo medir este contexto sin recortarlo.', 502)
                    if response.status_code >= 400:
                        raise LenyError("LENY_UNAVAILABLE", "Ollama no pudo iniciar la generación.")
                    lines = bounded_lines(response.aiter_bytes()).__aiter__()
                    while True:
                        elapsed = asyncio.get_running_loop().time() - started
                        remaining = config.leny_total_timeout - elapsed
                        if remaining <= 0:
                            raise LenyError("LENY_TOTAL_TIMEOUT", "La respuesta superó el tiempo total permitido.", 504)
                        phase_timeout = (config.leny_idle_timeout - (asyncio.get_running_loop().time() - last_content_at)
                                         if first else config.leny_first_token_timeout - elapsed)
                        total_deadline_first = remaining <= phase_timeout
                        timeout = min(remaining, phase_timeout)
                        if timeout <= 0:
                            code = "LENY_IDLE_TIMEOUT" if first else "LENY_FIRST_TOKEN_TIMEOUT"
                            raise LenyError(code, "El modelo tardó demasiado en producir contenido.", 504)
                        try:
                            line = await asyncio.wait_for(lines.__anext__(), timeout)
                        except StopAsyncIteration:
                            raise LenyError("LENY_INCOMPLETE", "La respuesta local terminó inesperadamente.", 502) from None
                        except asyncio.TimeoutError:
                            code = "LENY_TOTAL_TIMEOUT" if total_deadline_first else ("LENY_IDLE_TIMEOUT" if first else "LENY_FIRST_TOKEN_TIMEOUT")
                            raise LenyError(code, "El modelo superó el tiempo de espera permitido.", 504) from None
                        data = json.loads(line)
                        if not isinstance(data, dict) or data.get("error"):
                            raise LenyError("LENY_BAD_RESPONSE", "Ollama devolvió una respuesta inválida.", 502)
                        if data.get('done') is True:
                            self.response_complete = True
                            # Numeric runtime metadata only, no prompt/response/logprobs.
                            names = ('total_duration', 'load_duration', 'prompt_eval_count',
                                     'prompt_eval_cached_count', 'prompt_eval_duration', 'eval_count', 'eval_duration')
                            self.metrics = {name: data[name] for name in names
                                            if type(data.get(name)) is int and data[name] >= 0}
                        message = data.get("message", {})
                        if not isinstance(message, dict) or message.get("tool_calls"):
                            raise LenyError("LENY_BAD_RESPONSE", "El modelo solicitó una operación no disponible.", 502)
                        content = message.get("content", "")
                        if not isinstance(content, str):
                            raise LenyError("LENY_BAD_RESPONSE", "Ollama devolvió una respuesta inválida.", 502)
                        if content:
                            total_bytes += len(content.encode("utf-8"))
                            if total_bytes > config.leny_max_response_bytes:
                                raise LenyError("LENY_RESPONSE_LIMIT", "La respuesta superó el tamaño permitido.", 502)
                            first = True
                            last_content_at = asyncio.get_running_loop().time()
                            yield content
                        if data.get("done") is True:
                            if not first:
                                raise LenyError("LENY_EMPTY_RESPONSE", "El modelo no produjo una respuesta.", 502)
                            self.finish_reason = "length" if data.get("done_reason") == "length" else "stop"
                            return
                finally:
                    with anyio.CancelScope(shield=True):
                        await response.aclose()
        except LenyError:
            raise
        except asyncio.TimeoutError:
            code = "LENY_TOTAL_TIMEOUT" if config.leny_total_timeout <= config.leny_first_token_timeout else "LENY_FIRST_TOKEN_TIMEOUT"
            raise LenyError(code, "El modelo tardó demasiado en comenzar a responder.", 504) from None
        except httpx.ConnectTimeout:
            raise LenyError("LENY_CONNECT_TIMEOUT", "No se pudo conectar con Ollama a tiempo.", 504) from None
        except httpx.TimeoutException:
            raise LenyError("LENY_COMMUNICATION_TIMEOUT", "Se agotó el tiempo de comunicación con Ollama.", 504) from None
        except httpx.HTTPError:
            raise LenyError("LENY_UNAVAILABLE", "Se interrumpió la comunicación con Ollama.") from None
        except (ValueError, TypeError, KeyError, UnicodeError):
            raise LenyError("LENY_BAD_RESPONSE", "Ollama devolvió una respuesta inválida.", 502) from None


async def bounded_lines(chunks: AsyncIterator[bytes], limit: int = 65536) -> AsyncIterator[str]:
    buffer = b""
    async for chunk in chunks:
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            if len(line) > limit:
                raise LenyError("LENY_BAD_RESPONSE", "Ollama devolvió un evento demasiado grande.", 502)
            if line.strip():
                yield line.decode("utf-8")
        if len(buffer) > limit:
            raise LenyError("LENY_BAD_RESPONSE", "Ollama devolvió un evento demasiado grande.", 502)
    if buffer.strip():
        yield buffer.decode("utf-8")
