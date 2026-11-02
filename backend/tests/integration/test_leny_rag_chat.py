"""Publication, current ACL, sources and quarantine on guarded PostgreSQL only."""
from contextlib import contextmanager
import hashlib
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from alembic.migration import MigrationContext
from alembic.operations import Operations

from test_leny_rag_service import rag_context, _source, _submit, _worker, _complete
from test_leny_rag_schema import _rag, _migration, _public_structure


def prepared(context,worker):
    source=_source(context)
    data=b'synthetic original only'
    with context.cluster.engine.begin() as db:
        key=db.execute(text('UPDATE leny.documento_versiones SET sha256=:hash,size_bytes=:size,storage_key=:key WHERE id=:id RETURNING storage_key'),
            {'id':source[1],'hash':hashlib.sha256(data).hexdigest(),'size':len(data),'key':'versions/'+uuid4().hex+'.blob'}).scalar_one()
    root=context.service.documents.storage.root
    (root/'versions').mkdir(parents=True,exist_ok=True)
    (root/key).write_bytes(data)
    _submit(context,source)
    claim=context.service.claim(worker)
    _complete(context,claim)
    return source,claim


def publish(context,source,claim):
    from app.schemas.leny_documents import PublicationRequest
    from app.services.leny_rag_publication import PublicationService
    service=PublicationService(context.service.settings,context.service.sessions)
    with context.cluster.engine.connect() as db:
        revision=db.execute(text('SELECT revision FROM leny.documentos WHERE id=:id'),{'id':source[0]}).scalar_one()
    data=PublicationRequest(request_id=uuid4(),version_id=source[1],indexation_id=claim['indexation_id'],expected_revision=revision,confirm=True)
    try:return service.publish(context.actor,source[0],data),data
    finally:service.documents.engine.dispose()


@contextmanager
def role(context,code):
    with context.cluster.engine.begin() as db:
        old=db.execute(text('SELECT rol_id FROM cuentas WHERE id=:id'),{'id':context.actor.account_id}).scalar_one()
        created=db.execute(text('INSERT INTO roles(codigo,nombre,activo) VALUES(:code,:code,true) ON CONFLICT(codigo) DO NOTHING RETURNING id'),{'code':code}).scalar_one_or_none()
        identity=created or db.execute(text('SELECT id FROM roles WHERE codigo=:code'),{'code':code}).scalar_one()
        db.execute(text('UPDATE cuentas SET rol_id=:role WHERE id=:id'),{'role':identity,'id':context.actor.account_id})
    try:yield identity
    finally:
        with context.cluster.engine.begin() as db:
            db.execute(text('UPDATE cuentas SET rol_id=:role WHERE id=:id'),{'role':old,'id':context.actor.account_id})
            if created:
                db.execute(text('DELETE FROM leny.documento_roles_lectura WHERE role_id=:role AND document_id IN (SELECT id FROM leny.documentos WHERE created_by=:user)'),{'role':created,'user':context.actor.user_id})
                db.execute(text('DELETE FROM roles WHERE id=:id'),{'id':created})


def test_publication_replay_and_recontextualization_pin_the_approved_index(rag_context):
    from app.services.leny_rag_publication import PublicationService
    from app.services.leny_document_storage import DocumentError
    ctx=rag_context;worker=_worker(ctx)
    source,first=prepared(ctx,worker)
    result,data=publish(ctx,source,first)
    service=PublicationService(ctx.service.settings,ctx.service.sessions)
    try:
        assert service.publish(ctx.actor,source[0],data)==result
        _submit(ctx,source,action='recontextualize')
        second=ctx.service.claim(worker);_complete(ctx,second)
        with ctx.cluster.engine.connect() as db:
            assert db.execute(text('SELECT published_indexation_id FROM leny.documentos WHERE id=:id'),{'id':source[0]}).scalar_one()==first['indexation_id']
        with pytest.raises(DocumentError):
            service.publish(ctx.actor,source[0],data.model_copy(update={'request_id':uuid4(),'indexation_id':second['indexation_id'],'expected_revision':1}))
    finally:service.documents.engine.dispose()


