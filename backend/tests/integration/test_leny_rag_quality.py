"""SPEC04 candidate SQL/ownership tests, guarded isolated PostgreSQL only.

Vectors are synthetic. These tests cannot demonstrate semantic Qwen accuracy.
"""
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

import test_leny_rag_chat as chat
from test_leny_rag_service import rag_context, _worker
from test_leny_persistence import leny_store, leny_actor, other_leny_actor


@pytest.mark.parametrize('state_change', ['revoke_acl', 'unpublish'])
def test_coverage_prototype_only_loads_current_sql_eligible_metadata(rag_context, state_change):
    """Real SQL ACL/publication, draft coverage, synthetic source; no inference."""
    from app.services.leny_rag_coverage import CoverageVerifier, MemoryCoverageProvider, digest
    from app.services.leny_rag_retrieval import RetrievalService
    ctx = rag_context
    worker = _worker(ctx)
    source, claim = chat.prepared(ctx, worker)
    chat.publish(ctx, source, claim)
    restricted, other = chat.prepared(ctx, worker)
    chat.publish(ctx, restricted, other)
    config = ctx.service.settings.model_copy(update={'leny_rag_chat_enabled': True, 'leny_rag_profile': 'rag4_v1'})
    retrieval = RetrievalService(config, ctx.service.sessions)
    with chat.role(ctx, 'CAJA') as role_id:
        with ctx.cluster.engine.begin() as db:
            db.execute(text('INSERT INTO leny.documento_roles_lectura(document_id,role_id) VALUES(:doc,:role)'),
                       {'doc': source[0], 'role': role_id})
            original_hash = db.scalar(text('SELECT sha256 FROM leny.documento_versiones WHERE id=:version'),
                                      {'version': source[1]})
        rows = retrieval.search(ctx.actor, [1.0]+[0.0]*1023, 'protocolo')
        assert rows and {r['document_id'] for r in rows} == {source[0]}
        retrieval.revalidate(ctx.actor, rows)
        vocabulary = dict(version='pg-test-v1', concepts=[dict(id='topic', kind='topic', aliases=['protocolo'])])
        units = [dict(fragment_id=str(r['fragment_id']), text_sha256=digest(r['text']),
            spans=[dict(start=0,end=len(r['text']),sha256=digest(r['text']))], topics=['topic'], aspects=['aspect']) for r in rows]
        vocabulary['concepts'].append(dict(id='aspect', kind='aspect', aliases=['leer']))
        manifest = dict(revision=1, document_id=str(source[0]), version_id=str(source[1]),
            indexation_id=str(claim['indexation_id']), source_sha256=original_hash, source_hash_basis='original_file',
            vocabulary_version='pg-test-v1', units=units)
        # Hash comes from the isolated version row, not from an invented original.
        evidence = [dict(r, source_sha256=original_hash) for r in rows]
        provider = MemoryCoverageProvider(vocabulary, [manifest])
        gate = CoverageVerifier(provider)
        assert gate.evaluate('protocolo', evidence).reason == 'coverage_human_review_pending'
        assert gate.evaluate('protocolo', evidence, research=True).verdict == 'approved'
        assert not gate.evaluate('protocolo', evidence, research=True).release_allowed
        with ctx.cluster.engine.begin() as db:
            if state_change == 'revoke_acl':
                db.execute(text('DELETE FROM leny.documento_roles_lectura WHERE document_id=:doc AND role_id=:role'),
                           {'doc': source[0], 'role': role_id})
            else:
                db.execute(text('UPDATE leny.documentos SET published_version_id=NULL,published_indexation_id=NULL,'
                                'published_at=NULL,published_by=NULL WHERE id=:doc'), {'doc': source[0]})
        fresh = retrieval.search(ctx.actor, [1.0]+[0.0]*1023, 'protocolo')
        assert fresh == [] and provider.manifests(fresh) == []
        assert gate.evaluate('protocolo', fresh).reason == 'coverage_evidence_empty'


