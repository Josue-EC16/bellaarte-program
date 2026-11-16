"""External approval intersects real publication/ACL before SQL retrieval.

Guarded synthetic PG55432 fixture only; fake vectors and private synthetic
approval manifest. No Google/Ollama calls or commercial fixture operations.
"""
import hashlib
import json
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from test_leny_rag_service import rag_context, _worker
import test_leny_rag_service as rag
from test_leny_rag_chat import prepared, publish, role


VECTOR = [1.0] + [0.0] * 1023


def configure(context, tmp_path, *sources, sections=False):
    versions = []
    with context.cluster.engine.connect() as db:
        for source, claim in sources:
            digest = db.scalar(text('SELECT sha256 FROM leny.documento_versiones WHERE id=:id'), {'id': source[1]})
            versions.append(dict(document_id=str(source[0]), version_id=str(source[1]),
                indexation_id=str(claim['indexation_id']), sha256=digest))
    manifest = tmp_path / ('external-synthetic-' + uuid4().hex + '.json')
    manifest.write_text(json.dumps(dict(format_version=1, versions=versions)), encoding='utf-8')
    return context.service.settings.model_copy(update=dict(leny_llm_provider='gemini',
        leny_gemini_corpus_manifest=str(manifest), leny_rag_chat_enabled=True,
        leny_rag_profile='rag4_v1', leny_rag_ranking='hybrid',
        leny_rag_response_mode='controlled-synthesis-v1', leny_rag_section_context=sections))


def grant(context, source, role_id):
    with context.cluster.engine.begin() as db:
        db.execute(text('INSERT INTO leny.documento_roles_lectura(document_id,role_id) VALUES(:doc,:role)'),
            {'doc': source[0], 'role': role_id})


def titled(context, source, title):
    with context.cluster.engine.begin() as db:
        db.execute(text('UPDATE leny.documentos SET title=:title WHERE id=:id'), {'id': source[0], 'title': title})


def test_approved_acl_evidence_only_reaches_ranking_and_unapproved_title_is_absent(rag_context, tmp_path):
    from app.services.leny_rag_retrieval import RetrievalService
    ctx = rag_context
    worker = _worker(ctx)
    allowed = prepared(ctx, worker)
    unapproved = prepared(ctx, worker)
    title = 'NO APROBADO ' + uuid4().hex
    titled(ctx, unapproved[0], title)
    publish(ctx, *allowed)
    publish(ctx, *unapproved)
    retrieval = RetrievalService(configure(ctx, tmp_path, allowed), ctx.service.sessions)
    statements = []
    def capture(_connection, _cursor, statement, *_):
        if 'ORDER BY' in statement and 'rag_embeddings' in statement:
            statements.append(statement)
    event.listen(ctx.cluster.engine, 'before_cursor_execute', capture)
    try:
        with role(ctx, 'CAJA') as role_id:
            grant(ctx, allowed[0], role_id)
            grant(ctx, unapproved[0], role_id)
            rows = retrieval.search(ctx.actor, VECTOR, 'Precio empresarial')
            assert rows and {row['document_id'] for row in rows} == {allowed[0][0]}
            assert statements and all('jsonb_to_recordset' in query and 'external_grants' in query for query in statements)
            assert retrieval.search(ctx.actor, VECTOR, 'Documento ' + title + ', resume su contenido') == []
            retrieval.revalidate(ctx.actor, rows)
    finally:
        event.remove(ctx.cluster.engine, 'before_cursor_execute', capture)


def test_approved_but_no_acl_has_no_title_disclosure_or_candidates(rag_context, tmp_path):
    from app.services.leny_rag_retrieval import RetrievalService
    ctx = rag_context
    source, claim = prepared(ctx, _worker(ctx))
    title = 'RESTRINGIDO SINTETICO ' + uuid4().hex
    titled(ctx, source, title)
    publish(ctx, source, claim)
    retrieval = RetrievalService(configure(ctx, tmp_path, (source, claim)), ctx.service.sessions)
    with role(ctx, 'CAJA'):
        assert retrieval.search(ctx.actor, VECTOR, 'Precio empresarial') == []
        assert retrieval.search(ctx.actor, VECTOR, 'Documento ' + title + ', resume su contenido') == []


def test_explicit_title_and_document_scope_remain_narrow_with_two_approved_versions(rag_context, tmp_path):
    from app.services.leny_rag_retrieval import RetrievalService
    ctx = rag_context
    worker = _worker(ctx)
    first, second = prepared(ctx, worker), prepared(ctx, worker)
    title = 'MANUAL UNO ' + uuid4().hex
    titled(ctx, first[0], title)
    titled(ctx, second[0], 'MANUAL DOS ' + uuid4().hex)
    publish(ctx, *first)
    publish(ctx, *second)
    retrieval = RetrievalService(configure(ctx, tmp_path, first, second), ctx.service.sessions)
    with role(ctx, 'CAJA') as role_id:
        for source, _ in (first, second):
            grant(ctx, source, role_id)
        assert {row['document_id'] for row in retrieval.search(ctx.actor, VECTOR)} == {first[0][0], second[0][0]}
        rows = retrieval.search(ctx.actor, VECTOR, 'Documento ' + title + ', resume su contenido')
        assert rows and {row['document_id'] for row in rows} == {first[0][0]}
        scoped = retrieval.search(ctx.actor, VECTOR, 'Precio empresarial', document_ids=[first[0][0]])
        assert scoped and {row['document_id'] for row in scoped} == {first[0][0]}


