"""Gemini Developer API: stateless, no tools, no provider failover."""
import asyncio
import json
import random
import re
from copy import deepcopy
from time import monotonic
import anyio
import httpx
from app.services.leny_llm_contracts import Capability, LenyError, ProviderCapabilities
from app.services.leny_gemini_safety import check_runtime_secrets,check_user_context


class GeminiProvider:
    is_remote = True
    provider_name = 'gemini'
    capabilities = ProviderCapabilities(*(Capability.SUPPORTED for _ in range(6)))

    def __init__(self, config, *, usage=None, client_factory=None, authorize=None):
        self.config, self.usage = config, usage
        self.client_factory, self.authorize = client_factory, authorize
        self.model_name = config.leny_gemini_model
        self.effective_model = self.model_name
        self.finish_reason = 'stop'
        self.response_complete = self.inference_started = False
        self.metrics = {}
        self.network_metrics = dict(inference_calls_total=0,prompt_tokens_total=0,output_tokens_total=0,calls_without_token_counts=0,thinking_tokens_total=0)
        self._client = None
        self._counts = {}

    async def available(self):
        if not self.config.leny_gemini_enabled:
            raise LenyError('LENY_GEMINI_DISABLED', 'Gemini está deshabilitado.')
        if not self.config.leny_gemini_free_tier_confirmed:
            raise LenyError('LENY_GEMINI_TIER', 'Falta confirmar el nivel gratuito de Gemini.')
        if not self.config.gemini_api_key or not self.config.gemini_api_key.get_secret_value().strip():
            raise LenyError('LENY_GEMINI_KEY_MISSING', 'Gemini no tiene una credencial configurada.')
        # Keep the previous model valid for existing conversations. New ones
        # use the server configuration; there is no automatic model fallback.
        if self.model_name not in {'gemini-3.8-flash', 'gemini-3.5-flash-lite', 'gemini-3.1-flash-lite'}:
            raise LenyError('LENY_GEMINI_MODEL', 'El modelo Gemini no está autorizado.')

    async def _sdk(self):
        await self.available()
        if self._client is None:
            from google import genai
            from google.genai import types
            self._client = (self.client_factory or genai.Client)(
                api_key=self.config.gemini_api_key.get_secret_value(), vertexai=False, enterprise=False,
                http_options=types.HttpOptions(timeout=int(self.config.leny_gemini_timeout_seconds*1000),
                    retry_options=types.HttpRetryOptions(attempts=1),
                    client_args={'trust_env': False}, async_client_args={'trust_env': False}))
        return self._client

    async def aclose(self):
        if self._client is not None:
            client, self._client = self._client, None
            await client.aio.aclose()
            client.close()

    async def _reserve(self, phase, tokens):
        if self.usage is None:
            raise LenyError('LENY_GEMINI_QUOTA_UNAVAILABLE', 'El control de consumo de Gemini no está disponible.')
        end = monotonic()+61
        while True:
            try:
                return await anyio.to_thread.run_sync(lambda: self.usage.reserve(phase, tokens))
            except LenyError as error:
                wait = getattr(error, 'retry_after', 0)
                if error.code!='LENY_GEMINI_QUOTA' or wait<=0 or monotonic()+wait>end:
                    raise
                await asyncio.sleep(wait)

    async def _call(self, operation, phase, tokens, serialized):
        await self.available()
        check_runtime_secrets(self.config, serialized)
        # Inspect the entire outgoing payload, including evidence and metadata.
        # A finite external grant never overrides sensitive-content detection.
        check_user_context(serialized)
        for attempt in range(2):
            if self.authorize is not None:
                await self.authorize()
            identity = await self._reserve(phase, tokens)
            self.inference_started, self.response_complete = True, False
            self.metrics = {}
            error_code = None
            sent = False
            try:
                if self.authorize is not None:
                    await self.authorize()
                self.network_metrics['inference_calls_total'] += 1
                sent = True
                result = await asyncio.wait_for(operation(), 10 if phase=='count' else self.config.leny_gemini_timeout_seconds)
                self.response_complete = True
                effective = getattr(result,'model_version',None)
                if isinstance(effective,str) and re.fullmatch(r'[A-Za-z0-9._:-]{1,120}',effective):
                    self.effective_model = effective
                usage = getattr(result, 'usage_metadata', None)
                if usage:
                    for source,target in (('prompt_token_count','prompt_eval_count'),('candidates_token_count','eval_count'),('thoughts_token_count','thinking_tokens')):
                        value = getattr(usage, source, None)
                        if type(value) is int and value>=0:
                            self.metrics[target] = value
                return result
            except asyncio.CancelledError:
                error_code = 'LENY_GEMINI_CANCELLED'
                raise
            except (asyncio.TimeoutError, httpx.TimeoutException):
                error_code = 'LENY_GEMINI_TIMEOUT'
                raise LenyError(error_code, 'Gemini no respondió dentro del tiempo permitido.',504) from None
            except Exception as error:
                from google.genai.errors import APIError
                if isinstance(error, LenyError):
                    error_code = error.code
                    raise
                if isinstance(error, APIError):
                    code = error.code
                    self.response_complete = True
                    error_code = {401:'LENY_GEMINI_AUTH',403:'LENY_GEMINI_AUTH',404:'LENY_GEMINI_MODEL',429:'LENY_GEMINI_QUOTA',400:'LENY_GEMINI_REQUEST'}.get(code,'LENY_GEMINI_UNAVAILABLE')
                    if code==503 and attempt==0:
                        await asyncio.sleep(1+random.random())
                        continue
                    mapped = LenyError(error_code,'Gemini no pudo completar la solicitud. Revisa su disponibilidad o cuota; puedes iniciar otra conversación con Qwen.',429 if code==429 else 503)
                    mapped.provider_http_status = code
                    if code==429:
                        mapped.retry_after = 60
                        if re.search(r'per.?day|requestsperday|daily',json.dumps(getattr(error,'details',{})),re.I):
                            if hasattr(self.usage,'block_daily'):
                                mapped.retry_after = await anyio.to_thread.run_sync(self.usage.block_daily)
                    raise mapped from None
                error_code = 'LENY_GEMINI_CONNECTION'
                raise LenyError(error_code,'No se pudo conectar con Gemini.',503) from None
            finally:
                if sent:
                    for key,target in (('prompt_eval_count','prompt_tokens_total'),('eval_count','output_tokens_total'),('thinking_tokens','thinking_tokens_total')):
                        self.network_metrics[target] += self.metrics.get(key,0)
                    if 'prompt_eval_count' not in self.metrics or 'eval_count' not in self.metrics:
                        self.network_metrics['calls_without_token_counts'] += 1
                with anyio.CancelScope(shield=True):
                    await anyio.to_thread.run_sync(lambda: self.usage.finish(identity,metrics=self.metrics,error=error_code))

    @staticmethod
    def _parts(messages):
        system = '\n'.join(m['content'] for m in messages if m['role']=='system')
        contents = [{'role':'model' if m['role']=='assistant' else 'user','parts':[{'text':m['content']}]} for m in messages if m['role']!='system']
        return system,contents

    @staticmethod
    def _native_schema(schema):
        if schema is None:
            return None
        native_schema=deepcopy(schema)
        def compatible(node):
            if isinstance(node,dict):
                # Native API supports a subset. Server-side validators still
                # enforce duplicate references and complete source identity.
                node.pop('uniqueItems',None);node.pop('$schema',None)
                for value in node.values():compatible(value)
            elif isinstance(node,list):
                for value in node:compatible(value)
        compatible(native_schema)
        plan_fields = native_schema.get('properties', {})
        if set(plan_fields) == {'aspect','scope','relation','sources'}:
            # A syntactically valid plan must not pair absent/broader scope
            # with documentary references. Encode the existing server
            # invariant in Gemini's grammar; never normalize it into fact.
            variants = []
            for scopes,relations,with_sources in (
                (['matched'],['direct','partial','contradictory'],True),
                (['matched'],['tangential','absent'],False),
                ([s for s in plan_fields['scope']['enum'] if s!='matched'],
                 plan_fields['relation']['enum'],False)):
                variant = deepcopy(native_schema)
                props = variant['properties']
                props['scope']['enum'] = scopes
                props['relation']['enum'] = relations
                if with_sources:
                    props['sources']['minItems'] = 1
                else:
                    props['sources']['maxItems'] = 0
                variants.append(variant)
            native_schema = {'anyOf':variants}
        return native_schema

    async def measure_prompt(self, messages, schema=None):
        await self.available()
        schema = self._native_schema(schema)
        system,contents = self._parts(messages)
        serialized = json.dumps(dict(system=system,contents=contents,schema=schema),ensure_ascii=False,separators=(',',':'))
        if serialized in self._counts:
            return self._counts[serialized]
        upper = len(serialized.encode())+512
        if upper<=self.config.leny_gemini_input_token_budget:
            self._counts[serialized] = upper
            return upper
        client = await self._sdk()
        from google.genai import types
        response = await self._call(lambda: client.aio.models.count_tokens(model=self.model_name,contents=contents,
            config=types.CountTokensConfig(system_instruction=system)),'count',upper,serialized)
        count = getattr(response,'total_tokens',None)
        if type(count) is not int or count<1:
            raise LenyError('LENY_GEMINI_TOKEN_COUNT','No se pudo comprobar el tamaño del contexto.')
        # Native generation schema is not supported by Developer count_tokens.
        # Reserve all its UTF-8 bytes plus framing, without claiming exactness.
        total = count+len(json.dumps(schema,ensure_ascii=False).encode())+512
        self._counts[serialized] = total
        return total

    async def _generate(self,messages,schema=None,*,phase='generate'):
        from google.genai import types
        count = await self.measure_prompt(messages,schema)
        if count>self.config.leny_gemini_input_token_budget:
            raise LenyError('LENY_CONTEXT_LIMIT','El contexto no cabe en el presupuesto de Gemini. Precisa la sección.',422)
        system,contents = self._parts(messages)
        options = dict(system_instruction=system,max_output_tokens=self.config.leny_gemini_output_tokens,
            thinking_config=types.ThinkingConfig(thinking_level=self.config.leny_gemini_thinking_level,include_thoughts=False),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
        if schema is not None:
            native_schema=self._native_schema(schema)
            options.update(response_mime_type='application/json',response_json_schema=native_schema)
        request = dict(model=self.model_name,contents=contents,config=types.GenerateContentConfig(**options))
        serialized = json.dumps(dict(system=system,contents=contents,schema=self._native_schema(schema)),ensure_ascii=False)
        client = await self._sdk()
        result = await self._call(lambda:client.aio.models.generate_content(**request),phase,count,serialized)
        candidates = getattr(result,'candidates',None) or []
        if len(candidates)!=1:
            raise LenyError('LENY_GEMINI_EMPTY','Gemini no devolvió una respuesta utilizable.',502)
        candidate = candidates[0]
        reason = str(getattr(candidate.finish_reason,'value',candidate.finish_reason))
        self.finish_reason = 'length' if reason=='MAX_TOKENS' else 'stop'
        if reason!='STOP':
            raise LenyError('LENY_GEMINI_INCOMPLETE','Gemini no completó una respuesta que pueda verificarse.',502)
        parts = getattr(candidate.content,'parts',None) or []
        if any(getattr(p,'function_call',None) or getattr(p,'executable_code',None) for p in parts):
            raise LenyError('LENY_GEMINI_TOOLS_BLOCKED','El proveedor devolvió una operación no permitida.',502)
        value = ''.join(p.text or '' for p in parts if not getattr(p,'thought',False)).strip()
        if not value or len(value.encode())>self.config.leny_max_response_bytes:
            raise LenyError('LENY_GEMINI_EMPTY','Gemini devolvió una respuesta vacía o demasiado extensa.',502)
        if schema is not None:
            try: json.loads(value)
            except ValueError:
                raise LenyError('LENY_GEMINI_JSON','Gemini no devolvió una respuesta estructurada utilizable.',502) from None
        return value

    async def classify(self,messages,schema):
        return await self._generate(messages,schema,phase='classifier')

    async def structured(self,messages,schema):
        return await self._generate(messages,schema)

    async def stream(self,messages):
        # Full remote output before transport emission; no unverified deltas.
        yield await self._generate(messages)

    async def probe(self):
        client = await self._sdk()
        return await self._call(lambda:client.aio.models.get(model=self.model_name),'model',0,'{}')
