"""Conversation and authorized documentary evidence; no model-executed tools."""
from __future__ import annotations

import asyncio
import logging
from functools import partial
from time import monotonic

import anyio

from app.schemas.leny import DeltaEvent, DoneEvent, ErrorEvent, StartEvent
from app.services.leny_ollama import LenyError, OllamaProvider
from app.services.leny_store import LenyConflict
from app.services.leny_policy import (SYSTEM_PROMPT, PolicyDecision,
                                      contextual_decision, business_projection, capability_decision, clauses)
from app.services.leny_guard import OutputGuard
from app.services.leny_rag_routing import (candidate_enabled, candidate_decision, contextual_route,
                                         general_prompt, policy_version, question_with_topic, response_mode,
                                         retrieval_question, is_followup)
from app.services.leny_rag_diagnostics import RagDiagnostics


logger = logging.getLogger(__name__)
_UNSET = object()


def effective_policy(service):
    if candidate_enabled(service.config) and getattr(service, 'coverage_verifier', None) is not None:
        from app.services.leny_rag_coverage import COVERAGE_POLICY_VERSION
        return COVERAGE_POLICY_VERSION
    return policy_version(service.config)


async def threaded(function, *args, **kwargs):
    return await anyio.to_thread.run_sync(partial(function, *args, **kwargs))


def build_context(config, history: list[dict], message: str) -> list[dict[str, str]]:
    """UTF-8 bytes conservatively bound text tokens; reserve framing + generation."""
    budget = config.leny_num_ctx - config.leny_num_predict - 256
    system = {"role": "system", "content": general_prompt() if candidate_enabled(config) else SYSTEM_PROMPT}
    current = {"role": "user", "content": message}
    cost = lambda item: len(item["content"].encode("utf-8")) + 32
    used = cost(system) + cost(current)
    if used > budget:
        raise LenyError("LENY_CONTEXT_LIMIT", "El mensaje es demasiado extenso para el contexto configurado.", 422)
    selected = []
    # Add only complete, adjacent user/assistant pairs; never half a turn.
    for index in range(len(history) - 2, -1, -2):
        pair = history[index:index + 2]
        if [item["role"] for item in pair] != ["user", "assistant"]:
            continue
        pair_cost = sum(cost(item) for item in pair)
        if used + pair_cost > budget:
            break
        selected = pair + selected
        used += pair_cost
    return [system, *selected, current]