@pytest.mark.parametrize('code', ['ADMIN', 'CAJA', 'INV_BOUTIQUE', 'INV_TALLER', 'MODISTA'])
@pytest.mark.parametrize('ranking,neighbors', [('semantic', False), ('hybrid', False), ('semantic', True), ('hybrid', True)])
def test_candidate_ranking_and_neighbors_keep_sql_acl_and_publication(rag_context, code, ranking, neighbors):
    from app.services.leny_rag_retrieval import RetrievalService
    ctx = rag_context
    worker = _worker(ctx)
    allowed, first = chat.prepared(ctx, worker)
    chat.publish(ctx, allowed, first)
    restricted, second = chat.prepared(ctx, worker)
    chat.publish(ctx, restricted, second)
    config = ctx.service.settings.model_copy(update={'leny_rag_chat_enabled': True,
        'leny_rag_profile': 'rag4_v1', 'leny_rag_ranking': ranking, 'leny_rag_neighbor_chunks': neighbors})
    retrieval = RetrievalService(config, ctx.service.sessions)
    with chat.role(ctx, code) as role_id:
        with ctx.cluster.engine.begin() as db:
            db.execute(text('INSERT INTO leny.documento_roles_lectura(document_id,role_id) VALUES(:doc,:role)'),
                       {'doc': allowed[0], 'role': role_id})
        rows = retrieval.search(ctx.actor, [1.0] + [0.0]*1023, 'Precio empresarial descuento')
        assert {row['document_id'] for row in rows} == ({allowed[0], restricted[0]} if code == 'ADMIN' else {allowed[0]})
        assert {row['indexation_id'] for row in rows} <= {first['indexation_id'], second['indexation_id']}
        assert len(rows) <= 20 and len({row['fragment_id'] for row in rows}) == len(rows)
        assert all(isinstance(row['ordinal'], int) for row in rows)
        retrieval.revalidate(ctx.actor, rows)
        if code != 'ADMIN':
            with ctx.cluster.engine.begin() as db:
                db.execute(text('DELETE FROM leny.documento_roles_lectura WHERE document_id=:doc AND role_id=:role'),
                           {'doc': allowed[0], 'role': role_id})
            assert retrieval.search(ctx.actor, [1.0] + [0.0]*1023, 'Precio empresarial descuento') == []


def test_candidate_keeps_authorized_semantic_hits_without_lexical_matches(rag_context):
    from app.services.leny_rag_retrieval import RetrievalService
    ctx = rag_context
    source, claim = chat.prepared(ctx, _worker(ctx))
    chat.publish(ctx, source, claim)
    config = ctx.service.settings.model_copy(update={'leny_rag_chat_enabled': True, 'leny_rag_profile': 'rag4_v1',
                                                    'leny_rag_ranking': 'hybrid'})
    retrieval = RetrievalService(config, ctx.service.sessions)
    # A lexical non-match still retains semantic hits; no raw string SQL input.
    rows = retrieval.search(ctx.actor, [1.0] + [0.0]*1023, "' OR 1=1 -- zzznotaword")
    assert rows and {row['document_id'] for row in rows} == {source[0]}


