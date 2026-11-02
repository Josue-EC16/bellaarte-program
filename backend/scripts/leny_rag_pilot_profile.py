"""Prepare a private, reversible five-variable pilot change; never migrates DB.

Default command inspects configuration only. Activation/rollback require an
explicit CLI confirmation after the owner's separate deployment authorization.
No secrets or environment contents are printed. Services are not restarted.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from uuid import uuid4

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
CHANGES = {'LENY_RAG_PROFILE': 'rag4_v1', 'LENY_RAG_EVIDENCE_MODE': 'adaptive',
           'LENY_RAG_RANKING': 'hybrid', 'LENY_RAG_ADAPTIVE_TOKEN_PROBE': 'true',
           'LENY_TEMPERATURE': '0.0'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def render_environment(data: bytes) -> bytes:
    """Preserve all unrelated bytes, including secrets, BOM and line endings."""
    bom = data.startswith(b'\xef\xbb\xbf')
    text = data.decode('utf-8-sig')
    newline = '\r\n' if '\r\n' in text else '\n'
    result, seen = [], set()
    pattern = re.compile(r'^(\s*(?:export\s+)?)([A-Za-z_][A-Za-z_0-9]*)(\s*=\s*)(.*?)(\r\n|\n|\r|$)$')
    for line in text.splitlines(keepends=True):
        match = pattern.fullmatch(line)
        key = match.group(2).upper() if match else None
        if key not in CHANGES:
            result.append(line)
            continue
        if key in seen:
            raise ValueError('Duplicate pilot environment variable; review before activation')
        seen.add(key)
        comment = re.search(r'(\s+#.*)$', match.group(4))
        result.append(match.group(1)+match.group(2)+match.group(3)+CHANGES[key]
                      +(comment.group(1) if comment else '')+match.group(5))
    if set(CHANGES)-seen:
        if result and not result[-1].endswith(('\r','\n')):
            result[-1] += newline
        result.extend(key+'='+value+newline for key,value in CHANGES.items() if key not in seen)
    return (b'\xef\xbb\xbf' if bom else b'')+''.join(result).encode('utf-8')


def atomic_replace(path: Path, expected_sha256: str, replacement: bytes):
    from app.services.leny_document_storage import _check_path
    _check_path(path)
    if sha(path.read_bytes()) != expected_sha256:
        raise ValueError('Environment changed since preparation; no overwrite performed')
    temporary = path.with_name('.env.pilot-'+uuid4().hex+'.tmp')
    try:
        with temporary.open('xb') as handle:
            # The empty file may inherit directory permissions. Copy the source
            # DACL before writing any credential and retain it after os.replace.
            if os.name == 'nt':
                copy_windows_dacl(path,temporary)
            handle.write(replacement); handle.flush(); os.fsync(handle.fileno())
        # Recheck immediately before replacing; no unrelated config is merged.
        if sha(path.read_bytes()) != expected_sha256:
            raise ValueError('Environment changed during preparation')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def copy_windows_dacl(source: Path, target: Path):
    """Copy only DACL/protection; no privilege escalation or global ACL changes."""
    import ctypes
    from ctypes import wintypes
    api = ctypes.WinDLL('advapi32',use_last_error=True)
    api.GetFileSecurityW.argtypes = [wintypes.LPCWSTR,wintypes.DWORD,ctypes.c_void_p,
                                    wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    api.GetFileSecurityW.restype = wintypes.BOOL
    api.GetSecurityDescriptorControl.argtypes = [ctypes.c_void_p,ctypes.POINTER(wintypes.WORD),
                                                ctypes.POINTER(wintypes.DWORD)]
    api.GetSecurityDescriptorControl.restype = wintypes.BOOL
    api.SetFileSecurityW.argtypes = [wintypes.LPCWSTR,wintypes.DWORD,ctypes.c_void_p]
    api.SetFileSecurityW.restype = wintypes.BOOL
    size = wintypes.DWORD()
    api.GetFileSecurityW(str(source),4,None,0,ctypes.byref(size))
    if not size.value:
        raise OSError('Unable to read configuration DACL')
    descriptor = ctypes.create_string_buffer(size.value)
    if not api.GetFileSecurityW(str(source),4,descriptor,size,ctypes.byref(size)):
        raise OSError('Unable to read configuration DACL')
    control, revision = wintypes.WORD(), wintypes.DWORD()
    if not api.GetSecurityDescriptorControl(descriptor,ctypes.byref(control),ctypes.byref(revision)):
        raise OSError('Unable to read configuration DACL protection')
    protection = 0x80000000 if control.value & 0x1000 else 0x20000000
    if not api.SetFileSecurityW(str(target),4|protection,descriptor):
        raise OSError('Unable to preserve configuration DACL')


def validate_staged_settings(before, staged):
    from app.core.config import Settings
    old = Settings(_env_file=before)
    new = Settings(_env_file=staged)
    allowed = {name.lower() for name in CHANGES}
    old_values, new_values = old.model_dump(), new.model_dump()
    if any(old_values[k] != new_values[k] for k in old_values if k not in allowed):
        raise ValueError('Staging altered unrelated effective settings')
    expected = dict(leny_rag_profile='rag4_v1', leny_rag_evidence_mode='adaptive', leny_rag_ranking='hybrid',
                    leny_rag_adaptive_token_probe=True, leny_temperature=0.0)
    if any(getattr(new,k) != value for k,value in expected.items()):
        raise ValueError('Process environment overrides staged pilot settings')
    if not (new.leny_rag_chat_enabled and new.leny_rag_enabled and new.leny_documents_enabled
            and new.leny_keep_alive=='0' and new.leny_num_ctx==4096 and new.leny_num_predict==768
            and new.leny_rag_top_k==5 and new.leny_rag_candidates==20
            and new.leny_rag_min_ram_bytes>=2*1024**3 and new.leny_rag_min_resident_ram_bytes>=1024**3):
        raise ValueError('Usual resources or RAG configuration differ from the reviewed pilot')
    return {key:dict(before=getattr(old,key.lower()),after=getattr(new,key.lower())) for key in CHANGES}


def private_path(path):
    base = Path(os.environ['LOCALAPPDATA'])/'BAB_VDOS/leny-pilot'
    from app.services.leny_document_storage import _check_path
    path = Path(path).resolve()
    if not path.is_relative_to(base.resolve()) or path == base.resolve():
        raise ValueError('Use an existing, dedicated private pilot directory')
    _check_path(path)
    if not path.is_dir():
        raise ValueError('Private pilot package does not exist')
    return path


def validate_recovery_proof(private, proof, backup_root, source_root):
    from app.services.leny_document_storage import _check_path
    def file_hash(path):
        value = hashlib.sha256()
        with path.open('rb') as handle:
            for part in iter(lambda:handle.read(1024**2),b''):
                value.update(part)
        return value.hexdigest()
    required = ('backup_verified','isolated_restore_verified','isolated_database_removed',
                'business_library_unchanged','env_unchanged','source_freeze_verified')
    if not all(proof.get(key) is True for key in required):
        raise ValueError('Verified backup, recovery and unchanged state required')
    backup = Path(proof['backup_path']).resolve()
    _check_path(backup)
    if not backup.is_relative_to(backup_root.resolve()) or file_hash(backup) != proof['backup_sha256']:
        raise ValueError('Private backup integrity mismatch')
    if file_hash(private/'pilot-code.zip') != proof['code_sha256']:
        raise ValueError('Private code archive integrity mismatch')
    inventory = proof.get('source_files_sha256',{})
    if not inventory:
        raise ValueError('Frozen source inventory required')
    for name, expected in inventory.items():
        path = (source_root/name).resolve()
        if not path.is_relative_to(source_root.resolve()) or file_hash(path) != expected:
            raise ValueError('Pilot source changed since recovery rehearsal')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['inspect','prepare','activate','rollback'], nargs='?', default='inspect')
    parser.add_argument('--private-dir', type=Path)
    parser.add_argument('--confirm-activation', action='store_true')
    parser.add_argument('--confirm-rollback', action='store_true')
    args = parser.parse_args()
    os.chdir(BACKEND)
    env = BACKEND/'.env'
    if args.command == 'inspect':
        from app.core.config import Settings
        c = Settings(_env_file=env)
        print(json.dumps({'profile':c.leny_rag_profile,'rag_chat_enabled':c.leny_rag_chat_enabled,
                          'configuration_changed':False,'env_sha256':sha(env.read_bytes())}))
        return
    if args.private_dir is None:
        parser.error('--private-dir is required')
    private = private_path(args.private_dir)
    manifest = private/'profile-change.json'
    if args.command == 'prepare':
        if manifest.exists():
            raise ValueError('Profile package already exists; preserve its evidence')
        old = env.read_bytes()
        proposed = render_environment(old)
        before, staged = private/'env.before', private/'env.pilot'
        if before.exists() or staged.exists():
            raise ValueError('Private staging files already exist')
        before.write_bytes(old); staged.write_bytes(proposed)
        changes = validate_staged_settings(before,staged)
        record = dict(pilot='LENY RAG V1 - Piloto supervisado',state='prepared_not_activated',
                      created_utc=datetime.now(timezone.utc).isoformat(),before_sha256=sha(old),
                      proposed_sha256=sha(proposed),changes=changes)
        manifest.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'state':record['state'],'changes':changes,'business_env_modified':False}))
        return
    record = json.loads(manifest.read_text('utf-8'))
    old, proposed = (private/'env.before').read_bytes(), (private/'env.pilot').read_bytes()
    if sha(old) != record['before_sha256'] or sha(proposed) != record['proposed_sha256']:
        raise ValueError('Private configuration package integrity mismatch')
    if args.command == 'activate':
        if not args.confirm_activation:
            parser.error('Owner confirmation is required before --confirm-activation')
        validate_staged_settings(private/'env.before',private/'env.pilot')
        proof = json.loads((private/'recovery-proof.json').read_text('utf-8'))
        from app.core.config import Settings
        from app.services.leny_document_storage import DocumentStorage
        validate_recovery_proof(private,proof,DocumentStorage(Settings(_env_file=env)).root/'backups',ROOT)
        atomic_replace(env,record['before_sha256'],proposed)
        state = 'activated_reload_and_runtime_verification_required'
    else:
        if not args.confirm_rollback:
            parser.error('Use --confirm-rollback only for an authorized reversal')
        atomic_replace(env,record['proposed_sha256'],old)
        state = 'rolled_back_reload_and_runtime_verification_required'
    event = private/(args.command+'-'+uuid4().hex+'.json')
    event.write_text(json.dumps({'state':state,'created_utc':datetime.now(timezone.utc).isoformat()},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'state':state,'services_reloaded':False,'database_rollback_executed':False}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'operation_failed':type(error).__name__,'details_withheld':True}),file=sys.stderr)
        raise SystemExit(1)