class LenyService:
    def __init__(self, config, store, coordinator, provider_factory=None, rate_limiter=None,
                 retrieval=None,sources=None,inference_state=None,embedding_factory=None,coverage_verifier=None):
        self.config, self.store, self.coordinator = config, store, coordinator
        self.provider_factory = provider_factory or (lambda: OllamaProvider(config))
        self.rate_limiter = rate_limiter
        self.retrieval,self.sources,self.inference_state=retrieval,sources,inference_state
        self.embedding_factory=embedding_factory
        # Experimental dependency injection only. No env/API switch or default
        # adapter: the usual ERP retains its existing path and policy version.
        self.coverage_verifier = coverage_verifier

    async def reconcile(self) -> int:
        lease = None
        try:
            lease = await threaded(self.coordinator.acquire)
            return await threaded(self.store.reconcile)
        finally:
            if lease is not None:
                with anyio.CancelScope(shield=True):
                    await threaded(lease.close)

    async def status(self) -> dict:
        code = "LENY_READY"
        try:
            await self.provider_factory().available()
            await threaded(self.store.ready)
        except LenyError as error:
            code = error.code
        return {"available": code == "LENY_READY", "code": code, "model": self.config.leny_model,
                "max_message_chars": self.config.leny_max_message_chars,
                "request_timeout_seconds": self.config.leny_total_timeout}

    async def prepare(self, actor, payload):
        started = monotonic()
        if not self.config.leny_enabled:
            raise LenyError("LENY_DISABLED", "LENY está deshabilitado.")
        if len(payload.message) > self.config.leny_max_message_chars:
            raise LenyError("LENY_MESSAGE_LIMIT", "El mensaje supera el máximo de caracteres permitido.", 422)
        build_context(self.config, [], payload.message)
        try:
            await threaded(self.store.duplicate, actor, payload.conversation_id, payload.request_id, payload.message)
        except LenyConflict as duplicate:
            if duplicate.code != "LENY_REQUEST_DUPLICATE" or duplicate.generation_status != "generating":
                raise
            # A live worker may receive a retry left by a crashed worker. Reconcile
            # without asking Ollama to generate, but never disturb a live lease.
            lease = None
            try:
                with anyio.CancelScope(shield=True):
                    try:
                        lease = await threaded(self.coordinator.acquire)
                    except LenyError as error:
                        if error.code == "LENY_BUSY":
                            raise duplicate from None
                        raise
                    await threaded(self.store.reconcile)
                    await threaded(self.store.duplicate, actor, payload.conversation_id, payload.request_id, payload.message)
            finally:
                if lease is not None:
                    with anyio.CancelScope(shield=True):
                        await threaded(lease.close)
            raise duplicate
        # Ownership and durable message duplicates were checked above. Quota is
        # charged before checking model availability or acquiring the global lease.
        if self.rate_limiter is not None:
            with anyio.CancelScope(shield=True):
                await threaded(self.rate_limiter.admit, actor, payload)
        lease = None
        turn = None
        try:
            # Shield admission so cancellation cannot orphan a returned lock lease.
            with anyio.CancelScope(shield=True):
                lease = await threaded(self.coordinator.acquire)
                await threaded(self.store.reconcile)
                # Recheck after reconciliation, so a crashed duplicate reports interrupted.
                await threaded(self.store.duplicate, actor, payload.conversation_id, payload.request_id, payload.message)
                topics = []
                turn_options = {}
                if candidate_enabled(self.config):
                    topics = await threaded(self.store.topic_history, actor, payload.conversation_id, effective_policy(self))
                    turn_options['policy_version'] = effective_policy(self)
                assistant_id, history = await threaded(self.store.begin_turn, actor, payload.conversation_id,
                                                        payload.request_id, payload.message, self.config.leny_model, **turn_options)
                context = build_context(self.config, history, payload.message)
                route = candidate_decision if candidate_enabled(self.config) else capability_decision
                decision = route(payload.message, topics or history, self.config.leny_rag_chat_enabled)
                provider = self.provider_factory()
                turn = PreparedTurn(self, actor, payload, assistant_id, context, provider, lease, decision=decision, started=started)
                turn.topic_history = topics
                turn.response_mode = response_mode(payload.message, topics) if candidate_enabled(self.config) else 'answer'
            if decision is None or decision.reply is None:
                await asyncio.wait_for(provider.available(), turn.remaining())
            return turn
        except BaseException as error:
            with anyio.CancelScope(shield=True):
                if turn is not None:
                    turn.error_reason = error.code.lower() if isinstance(error, LenyError) else "leny_preparation_failed"
                    turn.diagnostics.reason = turn.error_reason
                    turn.diagnostics.outcome = 'failed' if isinstance(error, Exception) else 'interrupted'
                    await turn.close(final_status="failed" if isinstance(error, Exception) else "interrupted")
                elif lease is not None:
                    await threaded(lease.close)
                if self.rate_limiter is not None and (turn is None or not turn.finalized):
                    await threaded(self.rate_limiter.finish, actor, payload.request_id,
                                   "failed" if isinstance(error, Exception) else "interrupted")
            if isinstance(error, asyncio.TimeoutError):
                raise LenyError("LENY_TOTAL_TIMEOUT", "La solicitud superó el tiempo permitido.", 504) from None
            raise

    def admin_config(self):
        names = ("enabled", "model", "num_ctx", "num_predict", "temperature", "keep_alive", "connect_timeout",
                 "first_token_timeout", "idle_timeout", "total_timeout", "max_message_chars", "max_response_bytes", "retention_days",
                 "rate_limit", "rate_window_seconds", "output_holdback_chars", "classifier_timeout")
        return {name: getattr(self.config, "leny_" + name) for name in names} | {
            "max_concurrent_generations": 1,
            "rag_profile": self.config.leny_rag_profile,
            "rag_evidence_mode": self.config.leny_rag_evidence_mode,
            "rag_adaptive_token_probe": self.config.leny_rag_adaptive_token_probe,
            "rag_ranking": self.config.leny_rag_ranking,
            "rag_neighbor_chunks": self.config.leny_rag_neighbor_chunks,
            "rag_max_context_bytes": self.config.leny_rag_max_context_bytes,
        }