@pytest.mark.parametrize('old_policy', ['rag3-v1', 'rag4-v2', 'rag4-v3'])
def test_topic_history_only_current_owner_user_anchors_never_documentary_answers(leny_store, leny_actor, other_leny_actor, old_policy):
    from app.services.leny_ollama import LenyError
    from app.services.leny_rag_routing import RAG4_POLICY_VERSION
    conversation = UUID(leny_store.create(leny_actor)['id'])
    try:
        old, _ = leny_store.begin_turn(leny_actor, conversation, uuid4(), 'Tema de perfil anterior', 'synthetic')
        leny_store.save(leny_actor, conversation, old, 'OLD_DOCUMENT_SECRET', 'completed', category='business',
                        policy_version=old_policy, context_eligible=False)
        first, _ = leny_store.begin_turn(leny_actor, conversation, uuid4(), '¿Cómo se hacen los vestidos?', 'synthetic', policy_version=RAG4_POLICY_VERSION)
        leny_store.save(leny_actor, conversation, first, 'OBSOLETE_DOCUMENTARY_SECRET [S1]', 'completed',
                        category='business', reason='garment_procedure', policy_version=RAG4_POLICY_VERSION, context_eligible=False)
        assert leny_store.topic_history(leny_actor, conversation, RAG4_POLICY_VERSION) == [
            {'role': 'user', 'content': '¿Cómo se hacen los vestidos?', 'documentary': True}]
        second, history = leny_store.begin_turn(leny_actor, conversation, uuid4(), '¿Y después?', 'synthetic', policy_version=RAG4_POLICY_VERSION)
        assert history == []  # Documentary content remains excluded from generation context.
        leny_store.save(leny_actor, conversation, second, 'NEW_TEXT [S1]', 'completed', category='business',
                        reason='rag_followup', policy_version=RAG4_POLICY_VERSION, context_eligible=False)
        assert leny_store.topic_history(leny_actor, conversation, RAG4_POLICY_VERSION) == [
            {'role': 'user', 'content': '¿Cómo se hacen los vestidos?', 'documentary': True}]
        with pytest.raises(LenyError) as error:
            leny_store.topic_history(other_leny_actor, conversation, RAG4_POLICY_VERSION)
        assert error.value.status == 404
    finally:
        leny_store.remove(leny_actor, conversation)


def test_topic_history_excludes_refused_failed_and_missing_evidence(leny_store, leny_actor):
    from app.services.leny_rag_routing import RAG4_POLICY_VERSION
    conversation = UUID(leny_store.create(leny_actor)['id'])
    try:
        for category, reason, status in [('manipulation', 'suspected_instruction_override', 'completed'),
            ('business', 'leny_output_blocked', 'failed'), ('business', 'rag_evidence_insufficient', 'completed')]:
            assistant, _ = leny_store.begin_turn(leny_actor, conversation, uuid4(), 'Untrusted topic', 'synthetic', policy_version=RAG4_POLICY_VERSION)
            leny_store.save(leny_actor, conversation, assistant, 'Excluded', status, category=category,
                            reason=reason, policy_version=RAG4_POLICY_VERSION, context_eligible=False)
        assert leny_store.topic_history(leny_actor, conversation, RAG4_POLICY_VERSION) == []
    finally:
        leny_store.remove(leny_actor, conversation)


def test_latest_general_topic_supersedes_older_documentary_topic(leny_store, leny_actor):
    from app.services.leny_rag_routing import RAG4_POLICY_VERSION, candidate_decision
    conversation = UUID(leny_store.create(leny_actor)['id'])
    try:
        for question, eligible in [('¿Cómo se hacen los vestidos?', False),
                                   ('¿Qué es el margen de utilidad?', True)]:
            assistant, _ = leny_store.begin_turn(leny_actor, conversation, uuid4(), question,
                'synthetic', policy_version=RAG4_POLICY_VERSION)
            leny_store.save(leny_actor, conversation, assistant, 'SYNTHETIC', 'completed', category='business',
                            policy_version=RAG4_POLICY_VERSION, context_eligible=eligible)
        topics = leny_store.topic_history(leny_actor, conversation, RAG4_POLICY_VERSION)
        assert topics == [{'role': 'user', 'content': '¿Qué es el margen de utilidad?', 'documentary': False}]
        assert not candidate_decision('Resúmelo en cinco pasos', topics, True).documents
    finally:
        leny_store.remove(leny_actor, conversation)


