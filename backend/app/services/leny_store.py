"""Short, owner-scoped transactions for LENY. No commercial services are used."""
from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.core.audit import register_audit_event
from app.models.leny import LenyConversation, LenyMessage
from app.schemas.leny import ConversationResponse, MessageResponse
from app.services.leny_ollama import LenyError
from app.services.leny_policy import POLICY_VERSION


@dataclass(frozen=True)
class LenyActor:
    account_id: int
    user_id: int
    event_id: str
    ip_address: str | None = None
    user_agent: str | None = None


class LenyConflict(LenyError):
    def __init__(self, code: str, message: str, status: str | None = None, request_id: UUID | None = None):
        super().__init__(code, message, 409)
        self.generation_status, self.request_id = status, request_id


class LenyStore:
    def __init__(self, session_factory, sources=None):
        self.session_factory = session_factory
        self.sources = sources

    @contextmanager
    def transaction(self):
        with self.session_factory() as db, db.begin():
            # Local to this transaction; never change pooled-session defaults.
            db.execute(text("SET LOCAL lock_timeout = '5s'"))
            db.execute(text("SET LOCAL statement_timeout = '10s'"))
            yield db

    def ready(self) -> None:
        try:
            with self.transaction() as db:
                db.execute(select(LenyConversation.id).limit(0))
                db.execute(select(LenyMessage.id, LenyMessage.context_eligible).limit(0))
        except Exception:
            raise LenyError("LENY_STORAGE_UNAVAILABLE", "El historial de LENY no está disponible.") from None

    def audit(self, db, actor: LenyActor, action: str, conversation_id: UUID) -> None:
        register_audit_event(
            db, action=action, description=action.replace("_", " "),
            user=SimpleNamespace(id=actor.user_id), reference=str(conversation_id),
            module="LENY", submodule="CONVERSACIONES", table="leny.conversaciones",
            functional_action=action, event_id=actor.event_id, http_method="POST",
            ip_address=actor.ip_address, user_agent=actor.user_agent,
        )

    def input_rejected(self, actor: LenyActor) -> None:
        with self.transaction() as db:
            register_audit_event(
                db, action="LENY_INPUT_REJECTED", description="LENY INPUT REJECTED",
                user=SimpleNamespace(id=actor.user_id), module="LENY", submodule="VALIDACION",
                table="leny.mensajes", functional_action="LENY_INPUT_REJECTED", event_id=actor.event_id,
                http_method="POST", ip_address=actor.ip_address, user_agent=actor.user_agent,
            )

    @staticmethod
    def own(db, actor: LenyActor, conversation_id: UUID, *, lock=False):
        stmt = select(LenyConversation).where(LenyConversation.id == conversation_id, LenyConversation.user_id == actor.user_id)
        if lock:
            stmt = stmt.with_for_update()
        conversation = db.scalar(stmt)
        if conversation is None:
            raise LenyError("LENY_NOT_FOUND", "La conversación no existe.", 404)
        return conversation

    def create(self, actor: LenyActor) -> dict:
        with self.transaction() as db:
            item = LenyConversation(id=uuid4(), user_id=actor.user_id, account_id=actor.account_id, title="Nueva conversación")
            db.add(item)
            db.flush()
            self.audit(db, actor, "LENY_CONVERSATION_CREATED", item.id)
            return ConversationResponse.model_validate(item).model_dump(mode="json")

    def list(self, actor: LenyActor, page: int, page_size: int) -> dict:
        with self.transaction() as db:
            condition = LenyConversation.user_id == actor.user_id
            total = db.scalar(select(func.count()).select_from(LenyConversation).where(condition))
            rows = db.scalars(select(LenyConversation).where(condition).order_by(LenyConversation.updated_at.desc(), LenyConversation.id)
                              .offset((page - 1) * page_size).limit(page_size)).all()
            return {"items": [ConversationResponse.model_validate(r).model_dump(mode="json") for r in rows],
                    "total": total, "page": page, "page_size": page_size}

    def detail(self, actor: LenyActor, conversation_id: UUID, page: int, page_size: int) -> dict:
        with self.transaction() as db:
            conversation = self.own(db, actor, conversation_id)
            condition = LenyMessage.conversation_id == conversation.id
            total = db.scalar(select(func.count()).select_from(LenyMessage).where(condition))
            rows = db.scalars(select(LenyMessage).where(condition).order_by(LenyMessage.sequence.desc())
                              .offset((page - 1) * page_size).limit(page_size)).all()
            references=self.sources.for_messages(actor,[r.id for r in rows]) if self.sources else {}
            return {"conversation": ConversationResponse.model_validate(conversation).model_dump(mode="json"),
                    "items": [MessageResponse.model_validate(r).model_dump(mode="json") | {'sources':references.get(r.id,[])} for r in reversed(rows)],
                    "total": total, "page": page, "page_size": page_size}

    def remove(self, actor: LenyActor, conversation_id: UUID) -> None:
        with self.transaction() as db:
            conversation = self.own(db, actor, conversation_id, lock=True)
            if db.scalar(select(LenyMessage.id).where(LenyMessage.conversation_id == conversation.id, LenyMessage.status == "generating").limit(1)):
                raise LenyConflict("LENY_GENERATING", "Detén la respuesta antes de eliminar esta conversación.")
            self.audit(db, actor, "LENY_CONVERSATION_DELETED", conversation.id)
            db.delete(conversation)

    def duplicate(self, actor: LenyActor, conversation_id: UUID, request_id: UUID, message: str) -> None:
        with self.transaction() as db:
            self.own(db, actor, conversation_id)
            previous = db.scalar(select(LenyMessage).join(LenyConversation).where(
                LenyConversation.user_id == actor.user_id, LenyMessage.request_id == request_id, LenyMessage.role == "user"))
            if previous:
                if previous.conversation_id != conversation_id or previous.content != message:
                    raise LenyConflict("LENY_REQUEST_REUSED", "El identificador de solicitud ya fue utilizado.")
                assistant = db.scalar(select(LenyMessage).where(LenyMessage.request_id == request_id, LenyMessage.role == "assistant"))
                raise LenyConflict("LENY_REQUEST_DUPLICATE", "Esta solicitud ya fue registrada. Recupera su respuesta del historial.",
                                   assistant.status if assistant else "failed", request_id)

    def reconcile(self) -> int:
        """Called ONLY while holding the global generation lock (no live writer)."""
        with self.transaction() as db:
            abandoned = db.scalars(select(LenyMessage).where(LenyMessage.status == "generating").with_for_update()).all()
            for message in abandoned:
                message.status = "interrupted"
                conversation = db.get(LenyConversation, message.conversation_id)
                actor = LenyActor(conversation.account_id, conversation.user_id, str(uuid4()))
                self.audit(db, actor, "LENY_GENERATION_ABANDONED", conversation.id)
            return len(abandoned)

    def topic_history(self, actor: LenyActor, conversation_id: UUID, policy_version: str) -> list[dict]:
        """Owner-scoped topic hints only. Never reuse documentary assistant text.

        A prior completed business decision is not a permission. Every future
        retrieval still applies current account, Casbin, publication and SQL ACL.
        """
        from app.services.leny_rag_routing import is_followup
        with self.transaction() as db:
            self.own(db, actor, conversation_id)
            rows = db.scalars(select(LenyMessage).where(LenyMessage.conversation_id == conversation_id)
                              .order_by(LenyMessage.sequence.desc()).limit(40)).all()
            eligible = {m.request_id: m for m in rows if m.role == 'assistant' and m.status == 'completed'
                        and m.category == 'business' and m.policy_version == policy_version
                        and m.reason not in {'rag_evidence_insufficient', 'business_mixed'}}
            anchors = [m for m in rows if m.role == 'user' and m.request_id in eligible
                       and not is_followup(m.content)]
            # The most recent substantive topic supersedes earlier subjects.
            # A general-advice turn must not resurrect an older RAG procedure.
            return [{'role': 'user', 'content': m.content[:400],
                     'documentary': not eligible[m.request_id].context_eligible} for m in anchors[:1]]

    def topic_document_ids(self, actor: LenyActor, conversation_id: UUID, policy_version: str):
        """Private provenance identities only; fresh retrieval checks current SQL ACL.

        None means the anchor had no documentary references (general topic).
        An empty list means references were purged: never substitute another
        document. Old content, labels and locators are not read or returned.
        """
        from app.models.leny_rag_chat import LenyRagMessageSource as Source
        from app.models.leny_rag import LenyRagFragment, LenyRagIndexation
        from app.models.leny_documents import LenyDocumentVersion
        from app.services.leny_rag_routing import is_followup
        with self.transaction() as db:
            self.own(db, actor, conversation_id)
            rows = db.scalars(select(LenyMessage).where(LenyMessage.conversation_id == conversation_id)
                              .order_by(LenyMessage.sequence.desc()).limit(40)).all()
            eligible = {m.request_id: m for m in rows if m.role == 'assistant' and m.status == 'completed'
                        and m.category == 'business' and m.policy_version == policy_version
                        and m.reason not in {'rag_evidence_insufficient', 'business_mixed'}}
            anchor = next((m for m in rows if m.role == 'user' and m.request_id in eligible
                           and not is_followup(m.content)), None)
            if anchor is None or eligible[anchor.request_id].context_eligible:
                return None
            message_id = eligible[anchor.request_id].id
            return list(db.scalars(select(LenyDocumentVersion.document_id).distinct()
                .join(LenyRagIndexation, LenyRagIndexation.version_id == LenyDocumentVersion.id)
                .join(LenyRagFragment, LenyRagFragment.indexation_id == LenyRagIndexation.id)
                .join(Source, Source.fragment_id == LenyRagFragment.id)
                .where(Source.message_id == message_id)))

    def begin_turn(self, actor: LenyActor, conversation_id: UUID, request_id: UUID, message: str, model: str,
                   *, policy_version=POLICY_VERSION) -> tuple[UUID, list[dict]]:
        try:
            with self.transaction() as db:
                conversation = self.own(db, actor, conversation_id, lock=True)
                # Recheck inside the transaction; global UUID uniqueness protects all workers.
                if db.scalar(select(LenyMessage.id).where(LenyMessage.request_id == request_id).limit(1)):
                    raise LenyConflict("LENY_REQUEST_REUSED", "El identificador de solicitud ya fue utilizado.")
                if db.scalar(select(LenyMessage.id).where(LenyMessage.conversation_id == conversation.id,
                                                         LenyMessage.status == "generating").limit(1)):
                    raise LenyConflict("LENY_GENERATING", "Esta conversación ya tiene una respuesta en curso.")
                history = db.scalars(select(LenyMessage).where(LenyMessage.conversation_id == conversation.id)
                                     .order_by(LenyMessage.sequence.desc()).limit(40)).all()
                sequence = max((m.sequence for m in history), default=0) + 1
                complete_requests = {m.request_id for m in history if m.role == "assistant" and m.status == "completed"
                                     and m.context_eligible and m.policy_version == policy_version}
                context = [{"role": m.role, "content": m.content} for m in reversed(history) if m.request_id in complete_requests]
                assistant_id = uuid4()
                db.add_all([
                    LenyMessage(id=uuid4(), conversation_id=conversation.id, sequence=sequence, request_id=request_id,
                                role="user", content=message, status="completed"),
                    LenyMessage(id=assistant_id, conversation_id=conversation.id, sequence=sequence + 1, request_id=request_id,
                                role="assistant", content="", status="generating", model=model),
                ])
                conversation.updated_at = datetime.now(timezone.utc)
                self.audit(db, actor, "LENY_GENERATION_STARTED", conversation.id)
                db.flush()
                return assistant_id, context
        except IntegrityError:
            raise LenyConflict("LENY_REQUEST_REUSED", "El identificador de solicitud ya fue utilizado.") from None

    def save(self, actor: LenyActor, conversation_id: UUID, assistant_id: UUID, content: str, status: str,
             *, category=None, reason=None, policy_version=None, context_eligible=False) -> None:
        with self.transaction() as db:
            conversation = self.own(db, actor, conversation_id, lock=True)
            message = db.scalar(select(LenyMessage).where(LenyMessage.id == assistant_id, LenyMessage.conversation_id == conversation.id).with_for_update())
            if message is None or message.status != "generating":
                raise LenyConflict("LENY_GENERATION_CLOSED", "Esta generación ya está finalizada.")
            message.content, message.status = content, status
            message.category, message.reason, message.policy_version = category, reason, policy_version
            message.context_eligible = bool(context_eligible and status == "completed" and category == "business")
            conversation.updated_at = datetime.now(timezone.utc)
            if status != "generating":
                self.audit(db, actor, "LENY_GENERATION_" + status.upper(), conversation.id)
                if reason:
                    # Codes only: no prompts, model content or classifier reasoning.
                    self.audit(db, actor, "LENY_POLICY_" + reason.upper(), conversation.id)

    def purge(self, days: int, *, apply: bool = False) -> int:
        if days <= 0:
            return 0
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        with self.transaction() as db:
            active = select(LenyMessage.conversation_id).where(LenyMessage.status == "generating")
            candidates = db.scalars(select(LenyConversation).where(
                LenyConversation.updated_at < cutoff, LenyConversation.id.not_in(active)).with_for_update()).all()
            if apply:
                for conversation in candidates:
                    # Recheck after row locking: another transaction may have
                    # started a generation while this SELECT waited for its lock.
                    if db.scalar(select(LenyMessage.id).where(
                            LenyMessage.conversation_id == conversation.id, LenyMessage.status == "generating").limit(1)):
                        continue
                    actor = LenyActor(conversation.account_id, conversation.user_id, str(uuid4()))
                    self.audit(db, actor, "LENY_RETENTION_DELETED", conversation.id)
                    db.delete(conversation)
            return len(candidates)
