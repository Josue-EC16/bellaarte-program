"""Bounded, disposable parser process. Does not import ERP settings or database."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import sys
import zipfile


def attach_parser_job(name):
    """The Windows venv redirector may have spawned us before job assignment.

    Join/verify the parent's named job before importing any untrusted parser.
    This closes that redirector race without relying on private thread handles.
    """
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenJobObjectW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.OpenJobObjectW.restype = wintypes.HANDLE
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.IsProcessInJob.argtypes = [wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenJobObjectW(0x5, False, name)
    if not handle:
        raise ValueError('job')
    try:
        included = wintypes.BOOL()
        current = kernel.GetCurrentProcess()
        if not kernel.IsProcessInJob(current, handle, ctypes.byref(included)):
            raise ValueError('job')
        if not included.value and not kernel.AssignProcessToJobObject(handle, current):
            raise ValueError('job')
    finally:
        kernel.CloseHandle(handle)


def validate_pdf(path, limits):
    from pypdf import PdfReader, apply_configuration
    with apply_configuration(maximum_declared_stream_length=16 * 1024 * 1024):
        reader = PdfReader(path, strict=True)
        if reader.is_encrypted:
            raise ValueError('encrypted')
        count = len(reader.pages)
        if not 1 <= count <= limits['pdf_pages']:
            raise ValueError('pages')
        seen = set()
        nodes = 0

        def walk(value, depth=0):
            nonlocal nodes
            if depth > 64:
                raise ValueError('depth')
            if hasattr(value, 'get_object'):
                value = value.get_object()
            identity = id(value)
            if identity in seen:
                return
            seen.add(identity)
            nodes += 1
            if nodes > 50000:
                raise ValueError('objects')
            if isinstance(value, dict):
                if any(key in value for key in ('/JS', '/JavaScript', '/OpenAction', '/AA', '/EmbeddedFiles', '/XFA', '/RichMediaContent')):
                    raise ValueError('active')
                if str(value.get('/S', '')) in {'/JavaScript', '/Launch', '/GoToR', '/SubmitForm', '/ImportData', '/Rendition'}:
                    raise ValueError('active')
                if value.get('/Type') in {'/EmbeddedFile', '/Filespec'}:
                    raise ValueError('embedded')
                for item in value.values():
                    walk(item, depth + 1)
            elif isinstance(value, (tuple, list)):
                for item in value:
                    walk(item, depth + 1)
        walk(reader.trailer)
        return {'media_type': 'application/pdf', 'pages': count, 'preview_type': None}


def validate_docx(path, preview_path, limits):
    from defusedxml import ElementTree as ET
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if not entries or len(entries) > limits['zip_entries']:
            raise ValueError('entries')
        names = [item.filename for item in entries]
        if len(names) != len(set(names)) or not {'[Content_Types].xml', '_rels/.rels', 'word/document.xml'} <= set(names):
            raise ValueError('structure')
        total = 0
        document = None
        valid_main_type = False
        valid_office_relationship = False
        for entry in entries:
            name = PurePosixPath(entry.filename)
            if (name.is_absolute() or '..' in name.parts or '\\' in entry.filename or ':' in entry.filename
                    or entry.flag_bits & 1 or (entry.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError('path')
            if entry.file_size > limits['zip_entry_bytes'] or entry.file_size > max(entry.compress_size, 1) * limits['zip_ratio']:
                raise ValueError('expansion')
            total += entry.file_size
            if total > limits['zip_bytes']:
                raise ValueError('expansion')
            lower = entry.filename.lower()
            if any(word in lower for word in ('vbaproject', 'activex', 'embeddings/', 'customui/')):
                raise ValueError('active')
            # Read every entry: validates CRC and rejects truncated/inconsistent ZIPs.
            with archive.open(entry) as source:
                data = source.read(limits['zip_entry_bytes'] + 1)
            if len(data) != entry.file_size:
                raise ValueError('expansion')
            if lower.endswith(('.xml', '.rels')):
                tree = ET.fromstring(data, forbid_dtd=True, forbid_entities=True, forbid_external=True)
                stack = [(tree, 0)]
                visited = 0
                while stack:
                    node, depth = stack.pop()
                    visited += 1
                    if depth > 128 or visited > 100000:
                        raise ValueError('xml_complexity')
                    if node.attrib.get('TargetMode', '').lower() == 'external':
                        raise ValueError('external_relationship')
                    if 'macroenabled' in node.attrib.get('ContentType', '').lower():
                        raise ValueError('macro')
                    stack.extend((child, depth + 1) for child in node)
                if entry.filename == 'word/document.xml':
                    document = tree
                elif entry.filename == '[Content_Types].xml':
                    namespace = 'http://schemas.openxmlformats.org/package/2006/content-types'
                    if tree.tag != '{' + namespace + '}Types':
                        raise ValueError('content_types')
                    valid_main_type = any(node.attrib.get('PartName') == '/word/document.xml' and node.attrib.get('ContentType') == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml' for node in tree)
                elif entry.filename == '_rels/.rels':
                    namespace = 'http://schemas.openxmlformats.org/package/2006/relationships'
                    if tree.tag != '{' + namespace + '}Relationships':
                        raise ValueError('relationships')
                    valid_office_relationship = any(node.attrib.get('Type') == 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument' and node.attrib.get('Target') in {'word/document.xml','/word/document.xml'} for node in tree)
        if not valid_main_type or not valid_office_relationship or document is None or document.tag != '{' + ns['w'] + '}document':
            raise ValueError('document')
        blocks, chars, cells, truncated = [], 0, 0, False

        def text(node):
            return ''.join(item.text or '' for item in node.findall('.//w:t', ns))

        body = document.find('w:body', ns)
        if body is None:
            raise ValueError('body')
        for child in body:
            if len(blocks) >= 5000:
                truncated = True
                break
            if child.tag == '{' + ns['w'] + '}p':
                value = text(child)
                if chars + len(value) > 100000:
                    truncated = True
                    break
                blocks.append({'type': 'paragraph', 'text': value})
                chars += len(value)
            elif child.tag == '{' + ns['w'] + '}tbl':
                rows = [[text(cell) for cell in row.findall('w:tc', ns)] for row in child.findall('w:tr', ns)]
                size = sum(len(cell) for row in rows for cell in row)
                count = sum(len(row) for row in rows)
                if chars + size > 100000 or cells + count > 2000:
                    truncated = True
                    break
                chars += size
                cells += count
                blocks.append({'type': 'table', 'rows': rows})
        preview_path.write_text(json.dumps({'kind': 'docx', 'blocks': blocks, 'truncated': truncated}, ensure_ascii=True), encoding='utf-8')
        return {'media_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'preview_type': 'application/json'}


def validate_image(path, preview_path, limits, extension):
    import pyvips
    pyvips.cache_set_max_mem(32 * 1024 * 1024)
    pyvips.cache_set_max(0)
    loader = pyvips.Image.pngload if extension == '.png' else pyvips.Image.jpegload
    image = loader(str(path), access='sequential', fail_on='warning', unlimited=False)
    if image.width * image.height > limits['max_pixels'] or image.width < 1 or image.height < 1:
        raise ValueError('pixels')
    # Force the entire decoder, rather than trusting a lazy header/thumbnail read.
    image.avg()
    image = loader(str(path), access='sequential', fail_on='warning', unlimited=False)
    scale = min(1.0, 2048 / max(image.width, image.height))
    if scale < 1:
        image = image.resize(scale)
    image.pngsave(str(preview_path), keep=0)
    return {'media_type': 'image/png' if extension == '.png' else 'image/jpeg', 'preview_type': 'image/png'}


def main():
    config = json.loads(sys.stdin.read(16384))
    attach_parser_job(config['job_name'])
    path, preview = Path(config['path']), Path(config['preview'])
    extension, limits = config['extension'], config['limits']
    with path.open('rb') as handle:
        magic = handle.read(8)
    if extension == '.pdf' and magic.startswith(b'%PDF-'):
        result = validate_pdf(path, limits)
    elif extension == '.docx' and magic.startswith(b'PK\x03\x04'):
        result = validate_docx(path, preview, limits)
    elif extension in {'.jpg', '.jpeg', '.png'} and (magic.startswith(b'\xff\xd8\xff') if extension != '.png' else magic == b'\x89PNG\r\n\x1a\n'):
        result = validate_image(path, preview, limits, extension)
    else:
        raise ValueError('format')
    if preview.exists() and preview.stat().st_size > 16 * 1024 * 1024:
        raise ValueError('preview_limit')
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except ModuleNotFoundError:
        print('{"error":"DOCUMENT_VALIDATOR_MISSING"}')
        sys.exit(2)
    except Exception:
        # Parser exceptions may contain content, paths or XML. Never forward them.
        print('{"error":"DOCUMENT_INVALID_FILE"}')
        sys.exit(1)