def test_topic_document_ids_are_private_distinct_and_follow_latest_substantive_topic(
        rag_context, leny_store, leny_actor, other_leny_actor):
    from sqlalchemy import event
    from app.services.leny_ollama import LenyError
    from app.services.leny_rag_retrieval import RetrievalService
    from app.services.leny_rag_routing import RAG4_POLICY_VERSION
    from app.services.leny_rag_sources import SourceService

    ctx = rag_context
    worker = _worker(ctx)
    first, first_claim = chat.prepared(ctx, worker)
    chat.publish(ctx, first, first_claim)
    latest, latest_claim = chat.prepared(ctx, worker)
    chat.publish(ctx, latest, latest_claim)
    config = ctx.service.settings.model_copy(update={'leny_rag_chat_enabled': True, 'leny_rag_profile': 'rag4_v1'})
    retrieval = RetrievalService(config, ctx.service.sessions)
    sources = SourceService(config, ctx.service.sessions)
    conversation = UUID(leny_store.create(leny_actor)['id'])

    def complete(question, document, *, policy=RAG4_POLICY_VERSION, context_eligible=False):
        message, _ = leny_store.begin_turn(leny_actor, conversation, uuid4(), question,
                                         'synthetic', policy_version=policy)
        fragments = retrieval.search(leny_actor, [1.0] + [0.0]*1023, document_ids=[document])
        assert len(fragments) == 2  # Both references must collapse to one document identity.
        sources.persist(leny_actor, message, fragments)
        leny_store.save(leny_actor, conversation, message, 'SYNTHETIC_DOCUMENTARY_CONTENT [S1]',
                       'completed', category='business', reason='garment_procedure',
                       policy_version=policy, context_eligible=context_eligible)

    try:
        assert leny_store.topic_document_ids(leny_actor, conversation, RAG4_POLICY_VERSION) is None
        complete('Explica el procedimiento de confección', first[0])
        assert leny_store.topic_document_ids(leny_actor, conversation, RAG4_POLICY_VERSION) == [first[0]]
        complete('Explica la guía de inventario', latest[0])
        # Followup references and an old policy version cannot replace the latest
        # substantive topic, even when they point at another real document.
        complete('¿Y después?', first[0])
        complete('Tema de una política anterior', first[0], policy='rag3-v1')
        statements = []

        def record_select(_connection, _cursor, statement, _parameters, _context, _many):
            if statement.lstrip().upper().startswith('SELECT'):
                statements.append(statement.lower())

        event.listen(ctx.cluster.engine, 'before_cursor_execute', record_select)
        try:
            identities = leny_store.topic_document_ids(leny_actor, conversation, RAG4_POLICY_VERSION)
        finally:
            event.remove(ctx.cluster.engine, 'before_cursor_execute', record_select)
        assert identities == [latest[0]] and all(isinstance(identity, UUID) for identity in identities)
        # Provenance lookup may join private tables, but must not load document
        # text, labels or locators into this metadata-only path.
        assert statements
        assert not any(column in statement for statement in statements for column in
                       ('rag_fragmentos.text', 'rag_fragmentos.locator', 'documentos.title'))
        with pytest.raises(LenyError) as foreign:
            leny_store.topic_document_ids(other_leny_actor, conversation, RAG4_POLICY_VERSION)
        assert foreign.value.status == 404
        general, _ = leny_store.begin_turn(leny_actor, conversation, uuid4(), '¿Qué es el margen de utilidad?',
                                          'synthetic', policy_version=RAG4_POLICY_VERSION)
        leny_store.save(leny_actor, conversation, general, 'Orientación general sintética', 'completed',
                       category='business', policy_version=RAG4_POLICY_VERSION, context_eligible=True)
        assert leny_store.topic_document_ids(leny_actor, conversation, RAG4_POLICY_VERSION) is None
    finally:
        leny_store.remove(leny_actor, conversation)
        sources.documents.engine.dispose()


