"""Real local Qwen evaluation of the fixed synthetic SPEC-04 corpus on PG55432.

Never reads the ERP .env, business documents or business database. No migrations,
quota bypass, worker startup, foreign model unloading or automatic human review.
Use the PowerShell wrapper for existing DPAPI-protected test credentials.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from contextlib import contextmanager
import hashlib
import io
import json
import logging
import os
import re
from pathlib import Path
import subprocess
import shutil
import sys
from tempfile import mkdtemp
import time
import textwrap
from uuid import UUID, uuid4
import zipfile

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / 'scripts'))
CORPUS = BACKEND / 'tests/fixtures/leny_rag04_development.json'
ROLES = ('ADMIN', 'CAJA', 'INV_BOUTIQUE', 'INV_TALLER', 'MODISTA')


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def frozen_sources_match(root, files):
    root = Path(root).resolve()
    if not files:
        return False
    for relative, expected in files.items():
        path = root/relative
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
            return False
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            return False
    return True


async def trace_generation(provider, iterator, traces):
    """Evidence receipt is independent of the browser stream's final status.

    Content or a confirmed provider completion proves receipt of this prompt.
    A transport interruption before either remains unknown, never an empty
    evidence claim. Only synthetic fixture identities enter this trace.
    """
    traces['sent_fragment_ids'] = None
    traces['sent_evidence_basis'] = 'generation_attempt_unconfirmed'
    try:
        async for chunk in iterator:
            traces['sent_fragment_ids'] = list(traces.get('selected_fragment_ids', []))
            traces['sent_evidence_basis'] = 'provider_content_received'
            yield chunk
    finally:
        if provider.response_complete:
            traces['sent_fragment_ids'] = list(traces.get('selected_fragment_ids', []))
            traces['sent_evidence_basis'] = 'provider_completion_received'
        elif not provider.inference_started:
            traces['sent_fragment_ids'] = []
            traces['sent_evidence_basis'] = 'generation_not_started'


def annotate_target(observation, turn, target_turn):
    observation.update(observed_turn=turn, target_turn=target_turn,
                       target_executed=turn == target_turn)
    if turn != target_turn:
        observation['failure_stage'] = 'prerequisite'
    return observation


def select_cases(corpus, mode, limit=None):
    if mode == 'supervised':
        # Deployment preservation check, not another optimization campaign.
        wanted = ['rag04-natural-01', 'rag04-natural-08', 'rag04-acl-01',
                  'rag04-no_evidence-02', 'rag04-followup-03', 'rag04-acl-07']
        by_id = {case['id']: case for case in corpus['cases']}
        selected = [by_id[identity] for identity in wanted]
    elif mode == 'development':
        selected = corpus['cases']
    elif mode == 'stability':
        selected = [c for c in corpus['cases'] if c['id'] in {'rag04-acl-10', 'rag04-formats-05'}]
    elif mode in {'retrieval', 'focused'}:
        # Seen development failures plus natural questions and their security /
        # followup regressions. Never substitute this subset for the corpus84.
        wanted = {'literal': {3, 8}, 'synonyms': {7, 10, 11}, 'formats': {5, 6}}
        selected = [case for case in corpus['cases'] if
                    case['category'] in {'natural', 'multi_conflict', 'acl', 'no_evidence', 'followup'}
                    or int(case['id'].rsplit('-', 1)[1]) in wanted.get(case['category'], set())]
    elif mode == 'budget':
        template = corpus['cases'][0]
        selected = [dict(template, id='budget-fixed-'+str(cap), budget_variant={'mode': 'fixed', 'bytes': cap, 'probe': False})
                    for cap in (2048, 2304, 2560)]
        selected.append(dict(template, id='budget-adaptive', budget_variant={'mode': 'adaptive', 'bytes': 2048, 'probe': True}))
    elif mode == 'followup':
        selected = [case for case in corpus['cases'] if case['id'] in {
            'rag04-followup-01', 'rag04-followup-02', 'rag04-followup-03'}]
    elif mode == 'quality':
        wanted = (['rag04-natural-01', 'rag04-multi_conflict-06', 'rag04-formats-07'] +
                  [f'rag04-acl-{i:02d}' for i in (1, 3, 7, 8, 9, 10)] +
                  [f'rag04-no_evidence-{i:02d}' for i in range(1, 4)])
        by_id = {case['id']: case for case in corpus['cases']}
        selected = [by_id[identity] for identity in wanted]
    elif mode == 'diagnostic':
        # Explicit development failures; no new/holdout cases and no claim of
        # independent evaluation after looking at the first candidate run.
        wanted = ([f'rag04-natural-{i:02d}' for i in range(1, 5)] +
                  [f'rag04-literal-{i:02d}' for i in (3, 4, 5, 7, 9, 10)] +
                  [f'rag04-followup-{i:02d}' for i in (1, 3, 7)] +
                  ['rag04-out_capabilities-07'])
        by_id = {case['id']: case for case in corpus['cases']}
        selected = [by_id[identity] for identity in wanted]
    else:
        wanted = ([f'rag04-natural-{i:02d}' for i in range(1, 5)] +
                  [f'rag04-followup-{i:02d}' for i in range(1, 4)] +
                  ['rag04-out_capabilities-01', 'rag04-out_capabilities-07'])
        by_id = {case['id']: case for case in corpus['cases']}
        selected = [by_id[identity] for identity in wanted]
    return selected[:limit] if limit else list(selected)


def stress_procedure(corpus, minimum_bytes):
    """Technical budget variant, never masquerades as the frozen84-case corpus.

    Only descriptive repetition is added: no steps, amounts or conditions. The
    original gold remains a diagnostic reference, not re-labelled observations.
    """
    if not minimum_bytes:
        return corpus
    corpus = json.loads(json.dumps(corpus))
    procedure = next(doc for doc in corpus['documents'] if doc['id'] == 'synthetic-procedure-v1')
    description = ' Este fragmento pertenece al procedimiento ficticio de confección de vestidos; conserva la secuencia documentada.'
    for fragment in procedure['fragments']:
        while len(fragment['text'].encode('utf-8')) < minimum_bytes:
            fragment['text'] += description
    return corpus


class Journal:
    """Append/fsync before HTTP. A consumed/unknown attempt is never replayed."""
    def __init__(self, path, contract):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        records = []
        if self.path.exists():
            for line in self.path.read_text(encoding='utf-8').splitlines():
                # A torn final record is not guessed safe or overwritten.
                records.append(json.loads(line))
        if records and records[0] != {'event': 'contract', **contract}:
            raise ValueError('Checkpoint contract differs; use a distinct output/checkpoint.')
        self.records = records
        if not records:
            self.append({'event': 'contract', **contract})

    def append(self, record):
        with self.path.open('a', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(record, ensure_ascii=True, separators=(',', ':')) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        self.records.append(record)

    def consumed(self, case_id):
        return any(row.get('case_id') == case_id and row.get('event') in {'attempt', 'case'} for row in self.records)

    def completed(self):
        return {row['observation']['case_id']: row['observation'] for row in self.records if row.get('event') == 'case'}


def wait_retry(seconds, *, sleep=time.sleep, progress=print):
    remaining = max(1, min(int(seconds), 60))
    while remaining:
        interval = min(remaining, 30)
        progress(json.dumps({'event': 'quota_wait', 'remaining_seconds': remaining}), flush=True)
        sleep(interval)
        remaining -= interval


def guarded_database():
    """Install connection guards and verify identity before importing app settings."""
    from run_notification_integration import validated_configuration
    manifest, urls = validated_configuration()
    import psycopg2
    from psycopg2.extensions import parse_dsn
    from sqlalchemy import create_engine, event, text
    from sqlalchemy.engine import Engine
    original = psycopg2.connect

    def check(parameters):
        identity = (parameters.get('host'), str(parameters.get('port')),
                    parameters.get('dbname', parameters.get('database')), parameters.get('user'))
        if identity[:3] != ('127.0.0.1', '55432', 'bab_vdos_testing') or identity[3] not in {'bab_test_runner', 'bab_test_migrator'}:
            raise RuntimeError('Quality runner blocked a PostgreSQL target outside the isolated cluster.')
        if any(key in parameters for key in ('service', 'servicefile', 'passfile', 'hostaddr', 'options')):
            raise RuntimeError('Connection indirection is not allowed.')

    def engine_guard(_dialect, _record, args, kwargs):
        parameters = parse_dsn(args[0]) if args else {}
        parameters.update(kwargs)
        # Coordinator sets bounded query/network options; no target redirection.
        options = parameters.pop('options', None)
        if options not in (None, '-c statement_timeout=5000', '-c lock_timeout=5000 -c statement_timeout=15000'):
            raise RuntimeError('Unexpected connection options.')
        check(parameters)

    event.listen(Engine, 'do_connect', engine_guard)
    # psycopg2 sees the same safe coordinator option after SQLAlchemy's guard.
    def connect(dsn=None, *args, **kwargs):
        parameters = parse_dsn(dsn or '')
        parameters.update(kwargs)
        options = parameters.pop('options', None)
        if options not in (None, '-c statement_timeout=5000', '-c lock_timeout=5000 -c statement_timeout=15000'):
            raise RuntimeError('Unexpected connection options.')
        check(parameters)
        return original(dsn, *args, **kwargs)
    psycopg2.connect = connect
    for variable in ('TEST_MIGRATION_DATABASE_URL', 'TEST_DATABASE_URL'):
        engine = create_engine(urls[variable], hide_parameters=True)
        try:
            with engine.connect() as db:
                if db.scalar(text('SELECT instance_id FROM testing_control.instance')) != manifest['instance_id']:
                    raise RuntimeError('Isolated instance marker mismatch.')
                if db.scalar(text('SELECT current_database()')) != 'bab_vdos_testing':
                    raise RuntimeError('Isolated database mismatch.')
                if db.scalar(text('SELECT version_num FROM alembic_version')) != '20261020_0021':
                    raise RuntimeError('Existing migration0021 required; runner will not migrate.')
                if variable == 'TEST_MIGRATION_DATABASE_URL':
                    if Path(db.scalar(text('SHOW data_directory'))).resolve() != Path(manifest['data_directory']).resolve():
                        raise RuntimeError('Isolated data directory mismatch.')
        finally:
            engine.dispose()
    os.environ['TEST_PG_VALIDATED_INSTANCE'] = manifest['instance_id']
    return urls


def run_contracts(output):
    """Existing-schema regression only: no Alembic, grants, DDL or inference."""
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    from app.core.permissions import build_policy_lines
    from app.services import seed_service
    import pytest
    from app.services.leny_rag_evaluation import snapshot_manifest
    snapshot = snapshot_manifest(BACKEND.parent)
    sources = {name: value for name, value in snapshot['files'].items()
               if name.startswith(('backend/app/services/leny', 'backend/tests/integration/test_leny'))
               or name in {'backend/app/core/config.py', 'backend/scripts/run_leny_rag_quality.py'}}
    violations = []
    counts = {'passed': 0, 'failed': 0, 'skipped': 0, 'deselected': 0}
    def forbid_ddl(_connection, _cursor, statement, _parameters, _context, _many):
        # Fail even if a test/application catches the SQL exception.
        if re.search(r'\b(?:CREATE|ALTER|DROP|GRANT|REVOKE|TRUNCATE)\b', statement, re.I):
            violations.append('ddl_attempt')
            raise RuntimeError('DDL is forbidden in the existing-schema quality regression.')
    event.listen(Engine, 'before_cursor_execute', forbid_ddl)
    def verify_policy():
        if (BACKEND/'app/security/policy.csv').read_text(encoding='utf-8') != '\n'.join(build_policy_lines())+'\n':
            raise RuntimeError('Policy drift; no policy rewrite is authorized.')
    seed_service.sync_policy_file = verify_policy
    verify_policy()
    class Guard:
        def pytest_runtest_logreport(self, report):
            if report.when == 'call':
                counts[report.outcome] += 1
        def pytest_deselected(self, items):
            counts['deselected'] += len(items)
        @pytest.hookimpl(trylast=True)
        def pytest_sessionfinish(self, session, exitstatus):
            if violations:
                session.exitstatus = pytest.ExitCode.TESTS_FAILED
    selected = ['test_leny_rag_quality.py','test_leny_rag_chat.py','test_leny_rag_service.py',
                'test_leny_document_service.py','test_leny_rate_limit.py','test_leny_persistence.py']
    result = int(pytest.main(['-c', str(BACKEND.parent/'pytest.ini'), '--confcutdir', str(BACKEND/'tests'),
        '--basetemp', str(Path.cwd()/'pytest-tmp'), '-q', '-p', 'no:cacheprovider',
        '-k', 'not migration and not downgrade and not rolling_document_insert',
        *[str(BACKEND/'tests/integration'/name) for name in selected]], plugins=[Guard()]))
    Path(output).write_text(json.dumps({'scope': 'isolated_existing_schema_regression',
        'exit_code': result, 'migrations_executed': False, 'ddl_attempts': len(violations),
        'models_invoked': False, 'business_environment_modified': False, 'test_counts': counts,
        'source_files_sha256': sources, 'source_freeze_verified': frozen_sources_match(BACKEND.parent, sources)}, indent=2)+'\n', encoding='utf-8')
    return result


def configuration(settings, args):
    overrides = dict(database_url=os.environ['TEST_DATABASE_URL'], leny_enabled=True,
        leny_documents_enabled=True, leny_rag_enabled=True, leny_rag_chat_enabled=True,
        leny_keep_alive='0', leny_num_ctx=4096, leny_num_predict=768,
        leny_temperature=getattr(args, 'temperature', 0.3), leny_rate_limit=5,
        leny_rate_window_seconds=60, leny_rag_min_ram_bytes=2*1024**3,
        leny_rag_min_resident_ram_bytes=1024**3, leny_rag_cpu_threads=4,
        leny_rag_batch_size=2, leny_rag_top_k=5, leny_rag_candidates=20,
        leny_rag_profile=args.profile, leny_rag_evidence_mode=args.evidence_mode,
        leny_rag_max_context_bytes=args.budget, leny_rag_ranking=args.ranking,
        leny_rag_adaptive_token_probe=args.token_probe,
        leny_rag_neighbor_chunks=args.neighbors, leny_documents_root=str(Path.cwd()/'private-library'),
        backup_dir=str(Path.cwd()/'backup-lock'))
    for key, value in overrides.items():
        setattr(settings, key, value)
    # Paths and DB credentials are deliberately excluded from report identity.
    return {key: value for key, value in overrides.items() if key not in {'database_url', 'leny_documents_root', 'backup_dir'}}


def real_models(settings):
    from urllib.request import urlopen
    with urlopen(settings.leny_ollama_url + '/api/tags', timeout=5) as response:
        tags = json.load(response)['models']
    identities = {}
    for key, name in (('chat_digest', settings.leny_model), ('embedding_digest', settings.leny_rag_model)):
        match = next((model for model in tags if model.get('name') == name), None)
        if not match or not isinstance(match.get('digest'), str):
            raise RuntimeError('An explicitly configured local model is missing.')
        identities[key] = match['digest'].removeprefix('sha256:')
    if identities['embedding_digest'] != settings.leny_rag_model_digest:
        raise RuntimeError('Embedding model digest mismatch.')
    return identities


def assert_idle(sessions, settings, *, provider=True):
    from sqlalchemy import text
    with sessions() as db:
        if db.scalar(text("SELECT state FROM leny.inferencia_estado WHERE id=1")) != 'idle':
            raise RuntimeError('Unconfirmed inference: preserve markers and stop evaluation.')
        if db.scalar(text("SELECT EXISTS(SELECT 1 FROM leny.rag_workers WHERE provider_inflight OR unsafe_reason IS NOT NULL)")):
            raise RuntimeError('A documental inference requires reconciliation.')
        if db.scalar(text("SELECT EXISTS(SELECT 1 FROM leny.rag_trabajos WHERE status IN ('queued','running'))")):
            raise RuntimeError('Pending indexations: exclusive window is not ready.')
    if provider:
        from urllib.request import urlopen
        with urlopen(settings.leny_ollama_url + '/api/ps', timeout=5) as response:
            if json.load(response).get('models'):
                raise RuntimeError('Ollama has resident models; wait for natural expiry, never stop foreign models.')


async def embed_corpus(settings, coordinator, state, texts):
    from app.services.leny_rag_embeddings import EmbeddingProvider
    from app.services.leny_rag_common import available_ram
    vectors = []
    for offset in range(0, len(texts), 2):
        if available_ram() < 2*1024**3:
            raise RuntimeError('Cold RAM safety floor is not available.')
        lease, provider, identity, tracked = coordinator.acquire(), EmbeddingProvider(settings), uuid4(), False
        try:
            tracked = state.start(lease, identity, settings.leny_rag_model, 'query_embedding')
            vectors.extend(await provider.embed(texts[offset:offset+2]))
        finally:
            confirmed = not provider.inference_started
            try:
                if provider.owned_model:
                    await provider.release()
                confirmed = confirmed or (provider.response_complete and not provider.owned_model)
            finally:
                try:
                    if tracked:
                        state.finish(lease, identity, confirmed)
                finally:
                    lease.close()
        print(json.dumps({'event': 'synthetic_embeddings', 'completed': min(offset+2, len(texts)), 'total': len(texts)}), flush=True)
    return vectors


def synthetic_original(document):
    """Build a real, internally generated original; never extract enterprise text."""
    source = document.get('source_type', 'PDF_TEXT')
    values = [item['text'] for item in document['fragments']]
    if source.startswith('DOCX_'):
        from xml.sax.saxutils import escape
        paragraphs = ['<w:p><w:r><w:t>'+escape(value)+'</w:t></w:r></w:p>' for value in values]
        body = ''.join('<w:tr><w:tc>'+paragraph+'</w:tc></w:tr>' for paragraph in paragraphs) if source == 'DOCX_TABLE' else ''.join(paragraphs)
        if source == 'DOCX_TABLE':
            body = '<w:tbl>'+body+'</w:tbl>'
        result = io.BytesIO()
        with zipfile.ZipFile(result, 'w') as archive:
            archive.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
            archive.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
            archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+body+'</w:body></w:document>')
        return result.getvalue(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'synthetic.docx'
    if source == 'IMAGE_OCR':
        import pyvips
        image = pyvips.Image.text('\n'.join(values), font='Arial 22', width=1200)
        image = image.invert().embed(20, 20, image.width+40, image.height+40, extend='white')
        media = document.get('media_type', 'image/png')
        if media == 'image/jpeg':
            return image.jpegsave_buffer(Q=95), media, 'synthetic.jpg'
        if media != 'image/png':
            raise ValueError('Unsupported synthetic image media type.')
        return image.pngsave_buffer(), media, 'synthetic.png'
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, NumberObject, DecodedStreamObject
    writer = PdfWriter()
    for value in values:
        page = writer.add_blank_page(width=600, height=800)
        commands = []
        if source == 'PDF_OCR':
            import pyvips
            image = pyvips.Image.text(value, font='Arial 22', width=1000)
            image = image.invert().embed(20, 20, image.width+40, image.height+40, extend='white')
            raster = DecodedStreamObject(); raster.set_data(image.write_to_memory())
            raster.update({NameObject('/Type'): NameObject('/XObject'), NameObject('/Subtype'): NameObject('/Image'),
                NameObject('/Width'): NumberObject(image.width), NameObject('/Height'): NumberObject(image.height),
                NameObject('/ColorSpace'): NameObject('/DeviceGray'), NameObject('/BitsPerComponent'): NumberObject(8)})
            page[NameObject('/Resources')] = DictionaryObject({NameObject('/XObject'): DictionaryObject({NameObject('/Im0'): writer._add_object(raster)})})
            commands = [f'q 560 0 0 {min(740, image.height*560/image.width):.2f} 20 30 cm /Im0 Do Q'.encode('ascii')]
        else:
            font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'),
                NameObject('/BaseFont'): NameObject('/Helvetica'), NameObject('/Encoding'): NameObject('/WinAnsiEncoding')})
            page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
            commands = [b'BT /F1 10 Tf 30 760 Td 14 TL']
            for line in textwrap.wrap(value, 90):
                encoded = line.encode('cp1252', errors='strict').replace(b'\\', b'\\\\').replace(b'(', b'\\(').replace(b')', b'\\)')
                commands.append(b'('+encoded+b') Tj T*')
            commands.append(b'ET')
        stream = DecodedStreamObject(); stream.set_data(b'\n'.join(commands))
        page[NameObject('/Contents')] = writer._add_object(stream)
    result = io.BytesIO(); writer.write(result)
    return result.getvalue(), 'application/pdf', 'synthetic.pdf'


def setup_fixture(settings, sessions, corpus, vectors, owned):
    from sqlalchemy import text
    from app.models.leny_documents import (LenyDocumentFolder, LenyDocument, LenyDocumentVersion,
        LenyDocumentReadRole)
    from app.models.leny_rag import LenyRagIndexation, LenyRagFragment, LenyRagEmbedding
    from app.services.leny_rag_common import pipeline_config, PIPELINE_VERSION, CHUNKING_VERSION, OCR_VERSION
    from app.services.leny_rag_publication import PublicationService
    from app.schemas.leny_documents import PublicationRequest
    from app.services.leny_store import LenyActor
    publication = PublicationService(settings, sessions)
    prefix = owned['prefix']
    with sessions.begin() as db:
        existing_doc = db.scalar(text("SELECT id FROM roles WHERE codigo='DOC' AND activo"))
        # Test an inherited unauthorized role only if it already exists. Never
        # create a sixth role just to satisfy an evaluation fixture.
        for role in (*ROLES, *(('DOC',) if existing_doc else ())):
            role_id = db.scalar(text('SELECT id FROM roles WHERE codigo=:role AND activo'), {'role': role})
            if role_id is None:
                if db.scalar(text('SELECT id FROM roles WHERE codigo=:role'), {'role': role}) is not None:
                    raise RuntimeError('Inactive shared role; runner will not change it.')
                role_id = db.scalar(text('INSERT INTO roles(codigo,nombre,activo) VALUES(:role,:name,true) RETURNING id'),
                    {'role': role, 'name': 'SYNTHETIC '+role})
                owned['roles'].append(role_id)
            user = db.scalar(text("INSERT INTO usuarios(nombres,apellido_paterno,ci,celular,correo,zona,activo) VALUES('SYNTHETIC','RAG04',:ci,'00000000',:mail,'TEST',true) RETURNING id"),
                {'ci': prefix[:20]+str(len(owned['users'])), 'mail': prefix+role.lower()+'@example.invalid'})
            account = db.scalar(text("INSERT INTO cuentas(usuario_id,rol_id,username,password_hash,must_change_password,is_active) VALUES(:u,:r,:name,'NOT_A_LOGIN_HASH',false,true) RETURNING id"),
                {'u': user, 'r': role_id, 'name': prefix+role.lower()})
            owned['users'].append(user)
            owned['actors'][role] = dict(user=user, account=account, role_id=role_id)
        admin = owned['actors']['ADMIN']
        folder = LenyDocumentFolder(name='SYNTHETIC '+prefix, name_key='synthetic '+prefix, created_by=admin['user'])
        db.add(folder); db.flush(); owned['folder'] = folder.id
    actor = LenyActor(admin['account'], admin['user'], str(uuid4()))
    with publication.documents.lock():
        vector_iter = iter(vectors)
        for document in corpus['documents']:
            original, media_type, original_name = synthetic_original(document)
            if document.get('media_type', media_type) != media_type:
                raise ValueError('Synthetic corpus source type/media type mismatch.')
            storage_key = 'versions/'+uuid4().hex+'.blob'
            publication.documents.storage.path(storage_key).write_bytes(original)
            with sessions.begin() as db:
                doc = LenyDocument(folder_id=owned['folder'], title='SYNTHETIC '+document['id'], created_by=admin['user'])
                db.add(doc); db.flush(); owned['documents'].append(doc.id)
                owned['document_ids'][document['id']] = doc.id
                version = LenyDocumentVersion(document_id=doc.id, number=1, storage_key=storage_key,
                    sha256=hashlib.sha256(original).hexdigest(), size_bytes=len(original), media_type=media_type,
                    original_name=original_name, created_by=admin['user'])
                db.add(version); db.flush()
                index = LenyRagIndexation(version_id=version.id, model=settings.leny_rag_model,
                    model_digest=settings.leny_rag_model_digest, pipeline_version=PIPELINE_VERSION,
                    chunking_version=CHUNKING_VERSION, ocr_version=OCR_VERSION, config=pipeline_config(settings),
                    coverage={'warnings': [], 'synthetic': True}, status='validated',
                    chunk_count=len(document['fragments']), validated_at=datetime.now(timezone.utc))
                db.add(index); db.flush()
                for ordinal, item in enumerate(document['fragments']):
                    value = item['text']
                    source_type = document.get('source_type', 'PDF_TEXT')
                    locator = {'unit': ordinal, 'start': 0, 'end': len(value), 'offset_basis': 'NFC_CHARACTERS'}
                    if source_type.startswith('PDF_'):
                        locator['page'] = ordinal+1
                    elif source_type == 'DOCX_TABLE':
                        locator.update(table=1, row=ordinal+1, column=1)
                    elif source_type == 'DOCX_PARAGRAPH':
                        locator['paragraph'] = ordinal+1
                    fragment = LenyRagFragment(indexation_id=index.id, ordinal=ordinal, text=value,
                        sha256=hashlib.sha256(value.encode('utf-8')).hexdigest(), source_type=source_type, locator=locator,
                        char_count=len(value), byte_count=len(value.encode('utf-8')))
                    db.add(fragment); db.flush()
                    owned['fragment_ids'][str(fragment.id)] = item['id']
                    db.add(LenyRagEmbedding(fragment_id=fragment.id, indexation_id=index.id, embedding=next(vector_iter)))
                for role in document['roles']:
                    db.add(LenyDocumentReadRole(document_id=doc.id, role_id=owned['actors'][role]['role_id']))
                version.validated_indexation_id = index.id
                version.status = 'pending_publication'
                version_id, index_id, doc_id = version.id, index.id, doc.id
            publication.publish(actor, doc_id, PublicationRequest(request_id=uuid4(), version_id=version_id,
                indexation_id=index_id, expected_revision=1, confirm=True))
            owned.setdefault('identities', {})[document['id']] = dict(
                document_id=str(doc_id), version=1, version_id=str(version_id), indexation_id=str(index_id))


def cleanup(sessions, owned):
    """Only rows created by this invocation; no shared actors/roles are reassigned."""
    from sqlalchemy import text
    if not owned['users']:
        return
    with sessions.begin() as db:
        args = {'users': owned['users'], 'docs': [str(value) for value in owned['documents']]}
        for statement in (
            'DELETE FROM leny.conversaciones WHERE user_id=ANY(:users)',
            'DELETE FROM leny.admissions WHERE user_id=ANY(:users)',
            'DELETE FROM leny.rate_users WHERE user_id=ANY(:users)',
            'UPDATE leny.documentos SET published_version_id=NULL,published_indexation_id=NULL,published_at=NULL,published_by=NULL WHERE id=ANY(CAST(:docs AS uuid[]))',
            "UPDATE leny.documento_versiones SET validated_indexation_id=NULL,status='pending_contextualization' WHERE document_id=ANY(CAST(:docs AS uuid[]))",
            'DELETE FROM leny.rag_indexaciones WHERE version_id IN (SELECT id FROM leny.documento_versiones WHERE document_id=ANY(CAST(:docs AS uuid[])))',
            'DELETE FROM leny.documento_versiones WHERE document_id=ANY(CAST(:docs AS uuid[]))',
            'DELETE FROM leny.documentos WHERE id=ANY(CAST(:docs AS uuid[]))',
            'DELETE FROM leny.documento_operaciones WHERE user_id=ANY(:users)',
            'DELETE FROM leny.carpetas WHERE created_by=ANY(:users)',
            'DELETE FROM auditoria_sistema WHERE usu_id=ANY(:users)',
            'DELETE FROM cuentas WHERE usuario_id=ANY(:users)',
            'DELETE FROM usuarios WHERE id=ANY(:users)',
        ):
            db.execute(text(statement), args)
        for role in owned['roles']:
            db.execute(text('DELETE FROM roles WHERE id=:role AND NOT EXISTS(SELECT 1 FROM cuentas WHERE rol_id=:role)'), {'role': role})


@contextmanager
def case_scenario(sessions, owned, case):
    """Apply a state change between turns, only to this run's synthetic rows."""
    from sqlalchemy import text
    actor = owned['actors'][case['role']]
    change = case.get('state_change')
    undo = []
    if change == 'change_role':
        previous = owned['actors'][case['previous_role']]['role_id']
        with sessions.begin() as db:
            db.execute(text('UPDATE cuentas SET rol_id=:role WHERE id=:account AND usuario_id=:user'),
                       {'role': previous, 'account': actor['account'], 'user': actor['user']})
        undo.append(('role', actor['role_id']))

    def apply():
        if not change:
            return
        with sessions.begin() as db:
            if change == 'revoke_acl':
                identity = owned['document_ids']['synthetic-prices-v1']
                removed = db.execute(text('DELETE FROM leny.documento_roles_lectura WHERE document_id=:doc AND role_id=:role RETURNING role_id'),
                    {'doc': identity, 'role': actor['role_id']}).scalars().all()
                undo.extend(('acl', (identity, role)) for role in removed)
            elif change == 'withdraw_publication':
                identity = owned['document_ids']['synthetic-procedure-v1']
                previous = db.execute(text('SELECT published_version_id,published_indexation_id,published_at,published_by FROM leny.documentos WHERE id=:doc'),
                                      {'doc': identity}).one()
                undo.append(('publication', (identity, tuple(previous))))
                db.execute(text('UPDATE leny.documentos SET published_version_id=NULL,published_indexation_id=NULL,published_at=NULL,published_by=NULL WHERE id=:doc'), {'doc': identity})
            elif change == 'change_role':
                db.execute(text('UPDATE cuentas SET rol_id=:role WHERE id=:account AND usuario_id=:user'),
                           {'role': actor['role_id'], 'account': actor['account'], 'user': actor['user']})
            else:
                raise ValueError('Unknown synthetic state change')
    try:
        yield apply
    finally:
        with sessions.begin() as db:
            for kind, value in reversed(undo):
                if kind == 'role':
                    db.execute(text('UPDATE cuentas SET rol_id=:role WHERE id=:account AND usuario_id=:user'),
                               {'role': value, 'account': actor['account'], 'user': actor['user']})
                elif kind == 'acl':
                    identity, role = value
                    db.execute(text('INSERT INTO leny.documento_roles_lectura(document_id,role_id) VALUES(:doc,:role) ON CONFLICT DO NOTHING'),
                               {'doc': identity, 'role': role})
                else:
                    identity, (version, index, published, user) = value
                    db.execute(text('UPDATE leny.documentos SET published_version_id=:version,published_indexation_id=:index,published_at=:at,published_by=:user WHERE id=:doc'),
                               {'doc': identity, 'version': version, 'index': index, 'at': published, 'user': user})


