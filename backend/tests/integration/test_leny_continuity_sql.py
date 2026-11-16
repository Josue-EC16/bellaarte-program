"""Owner-scoped history and documentary revocation on synthetic PG55432 only."""
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4
import pytest
from sqlalchemy import text
from test_leny_rag_service import rag_context,_worker
from test_leny_rag_chat import prepared,publish,role
from test_leny_spec03_scope import configure,grant,VECTOR


@pytest.mark.parametrize('revocation',['acl','publication','external'])
def test_history_context_requires_current_acl_publication_and_external_consent(rag_context,tmp_path,revocation):
    from app.services.leny_llm_contracts import LenyError
    from app.services.leny_spec03_context import load_context
    from app.services.leny_rag_retrieval import RetrievalService
    from app.services.leny_rag_sources import SourceService
    from app.services.leny_store import LenyActor
    ctx=rag_context;source,claim=prepared(ctx,_worker(ctx));publish(ctx,source,claim)
    config=configure(ctx,tmp_path,(source,claim)).model_copy(update={'leny_continuity_enabled':True})
    actor=LenyActor(ctx.actor.account_id,ctx.actor.user_id,str(uuid4()))
    conversation,assistant,request=uuid4(),uuid4(),uuid4()
    sources=SourceService(config,ctx.service.sessions)
    @contextmanager
    def transaction():
        with ctx.service.sessions() as db,db.begin():yield db
    def own(db,current,identity):
        if not db.scalar(text('SELECT count(*) FROM leny.conversaciones WHERE id=:id AND user_id=:user'),
            {'id':identity,'user':current.user_id}):raise LenyError('LENY_NOT_FOUND','No disponible.',404)
    store=SimpleNamespace(transaction=transaction,own=own)
    try:
        with role(ctx,'CAJA') as role_id:
            grant(ctx,source,role_id)
            rows=RetrievalService(config,ctx.service.sessions).search(actor,VECTOR)
            with ctx.cluster.engine.begin() as db:
                db.execute(text("INSERT INTO leny.conversaciones(id,user_id,account_id,title) VALUES(:id,:user,:account,'Synthetic continuity')"),
                    {'id':conversation,'user':actor.user_id,'account':actor.account_id})
                for seq,identity,role_name,content,status in ((1,uuid4(),'user','Cómo se hacen los vestidos','completed'),
                    (2,assistant,'assistant','Primero se revisan las medidas.','generating')):
                    db.execute(text('INSERT INTO leny.mensajes(id,conversation_id,sequence,request_id,role,content,status,category,context_eligible) '
                        "VALUES(:id,:conv,:seq,:req,:role,:content,:status,'business',false)"),
                        {'id':identity,'conv':conversation,'seq':seq,'req':request,'role':role_name,'content':content,'status':status})
            sources.persist(actor,assistant,rows[:1])
            with ctx.cluster.engine.begin() as db:db.execute(text("UPDATE leny.mensajes SET status='completed' WHERE id=:id"),{'id':assistant})
            context=load_context(store,actor,conversation,'¿Quién lo hace?',config)
            assert len(context.pairs)==2 and context.source_ids and not context.latest_unavailable
            # Even a fully worded new topic may inspect safe history, but must
            # never inherit another person's conversation.
            other=LenyActor(actor.account_id,actor.user_id+999999,str(uuid4()))
            with pytest.raises(LenyError):load_context(store,other,conversation,'¿Quién es el gerente?',config)
            if revocation=='external':
                from pathlib import Path
                Path(config.leny_gemini_corpus_manifest).write_text('{"format_version":1,"versions":[]}',encoding='utf-8')
            else:
                with ctx.cluster.engine.begin() as db:
                    if revocation=='acl':db.execute(text('DELETE FROM leny.documento_roles_lectura WHERE document_id=:id AND role_id=:role'),{'id':source[0],'role':role_id})
                    else:db.execute(text('UPDATE leny.documentos SET published_version_id=NULL,published_indexation_id=NULL,published_at=NULL,published_by=NULL WHERE id=:id'),{'id':source[0]})
            revoked=load_context(store,actor,conversation,'¿Quién lo hace?',config)
            assert revoked.pairs==[] and revoked.latest_unavailable and revoked.revoked
    finally:
        with ctx.cluster.engine.begin() as db:db.execute(text('DELETE FROM leny.conversaciones WHERE id=:id AND user_id=:user'),{'id':conversation,'user':actor.user_id})
        sources.documents.engine.dispose()