@pytest.mark.parametrize('code',['ADMIN','CAJA','INV_BOUTIQUE','INV_TALLER','MODISTA'])
def test_exact_retrieval_filters_current_document_acl_in_sql(rag_context,code):
    from app.services.leny_rag_retrieval import RetrievalService
    ctx=rag_context;worker=_worker(ctx)
    allowed,first=prepared(ctx,worker);publish(ctx,allowed,first)
    restricted,second=prepared(ctx,worker);publish(ctx,restricted,second)
    config=ctx.service.settings.model_copy(update={'leny_rag_chat_enabled':True})
    retrieval=RetrievalService(config,ctx.service.sessions)
    with role(ctx,code) as role_id:
        with ctx.cluster.engine.begin() as db:
            db.execute(text('INSERT INTO leny.documento_roles_lectura(document_id,role_id) VALUES(:doc,:role)'),{'doc':allowed[0],'role':role_id})
        rows=retrieval.search(ctx.actor,[1.0]+[0.0]*1023)
        assert {row['document_id'] for row in rows}==({allowed[0],restricted[0]} if code=='ADMIN' else {allowed[0]})


def test_source_owner_revocation_and_purge_leave_only_unavailable_reference(rag_context):
    from app.services.leny_rag_sources import SourceService
    from app.services.leny_store import LenyStore,LenyActor
    from app.services.leny_rag_retrieval import RetrievalService
    from app.services.leny_rag_service import purge_derived
    from app.services.leny_ollama import LenyError
    ctx=rag_context;worker=_worker(ctx);source,claim=prepared(ctx,worker);publish(ctx,source,claim)
    config=ctx.service.settings.model_copy(update={'leny_rag_chat_enabled':True})
    sources=SourceService(config,ctx.service.sessions);store=LenyStore(ctx.service.sessions,sources)
    actor=LenyActor(ctx.actor.account_id,ctx.actor.user_id,str(uuid4()))
    conversation=store.create(actor);message,_=store.begin_turn(actor,conversation['id'],uuid4(),'Según manual boutique',config.leny_model)
    retrieval=RetrievalService(config,ctx.service.sessions)
    fragments=retrieval.search(actor,[1.0]+[0.0]*1023)[:1]
    sources.persist(actor,message,fragments)
    store.save(actor,conversation['id'],message,'Texto previamente recibido [S1]','completed',category='business',context_eligible=False)
    ref=sources.for_messages(actor,[message])[message][0]
    assert sources.resolve(actor,ref['source_id'])['available']
    with pytest.raises(LenyError) as foreign:
        sources.resolve(SimpleNamespace(account_id=actor.account_id,user_id=999999),ref['source_id'])
    assert foreign.value.status==404
    with ctx.service.documents.lock(),ctx.service.documents.transaction() as db:
        db.execute(text('UPDATE leny.documentos SET published_version_id=NULL,published_indexation_id=NULL,published_at=NULL,published_by=NULL WHERE id=:id'),{'id':source[0]})
        purge_derived(db,source[1])
    unavailable=sources.for_messages(actor,[message])[message][0]
    assert unavailable=={'source_id':ref['source_id'],'available':False,'citation_id':'S1','warnings':[]}
    assert store.detail(actor,conversation['id'],1,50)['items'][-1]['content']=='Texto previamente recibido [S1]'
    sources.documents.engine.dispose()


def test_trash_clears_publication_and_restore_never_republishes(rag_context):
    ctx=rag_context;worker=_worker(ctx);source,claim=prepared(ctx,worker)
    result,_=publish(ctx,source,claim)
    with ctx.service.documents.lock():ctx.service.documents.trash(ctx.actor,source[0],result['revision'])
    with ctx.cluster.engine.connect() as db:
        assert db.execute(text('SELECT state,published_version_id,published_indexation_id FROM leny.documentos WHERE id=:id'),{'id':source[0]}).one()==('trash',None,None)


def test_new_migration_roundtrip_preserves_public_and_existing_vectors(pg_cluster):
    with _rag(pg_cluster) as db:
        before=_public_structure(db)
        with Operations.context(MigrationContext.configure(db)):
            migration=_migration('20261020_0021_leny_publication_sources.py')
            migration.downgrade();migration.upgrade()
        assert _public_structure(db)==before
        assert db.execute(text('SELECT state FROM leny.inferencia_estado WHERE id=1')).scalar_one()=='idle'


