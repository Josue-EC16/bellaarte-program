"""Prepare pinned local native tools; verify pgvector in a NEW isolated cluster.

Requires explicit operator authorization. Never starts/stops the ERP database.
--install-pgvector adds the verified extension files to PG17; no SQL on business DB.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import secrets
import shutil
import socket
import subprocess
import sys
from urllib.request import Request, urlopen
from uuid import uuid4
import zipfile

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from app.services.leny_document_storage import protect_directory, _check_path

PG = Path(r'C:\laragon\bin\postgresql\postgresql-17.9-1')
ROOT = Path(os.environ['LOCALAPPDATA']) / 'BAB_VDOS' / 'leny-rag-runtime'
TESS_URL = 'https://github.com/tesseract-ocr/tesseract/releases/download/5.5.3/tesseract-ocr-w64-setup-5.5.3.20260724.exe'
TESS_SHA = 'bee9e3434bd94fd65387d9be28cd467a41f61b1275383b55b0f59a1331270ae4'


def fetch(url, destination, expected=None):
    if not destination.exists():
        request = Request(url, headers={'User-Agent': 'BAB-VDOS-local-runtime'})
        partial = destination.with_name(destination.name + '.part-' + uuid4().hex)
        try:
            with urlopen(request, timeout=60) as source, partial.open('xb') as target:
                count = 0
                while chunk := source.read(1024 * 1024):
                    count += len(chunk)
                    if count > 150 * 1024**2:
                        raise RuntimeError('Native artifact exceeds download limit.')
                    target.write(chunk)
            if expected and hashlib.sha256(partial.read_bytes()).hexdigest() != expected:
                raise RuntimeError('Native artifact checksum mismatch.')
            partial.rename(destination)
        finally:
            partial.unlink(missing_ok=True)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    if expected and digest != expected:
        raise RuntimeError('Native artifact checksum mismatch.')
    return digest


def remote_json(url):
    with urlopen(Request(url, headers={'User-Agent': 'BAB-VDOS-local-runtime'}), timeout=30) as response:
        return json.load(response)


def run(arguments, *, env=None, cwd=None, timeout=120, log='native.log'):
    with (ROOT / log).open('ab') as errors:
        subprocess.run([str(a) for a in arguments], check=True, timeout=timeout,
                       env=env, cwd=cwd, stdout=errors, stderr=errors,
                       creationflags=subprocess.CREATE_NO_WINDOW)


def tool_output(arguments):
    result = subprocess.run([str(a) for a in arguments], check=True, timeout=30,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    return result.stdout.decode('utf-8', errors='replace').strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-pgvector', action='store_true')
    args = parser.parse_args()
    if os.name != 'nt' or not PG.joinpath('bin/pg_config.exe').is_file():
        raise RuntimeError('Reviewed Windows PG17 installation required.')
    _check_path(ROOT)
    if ROOT.exists() and not (ROOT / '.leny-rag-runtime').exists() and any(ROOT.iterdir()):
        raise RuntimeError('Refusing an existing unowned runtime directory.')
    ROOT.mkdir(parents=True, exist_ok=True)
    protect_directory(ROOT)
    (ROOT / '.leny-rag-runtime').touch()
    downloads = ROOT / 'downloads'
    downloads.mkdir(exist_ok=True)
    manifest_path = ROOT / 'runtime.json'
    report = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    def record():
        manifest_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    assert tool_output([PG / 'bin/pg_config.exe', '--version']) == 'PostgreSQL 17.9'

    clone = ROOT / 'postgresql-17.9'
    if not clone.exists():
        clone.mkdir()
        for name in ('bin', 'include', 'lib', 'share'):
            shutil.copytree(PG / name, clone / name)
    source_dir = ROOT / 'pgvector-source'
    if not source_dir.exists():
        ref = remote_json('https://api.github.com/repos/pgvector/pgvector/git/ref/tags/v0.8.7')['object']
        if ref['type'] == 'tag':
            ref = remote_json(ref['url'])['object']
        if ref['type'] != 'commit':
            raise RuntimeError('Unexpected source reference.')
        commit = ref['sha']
        source_zip = downloads / ('pgvector-' + commit + '.zip')
        digest = fetch('https://codeload.github.com/pgvector/pgvector/zip/' + commit, source_zip)
        with zipfile.ZipFile(source_zip) as archive:
            for item in archive.infolist():
                parts = PurePosixPath(item.filename)
                if parts.is_absolute() or '..' in parts.parts or '\\' in item.filename or item.file_size > 16 * 1024**2:
                    raise RuntimeError('Unsafe native source archive.')
            archive.extractall(ROOT / 'source-unpack')
        unpacked = ROOT / 'source-unpack' / ('pgvector-' + commit)
        unpacked.rename(source_dir)
        report['pgvector_source'] = {'version': '0.8.7', 'commit': commit, 'archive_sha256': digest}
        record()
    if not clone.joinpath('lib/vector.dll').exists():
        vcvars = Path(r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat')
        if not vcvars.is_file():
            raise RuntimeError('Reviewed MSVC2022 x64 compiler unavailable.')
        command = 'cmd.exe /d /s /c "call "' + str(vcvars) + '" >nul && set"'
        captured = subprocess.run(command, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, check=True, timeout=60,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
        environment = {key.upper(): value for key, value in os.environ.items()}
        for line in captured.stdout.decode('mbcs', errors='replace').splitlines():
            if '=' in line and not line.startswith('='):
                key, value = line.split('=', 1)
                environment[key.upper()] = value
        environment['PGROOT'] = str(clone)
        nmake = shutil.which('nmake.exe', path=environment.get('PATH', ''))
        if not nmake:
            raise RuntimeError('MSVC2022 nmake not found in compiler environment.')
        run([nmake, '/F', 'Makefile.win'], env=environment, cwd=source_dir, log='pgvector-build.log')
        run([nmake, '/F', 'Makefile.win', 'install'], env=environment, cwd=source_dir, log='pgvector-build.log')

    if not report.get('pgvector_isolated_verified'):
        data = ROOT / ('verification-' + uuid4().hex)
        password = secrets.token_hex(24)
        secret = ROOT / ('.init-' + uuid4().hex)
        secret.write_text(password, encoding='ascii')
        port = 55433
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', port)) == 0:
                raise RuntimeError('Isolated verification port occupied; nothing stopped.')
        started = False
        environment = {key: value for key, value in os.environ.items() if not key.upper().startswith('PG')}
        environment.update(PGPASSWORD=password, PGCONNECT_TIMEOUT='5')
        try:
            run([clone / 'bin/initdb.exe', '-D', data, '-U', 'leny_vector_check', '-A', 'scram-sha-256',
                 '--encoding=UTF8', '--locale=C', '--pwfile', secret])
            secret.unlink(missing_ok=True)
            with (data / 'postgresql.conf').open('a', encoding='ascii') as config:
                config.write("\nlisten_addresses='127.0.0.1'\nport=55433\n")
            run([clone / 'bin/pg_ctl.exe', '-D', data, '-l', ROOT / 'vector-check-server.log', '-w', '-t', '30', 'start'])
            started = True
            import psycopg2
            from contextlib import closing
            with closing(psycopg2.connect(host='127.0.0.1', port=port, user='leny_vector_check', password=password, dbname='postgres')) as db, db:
                with db.cursor() as cursor:
                    cursor.execute('CREATE SCHEMA leny')
                    cursor.execute("CREATE EXTENSION vector WITH SCHEMA leny VERSION '0.8.7'")
                    cursor.execute('CREATE TABLE leny.vector_check(id integer PRIMARY KEY, value leny.vector(1024))')
                    one = '[' + ','.join(['1'] + ['0'] * 1023) + ']'
                    two = '[' + ','.join(['0', '1'] + ['0'] * 1022) + ']'
                    cursor.execute('INSERT INTO leny.vector_check VALUES (1,%s),(2,%s)', (one, two))
                    cursor.execute('SELECT id,leny.vector_dims(value), value OPERATOR(leny.<=>) %s::leny.vector FROM leny.vector_check ORDER BY id', (one,))
                    rows = cursor.fetchall()
                    assert rows == [(1, 1024, 0.0), (2, 1024, 1.0)]
            dump = ROOT / 'vector-verification.dump'
            run([clone / 'bin/pg_dump.exe', '-h', '127.0.0.1', '-p', str(port), '-U', 'leny_vector_check',
                 '-d', 'postgres', '-Fc', '-f', dump], env=environment)
            run([clone / 'bin/createdb.exe', '-h', '127.0.0.1', '-p', str(port), '-U', 'leny_vector_check', 'restored_vector'], env=environment)
            run([clone / 'bin/pg_restore.exe', '-h', '127.0.0.1', '-p', str(port), '-U', 'leny_vector_check',
                 '-d', 'restored_vector', '--exit-on-error', dump], env=environment)
            with closing(psycopg2.connect(host='127.0.0.1', port=port, user='leny_vector_check', password=password, dbname='restored_vector')) as db, db:
                with db.cursor() as cursor:
                    cursor.execute('SELECT count(*), min(leny.vector_dims(value)) FROM leny.vector_check')
                    assert cursor.fetchone() == (2, 1024)
            report['pgvector_isolated_verified'] = True
            report['pgvector_backup_restore_verified'] = True
            record()
        finally:
            secret.unlink(missing_ok=True)
            if started:
                run([clone / 'bin/pg_ctl.exe', '-D', data, '-w', '-t', '30', '-m', 'fast', 'stop'])

    tess = ROOT / 'tesseract'
    if not (tess / 'tesseract.exe').is_file():
        installer = downloads / 'tesseract-5.5.3.exe'
        fetch(TESS_URL, installer, TESS_SHA)
        # The vendor installer requires elevation even for a private target.
        # Extract only its native payload using the already-installed 7-Zip;
        # no installer scripts, registry changes or Windows service are needed.
        seven_zip = Path(r'C:\Program Files\7-Zip\7z.exe')
        if not seven_zip.is_file():
            raise RuntimeError('Installed 7-Zip required to prepare private OCR without global installation.')
        run([seven_zip, 'x', installer, '-o' + str(tess), '-y'], timeout=120, log='tesseract-install.log')
    output = tool_output([tess / 'tesseract.exe', '--version'])
    if 'tesseract v5.5.3' not in output and 'tesseract 5.5.3' not in output:
        raise RuntimeError('Unexpected Tesseract version.')
    language_commit = report.get('tessdata_commit') or remote_json('https://api.github.com/repos/tesseract-ocr/tessdata_fast/commits/main')['sha']
    (tess / 'tessdata').mkdir(exist_ok=True)
    language_files = {}
    for language in ('spa', 'eng', 'osd'):
        destination = tess / 'tessdata' / (language + '.traineddata')
        # Replace installer-supplied language data only by a separate pinned private directory.
        pinned = ROOT / 'tessdata'
        pinned.mkdir(exist_ok=True)
        destination = pinned / (language + '.traineddata')
        language_files[language] = fetch('https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/' + language_commit + '/' + language + '.traineddata', destination,
                                         report.get('tessdata_files', {}).get(language))
    languages = tool_output([tess / 'tesseract.exe', '--tessdata-dir', ROOT / 'tessdata', '--list-langs'])
    if not all(language in languages.splitlines() for language in ('spa', 'eng', 'osd')):
        raise RuntimeError('Required OCR languages unavailable.')
    report.update(tesseract_version='5.5.3', tesseract_executable=str(tess / 'tesseract.exe'),
                  tessdata_directory=str(ROOT / 'tessdata'), tessdata_commit=language_commit, tessdata_files=language_files)
    if args.install_pgvector:
        files = [clone / 'lib/vector.dll', clone / 'share/extension/vector.control', *sorted((clone / 'share/extension').glob('vector--*.sql'))]
        installed = {}
        for source in files:
            relative = source.relative_to(clone)
            destination = PG / relative
            _check_path(destination)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            if destination.exists():
                if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
                    raise RuntimeError('Existing native file differs; refusing replacement.')
            else:
                with source.open('rb') as origin, destination.open('xb') as target:
                    shutil.copyfileobj(origin, target)
            installed[relative.as_posix()] = digest
        report['pgvector_shared_files'] = installed
    record()
    print(json.dumps({'pgvector_version':'0.8.7', 'isolated_verified':report['pgvector_isolated_verified'],
                      'backup_restore_verified':report['pgvector_backup_restore_verified'], 'tesseract_version':'5.5.3',
                      'languages':['spa','eng','osd'], 'shared_pg_files_installed':bool(report.get('pgvector_shared_files'))}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Runtime preparation stopped: ' + (str(error) if type(error) is RuntimeError else type(error).__name__), file=sys.stderr)
        raise SystemExit(1) from None
