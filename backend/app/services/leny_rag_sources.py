"""Owner-bound sources; no content or metadata survives an authorization failure."""
from uuid import uuid4

from sqlalchemy import select, text

from app.models.leny import LenyMessage, LenyConversation
from app.models.leny_rag_chat import LenyRagMessageSource as Source
from app.schemas.leny_rag_chat import SourceReference, SourceDetail
from app.services.leny_document_service import DocumentService
from app.services.leny_ollama import LenyError
from app.services.leny_rag_retrieval import ELIGIBLE, parameters, reader


class SourceService:
    def __init__(self, config, sessions):
        self.config, self.sessions = config, sessions
        self.documents = DocumentService(config,sessions)

    def audit_read(self,actor,source_id,download=False):
        # Once per HTTP access, never once per streamed block; codes/IDs only.
        with self.documents.reading() as db:
            self.documents.audit(db,actor,'LENY_RAG_SOURCE_DOWNLOADED' if download else 'LENY_RAG_SOURCE_READ',source_id)
            db.commit()

    def _available(self, db, actor, message_ids):
        reader(db,actor)
        query = ELIGIBLE+"""SELECT s.id source_id,s.message_id,s.ordinal,f.id fragment_id,
          e.title label,e.version,f.locator,f.source_type,f.text,e.coverage,
          e.storage_key,e.media_type,e.original_name,e.size_bytes,e.sha256
          FROM eligible e JOIN leny.rag_fragmentos f ON f.indexation_id=e.indexation_id
          JOIN leny.rag_fuentes_mensaje s ON s.fragment_id=f.id
          JOIN leny.mensajes m ON m.id=s.message_id
          JOIN leny.conversaciones c ON c.id=m.conversation_id
          WHERE c.user_id=:user AND m.role='assistant' AND m.status='completed'
          AND m.id=ANY(CAST(:messages AS uuid[])) ORDER BY s.ordinal"""
        return {row['source_id']:dict(row) for row in db.execute(text(query),parameters(self.config,actor)|{'messages':[str(x) for x in message_ids]}).mappings()}

    @staticmethod
    def reference(source,row=None):
        base=dict(source_id=source.id,available=bool(row),citation_id='S'+str(source.ordinal))
        if row:
            base.update(label=row['label'],version=row['version'],locator=row['locator'],source_type=row['source_type'],
                        warnings=[str(w)[:200] for w in row['coverage'].get('warnings',[])[:10]])
        return SourceReference(**base).model_dump(mode='json',exclude_none=True)

    def for_messages(self, actor, message_ids):
        if not message_ids: return {}
        with self.documents.reading() as db:
            sources=list(db.scalars(select(Source).join(LenyMessage,LenyMessage.id==Source.message_id)
                .join(LenyConversation,LenyConversation.id==LenyMessage.conversation_id)
                .where(LenyConversation.user_id==actor.user_id,LenyMessage.id.in_(message_ids),LenyMessage.status=='completed')
                .order_by(Source.message_id,Source.ordinal)))
            available=self._available(db,actor,message_ids) if self.config.leny_rag_chat_enabled else {}
            result={}
            for source in sources:
                result.setdefault(source.message_id,[]).append(self.reference(source,available.get(source.id)))
            return result

    def persist(self, actor, message_id, fragments):
        with self.documents.lock(),self.documents.transaction() as db:
            reader(db,actor)
            message=db.scalar(select(LenyMessage).join(LenyConversation).where(LenyMessage.id==message_id,
                LenyConversation.user_id==actor.user_id,LenyMessage.role=='assistant',LenyMessage.status=='generating').with_for_update())
            if message is None: raise LenyError('LENY_NOT_FOUND','La conversación no existe.',404)
            ids=[str(row['fragment_id']) for row in fragments]
            allowed=set(db.execute(text(ELIGIBLE+'SELECT f.id FROM eligible e JOIN leny.rag_fragmentos f ON f.indexation_id=e.indexation_id WHERE f.id=ANY(CAST(:ids AS uuid[]))'),parameters(self.config,actor)|{'ids':ids}).scalars())
            if allowed!={row['fragment_id'] for row in fragments}:
                raise LenyError('LENY_RAG_SOURCE_REVOKED','La fuente dejó de estar disponible.',409)
            for ordinal,row in enumerate(fragments,1):
                db.add(Source(id=uuid4(),message_id=message_id,fragment_id=row['fragment_id'],ordinal=ordinal))
            self.documents.audit(db,actor,'LENY_RAG_EVIDENCE_SELECTED',message_id)

    def resolve(self,actor,source_id,*,internal=False):
        if not self.config.leny_rag_chat_enabled:
            raise LenyError('LENY_SOURCE_UNAVAILABLE','Fuente no disponible.',404)
        with self.documents.reading() as db:
            source=db.scalar(select(Source).join(LenyMessage,LenyMessage.id==Source.message_id)
                .join(LenyConversation,LenyConversation.id==LenyMessage.conversation_id)
                .where(Source.id==source_id,LenyConversation.user_id==actor.user_id,LenyMessage.status=='completed'))
            if source is None: raise LenyError('LENY_SOURCE_UNAVAILABLE','Fuente no disponible.',404)
            row=self._available(db,actor,[source.message_id]).get(source.id)
            if not row: raise LenyError('LENY_SOURCE_UNAVAILABLE','Fuente no disponible.',404)
            if internal:return row
            return SourceDetail(**self.reference(source,row),text=row['text']).model_dump(mode='json',exclude_none=True)