class PreparedTurn:
    def __init__(self, service, actor, payload, assistant_id, context, provider, lease, *, decision=_UNSET, started=None):
        self.service, self.actor, self.payload = service, actor, payload
        self.assistant_id, self.context, self.provider, self.lease = assistant_id, context, provider, lease
        self.content, self.finalized, self.closed = "", False, False
        # None is an intentional request for contextual classification. Do not
        # silently re-run an older policy that can deny an enabled capability.
        self.decision = capability_decision(payload.message, context[1:-1], service.config.leny_rag_chat_enabled) if decision is _UNSET else decision
        self.topic_history = []
        self.started = started if started is not None else monotonic()
        self.guard = OutputGuard(general_prompt() if candidate_enabled(service.config) else SYSTEM_PROMPT,
                                 service.config.leny_output_holdback_chars)
        self.output_blocked = False
        self.error_reason = None
        self.fragments=[]
        self.documental=False
        self.measured_context=False
        self.response_mode='answer'
        self.documented_reply=None
        self.evidence_verdict = None
        self.coverage_binding = None
        self.coverage_reason = None
        self.question=payload.message
        self.timings={}
        self.diagnostics = RagDiagnostics(getattr(service.config, 'leny_rag_profile', 'legacy'), self.started)
        if getattr(service,'inference_state',None):
            from app.services.leny_inference_state import ManagedProvider
            self.provider=ManagedProvider(provider,service.inference_state,lease,payload.request_id,self.remaining)

    def remaining(self):
        return max(0.001, self.service.config.leny_total_timeout - (monotonic() - self.started))

    async def save(self, status):
        decision = self.decision or PolicyDecision("ambiguous", "classification_pending")
        await threaded(self.service.store.save, self.actor, self.payload.conversation_id, self.assistant_id, self.content, status,
                       category=decision.category, reason=self.error_reason or decision.reason,
                       policy_version=effective_policy(self.service), context_eligible=decision.category == "business" and not decision.mixed and not self.output_blocked and not self.documental)
        if status != "generating":
            self.finalized = True
            limiter = getattr(self.service, "rate_limiter", None)
            if limiter is not None:
                await threaded(limiter.finish, self.actor, self.payload.request_id,
                               "refused" if decision.reply and status == "completed" else status)

    async def close(self, *, final_status="interrupted"):
        if self.closed:
            return
        self.closed = True
        with anyio.CancelScope(shield=True):
            try:
                if not self.finalized:
                    await self.save(final_status)
            except Exception:
                # A later lease holder reconciles the durable generating marker.
                logger.warning("LENY_FINALIZATION_DEFERRED")
            finally:
                try:
                    if self.documental:
                        self.timings['total_seconds']=round(monotonic()-self.started,4)
                        logger.info('LENY_RAG_TIMING',extra={'leny_timings':dict(self.timings)})
                    self.diagnostics.duration('total', monotonic() - self.started)
                    if self.diagnostics.outcome == 'pending':
                        self.diagnostics.outcome = final_status
                    logger.info('LENY_RAG_PIPELINE', extra={'leny_rag': self.diagnostics.snapshot()})
                finally:
                    # Diagnostics must never retain a PostgreSQL lock/connection.
                    await threaded(self.lease.close)

    async def heartbeat(self):
        while True:
            await anyio.sleep(1)
            await threaded(self.lease.check)
            if self.fragments:
                await threaded(self.service.retrieval.revalidate,self.actor,self.fragments)
                await self.revalidate_coverage()

    async def check_coverage(self, rows):
        verifier = getattr(self.service, 'coverage_verifier', None)
        if verifier is None:
            return None
        started = monotonic()
        try:
            result = await threaded(verifier.evaluate, self.payload.message, rows, history=self.topic_history)
        except (ValueError, TypeError, KeyError):
            raise LenyError('LENY_RAG_COVERAGE_INVALID', 'No se pudo verificar la cobertura de las fuentes.', 502) from None
        finally:
            self.diagnostics.duration('coverage', monotonic()-started)
        self.diagnostics.count('coverage_checked', len(rows))
        self.diagnostics.count('coverage_accepted', len(rows) if result.release_allowed else 0)
        return result

    async def revalidate_coverage(self):
        if self.coverage_binding is None:
            return
        checked = await self.check_coverage(self.fragments)
        if (checked is None or not checked.release_allowed
                or checked.fragment_ids != self.coverage_binding.fragment_ids
                or checked.manifest_fingerprints != self.coverage_binding.manifest_fingerprints):
            raise LenyError('LENY_RAG_COVERAGE_CHANGED', 'La cobertura verificada dejó de estar disponible.', 409)

    async def select_evidence(self, candidates):
        """Conservative default; optional bounded cold prefill experiment.

        At most three one-token probes, discarded before browser streaming. Two
        identical cold counts must agree before spending more than the byte
        bound. Reserve another32tokens for the actual relevance-verdict value.
        Missing instrumentation falls back to the conservative pack; uncertainty
        or transport errors retain the existing quarantine behavior.
        """
        from app.services.leny_rag_retrieval import pack_context
        config = self.service.config
        safe = pack_context(config, self.question, candidates, response_mode=self.response_mode, source_limit=20)
        if not (candidate_enabled(config) and config.leny_rag_evidence_mode == 'adaptive'
                and config.leny_rag_adaptive_token_probe and config.leny_keep_alive == '0'):
            return safe
        selected, context = pack_context(config, self.question, candidates, verdict='contradictory', for_probe=True,
                                         response_mode=self.response_mode, source_limit=20)
        if not selected:
            return safe
        if [row['fragment_id'] for row in selected] == [row['fragment_id'] for row in safe[0]]:
            # Measuring cannot recover additional evidence in this turn. Keep
            # the proven byte bound and avoid duplicate cold model loads.
            return safe
        budget = config.leny_num_ctx - config.leny_num_predict - 256 - 32
        probe_started = monotonic()
        calls = 0
        try:
            while selected and calls < 2:
                await threaded(self.service.retrieval.revalidate, self.actor, selected)
                tokens = await asyncio.wait_for(self.provider.measure_prompt(context), self.remaining())
                calls += 1
                self.diagnostics.count('probe_count', calls)
                self.diagnostics.count('probe_prompt_tokens', tokens)
                if tokens <= budget:
                    repeated = await asyncio.wait_for(self.provider.measure_prompt(context), self.remaining())
                    calls += 1
                    self.diagnostics.count('probe_count', calls)
                    if repeated == tokens:
                        self.measured_context = True
                        return selected, context
                    return safe
                # One smaller whole-fragment attempt leaves room to verify the
                # second count. Never cut a step or silently grow num_ctx.
                limit = max(0, int(len(selected) * budget / tokens) - 1)
                selected, context = pack_context(config, self.question, selected[:limit],
                                               verdict='contradictory', for_probe=True, response_mode=self.response_mode, source_limit=20)
            return safe
        except LenyError as error:
            if error.code != 'LENY_RAG_PROBE_UNAVAILABLE':
                raise
            return safe
        finally:
            self.diagnostics.duration('context_probe', monotonic()-probe_started)

    async def prepare_documental(self):
        import json
        from app.services.leny_rag_retrieval import (pack_context, NO_EVIDENCE, CONTEXT_LIMIT, RELEVANCE_PROMPT,
            RELEVANCE_SCHEMA, RAG4_RELEVANCE_PROMPT, relevance_schema, reviewed_selection)
        from app.services.leny_rag_grounding import grounded_reply
        from app.services.leny_rag_common import QUERY_POLICY,available_ram,RagError
        from app.services.leny_rag_embeddings import EmbeddingProvider
        self.documental=True
        config=self.service.config
        candidate = candidate_enabled(config)
        if candidate:
            self.question = retrieval_question(self.question)
        if not self.service.retrieval or not await threaded(self.service.retrieval.ready):
            raise LenyError('LENY_RAG_UNAVAILABLE','La consulta documental no está disponible.',503)
        if len(self.question.encode())>config.leny_rag_query_max_bytes:
            raise LenyError('LENY_RAG_QUERY_LIMIT','La pregunta documental es demasiado extensa. Formula una consulta más breve.',422)
        if await threaded(available_ram)<config.leny_rag_min_ram_bytes:
            raise LenyError('LENY_RAG_MEMORY','No hay memoria disponible suficiente para la consulta documental.',503)
        settings=config.model_copy(update={'leny_rag_batch_seconds':config.leny_rag_query_embed_timeout_seconds,
                                          'leny_rag_read_seconds':config.leny_rag_query_embed_timeout_seconds})
        embedding=(self.service.embedding_factory or EmbeddingProvider)(settings)
        embedding.inference_started=False
        embedding_started=monotonic()
        try:
            async def embed():return await embedding.embed([QUERY_POLICY['template'].format(query=self.question)])
            if self.service.inference_state:
                vectors=await self.provider.call(embed,config.leny_rag_model,'query_embedding',
                    lambda:embedding.response_complete or not embedding.inference_started)
            else:vectors=await asyncio.wait_for(embed(),min(self.remaining(),config.leny_rag_query_embed_timeout_seconds))
            if await threaded(available_ram)<config.leny_rag_min_resident_ram_bytes:
                raise LenyError('LENY_RAG_MEMORY','No hay margen de memoria suficiente para continuar la consulta documental.',503)
        except RagError as error:
            raise LenyError('LENY_'+error.code,error.message,error.status) from None
        finally:
            if embedding.owned_model and embedding.response_complete:
                with anyio.CancelScope(shield=True):
                    try:await embedding.release()
                    except Exception:logger.warning('LENY_RAG_EMBEDDING_RELEASE_DEFERRED')
        self.timings['embedding_and_release_seconds']=round(monotonic()-embedding_started,4)
        self.diagnostics.duration('embedding_and_release', monotonic()-embedding_started)
        search_started=monotonic()
        search_options = {'question': self.question} if candidate_enabled(config) else {}
        if candidate and self.topic_history and is_followup(self.payload.message):
            documents = await threaded(self.service.store.topic_document_ids, self.actor,
                                       self.payload.conversation_id, effective_policy(self.service))
            if isinstance(documents, list):
                search_options['document_ids'] = documents
        candidates=await threaded(self.service.retrieval.search,self.actor,vectors[0], **search_options)
        self.timings['search_seconds']=round(monotonic()-search_started,4)
        self.diagnostics.duration('search', monotonic()-search_started)
        self.diagnostics.count('candidates', len(candidates))
        packing_started=monotonic()
        if candidate:
            selected, context, verdict = await self.review_candidates(candidates)
            data = {'verdict': verdict}
        else:
            selected, context = await self.select_evidence(candidates)
            data = None
        self.timings['context_seconds']=round(monotonic()-packing_started,4)
        self.diagnostics.duration('context', monotonic()-packing_started)
        self.diagnostics.count('selected', len(selected))
        self.diagnostics.count('evidence_bytes', sum(len(row['text'].encode('utf-8')) for row in selected))
        if not selected:
            if candidate:
                self.diagnostics.verdict = 'none'
                return NO_EVIDENCE
            return CONTEXT_LIMIT if candidates else NO_EVIDENCE
        await threaded(self.service.retrieval.revalidate,self.actor,selected)
        review=[{'role':'system','content':RAG4_RELEVANCE_PROMPT if candidate else RELEVANCE_PROMPT},context[-1]]
        review_started = monotonic()
        try:
            if not candidate:
                raw = await self.provider.classify(review, RELEVANCE_SCHEMA)
                data=json.loads(raw)
                if not isinstance(data, dict) or set(data)!={'verdict'} or data['verdict'] not in {'sufficient','partial','contradictory','none'}:
                    raise ValueError('Invalid relevance result')
        except (ValueError,TypeError,KeyError):
            if not candidate_enabled(config):return NO_EVIDENCE
            raise LenyError('LENY_RAG_REVIEW_INVALID', 'No se pudo verificar la pertinencia de las fuentes. La consulta documental no se completó.', 502) from None
        finally:
            if not candidate:
                self.diagnostics.duration('review', monotonic()-review_started)
        self.diagnostics.verdict = data['verdict']
        self.evidence_verdict = data['verdict']
        if data['verdict'] == 'none':return NO_EVIDENCE
        if candidate and len(selected) > min(config.leny_rag_top_k, 5):
            # A chosen document's remaining conditions cannot be silently
            # dropped to squeeze it through the final five-source ceiling.
            raise LenyError('LENY_RAG_CONTEXT_LIMIT', 'Las fuentes pertinentes exceden el límite de contexto. Precisa la sección que necesitas.', 422)
        if candidate_enabled(config):
            checked, context = pack_context(config, self.question, selected, verdict=data['verdict'],
                                           for_probe=self.measured_context, response_mode=self.response_mode)
            if [row['fragment_id'] for row in checked] != [row['fragment_id'] for row in selected]:
                raise LenyError('LENY_CONTEXT_LIMIT', 'La evidencia no cabe íntegra en el contexto disponible.', 422)
        self.diagnostics.count('prompt_bytes', sum(len(row['content'].encode('utf-8')) + 32 for row in context))
        self.diagnostics.count('selected', len(selected))
        self.diagnostics.count('evidence_bytes', sum(len(row['text'].encode('utf-8')) for row in selected))
        if candidate and getattr(self.service, 'coverage_verifier', None) is not None:
            # Check the final expanded/packed evidence, before any source is
            # persisted or content emitted. Never inspect Qwen's aspect label.
            await threaded(self.service.retrieval.revalidate, self.actor, selected)
            coverage = await self.check_coverage(selected)
            if not coverage.release_allowed:
                self.coverage_reason = coverage.reason
                if coverage.verdict == 'not_covered':
                    return 'No dispongo de evidencia verificada que respalde ese asunto y sus condiciones. Puedes precisar la consulta.'
                return ('No puedo verificar con seguridad la cobertura documental de tu consulta. '
                        'Precisa el asunto o solicita una revisión de las fuentes.')
            self.coverage_binding = coverage
            if coverage.verdict in {'partial', 'conflicting'}:
                self.evidence_verdict = 'partial' if coverage.verdict == 'partial' else 'contradictory'
        await threaded(self.service.sources.persist,self.actor,self.assistant_id,selected)
        self.fragments,self.context=selected,context
        self.guard=OutputGuard(context[0]['content'],config.leny_output_holdback_chars,
            citations={'S'+str(i+1) for i in range(len(selected))}, require_citation=candidate_enabled(config),
            canonical_citations=candidate_enabled(config),
            max_bytes=config.leny_max_response_bytes if candidate_enabled(config) else None)
        if candidate and self.response_mode in {'next_step', 'continuation'}:
            from app.services.leny_rag_followup import next_documented_point
            anchor = next((row['content'] for row in reversed(self.topic_history) if row.get('role') == 'user'), '')
            self.documented_reply = next_documented_point(anchor, selected, continuation=self.response_mode == 'continuation')
            self.diagnostics.count('documented_excerpt', 1)
        elif candidate:
            self.documented_reply = grounded_reply(selected, self.response_mode)
            self.diagnostics.count('documented_excerpt', 1)
            self.diagnostics.count('grounded_excerpt', 1)
        return None

    async def review_candidates(self, candidates):
        """One bounded joint plan instead of accumulating per-document partials."""
        import json
        import re
        from app.services.leny_rag_grounding import unsupported_request
        from app.services.leny_rag_selection import preselect, plan_payload, plan_schema, verify_plan, PLAN_PROMPT
        from app.services.leny_rag_retrieval import pack_context
        config = self.service.config
        started = monotonic()
        review_seconds = 0.0
        selection_seconds = 0.0
        try:
            pool = preselect(candidates, question=self.question)
            selection_seconds = monotonic()-started
            if not pool:
                return [], [], 'none'
            if unsupported_request(self.question, pool):
                self.diagnostics.count('unsupported_request', 1)
                return [], [], 'none'
            # Existing exact-context probes, memory floors, lease and deadline
            # apply to the review too. Do not measure a different JSON payload.
            payload = plan_payload(self.question, pool)
            review = [{'role': 'system', 'content': PLAN_PROMPT},
                      {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}]
            budget = config.leny_num_ctx-config.leny_num_predict-256
            size = sum(len(item['content'].encode('utf-8'))+32 for item in review)
            if size > budget:
                if not (config.leny_rag_evidence_mode == 'adaptive' and config.leny_rag_adaptive_token_probe
                        and config.leny_keep_alive == '0'):
                    raise LenyError('LENY_RAG_CONTEXT_LIMIT', 'La evidencia no cabe en el contexto disponible.', 422)
                tokens = await self.provider.measure_prompt(review)
                repeated = await self.provider.measure_prompt(review)
                if tokens != repeated or tokens > budget:
                    raise LenyError('LENY_RAG_CONTEXT_LIMIT', 'No se confirmó espacio para la revisión.', 422)
            await threaded(self.service.retrieval.revalidate, self.actor, pool)
            try:
                review_started = monotonic()
                raw = await self.provider.classify(review, plan_schema(len(pool)))
                review_seconds = monotonic()-review_started
                selection_started = monotonic()
                selected, verdict, relation = verify_plan(raw, pool)
            except (ValueError, TypeError, KeyError):
                raise LenyError('LENY_RAG_REVIEW_INVALID', 'No se pudo verificar la pertinencia de las fuentes.', 502) from None
            self.diagnostics.count('review_documents', len({r.get('document_id', r['fragment_id']) for r in pool}))
            if not selected:
                return [], [], 'none'
            if unsupported_request(self.question, selected):
                self.diagnostics.count('unsupported_request', 1)
                return [], [], 'none'
            complete = bool(re.search(r'completo|todos|pasos|etapas|proceso|procedimiento|c[oó]mo.*(?:hace|confecc|fabric)',
                                      self.question, re.I))
            if complete:
                # Preserve ALL retrieved parts of each chosen procedure. The
                # count check detects missing SQL candidates; no old text or
                # foreign document may be loaded to manufacture completeness.
                identities = {r.get('document_id', r['fragment_id']) for r in selected}
                selected = [r for r in pool if r.get('document_id', r['fragment_id']) in identities]
                for identity in identities:
                    parts = [r for r in selected if r.get('document_id', r['fragment_id']) == identity]
                    if any(type(r.get('document_fragment_count')) is int and
                           r['document_fragment_count'] != len(parts) for r in parts):
                        raise LenyError('LENY_RAG_CONTEXT_LIMIT', 'El procedimiento no se recuperó de forma íntegra.', 422)
            if len(selected) > min(config.leny_rag_top_k, 5):
                raise LenyError('LENY_RAG_CONTEXT_LIMIT', 'La evidencia íntegra excede el máximo de fuentes.', 422)
            selection_seconds += monotonic()-selection_started
            checked, context = await self.select_evidence(selected)
            if [r['fragment_id'] for r in checked] != [r['fragment_id'] for r in selected]:
                raise LenyError('LENY_RAG_CONTEXT_LIMIT', 'La evidencia no cabe de forma íntegra.', 422)
            return checked, context, verdict
        finally:
            self.diagnostics.duration('review', review_seconds)
            self.diagnostics.duration('selection', selection_seconds)

    async def events(self):
        iterator = None
        heartbeat = asyncio.create_task(self.heartbeat())
        pending = None
        checkpoint = monotonic()
        try:
            yield StartEvent(conversation_id=self.payload.conversation_id, request_id=self.payload.request_id,
                             assistant_message_id=self.assistant_id).model_dump_json() + "\n"
            if self.decision is None:
                routing_started = monotonic()
                classify = contextual_route if candidate_enabled(self.service.config) else contextual_decision
                pending = asyncio.create_task(classify(self.provider, self.payload.message,
                    self.topic_history or self.context[1:-1], documents=self.service.config.leny_rag_chat_enabled))
                done, _ = await asyncio.wait({pending, heartbeat}, timeout=self.remaining(), return_when=asyncio.FIRST_COMPLETED)
                if heartbeat in done:
                    await heartbeat
                if pending not in done:
                    raise LenyError("LENY_TOTAL_TIMEOUT", "La solicitud superó el tiempo permitido.", 504)
                self.decision = await pending
                self.diagnostics.duration('routing', monotonic()-routing_started)
            self.diagnostics.route = 'documentary' if self.decision.documents else self.decision.category
            self.diagnostics.reason = self.decision.reason
            self.diagnostics.count('topic_questions', len(self.topic_history))
            if self.decision.category == "business" and self.decision.mixed:
                projection = business_projection(self.payload.message)
                if self.service.config.leny_rag_chat_enabled:
                    parts=clauses(self.payload.message)
                    route = candidate_decision if candidate_enabled(self.service.config) else capability_decision
                    permitted=[part for part in parts if (decision:=route(part,[],True)) and decision.category=='business' and not decision.mixed]
                    projection='\n'.join(permitted) if permitted and len(permitted)<len(parts) else None
                if projection is None:
                    self.decision = PolicyDecision("ambiguous", "mixed_separation_uncertain")
                else:
                    self.context = build_context(self.service.config, [], projection)
                    self.question=projection
                    route = candidate_decision if candidate_enabled(self.service.config) else capability_decision
                    routed=route(projection,[],self.service.config.leny_rag_chat_enabled)
                    self.decision=PolicyDecision('business','business_mixed',True,bool(routed and routed.documents))
            if self.decision.reply:
                self.diagnostics.outcome = 'policy'
                self.content = self.decision.reply
                if self.decision.category=='unavailable' and self.service.config.leny_rag_chat_enabled:
                    self.content='No tengo herramientas para consultar tablas privadas, buscar en Internet ni ejecutar cambios en el ERP. Solo puedo ofrecer orientación empresarial y consultar documentación publicada para tu rol.'
                await self.save("completed")
                yield DeltaEvent(text=self.content).model_dump_json() + "\n"
                yield DoneEvent(status="completed", finish_reason="policy", outcome="clarification" if self.decision.category == "ambiguous" else "refused",
                                reason_code=self.decision.reason).model_dump_json() + "\n"
                return
            if self.decision.documents:
                if candidate_enabled(self.service.config):
                    self.question = question_with_topic(self.question, self.topic_history)
                reply=await asyncio.wait_for(self.prepare_documental(),self.remaining())
                if reply:
                    self.content=reply
                    self.error_reason='rag_evidence_insufficient'
                    self.diagnostics.reason = self.coverage_reason or self.error_reason
                    self.diagnostics.outcome = 'no_evidence'
                    await self.save('completed')
                    self.diagnostics.duration('first_content', monotonic()-self.started)
                    yield DeltaEvent(text=reply).model_dump_json()+'\n'
                    yield DoneEvent(status='completed',finish_reason='evidence',outcome='clarification',reason_code=self.coverage_reason or self.error_reason).model_dump_json()+'\n'
                    return
            if self.decision.mixed:
                self.content = "Responderé únicamente la parte empresarial; la otra solicitud está fuera de mi ámbito.\n\n"
                yield DeltaEvent(text=self.content).model_dump_json() + "\n"
            if candidate_enabled(self.service.config) and self.evidence_verdict in {'partial', 'contradictory'}:
                notice = ('La evidencia disponible es parcial; esta respuesta se limita a los puntos documentados.\n\n'
                          if self.evidence_verdict == 'partial' else
                          'Se muestran las fuentes por separado; no se establece prioridad entre ellas.\n\n')
                if self.fragments:
                    await threaded(self.service.retrieval.revalidate, self.actor, self.fragments)
                    await self.revalidate_coverage()
                self.content += notice
                self.diagnostics.duration('first_content', monotonic()-self.started)
                yield DeltaEvent(text=notice).model_dump_json() + '\n'
            if self.documented_reply is not None:
                async def excerpt():
                    parts = self.documented_reply[0].split('\n\n')
                    for index, part in enumerate(parts):
                        await anyio.sleep(0)
                        yield ('\n\n' if index else '')+part
                iterator = excerpt().__aiter__()
            else:
                iterator = self.provider.stream(self.context).__aiter__()
            generation_started = monotonic()
            while True:
                pending = asyncio.create_task(iterator.__anext__())
                done, _ = await asyncio.wait({pending, heartbeat}, timeout=self.remaining(), return_when=asyncio.FIRST_COMPLETED)
                if heartbeat in done:
                    await heartbeat
                if pending not in done:
                    raise LenyError("LENY_TOTAL_TIMEOUT", "La solicitud superó el tiempo permitido.", 504)
                try:
                    content = await pending
                except StopAsyncIteration:
                    break
                content = self.guard.feed(content)
                if self.fragments:
                    await threaded(self.service.retrieval.revalidate,self.actor,self.fragments)
                    await self.revalidate_coverage()
                self.content += content
                if monotonic() - checkpoint >= 1:
                    await self.save("generating")
                    checkpoint = monotonic()
                if content:
                    if 'first_content' not in self.diagnostics.durations:
                        self.diagnostics.duration('first_content', monotonic()-self.started)
                    self.timings.setdefault('first_content_seconds',round(monotonic()-self.started,4))
                    yield DeltaEvent(text=content).model_dump_json() + "\n"
            tail = self.guard.feed("", final=True)
            if self.fragments:
                import re
                self.diagnostics.count('citations', len(set(re.findall(r'\[(S\d+)\]', self.guard.text))))
            self.diagnostics.duration('render' if self.documented_reply is not None else 'generation', monotonic()-generation_started)
            metrics = {} if self.documented_reply is not None else getattr(self.provider, 'metrics', {})
            if isinstance(metrics, dict):
                for key in ('prompt_eval_count', 'prompt_eval_cached_count', 'eval_count'):
                    if type(metrics.get(key)) is int and metrics[key] >= 0:
                        self.diagnostics.count(key, metrics[key])
                for key, name in (('load_duration', 'load'), ('prompt_eval_duration', 'prompt_eval'), ('eval_duration', 'eval'), ('total_duration', 'provider_total')):
                    if type(metrics.get(key)) is int and metrics[key] >= 0:
                        self.diagnostics.duration(name, metrics[key] / 1e9)
            if self.fragments:
                await threaded(self.service.retrieval.revalidate,self.actor,self.fragments)
                await self.revalidate_coverage()
            self.content += tail
            if tail:
                self.timings.setdefault('first_content_seconds',round(monotonic()-self.started,4))
                yield DeltaEvent(text=tail).model_dump_json() + "\n"
            finish_reason = 'evidence' if self.documented_reply is not None else getattr(self.provider, "finish_reason", "stop")
            status = "interrupted" if finish_reason == "length" else "completed"
            self.diagnostics.outcome = status
            await self.save(status)
            sources=[]
            if self.fragments and status=='completed':
                await threaded(self.service.retrieval.revalidate,self.actor,self.fragments)
                await self.revalidate_coverage()
                sources=(await threaded(self.service.sources.for_messages,self.actor,[self.assistant_id])).get(self.assistant_id,[])
            outcome = 'clarification' if self.documented_reply is not None and self.documented_reply[1] else 'answered'
            yield DoneEvent(status=status, finish_reason=finish_reason, outcome=outcome,
                            reason_code=self.decision.reason,sources=sources).model_dump_json() + "\n"
        except (LenyError, asyncio.TimeoutError) as error:
            if isinstance(error, asyncio.TimeoutError):
                error = LenyError('LENY_TOTAL_TIMEOUT', 'La consulta superó el tiempo permitido.', 504)
            self.output_blocked = error.code == "LENY_OUTPUT_BLOCKED"
            self.error_reason = error.code.lower()
            self.diagnostics.reason = self.error_reason
            self.diagnostics.outcome = 'failed'
            try:
                await self.save("failed")
            except Exception:
                # A storage failure must not replace a safe NDJSON error with
                # an uncaught exception containing SQL parameters or content.
                logger.warning("LENY_FINALIZATION_DEFERRED")
            yield ErrorEvent(code=error.code, message=error.message).model_dump_json() + "\n"
        except Exception:
            self.diagnostics.reason = 'leny_internal_error'
            self.diagnostics.outcome = 'failed'
            logger.warning("LENY_GENERATION_FAILED")
            try:
                await self.save("failed")
            except Exception:
                logger.warning("LENY_FINALIZATION_DEFERRED")
            yield ErrorEvent(code="LENY_INTERNAL_ERROR", message="No se pudo completar la respuesta de LENY.").model_dump_json() + "\n"
        finally:
            with anyio.CancelScope(shield=True):
                for task in (pending, heartbeat):
                    if task is not None:
                        task.cancel()
                await asyncio.gather(*(task for task in (pending, heartbeat) if task is not None), return_exceptions=True)
                try:
                    if iterator is not None:
                        await iterator.aclose()
                except Exception:
                    logger.warning("LENY_PROVIDER_CLOSE_DEFERRED")
                finally:
                    await self.close()