def run_child(arguments):
    args = argparse.Namespace(**arguments)
    guarded_database()
    from app.core.config import settings
    configured = configuration(settings, args)
    if args.mode == 'contracts':
        return run_contracts(args.output)
    from app.services.leny_rag_evaluation import validate_corpus, snapshot_manifest, digest
    corpus = validate_corpus(json.loads(CORPUS.read_text(encoding='utf-8')))
    corpus = stress_procedure(corpus, args.procedure_stress_bytes)
    cases = select_cases(corpus, args.mode, args.case_limit)
    identities = real_models(settings)
    snapshot = snapshot_manifest(BACKEND.parent)
    contract = dict(profile=args.profile, corpus_sha256=digest(CORPUS), model_identity=identities,
        configuration_sha256=sha(configured), snapshot_manifest_sha256=snapshot['manifest_sha256'])
    if args.procedure_stress_bytes:
        contract.update(corpus_sha256=sha(corpus), base_corpus_sha256=digest(CORPUS),
                        fixture_variant='procedure_stress', fixture_variant_sha256=sha(corpus))
    journal = Journal(args.checkpoint, contract)
    from sqlalchemy import text
    from app.core.database import engine, SessionLocal, get_db
    from app.services.leny_coordination import PostgresCoordinator
    from app.services.leny_inference_state import InferenceState
    from app.services.leny_rag_common import available_ram
    from app.services import seed_service
    from app.core.permissions import build_policy_lines
    def verify_policy():
        if (BACKEND/'app/security/policy.csv').read_text(encoding='utf-8') != '\n'.join(build_policy_lines())+'\n':
            raise RuntimeError('Policy drift; quality runner will not rewrite policies.')
    seed_service.sync_policy_file = verify_policy
    verify_policy()
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.routers import leny, leny_sources
    from app.core.security import create_access_token
    from app.services.leny_store import LenyStore
    from app.services.leny_service import LenyService
    from app.services.leny_rate_limit import RateLimiter
    from app.services.leny_rag_retrieval import RetrievalService
    from app.services.leny_rag_sources import SourceService
    from app.services.leny_ollama import OllamaProvider
    coordinator, state = PostgresCoordinator(settings.effective_database_url), InferenceState(SessionLocal)
    assert_idle(SessionLocal, settings)
    with SessionLocal() as db:
        if db.scalar(text('SELECT EXISTS(SELECT 1 FROM leny.documentos WHERE published_indexation_id IS NOT NULL)')):
            raise RuntimeError('Published isolated fixtures already exist; do not mix different evaluation runs.')
    owned = dict(prefix='rag04_'+uuid4().hex[:14]+'_', users=[], roles=[], documents=[], document_ids={}, actors={}, fragment_ids={})
    traces, diagnostics = {}, []
    class TracedRetrieval(RetrievalService):
        def search(self, *values, **keywords):
            result = super().search(*values, **keywords)
            traces['candidate_fragment_ids'] = [owned['fragment_ids'].get(str(row['fragment_id']), 'UNKNOWN') for row in result]
            traces['sql_candidates'] = [dict(rank=i, fragment=owned['fragment_ids'].get(str(r['fragment_id']), 'UNKNOWN'),
                document_id=str(r['document_id']), version_id=str(r['version_id']), version=r['version'],
                indexation_id=str(r['indexation_id']), distance=float(r['distance']),
                rrf_score=float(r['rrf_score']) if 'rrf_score' in r else None) for i, r in enumerate(result, 1)]
            return result
    class TracedSources(SourceService):
        def persist(self, actor, message_id, fragments):
            traces['selected_fragment_ids'] = [owned['fragment_ids'].get(str(row['fragment_id']), 'UNKNOWN') for row in fragments]
            return super().persist(actor, message_id, fragments)
    class TracedProvider(OllamaProvider):
        async def classify(self, messages, schema):
            result = await super().classify(messages, schema)
            # Only the isolated synthetic corpus reaches this producer. Capture
            # the review stage independently of final source persistence.
            if ('relevant_sources' in schema.get('properties', {}) or 'documents' in schema.get('properties', {})
                    or set(schema.get('properties', {})) in ({'verdict'}, {'aspect', 'scope', 'relation', 'sources'})):
                data = json.loads(messages[-1]['content'])
                if 'candidates' in data:
                    values = [part['text'] for part in data['candidates']]
                elif 'documents' in data:
                    values = [part for doc in data['documents'] for part in doc['parts']]
                else:
                    values = [part['text'] for doc in data['evidence'] for part in doc['parts']]
                mapping = {item['text']: key for doc in corpus['documents'] for item in doc['fragments'] for key in [item['id']]}
                reviewed = [mapping.get(value, 'UNKNOWN') for value in values]
                traces.setdefault('review_fragment_ids', []).extend(item for item in reviewed if item not in traces.get('review_fragment_ids', []))
                try: decision = json.loads(result)
                except ValueError: decision = {'invalid': True}
                traces.setdefault('document_reviews', []).append({'fragment_ids': reviewed, 'decision': decision})
                traces['review_decision'] = decision
            return result
        async def stream(self, messages):
            async for chunk in trace_generation(self, super().stream(messages), traces):
                yield chunk
    class Diagnostics(logging.Handler):
        def emit(self, record):
            if hasattr(record, 'leny_rag'):
                diagnostics.append(record.leny_rag)
    handler, logger = Diagnostics(), logging.getLogger('app.services.leny_service')
    old_level = logger.level
    logger.addHandler(handler); logger.setLevel(logging.INFO)
    sources = TracedSources(settings, SessionLocal)
    service = LenyService(settings, LenyStore(SessionLocal, sources), coordinator,
        provider_factory=lambda: TracedProvider(settings),
        rate_limiter=RateLimiter(SessionLocal, 5, 60), retrieval=TracedRetrieval(settings, SessionLocal),
        sources=sources, inference_state=state)
    if args.mode == 'supervised':
        from app.services.leny_rag_routing import policy_version
        if service.coverage_verifier is not None or policy_version(settings) != 'rag4-v4':
            raise RuntimeError('Supervised pilot must preserve rag4-v4 without experimental coverage.')
    app = FastAPI()
    app.include_router(leny.router, prefix='/api/v1/leny')
    app.include_router(leny_sources.router, prefix='/api/v1/leny')
    def isolated_db():
        with SessionLocal() as db:
            yield db
    app.dependency_overrides[get_db] = isolated_db
    app.dependency_overrides[leny.get_leny_service] = lambda: service
    app.dependency_overrides[leny_sources.get_source_service] = lambda: sources
    observations = dict(schema_version='rag04-real-synthetic-observations-v1', data_classification='synthetic',
        **contract, comparison_contract_sha256=sha({'models': identities, 'corpus': digest(CORPUS),
            'context': 4096, 'generation': 768, 'quota': [5, 60], 'top_k': 5}), cases=[],
        human_review_complete=False, business_e2e_executed=False, holdout_executed=False,
        extraction_formats_evaluated=False, settings=configured, runner_mode=args.mode,
        original_representation='generated synthetic originals with fixture source types; extraction not evaluated by this runner',
        created_at_utc=datetime.now(timezone.utc).isoformat())
    from app.services.leny_rag_routing import policy_version
    from app.services.leny_rag_grounding import GROUNDING_VERSION
    observations['component_versions'] = {'policy': policy_version(settings),
        'documentary_output': GROUNDING_VERSION if args.profile == 'rag4_v1' else 'legacy_generation',
        'retrieval': 'sql-acl-current-publication', 'ranking': settings.leny_rag_ranking}
    if args.profile == 'rag4_v1':
        from app.services.leny_rag_selection import SELECTION_VERSION
        observations['component_versions']['selection'] = SELECTION_VERSION
    if args.procedure_stress_bytes:
        observations['scope'] = 'synthetic_budget_experiment_not_development_corpus'
        observations['procedure_stress_bytes'] = args.procedure_stress_bytes
    observations['source_files_sha256'] = {path: value for path, value in snapshot['files'].items()
        if path.startswith('backend/app/services/leny') or path in {
            'backend/app/core/config.py', 'backend/scripts/run_leny_rag_quality.py',
            'backend/scripts/run_leny_rag_quality.ps1', 'backend/scripts/leny_rag_layered_evaluation.py',
            'backend/tests/fixtures/leny_rag04_development.json'}}
    def save_report():
        observations['cases'] = list(journal.completed().values())
        Path(args.output).write_text(json.dumps(observations, ensure_ascii=True, indent=2)+'\n', encoding='utf-8')
    try:
        texts = [fragment['text'] for doc in corpus['documents'] for fragment in doc['fragments']]
        vectors = asyncio.run(embed_corpus(settings, coordinator, state, texts))
        setup_fixture(settings, SessionLocal, corpus, vectors, owned)
        if args.mode == 'retrieval':
            from leny_rag_layered_evaluation import retrieval_cases
            retrieval_cases(settings, SessionLocal, coordinator, state, corpus, cases,
                            owned, journal, save_report)
            observations['scope'] = 'synthetic_sql_selection_without_qwen_generation'
            return 0
        with TestClient(app) as client:
            if client.get('/api/v1/leny/status').status_code != 401:
                raise RuntimeError('Authentication requirement failed.')
            for case in cases:
                if Path(args.output+'.stop').exists():
                    observations['stopped_early'] = 'operator_requested_between_cases'
                    break
                case_id = case['id']
                if case.get('budget_variant'):
                    variant = case['budget_variant']
                    settings.leny_rag_evidence_mode = variant['mode']
                    settings.leny_rag_max_context_bytes = variant['bytes']
                    settings.leny_rag_adaptive_token_probe = variant['probe']
                if journal.consumed(case_id):
                    if case_id not in journal.completed():
                        journal.append({'event': 'case', 'observation': {'case_id': case_id, 'status': 'failed',
                            'route': 'unknown', 'error_code': 'previous_attempt_consumed_or_unknown', 'human_review': None}, 'case_id': case_id})
                    continue
                if case['role'] not in owned['actors']:
                    journal.append({'event': 'case', 'case_id': case_id, 'observation': {'case_id': case_id,
                        'status': 'failed', 'route': 'unknown', 'target_executed': False,
                        'failure_stage': 'setup', 'error_code': 'preexisting_unauthorized_role_absent', 'human_review': None}})
                    save_report(); continue
                with case_scenario(SessionLocal, owned, case) as apply_change:
                    actor = owned['actors'][case['role']]
                    headers = {'Authorization': 'Bearer '+create_access_token(str(actor['account']), case['role'])}
                    created = client.post('/api/v1/leny/conversations', headers=headers)
                    if created.status_code == 403:
                        request = uuid4()
                        journal.append({'event': 'attempt', 'case_id': case_id, 'turn': 0, 'request_id': str(request)})
                        denied = client.post('/api/v1/leny/chat', headers=headers, json={
                            'conversation_id': str(uuid4()), 'request_id': str(request), 'message': case['question']})
                        journal.append({'event': 'case', 'case_id': case_id, 'observation': {
                            'case_id': case_id, 'request_id': str(request), 'status': 'rejected' if denied.status_code == 403 else 'failed',
                            'route': 'forbidden' if denied.status_code == 403 else 'unknown', 'http_status': denied.status_code,
                            'candidate_fragment_ids': [], 'selected_fragment_ids': [], 'sent_fragment_ids': [],
                            'citation_fragment_ids': [], 'review': None}})
                        save_report()
                        continue
                    if created.status_code != 201:
                        raise RuntimeError('Could not create an isolated conversation.')
                    conversation = created.json()['id']
                    questions = [*case.get('prior_user_questions', []), case['question']]
                    final = None
                    for turn, question in enumerate(questions):
                        if turn == len(questions)-1:
                            apply_change()
                        request = uuid4()
                        traces.clear(); diagnostics.clear()
                        while True:
                            journal.append({'event': 'attempt', 'case_id': case_id, 'turn': turn,
                                'request_id': str(request), 'time_utc': datetime.now(timezone.utc).isoformat()})
                            before = time.monotonic()
                            ram_before = available_ram()
                            response = client.post('/api/v1/leny/chat', headers=headers,
                                json={'conversation_id': conversation, 'request_id': str(request), 'message': question})
                            elapsed = (time.monotonic()-before)*1000
                            if response.status_code != 429:
                                break
                            with SessionLocal() as db:
                                admitted = db.scalar(text('SELECT EXISTS(SELECT 1 FROM leny.admissions WHERE user_id=:user AND request_id=:request)'),
                                    {'user': actor['user'], 'request': request})
                            if admitted:
                                break  # May have consumed quota: never repeat it.
                            journal.append({'event': 'not_admitted_429', 'case_id': case_id, 'request_id': str(request)})
                            wait_retry(response.headers.get('Retry-After', '3'))
                        events = [json.loads(line) for line in response.text.splitlines()] if response.status_code == 200 else []
                        last = events[-1] if events else {}
                        text_output = ''.join(event.get('text', '') for event in events if event.get('type') == 'delta')
                        diagnostic = diagnostics[-1] if diagnostics else {}
                        route_map = {'documentary': 'rag', 'business': 'general', 'out_of_scope': 'outside',
                            'manipulation': 'reject', 'dangerous': 'reject', 'unavailable': 'unavailable', 'ambiguous': 'ambiguous'}
                        final = dict(case_id=case_id, status='completed' if last.get('type') == 'done' and last.get('status') == 'completed' else 'failed',
                            route=route_map.get(diagnostic.get('route'), 'unknown'), latency_ms=elapsed,
                            request_id=str(request), latency_scope='generation_request',
                            response_text=text_output, http_status=response.status_code, diagnostics=diagnostic,
                            ram_available_before_bytes=ram_before, ram_available_after_bytes=available_ram(),
                            human_review=None, **traces)
                        final.setdefault('sent_fragment_ids', [])  # No generation invocation.
                        if diagnostic.get('counts', {}).get('documented_excerpt') == 1:
                            # These selected rows were a subset of the confirmed
                            # relevance prompt received by Qwen. The final text
                            # is a backend quote, not invented model generation.
                            final['sent_fragment_ids'] = traces.get('selected_fragment_ids', [])
                            final['sent_evidence_basis'] = 'confirmed_relevance_prompt_for_documented_excerpt'
                            final['response_origin'] = 'backend_documented_excerpt'
                            final['generator_fragment_ids'] = []
                            final['render_fragment_ids'] = traces.get('selected_fragment_ids', [])
                            final['generator_invoked'] = False
                            if diagnostic.get('counts', {}).get('grounded_excerpt') == 1:
                                final['response_origin'] = 'backend_grounded_excerpts'
                        else:
                            final['response_origin'] = 'model_or_policy'
                        annotate_target(final, turn, len(questions)-1)
                        chosen = traces.get('selected_fragment_ids', [])
                        labels = {'S'+str(index+1): value for index, value in enumerate(chosen)}
                        final['citation_fragment_ids'] = list(dict.fromkeys(
                            labels.get(label, 'UNKNOWN_CITATION') for label in re.findall(r'\[(S\d+)\]', text_output)))
                        final['review'] = None  # A human must explicitly review semantic claims.
                        if case.get('budget_variant'):
                            final['budget_variant'] = case['budget_variant']
                        final['abstained'] = diagnostic.get('outcome') == 'no_evidence'
                        if final['abstained']:
                            final['route'] = 'no_evidence'
                        if response.status_code == 403:
                            final.update(route='forbidden', status='rejected')
                        if response.status_code == 422:
                            final.update(route='reject', status='rejected', rejection_stage='input_validation')
                        final['error_code'] = last.get('code') if last.get('type') == 'error' else None
                        journal.append({'event': 'turn', 'case_id': case_id, 'turn': turn, 'http_status': response.status_code,
                            'status': final['status'], 'diagnostics': diagnostic, 'latency_ms': elapsed,
                            # Synthetic-only producer: retain prerequisite evidence
                            # as well as the target, without changing target gold.
                            'observation': final})
                        assert_idle(SessionLocal, settings, provider=False)
                        if final['status'] != 'completed':
                            break
                    journal.append({'event': 'case', 'case_id': case_id, 'observation': final})
                    save_report()
                    print(json.dumps({'event': 'case_complete', 'case_id': case_id, 'status': final['status'],
                        'route': final['route'], 'latency_ms': elapsed}), flush=True)
                    if args.mode == 'focused' and case.get('critical_natural') and final['status'] != 'completed':
                        observations['stopped_early'] = 'critical_natural_operational_failure'
                        break
    finally:
        save_report()
        try:
            observations['source_freeze_verified'] = frozen_sources_match(BACKEND.parent, observations['source_files_sha256'])
            observations['model_identity_verified'] = real_models(settings) == identities
        except Exception:
            observations['source_freeze_verified'] = observations['model_identity_verified'] = False
        try:
            assert_idle(SessionLocal, settings, provider=False)
            cleanup(SessionLocal, owned)
            observations['cleanup_confirmed'] = True
        except Exception:
            observations['cleanup_confirmed'] = False
            observations['cleanup_reason'] = 'protected_rows_preserved_for_reconciliation'
            raise
        finally:
            save_report()
            logger.removeHandler(handler); logger.setLevel(old_level)
            coordinator.engine.dispose(); engine.dispose()
    return 0 if observations['source_freeze_verified'] and observations['model_identity_verified'] else 2


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--profile', choices=('legacy', 'rag4_v1'), required=True)
    result.add_argument('--mode', choices=('pilot', 'followup', 'diagnostic', 'quality', 'contracts', 'development', 'budget', 'retrieval', 'focused', 'stability', 'supervised'), default='pilot')
    result.add_argument('--evidence-mode', choices=('fixed', 'adaptive'), default='fixed')
    result.add_argument('--budget', type=int, choices=(2048, 2304, 2560), default=2048)
    result.add_argument('--ranking', choices=('semantic', 'hybrid'), default='semantic')
    result.add_argument('--neighbors', action='store_true')
    result.add_argument('--temperature', type=float, choices=(0.0, 0.3), default=0.3,
                        help='Isolated generation experiment only; classifiers remain0. No ERP env change.')
    result.add_argument('--token-probe', action='store_true', help='Candidate adaptive cold prefill probes; subject to the same lease/deadline.')
    result.add_argument('--procedure-stress-bytes', type=int, choices=(900, 1200), default=0,
                        help='Separate technical whole-procedure budget variant; cannot be scored as the frozen84cases.')
    result.add_argument('--case-limit', type=int, choices=range(1, 85), metavar='1..84')
    result.add_argument('--output', required=True)
    result.add_argument('--checkpoint')
    result.add_argument('--exclusive-window-confirmed', action='store_true',
        help='Acknowledge the separately authorized exclusive local LENY window, with indexations stopped.')
    return result


