"""Real SQL tests on the existing guarded synthetic PostgreSQL cluster only."""
from uuid import uuid4

from sqlalchemy import text

import test_leny_rag_chat as chat
import test_leny_rag_service as rag
from test_leny_rag_service import rag_context


def test_section_context_and_source_overview_keep_acl_and_final_fragment(rag_context, monkeypatch):
    from app.services.leny_rag_chunking import fragment_units
    from app.services.leny_rag_retrieval import RetrievalService
    context = rag_context
    contents = ['Funciones de la modista', 'Revisar las medidas antes del corte.',
                'Preparar las piezas.', 'Funciones de la asesora de moda',
                'Orientar a la clienta.', 'Registrar la elección.', 'Comprobar la entrega.']
    units = [dict(text=value, source_type='DOCX_PARAGRAPH',
                  locator=dict(block=i, paragraph=i+1, **({'style': 'Heading2'} if i in (0, 3) else {})))
             for i, value in enumerate(contents)]
    monkeypatch.setattr(rag, '_fragments', lambda ctx, count=2: fragment_units(units, ctx.service.settings))
    source, claim = chat.prepared(context, rag._worker(context))
    title = 'MANUAL SINTETICO '+uuid4().hex
    with context.cluster.engine.begin() as db:
        db.execute(text('UPDATE leny.documentos SET title=:title WHERE id=:id'), {'title': title, 'id': source[0]})
    chat.publish(context, source, claim)
    config = context.service.settings.model_copy(update=dict(leny_rag_chat_enabled=True, leny_rag_profile='rag4_v1',
        leny_rag_response_mode='controlled-synthesis-v1', leny_rag_section_context=True, leny_rag_source_coverage=True))
    retrieval = RetrievalService(config, context.service.sessions)
    with chat.role(context, 'CAJA') as role:
        with context.cluster.engine.begin() as db:
            db.execute(text('INSERT INTO leny.documento_roles_lectura(document_id,role_id) VALUES(:id,:role)'),
                       {'id': source[0], 'role': role})
        rows = retrieval.search(context.actor, [1.0]+[0.0]*1023, 'responsabilidades de la modista')
        body = next(row for row in rows if row['ordinal'] == 1)
        heading = next(row for row in rows if row['ordinal'] == 0)
        assert body['context_fragment_id'] == heading['fragment_id']
        assert body['locator']['heading'] == contents[0]
        overview = retrieval.search(context.actor, [1.0]+[0.0]*1023, 'Documento '+title+', resume su contenido')
        assert 0 in {row['ordinal'] for row in overview} and 6 in {row['ordinal'] for row in overview}
        assert len(overview) <= 20
        assert {row['document_id'] for row in overview} == {source[0]}
        retrieval.revalidate(context.actor, overview)
        with context.cluster.engine.begin() as db:
            db.execute(text('DELETE FROM leny.documento_roles_lectura WHERE document_id=:id AND role_id=:role'),
                       {'id': source[0], 'role': role})
        assert retrieval.search(context.actor, [1.0]+[0.0]*1023, 'Documento '+title+', resume su contenido') == []


def test_role_outline_stops_at_another_heading_even_for_an_unknown_role(rag_context, monkeypatch):
    from app.services.leny_rag_chunking import fragment_units
    from app.services.leny_rag_retrieval import RetrievalService
    context = rag_context
    contents = ['Funciones de la modista', '• Cortar las piezas según medidas aprobadas.',
                '• Revisar las costuras.', 'Funciones de caja', '• Cobrar el pedido.']
    units = [dict(text=value, source_type='DOCX_PARAGRAPH',
                  locator=dict(block=i, paragraph=i+1, **({'style': 'Heading2'} if i in (0, 3) else {})))
             for i, value in enumerate(contents)]
    monkeypatch.setattr(rag, '_fragments', lambda ctx, count=2: fragment_units(units, ctx.service.settings))
    source, claim = chat.prepared(context, rag._worker(context))
    chat.publish(context, source, claim)
    config = context.service.settings.model_copy(update=dict(leny_rag_chat_enabled=True, leny_rag_profile='rag4_v1',
        leny_rag_response_mode='controlled-synthesis-v1', leny_rag_section_context=True))
    retrieval = RetrievalService(config, context.service.sessions)
    with chat.role(context, 'CAJA') as role:
        with context.cluster.engine.begin() as db:
            db.execute(text('INSERT INTO leny.documento_roles_lectura(document_id,role_id) VALUES(:id,:role)'),
                       {'id': source[0], 'role': role})
        rows = retrieval.search(context.actor, [1.0]+[0.0]*1023, 'responsabilidades de la modista')
        assert rows and {row['ordinal'] for row in rows} <= {0, 1, 2}
        assert any('Cortar' in row['text'] for row in rows)
        assert all('Cobrar' not in row['text'] for row in rows)