def test_singleton_quarantine_survives_history_and_blocks_generation(rag_context):
    from app.services.leny_inference_state import InferenceState
    from app.services.leny_coordination import PostgresCoordinator
    from app.services.leny_ollama import LenyError
    ctx=rag_context
    coordinator=PostgresCoordinator(ctx.service.settings.effective_database_url)
    state=InferenceState(ctx.service.sessions);lease=coordinator.acquire();request=uuid4()
    try:
        assert state.start(lease,request,ctx.service.settings.leny_model,'generation')
        state.finish(lease,request,False);lease.close()
        with pytest.raises(LenyError) as blocked:coordinator.acquire()
        assert blocked.value.code=='LENY_INFERENCE_UNCERTAIN'
    finally:
        lease.close()
        with ctx.cluster.engine.begin() as db:
            db.execute(text("UPDATE leny.inferencia_estado SET state='idle',request_id=NULL,model=NULL,phase=NULL WHERE request_id=:id"),{'id':request})
        coordinator.engine.dispose()


def test_published_index_state_cannot_be_changed_by_direct_sql(rag_context):
    ctx=rag_context;worker=_worker(ctx);source,claim=prepared(ctx,worker);publish(ctx,source,claim)
    with ctx.cluster.engine.begin() as db:
        with pytest.raises(IntegrityError),db.begin_nested():
            db.execute(text("UPDATE leny.rag_indexaciones SET status='failed' WHERE id=:id"),{'id':claim['indexation_id']})


def test_rolling_document_insert_remains_compatible_with_schema0020(pg_cluster,synthetic_recipient):
    from sqlalchemy.orm import Session
    from app.models.leny_documents import LenyDocument
    from test_leny_rag_schema import _source as sql_source
    with _rag(pg_cluster) as db:
        document,_=sql_source(db,synthetic_recipient)
        folder=db.execute(text('SELECT folder_id FROM leny.documentos WHERE id=:id'),{'id':document}).scalar_one()
        with Operations.context(MigrationContext.configure(db)):
            _migration('20261020_0021_leny_publication_sources.py').downgrade()
        with Session(bind=db,join_transaction_mode='create_savepoint') as session:
            session.add(LenyDocument(id=uuid4(),folder_id=folder,title='QA rolling compatibility',created_by=synthetic_recipient.user_id))
            session.flush()


def test_revocation_after_retrieval_prevents_context_and_future_lookup(rag_context):
    from app.services.leny_rag_retrieval import RetrievalService
    from app.services.leny_ollama import LenyError
    ctx=rag_context;worker=_worker(ctx);source,claim=prepared(ctx,worker);publish(ctx,source,claim)
    retrieval=RetrievalService(ctx.service.settings.model_copy(update={'leny_rag_chat_enabled':True}),ctx.service.sessions)
    with role(ctx,'CAJA') as role_id:
        with ctx.cluster.engine.begin() as db:
            db.execute(text('INSERT INTO leny.documento_roles_lectura(document_id,role_id) VALUES(:doc,:role)'),{'doc':source[0],'role':role_id})
        selected=retrieval.search(ctx.actor,[1.0]+[0.0]*1023)
        assert selected
        with ctx.cluster.engine.begin() as db:
            db.execute(text('DELETE FROM leny.documento_roles_lectura WHERE document_id=:doc'),{'doc':source[0]})
        with pytest.raises(LenyError) as rejected:retrieval.revalidate(ctx.actor,selected)
        assert rejected.value.code=='LENY_RAG_SOURCE_REVOKED'
        assert retrieval.search(ctx.actor,[1.0]+[0.0]*1023)==[]


def test_downgrade_refuses_to_erase_existing_publication(rag_context):
    from sqlalchemy.exc import DBAPIError
    ctx=rag_context;worker=_worker(ctx);source,claim=prepared(ctx,worker);publish(ctx,source,claim)
    with ctx.cluster.engine.begin() as db:
        with pytest.raises(DBAPIError),db.begin_nested():
            with Operations.context(MigrationContext.configure(db)):
                _migration('20261020_0021_leny_publication_sources.py').downgrade()
        assert db.scalar(text('SELECT published_indexation_id FROM leny.documentos WHERE id=:id'),{'id':source[0]})==claim['indexation_id']
        assert db.scalar(text("SELECT to_regclass('leny.rag_fuentes_mensaje') IS NOT NULL"))