@pytest.mark.parametrize('revocation', ['acl', 'publication', 'external'])
def test_revoked_evidence_cannot_revalidate_and_local_source_obeys_current_acl(rag_context, tmp_path, revocation):
    from app.services.leny_llm_contracts import LenyError
    from app.services.leny_rag_retrieval import RetrievalService
    from app.services.leny_rag_sources import SourceService
    from app.services.leny_store import LenyActor
    ctx = rag_context
    source, claim = prepared(ctx, _worker(ctx))
    publish(ctx, source, claim)
    config = configure(ctx, tmp_path, (source, claim))
    retrieval, sources = RetrievalService(config, ctx.service.sessions), SourceService(config, ctx.service.sessions)
    conversation, message = uuid4(), uuid4()
    actor = LenyActor(ctx.actor.account_id, ctx.actor.user_id, str(uuid4()))
    try:
        with role(ctx, 'CAJA') as role_id:
            grant(ctx, source, role_id)
            rows = retrieval.search(actor, VECTOR)
            assert rows
            # Raw minimal history works at isolated revision0023 and avoids
            # applying0024/0025 only to exercise SourceService's owner/ACL query.
            with ctx.cluster.engine.begin() as db:
                db.execute(text("INSERT INTO leny.conversaciones(id,user_id,account_id,title) VALUES(:id,:user,:account,'Synthetic external test')"),
                    dict(id=conversation, user=actor.user_id, account=actor.account_id))
                db.execute(text("INSERT INTO leny.mensajes(id,conversation_id,sequence,request_id,role,content,status) VALUES(:id,:conversation,1,:request,'assistant','','generating')"),
                    dict(id=message, conversation=conversation, request=uuid4()))
            sources.persist(actor, message, rows[:1])
            with ctx.cluster.engine.begin() as db:
                db.execute(text("UPDATE leny.mensajes SET status='completed' WHERE id=:id"), {'id': message})
            reference = sources.for_messages(actor, [message])[message][0]
            assert reference['available']
            assert sources.resolve(actor, reference['source_id'])['available']
            if revocation == 'external':
                config_path = config.leny_gemini_corpus_manifest
                from pathlib import Path
                Path(config_path).write_text('{"format_version":1,"versions":[]}', encoding='utf-8')
            else:
                with ctx.cluster.engine.begin() as db:
                    if revocation == 'acl':
                        db.execute(text('DELETE FROM leny.documento_roles_lectura WHERE document_id=:id AND role_id=:role'),
                            {'id': source[0], 'role': role_id})
                    else:
                        db.execute(text('UPDATE leny.documentos SET published_version_id=NULL,published_indexation_id=NULL,published_at=NULL,published_by=NULL WHERE id=:id'), {'id': source[0]})
            assert retrieval.search(actor, VECTOR) == []
            with pytest.raises(LenyError) as revoked:
                retrieval.revalidate(actor, rows)
            assert revoked.value.code == 'LENY_RAG_SOURCE_REVOKED'
            # External approval governs transmission, not local document ACL.
            # Removing only external consent preserves the user's local source.
            current = sources.for_messages(actor, [message])[message][0]
            if revocation == 'external':
                assert current['available'] and sources.resolve(actor, reference['source_id'])['available']
            else:
                assert current == dict(source_id=reference['source_id'], available=False, citation_id='S1', warnings=[])
                with pytest.raises(LenyError) as blocked:
                    sources.resolve(actor, reference['source_id'])
                assert blocked.value.status == 404
    finally:
        with ctx.cluster.engine.begin() as db:
            db.execute(text('DELETE FROM leny.conversaciones WHERE id=:id AND user_id=:user'), {'id': conversation, 'user': actor.user_id})
        sources.documents.engine.dispose()


def test_section_context_keeps_current_approved_index_identity(rag_context, tmp_path, monkeypatch):
    from app.services.leny_rag_chunking import fragment_units
    from app.services.leny_rag_retrieval import RetrievalService
    ctx = rag_context
    texts = ['Funciones de la modista', 'Revisar las medidas antes del corte.',
        'Preparar las piezas.', 'Funciones de la asesora de moda', 'Orientar a la clienta.']
    units = [dict(text=value, source_type='DOCX_PARAGRAPH', locator=dict(block=i, paragraph=i + 1,
        **({'style': 'Heading2'} if i in (0, 3) else {}))) for i, value in enumerate(texts)]
    monkeypatch.setattr(rag, '_fragments', lambda context, count=2: fragment_units(units, context.service.settings))
    source, claim = prepared(ctx, _worker(ctx))
    publish(ctx, source, claim)
    retrieval = RetrievalService(configure(ctx, tmp_path, (source, claim), sections=True), ctx.service.sessions)
    with role(ctx, 'CAJA') as role_id:
        grant(ctx, source, role_id)
        rows = retrieval.search(ctx.actor, VECTOR, 'responsabilidades de la modista')
        body = next(row for row in rows if row['ordinal'] == 1)
        heading = next(row for row in rows if row['ordinal'] == 0)
        assert body['context_fragment_id'] == heading['fragment_id']
        assert body['locator']['heading'] == texts[0]
        by_id = {row['fragment_id']: row for row in rows}
        for row in rows:
            assert row['indexation_id'] == claim['indexation_id']
            if row.get('context_fragment_id'):
                context_row = by_id[row['context_fragment_id']]
                assert context_row['indexation_id'] == row['indexation_id']
                assert context_row['document_id'] == row['document_id']
        retrieval.revalidate(ctx.actor, rows)