def main():
    args = parser().parse_args()
    if args.mode == 'budget':
        if args.profile != 'rag4_v1':
            parser().error('--mode budget requires the candidate profile.')
        args.procedure_stress_bytes = args.procedure_stress_bytes or 900
    if args.token_probe and (args.profile != 'rag4_v1' or args.evidence_mode != 'adaptive'):
        parser().error('--token-probe requires --profile rag4_v1 --evidence-mode adaptive.')
    if not args.exclusive_window_confirmed:
        print('An explicitly authorized exclusive LENY window is required; nothing executed.', file=sys.stderr)
        return 2
    from run_notification_integration import validated_configuration
    try:
        _, urls = validated_configuration()
        args.output = str(Path(args.output).resolve())
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        args.checkpoint = str(Path(args.checkpoint or args.output+'.jsonl').resolve())
        if args.output == args.checkpoint:
            raise ValueError('Report and checkpoint must be distinct.')
        if Path(args.output).exists() and not Path(args.checkpoint).exists():
            raise ValueError('Existing report requires its matching checkpoint; refusing overwrite.')
    except (ValueError, KeyError, OSError):
        print('Explicit isolated PG55432 manifest/credentials required; no ERP fallback.', file=sys.stderr)
        return 2
    from run_base_tests import _child_environment
    temporary = mkdtemp(prefix='bab-vdos-rag04-quality-')
    owned_temporary = Path(temporary).resolve(strict=True)
    completed_safely = False
    try:
        environment = _child_environment(temporary)
        environment.update(urls, DATABASE_URL=urls['TEST_DATABASE_URL'],
            TEST_PG_MANIFEST=str(Path(os.environ['TEST_PG_MANIFEST']).resolve()))
        bootstrap = "import runpy,json,sys; m=runpy.run_path(sys.argv[1]); raise SystemExit(m['run_child'](json.loads(sys.argv[2])))"
        result = subprocess.run([sys.executable, '-B', '-c', bootstrap, str(Path(__file__).resolve()), json.dumps(vars(args))],
            cwd=temporary, env=environment, check=False)
        completed_safely = result.returncode == 0
        return result.returncode
    finally:
        if completed_safely:
            target = Path(temporary).resolve(strict=True)
            if target != owned_temporary or not target.name.startswith('bab-vdos-rag04-quality-') or target.is_symlink():
                raise RuntimeError('Owned temporary directory identity changed; refusing recursive cleanup.')
            shutil.rmtree(target)
        else:
            print('Owned isolated artifacts preserved after unsuccessful execution; reconcile inference before cleanup.', file=sys.stderr)


if __name__ == '__main__':
    raise SystemExit(main())