def test_topic_document_ids_keep_purged_latest_references_empty_without_falling_back(
        rag_context, leny_store, leny_actor):
    from app.services.leny_rag_retrieval import RetrievalService
    from app.services.leny_rag_routing import RAG4_POLICY_VERSION
    from app.services.leny_rag_service import purge_derived
    from app.services.leny_rag_sources import SourceService

    ctx = rag_context
    worker = _worker(ctx)
    older, older_claim = chat.prepared(ctx, worker)
    chat.publish(ctx, older, older_claim)
    latest, latest_claim = chat.prepared(ctx, worker)
    chat.publish(ctx, latest, latest_claim)
    config = ctx.service.settings.model_copy(update={'leny_rag_chat_enabled': True, 'leny_rag_profile': 'rag4_v1'})
    retrieval = RetrievalService(config, ctx.service.sessions)
    sources = SourceService(config, ctx.service.sessions)
    conversation = UUID(leny_store.create(leny_actor)['id'])
    try:
        for question, source in [('Explica la guía anterior', older), ('Explica el procedimiento actual', latest)]:
            message, _ = leny_store.begin_turn(leny_actor, conversation, uuid4(), question,
                                              'synthetic', policy_version=RAG4_POLICY_VERSION)
            rows = retrieval.search(leny_actor, [1.0] + [0.0]*1023, document_ids=[source[0]])
            sources.persist(leny_actor, message, rows)
            leny_store.save(leny_actor, conversation, message, 'SYNTHETIC [S1]', 'completed', category='business',
                           policy_version=RAG4_POLICY_VERSION, context_eligible=False)
        assert leny_store.topic_document_ids(leny_actor, conversation, RAG4_POLICY_VERSION) == [latest[0]]
        with ctx.service.documents.lock(), ctx.service.documents.transaction() as db:
            db.execute(text('UPDATE leny.documentos SET published_version_id=NULL,published_indexation_id=NULL,'
                            'published_at=NULL,published_by=NULL WHERE id=:doc'), {'doc': latest[0]})
            purge_derived(db, latest[1])
        assert leny_store.topic_document_ids(leny_actor, conversation, RAG4_POLICY_VERSION) == []
        # An available older document must not be substituted for a purged topic.
        assert retrieval.search(leny_actor, [1.0] + [0.0]*1023, document_ids=[older[0]])
        assert retrieval.search(leny_actor, [1.0] + [0.0]*1023, document_ids=[]) == []
    finally:
        leny_store.remove(leny_actor, conversation)
        sources.documents.engine.dispose()


@pytest.mark.parametrize('ranking,neighbors', [('semantic', False), ('hybrid', False),
                                               ('semantic', True), ('hybrid', True)])
def test_topic_document_scope_narrows_current_publications_without_granting_acl(rag_context, ranking, neighbors):
    from app.services.leny_rag_retrieval import RetrievalService

    ctx = rag_context
    worker = _worker(ctx)
    allowed, first = chat.prepared(ctx, worker)
    chat.publish(ctx, allowed, first)
    other, second = chat.prepared(ctx, worker)
    chat.publish(ctx, other, second)
    config = ctx.service.settings.model_copy(update={'leny_rag_chat_enabled': True,
        'leny_rag_profile': 'rag4_v1', 'leny_rag_ranking': ranking, 'leny_rag_neighbor_chunks': neighbors})
    retrieval = RetrievalService(config, ctx.service.sessions)
    vector = [1.0] + [0.0]*1023
    question = 'Precio empresarial descuento'
    both = [allowed[0], other[0]]
    assert {row['document_id'] for row in retrieval.search(ctx.actor, vector, question, document_ids=both)} == set(both)
    assert {row['document_id'] for row in retrieval.search(ctx.actor, vector, question,
                                                         document_ids=[allowed[0]])} == {allowed[0]}
    assert retrieval.search(ctx.actor, vector, question, document_ids=[]) == []
    assert retrieval.search(ctx.actor, vector, question, document_ids=[uuid4()]) == []
    with chat.role(ctx, 'CAJA') as role_id:
        with ctx.cluster.engine.begin() as db:
            db.execute(text('INSERT INTO leny.documento_roles_lectura(document_id,role_id) VALUES(:doc,:role)'),
                       {'doc': allowed[0], 'role': role_id})
        assert {row['document_id'] for row in retrieval.search(ctx.actor, vector, question,
                                                             document_ids=both)} == {allowed[0]}
        assert retrieval.search(ctx.actor, vector, question, document_ids=[other[0]]) == []
        with ctx.cluster.engine.begin() as db:
            db.execute(text('DELETE FROM leny.documento_roles_lectura WHERE document_id=:doc AND role_id=:role'),
                       {'doc': allowed[0], 'role': role_id})
        assert retrieval.search(ctx.actor, vector, question, document_ids=[allowed[0]]) == []
    # ADMIN can still read the other publication; withdrawing this topic must
    # yield no evidence instead of reviving cached fragments or another topic.
    with ctx.cluster.engine.begin() as db:
        db.execute(text('UPDATE leny.documentos SET published_version_id=NULL,published_indexation_id=NULL,'
                        'published_at=NULL,published_by=NULL WHERE id=:doc'), {'doc': allowed[0]})
    assert retrieval.search(ctx.actor, vector, question, document_ids=[allowed[0]]) == []
    assert {row['document_id'] for row in retrieval.search(ctx.actor, vector, question,
                                                         document_ids=[other[0]])} == {other[0]}


