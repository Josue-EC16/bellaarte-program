"""Bounded CPU embeddings through local Ollama; no generation or tool access."""
from __future__ import annotations

import asyncio
import json
import math
import time

import httpx

from app.services.leny_rag_common import RagError


class EmbeddingProvider:
    def __init__(self, settings, transport=None):
        self.settings, self.transport = settings, transport
        self.owned_model = False
        self.last_metrics = {}
        self.response_complete = False
        self.inference_started = False

    def client(self):
        return httpx.AsyncClient(base_url=self.settings.leny_ollama_url, trust_env=False,
                                 follow_redirects=False, transport=self.transport,
                                 timeout=httpx.Timeout(self.settings.leny_rag_read_seconds,
                                                       connect=self.settings.leny_rag_connect_seconds))

    async def request(self, client, method, endpoint, payload=None, *, inference=False):
        started = time.monotonic()
        self.response_complete = False if inference else self.response_complete
        try:
            async def receive():
                async with client.stream(method, endpoint, json=payload) as response:
                    data = bytearray()
                    async for block in response.aiter_bytes():
                        data.extend(block)
                        if len(data) > 1024**2:
                            raise RagError('RAG_PROVIDER_RESPONSE', uncertain=inference)
                    if inference:
                        self.response_complete = True
                        if response.status_code == 200 and payload and payload.get('input'):
                            self.owned_model = True
                    if response.status_code == 400:
                        raise RagError('RAG_INPUT_CONTEXT', 422)
                    if response.status_code != 200:
                        raise RagError('RAG_PROVIDER_UNAVAILABLE')
                    decoded = json.loads(data)
                    if not isinstance(decoded, dict) or 'error' in decoded:
                        raise RagError('RAG_PROVIDER_RESPONSE')
                    return decoded
            if inference:self.inference_started = True
            result = await asyncio.wait_for(receive(), timeout=self.settings.leny_rag_batch_seconds)
            self.last_metrics['http_seconds'] = round(time.monotonic() - started, 4)
            return result
        except (asyncio.TimeoutError, httpx.TimeoutException):
            raise RagError('RAG_PROVIDER_TIMEOUT', uncertain=inference and not self.response_complete) from None
        except (httpx.HTTPError, ValueError, TypeError):
            raise RagError('RAG_PROVIDER_UNAVAILABLE', uncertain=inference and not self.response_complete) from None

    async def verify(self, *, allow_owned=False):
        async with self.client() as client:
            tags = await self.request(client, 'GET', '/api/tags')
            model = next((item for item in tags.get('models', []) if item.get('name') == self.settings.leny_rag_model), None)
            if model is None:
                raise RagError('RAG_MODEL_MISSING')
            if model.get('digest', '').removeprefix('sha256:') != self.settings.leny_rag_model_digest:
                raise RagError('RAG_MODEL_CHANGED')
            show = await self.request(client, 'POST', '/api/show', {'model': self.settings.leny_rag_model})
            if show.get('remote_host') or show.get('remote_model') or 'embedding' not in show.get('capabilities', []):
                raise RagError('RAG_MODEL_CHANGED')
            info = show.get('model_info', {})
            dimensions = [value for key, value in info.items() if key.endswith('.embedding_length')]
            if dimensions != [1024]:
                raise RagError('RAG_PROVIDER_RESPONSE')
            running = await self.request(client, 'GET', '/api/ps')
            resident = next((item for item in running.get('models', []) if item.get('name') == self.settings.leny_rag_model), None)
            if resident and not (allow_owned and self.owned_model):
                raise RagError('RAG_EXTERNAL_MODEL', 429)
            if resident and (resident.get('size_vram') != 0 or resident.get('digest', '').removeprefix('sha256:') != self.settings.leny_rag_model_digest):
                raise RagError('RAG_CPU_REQUIRED')
        return {'model': self.settings.leny_rag_model, 'dimension':1024, 'digest':self.settings.leny_rag_model_digest}

    async def embed(self, texts):
        if not texts or len(texts) > self.settings.leny_rag_batch_size or any(not isinstance(t, str) or not t.strip() or len(t.encode()) > self.settings.leny_rag_chunk_bytes for t in texts):
            raise RagError('RAG_INPUT_CONTEXT', 422)
        await self.verify(allow_owned=True)
        payload = {'model': self.settings.leny_rag_model, 'input':texts, 'truncate':False,
                   'keep_alive':'30s', 'options':{'num_gpu':0, 'num_thread':self.settings.leny_rag_cpu_threads,
                                                'num_ctx':self.settings.leny_rag_num_ctx}}
        async with self.client() as client:
            response = await self.request(client, 'POST', '/api/embed', payload, inference=True)
            # Record ownership only after a complete response, including malformed output.
            self.owned_model = True
            if response.get('model') != self.settings.leny_rag_model:
                raise RagError('RAG_PROVIDER_RESPONSE')
            vectors = response.get('embeddings')
            if not isinstance(vectors, list) or len(vectors) != len(texts):
                raise RagError('RAG_PROVIDER_RESPONSE')
            for vector in vectors:
                if (not isinstance(vector, list) or len(vector) != 1024 or
                        any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in vector)
                        or not any(x != 0 for x in vector)):
                    raise RagError('RAG_PROVIDER_RESPONSE')
            running = await self.request(client, 'GET', '/api/ps')
            resident = next((item for item in running.get('models', []) if item.get('name') == self.settings.leny_rag_model), None)
            if resident is None or resident.get('size_vram') != 0:
                raise RagError('RAG_CPU_REQUIRED')
            if resident.get('digest', '').removeprefix('sha256:') != self.settings.leny_rag_model_digest:
                raise RagError('RAG_MODEL_CHANGED')
            for key in ('total_duration', 'load_duration', 'prompt_eval_count'):
                value = response.get(key)
                if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
                    self.last_metrics[key] = value
            return vectors

    async def release(self):
        if not self.owned_model:
            return
        # Only this adapter's model, never the generative model or other tags.
        await self.verify(allow_owned=True)
        async with self.client() as client:
            await self.request(client, 'POST', '/api/embed', {'model':self.settings.leny_rag_model, 'input':[], 'keep_alive':0}, inference=True)
            running = await self.request(client, 'GET', '/api/ps')
            if any(item.get('name') == self.settings.leny_rag_model for item in running.get('models', [])):
                raise RagError('RAG_PROVIDER_RESPONSE')
        self.owned_model = False
