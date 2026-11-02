"""Disposable extraction process; no ERP configuration, credentials or database.

The parent passes configuration over stdin and assigns a Windows Job Object.
Only stable reason codes and bounded progress events leave this process.
"""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import unicodedata
import zipfile


class ExtractionError(Exception):
    pass


def load_validator():
    source = Path(__file__).with_name('validate_leny_document.py')
    spec = importlib.util.spec_from_file_location('leny_disposable_validator', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize(value):
    return unicodedata.normalize('NFC', value.replace('\r\n', '\n').replace('\r', '\n').replace('\x00', ''))


class Extractor:
    def __init__(self, config, validator):
        self.config = config
        self.validator = validator
        self.path = Path(config['path'])
        self.work = Path(config['work_dir'])
        self.limits = config['limits']
        self.rag = config['rag']
        self.units = []
        self.text_bytes = 0
        self.coverage = {'pages': 0, 'text_pages': 0, 'ocr_pages': 0, 'blank_pages': 0,
                         'paragraphs': 0, 'tables': 0, 'warnings': [], 'complete': False}

    def budget(self):
        if sum(item.stat().st_size for item in self.work.rglob('*') if item.is_file()) > self.rag['temp_bytes']:
            raise ExtractionError('RAG_TEMP_LIMIT')

    def add(self, value, kind, locator):
        value = normalize(value)
        if not value.strip():
            return
        self.text_bytes += len(value.encode('utf-8'))
        if self.text_bytes > self.rag['max_text_bytes'] or len(self.units) >= 10000:
            raise ExtractionError('RAG_TEXT_LIMIT')
        self.units.append({'text': value, 'source_type': kind, 'locator': locator})

    def emit(self, stage, current, total):
        print(json.dumps({'stage': stage, 'current': current, 'total': total}), flush=True)

    def ocr_tools(self):
        executable, data = Path(self.config['tesseract']), Path(self.config['tessdata'])
        if not executable.is_file() or not data.is_dir() or any(not (data / (language + '.traineddata')).is_file() for language in ('spa', 'eng', 'osd')):
            raise ExtractionError('RAG_OCR_UNAVAILABLE')
        return executable, data

    def ocr(self, image_path, locator):
        executable, data = self.ocr_tools()
        deadline = time.monotonic() + self.rag['ocr_seconds']
        prefix = [str(executable), str(image_path), 'stdout', '--tessdata-dir', str(data)]
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        try:
            # Orientation detection is advisory. Sparse pages legitimately have
            # too few characters for OSD; failure never means OCR succeeded.
            orientation = subprocess.run(prefix + ['-l', 'osd', '--psm', '0'], stdout=subprocess.PIPE,
                                         stderr=subprocess.DEVNULL, timeout=max(0.1, min(10, deadline - time.monotonic())),
                                         creationflags=flags)
            if len(orientation.stdout) > 8192:
                raise ExtractionError('RAG_OCR_FAILED')
            info = orientation.stdout.decode('utf-8', errors='replace')
            angle = re.search(r'^Rotate: (0|90|180|270)$', info, re.MULTILINE)
            confidence = re.search(r'^Orientation confidence: ([0-9.]+)$', info, re.MULTILINE)
            if orientation.returncode == 0 and angle and confidence and float(confidence.group(1)) >= 5:
                degrees = int(angle.group(1))
                locator['orientation_degrees'] = degrees
                if degrees:
                    import pyvips
                    image = pyvips.Image.new_from_file(str(image_path), access='sequential')
                    rotated = self.work / 'oriented.png'
                    image.rot({90: 'd90', 180: 'd180', 270: 'd270'}[degrees]).pngsave(str(rotated), keep=0)
                    image_path = rotated
            output = self.work / 'ocr.tsv'
            with output.open('wb') as handle:
                result = subprocess.run([str(executable), str(image_path), 'stdout', '--tessdata-dir', str(data),
                                         '-l', 'spa+eng', '--psm', '3', '-c', 'tessedit_create_tsv=1'], stdout=handle,
                                        stderr=subprocess.DEVNULL, timeout=max(0.1, deadline - time.monotonic()), creationflags=flags)
            if result.returncode or output.stat().st_size > 8 * 1024**2:
                raise ExtractionError('RAG_OCR_FAILED')
            self.budget()
            lines, current, words, confidences = [], None, [], []
            with output.open(encoding='utf-8', newline='') as handle:
                for row in csv.DictReader(handle, delimiter='\t', quoting=csv.QUOTE_NONE):
                    if row.get('level') != '5':
                        continue
                    word = row.get('text', '').strip()
                    if not word:
                        continue
                    key = (row.get('block_num'), row.get('par_num'), row.get('line_num'))
                    if current is not None and key != current:
                        lines.append(' '.join(words))
                        words = []
                    current = key
                    words.append(word)
                    try:
                        confidence = float(row.get('conf', '-1'))
                        if 0 <= confidence <= 100:
                            confidences.append(confidence)
                    except ValueError:
                        pass
                if words:
                    lines.append(' '.join(words))
            if not lines:
                # A nonblank raster without recognized words is not reported as
                # complete, preventing accidental validation of a scanned page.
                raise ExtractionError('RAG_OCR_FAILED')
            average = round(sum(confidences) / len(confidences), 2) if confidences else None
            locator['ocr_confidence'] = average
            if average is None or average < 50:
                self.coverage['warnings'].append({'code': 'OCR_LOW_CONFIDENCE', 'locator': dict(locator)})
            return '\n'.join(lines)
        except subprocess.TimeoutExpired:
            raise ExtractionError('RAG_OCR_TIMEOUT') from None
        except OSError:
            raise ExtractionError('RAG_OCR_UNAVAILABLE') from None
        finally:
            for name in ('ocr.tsv', 'oriented.png'):
                (self.work / name).unlink(missing_ok=True)

    def raster_ocr(self, image, locator, kind):
        if image.width * image.height > self.rag['render_pixels']:
            raise ExtractionError('RAG_RENDER_LIMIT')
        if image.bands > 1:
            image = image.colourspace('b-w')
        # A sequential decoder cannot be evaluated repeatedly by avg/deviate
        # and then pngsave. Materialize the already pixel-bounded grayscale.
        image = image.copy_memory()
        # A near-white uniform page can be accounted for without inventing text.
        if image.avg() > 245 and image.deviate() < 2:
            self.coverage['blank_pages'] += 1
            return
        if self.coverage['ocr_pages'] >= self.rag['ocr_pages']:
            raise ExtractionError('RAG_OCR_PAGE_LIMIT')
        raster = self.work / 'page.png'
        image.pngsave(str(raster), keep=0)
        self.budget()
        # The number of pages requiring OCR is not yet known in a mixed PDF.
        self.emit('ocr', self.coverage['ocr_pages'], 0)
        try:
            text = self.ocr(raster, locator)
            self.add(text, kind, locator)
            self.coverage['ocr_pages'] += 1
            self.emit('ocr', self.coverage['ocr_pages'], 0)
        finally:
            raster.unlink(missing_ok=True)

    def pdf(self):
        from pypdf import PdfReader, apply_configuration
        import pypdfium2 as pdfium
        import pyvips
        metadata = self.validator.validate_pdf(self.path, self.limits)
        self.coverage['pages'] = metadata['pages']
        with apply_configuration(maximum_declared_stream_length=16 * 1024**2):
            reader = PdfReader(self.path, strict=True)
            document = pdfium.PdfDocument(str(self.path))
            try:
                for index, source in enumerate(reader.pages):
                    self.emit('extraction', index, len(reader.pages))
                    text = normalize(source.extract_text() or '')
                    # Short valid headings/numbers are retained, but too little
                    # text for a page may be merely a scanner footer: OCR it.
                    if len(''.join(text.split())) >= 20:
                        self.add(text, 'PDF_TEXT', {'page': index + 1})
                        self.coverage['text_pages'] += 1
                        continue
                    page = document[index]
                    try:
                        scale = self.rag['ocr_dpi'] / 72
                        width, height = page.get_size()
                        if int(width * scale + 1) * int(height * scale + 1) > self.rag['render_pixels']:
                            raise ExtractionError('RAG_RENDER_LIMIT')
                        bitmap = page.render(scale=scale, grayscale=True, may_draw_forms=False)
                        try:
                            pixels = bitmap.to_numpy()
                            image = pyvips.Image.new_from_memory(pixels.tobytes(), bitmap.width, bitmap.height, 1, 'uchar')
                            self.raster_ocr(image, {'page': index + 1}, 'PDF_OCR')
                        finally:
                            bitmap.close()
                    finally:
                        page.close()
                    self.budget()
            finally:
                document.close()
        self.emit('extraction', self.coverage['pages'], self.coverage['pages'])

    def docx(self):
        from defusedxml import ElementTree as ET
        preview = self.work / 'validation-preview.json'
        try:
            # Full ZIP CRC, expansion, relationship and active-content checking.
            # Its intentionally bounded preview is never used as extraction.
            self.validator.validate_docx(self.path, preview, self.limits)
        finally:
            preview.unlink(missing_ok=True)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        w = '{' + ns['w'] + '}'
        with zipfile.ZipFile(self.path) as archive:
            document = ET.fromstring(archive.read('word/document.xml'), forbid_dtd=True, forbid_entities=True, forbid_external=True)
        body = document.find('w:body', ns)

        def content(node):
            return ''.join(item.text or '' if item.tag == w + 't' else '\t' if item.tag == w + 'tab' else '\n'
                           for item in node.iter() if item.tag in {w + 't', w + 'tab', w + 'br', w + 'cr'})

        table_number = paragraph_number = 0
        for index, child in enumerate(body):
            self.emit('extraction', index, len(body))
            if child.tag == w + 'p':
                paragraph_number += 1
                locator = {'paragraph': paragraph_number, 'block': index}
                style = child.find('w:pPr/w:pStyle', ns)
                if style is not None and style.attrib.get(w + 'val'):
                    locator['style'] = style.attrib[w + 'val'][:128]
                self.add(content(child), 'DOCX_PARAGRAPH', locator)
            elif child.tag == w + 'tbl':
                table_number += 1
                header = None
                for row_number, row in enumerate(child.findall('w:tr', ns), 1):
                    value = '\t|\t'.join(content(cell) for cell in row.findall('w:tc', ns))
                    locator = {'table': table_number, 'row': row_number, 'block': index}
                    if row.find('w:trPr/w:tblHeader', ns) is not None:
                        header = (value, row_number)
                    elif header and len(header[0]) + len(value) + 1 <= 1600 and len((header[0] + '\n' + value).encode('utf-8')) <= 3072:
                        value = header[0] + '\n' + value
                        locator['header_row'] = header[1]
                    self.add(value, 'DOCX_TABLE', locator)
        self.coverage['paragraphs'], self.coverage['tables'] = paragraph_number, table_number
        if document.find('.//w:drawing', ns) is not None or document.find('.//w:pict', ns) is not None:
            self.coverage['warnings'].append({'code': 'DOCX_EMBEDDED_IMAGES_NOT_OCR'})
        self.emit('extraction', len(body), len(body))

    def image(self):
        import pyvips
        preview = self.work / 'validation-preview.png'
        try:
            self.validator.validate_image(self.path, preview, self.limits, self.path.suffix.lower())
        finally:
            preview.unlink(missing_ok=True)
        image = pyvips.Image.new_from_file(str(self.path), access='sequential', fail_on='warning').autorot()
        if image.hasalpha():
            image = image.flatten(background=[255])
        self.coverage['pages'] = 1
        self.raster_ocr(image, {'image': 1, 'orientation': 'EXIF_AUTOROT'}, 'IMAGE_OCR')
        self.emit('extraction', 1, 1)

    def run(self):
        import pyvips
        pyvips.cache_set_max(0)
        pyvips.cache_set_max_mem(32 * 1024**2)
        suffix = self.path.suffix.lower()
        if suffix == '.pdf':
            self.pdf()
        elif suffix == '.docx':
            self.docx()
        elif suffix in {'.png', '.jpg', '.jpeg'}:
            self.image()
        else:
            raise ExtractionError('RAG_INVALID_DOCUMENT')
        if not self.units:
            raise ExtractionError('RAG_NO_TEXT')
        self.budget()
        self.coverage['complete'] = True
        self.coverage['text_bytes'] = self.text_bytes
        return {'units': self.units, 'coverage': self.coverage}


def main():
    config = json.loads(sys.stdin.read(16384))
    validator = load_validator()
    validator.attach_parser_job(config['job_name'])
    target = Path(config['result'])
    try:
        result = Extractor(config, validator).run()
    except ExtractionError as error:
        result = {'error': str(error)}
    except ModuleNotFoundError:
        result = {'error': 'RAG_EXTRACTION_UNAVAILABLE'}
    except Exception:
        result = {'error': 'RAG_INVALID_DOCUMENT'}
    target.write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
    return 1 if 'error' in result else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        # Never emit parser exceptions, source text, file paths or credentials.
        sys.exit(1)