def test_topic_document_scope_uses_newly_published_version_not_historical_fragments(rag_context):
    import hashlib
    from app.services.leny_rag_retrieval import RetrievalService
    from test_leny_rag_service import _submit, _complete

    ctx = rag_context
    worker = _worker(ctx)
    source, first = chat.prepared(ctx, worker)
    chat.publish(ctx, source, first)
    config = ctx.service.settings.model_copy(update={'leny_rag_chat_enabled': True,
        'leny_rag_profile': 'rag4_v1', 'leny_rag_ranking': 'hybrid', 'leny_rag_neighbor_chunks': True})
    retrieval = RetrievalService(config, ctx.service.sessions)
    vector = [1.0] + [0.0]*1023
    scope = [source[0]]
    original_rows = retrieval.search(ctx.actor, vector, 'Precio empresarial', document_ids=scope)
    assert original_rows and {row['version_id'] for row in original_rows} == {source[1]}
    original_ids = {row['fragment_id'] for row in original_rows}

    replacement = (source[0], uuid4())
    content = b'synthetic replacement original only'
    key = 'versions/' + uuid4().hex + '.blob'
    ctx.service.documents.storage.path(key).write_bytes(content)
    with ctx.cluster.engine.begin() as db:
        db.execute(text('INSERT INTO leny.documento_versiones '
                        '(id,document_id,number,storage_key,sha256,size_bytes,media_type,original_name,created_by) '
                        "VALUES(:version,:doc,2,:key,:hash,:size,'application/pdf','QA-version-2.pdf',:user)"),
                   {'version': replacement[1], 'doc': replacement[0], 'key': key,
                    'hash': hashlib.sha256(content).hexdigest(), 'size': len(content), 'user': ctx.actor.user_id})
    _submit(ctx, replacement)
    second = ctx.service.claim(worker)
    assert second and second['indexation_id'] != first['indexation_id']
    _complete(ctx, second)
    # Contextualizing a new version alone does not change the publication.
    assert {row['fragment_id'] for row in retrieval.search(ctx.actor, vector, 'Precio empresarial',
                                                          document_ids=scope)} == original_ids
    chat.publish(ctx, replacement, second)
    current = retrieval.search(ctx.actor, vector, 'Precio empresarial', document_ids=scope)
    assert current and {row['document_id'] for row in current} == {source[0]}
    assert {row['version_id'] for row in current} == {replacement[1]}
    assert {row['version'] for row in current} == {2}
    assert {row['indexation_id'] for row in current} == {second['indexation_id']}
    assert original_ids.isdisjoint(row['fragment_id'] for row in current)
