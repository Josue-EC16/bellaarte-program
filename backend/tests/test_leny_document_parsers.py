"""Real decoder functions; subprocess/Job tests run in the explicit parser launcher."""
import io
import json
from pathlib import Path
import runpy
from types import SimpleNamespace
import zipfile

import pytest

PARSER = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/validate_leny_document.py'))
LIMITS = dict(pdf_pages=50, zip_entries=1000, zip_bytes=32*1024**2, zip_entry_bytes=8*1024**2, zip_ratio=100, max_pixels=12_000_000)


def docx_bytes(*, external=False, bomb=False, text='Control de inventarios'):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        archive.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"' + (' TargetMode="External"' if external else '') + '/></Relationships>')
        archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>'+text+'</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Stock</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
        if bomb:
            archive.writestr('word/bomb.xml', 'a' * 200000)
    return output.getvalue()


def test_pdf_real_parser_and_page_limit(tmp_path):
    from pypdf import PdfWriter
    path = tmp_path/'valid.pdf'
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with path.open('wb') as handle:
        writer.write(handle)
    assert PARSER['validate_pdf'](path, LIMITS)['pages'] == 1
    with pytest.raises(ValueError):
        PARSER['validate_pdf'](path, {**LIMITS, 'pdf_pages':0})


def test_pdf_active_content_and_encryption_rejected(tmp_path):
    from pypdf import PdfWriter
    for active in (True, False):
        path = tmp_path/('active.pdf' if active else 'secret.pdf')
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        if active:
            writer.add_js("app.alert('untrusted')")
        else:
            writer.encrypt('synthetic-password')
        with path.open('wb') as handle:
            writer.write(handle)
        with pytest.raises(ValueError):
            PARSER['validate_pdf'](path, LIMITS)


def test_docx_preview_escapes_as_data_and_tables(tmp_path):
    path, preview = tmp_path/'valid.docx', tmp_path/'preview.json'
    path.write_bytes(docx_bytes(text='&lt;script&gt;alert(1)&lt;/script&gt;'))
    assert PARSER['validate_docx'](path, preview, LIMITS)['preview_type'] == 'application/json'
    data = json.loads(preview.read_text())
    assert data['blocks'][0]['text'] == '<script>alert(1)</script>'
    assert data['blocks'][1]['rows'] == [['Stock']]
    assert data['truncated'] is False


def test_docx_preview_limits_empty_paragraphs_without_losing_truncation_signal(tmp_path):
    source = io.BytesIO(docx_bytes())
    path = tmp_path/'many-paragraphs.docx'
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(path,'w') as target:
        for name in original.namelist():
            data = original.read(name)
            if name == 'word/document.xml':
                data = ('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + '<w:p/>'*6000 + '</w:body></w:document>').encode()
            target.writestr(name,data)
    preview=tmp_path/'preview.json'
    PARSER['validate_docx'](path,preview,LIMITS)
    result=json.loads(preview.read_text())
    assert len(result['blocks'])==5000 and result['truncated'] is True
    assert preview.stat().st_size < 1024**2


@pytest.mark.parametrize('options', [{'external':True}, {'bomb':True}])
def test_docx_external_and_compression_bomb_rejected(tmp_path, options):
    path = tmp_path/'unsafe.docx'
    path.write_bytes(docx_bytes(**options))
    with pytest.raises(ValueError):
        PARSER['validate_docx'](path, tmp_path/'preview.json', LIMITS)


def test_docx_entities_and_traversal_rejected(tmp_path):
    for content in (b'<!DOCTYPE x [<!ENTITY e SYSTEM "file:///private">]><x>&e;</x>', b'<x/>'):
        path = tmp_path/'unsafe.docx'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('[Content_Types].xml', content)
            archive.writestr('_rels/.rels', '<x/>')
            archive.writestr('word/document.xml', '<x/>')
            archive.writestr('../escape.xml', '<x/>')
        with pytest.raises(Exception):
            PARSER['validate_docx'](path, tmp_path/'preview.json', LIMITS)


@pytest.mark.parametrize('extension', ['.png','.jpg'])
def test_real_image_decode_preview_and_pixel_limit(tmp_path, extension):
    import pyvips
    path, preview = tmp_path/('valid'+extension), tmp_path/'preview.png'
    image = pyvips.Image.black(32, 24)
    image.write_to_file(str(path))
    result = PARSER['validate_image'](path, preview, LIMITS, extension)
    assert result['preview_type'] == 'image/png' and preview.exists()
    with pytest.raises(ValueError):
        PARSER['validate_image'](path, preview, {**LIMITS,'max_pixels':10}, extension)


def test_bounded_native_process_and_private_storage(tmp_path):
    # Explicit opt-in launcher only; base suite must keep its process guard.
    import os
    if os.environ.get('LENY_PARSER_NATIVE_TESTS') != '1':
        pytest.skip('Native Job Object exercised by check_leny_document_parsers.py')
    from app.services.leny_document_storage import DocumentStorage, DocumentError
    from app.services.leny_document_validation import validate_document
    from pypdf import PdfWriter
    config = SimpleNamespace(leny_documents_root=str(tmp_path/'private'), leny_documents_validation_seconds=30,
                            leny_documents_validation_memory_mb=768, **{'leny_documents_'+key:value for key,value in LIMITS.items()})
    storage = DocumentStorage(config)
    storage.initialize()
    stage = storage.new_stage()
    writer = PdfWriter()
    writer.add_blank_page(width=100,height=100)
    with storage.path(stage).open('wb') as handle:
        writer.write(handle)
    assert validate_document(storage, stage, '.pdf', config)['pages'] == 1
    storage.path(stage).write_bytes(b'not a pdf')
    with pytest.raises(DocumentError):
        validate_document(storage, stage, '.pdf', config)


@pytest.mark.parametrize('key', ['../private','versions/../secret','C:/secret','versions/not-a-uuid.blob','/absolute'])
def test_storage_path_allowlist(tmp_path, key):
    from app.services.leny_document_storage import DocumentStorage, DocumentError
    storage = DocumentStorage(SimpleNamespace(leny_documents_root=str(tmp_path/'private')))
    with pytest.raises(DocumentError):
        storage.path(key)
