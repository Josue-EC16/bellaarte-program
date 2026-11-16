"""Reversible profile edit safety; synthetic env only, no service or DB effects."""
import pytest
import os

from scripts.leny_rag_pilot_profile import CHANGES, render_environment, sha, atomic_replace, validate_recovery_proof


@pytest.mark.parametrize('newline,bom', [('\n',False),('\r\n',False),('\r\n',True)])
def test_only_reviewed_values_change_and_private_bytes_are_preserved(newline, bom):
    source = newline.join(['# synthetic settings','DB_PASS="unit-only-$-`-value"',
        'LENY_RAG_PROFILE=legacy # keep explanation','leny_temperature = 0.3',
        'LENY_RAG_CHAT_ENABLED=true','OTHER_PRIVATE_VALUE=abc'])
    data = (b'\xef\xbb\xbf' if bom else b'')+source.encode()
    result = render_environment(data)
    assert b'DB_PASS="unit-only-$-`-value"' in result
    assert b'OTHER_PRIVATE_VALUE=abc' in result
    assert b'LENY_RAG_CHAT_ENABLED=true' in result
    assert b'LENY_RAG_PROFILE=rag4_v1 # keep explanation' in result
    assert b'leny_temperature = 0.0' in result
    assert result.startswith(b'\xef\xbb\xbf') == bom
    assert render_environment(result) == result
    if newline=='\r\n': assert b'\n' not in result.replace(b'\r\n',b'')


def test_duplicate_keys_do_not_choose_an_arbitrary_effective_profile():
    with pytest.raises(ValueError):render_environment(b'LENY_RAG_PROFILE=legacy\nleny_rag_profile=legacy\n')


def test_atomic_apply_and_reverse_do_not_overwrite_unrelated_intervening_edit(tmp_path):
    env = tmp_path/'.env'
    old = b'LENY_RAG_PROFILE=legacy\nPRIVATE_SYNTHETIC=unchanged\n'
    env.write_bytes(old)
    new = render_environment(old)
    atomic_replace(env,sha(old),new)
    assert env.read_bytes()==new
    atomic_replace(env,sha(new),old)
    assert env.read_bytes()==old
    env.write_bytes(old+b'NEW_SETTING=1\n')
    with pytest.raises(ValueError):atomic_replace(env,sha(old),new)
    assert env.read_bytes()==old+b'NEW_SETTING=1\n'
    assert not list(tmp_path.glob('*.tmp'))


def test_activation_requires_intact_backup_code_and_unchanged_sources(tmp_path):
    private=tmp_path/'private'; private.mkdir()
    backups=tmp_path/'backups'; backups.mkdir()
    source=tmp_path/'source'; source.mkdir()
    (private/'pilot-code.zip').write_bytes(b'synthetic-code')
    backup=backups/'synthetic.zip'; backup.write_bytes(b'synthetic-backup')
    app=source/'app.py'; app.write_bytes(b'synthetic-source')
    proof={key:True for key in ('backup_verified','isolated_restore_verified','isolated_database_removed',
        'business_library_unchanged','env_unchanged','source_freeze_verified')}
    proof.update(backup_path=str(backup),backup_sha256=sha(backup.read_bytes()),
        code_sha256=sha((private/'pilot-code.zip').read_bytes()),source_files_sha256={'app.py':sha(app.read_bytes())})
    validate_recovery_proof(private,proof,backups,source)
    proof['isolated_restore_verified']=False
    with pytest.raises(ValueError):validate_recovery_proof(private,proof,backups,source)
    proof['isolated_restore_verified']=True
    backup.write_bytes(b'changed')
    with pytest.raises(ValueError):validate_recovery_proof(private,proof,backups,source)
    backup.write_bytes(b'synthetic-backup')
    app.write_bytes(b'changed')
    with pytest.raises(ValueError):validate_recovery_proof(private,proof,backups,source)


@pytest.mark.skipif(os.name!='nt',reason='Native Windows configuration DACL preservation')
def test_windows_replacement_preserves_restricted_dacl_before_any_secret_is_written(tmp_path,monkeypatch):
    import ctypes
    from ctypes import wintypes
    from scripts import leny_rag_pilot_profile as module
    from app.services.leny_document_storage import protect_directory

    def dacl(path):
        api=ctypes.WinDLL('advapi32',use_last_error=True)
        api.GetFileSecurityW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
        api.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes=[ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(wintypes.LPWSTR),ctypes.c_void_p]
        kernel=ctypes.WinDLL('kernel32'); kernel.LocalFree.argtypes=[ctypes.c_void_p]
        size=wintypes.DWORD(); api.GetFileSecurityW(str(path),4,None,0,ctypes.byref(size))
        buffer=ctypes.create_string_buffer(size.value)
        assert api.GetFileSecurityW(str(path),4,buffer,size,ctypes.byref(size))
        value=wintypes.LPWSTR()
        assert api.ConvertSecurityDescriptorToStringSecurityDescriptorW(buffer,1,4,ctypes.byref(value),None)
        try:return value.value
        finally:kernel.LocalFree(value)

    env=tmp_path/'.env'; old=b'SYNTHETIC_SECRET=before\n'; new=b'SYNTHETIC_SECRET=after\n'
    env.write_bytes(old)
    protect_directory(env)  # Apply a protected owner/SYSTEM/Admin DACL to this synthetic file only.
    expected=dacl(env)
    original_copy=module.copy_windows_dacl
    observed=[]
    def assert_empty_then_copy(source,target):
        assert target.read_bytes()==b''
        original_copy(source,target)
        assert dacl(target)==expected
        observed.append(True)
    monkeypatch.setattr(module,'copy_windows_dacl',assert_empty_then_copy)
    atomic_replace(env,sha(old),new)
    assert observed==[True] and env.read_bytes()==new and dacl(env)==expected
    atomic_replace(env,sha(new),old)
    assert len(observed)==2 and env.read_bytes()==old and dacl(env)==expected


@pytest.mark.skipif(os.name!='nt',reason='Native Windows configuration DACL preservation')
def test_configuration_remains_untouched_if_dacl_cannot_be_copied(tmp_path,monkeypatch):
    from scripts import leny_rag_pilot_profile as module
    env=tmp_path/'.env'; before=b'SYNTHETIC_SECRET=before\n'; env.write_bytes(before)
    def fail_closed(source,target):
        assert target.read_bytes()==b''
        raise OSError('synthetic access denied')
    monkeypatch.setattr(module,'copy_windows_dacl',fail_closed)
    with pytest.raises(OSError):atomic_replace(env,sha(before),b'SYNTHETIC_SECRET=after\n')
    assert env.read_bytes()==before
    assert not list(tmp_path.glob('.env.pilot-*.tmp'))
