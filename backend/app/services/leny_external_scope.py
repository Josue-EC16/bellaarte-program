"""Finite, version-bound owner approval for external processing; never an ACL."""
import hashlib
import json
import os
import re
from pathlib import Path
from time import time
from uuid import UUID
from app.services.leny_llm_contracts import LenyError


def approved_versions(config):
    path=getattr(config,'leny_gemini_corpus_manifest',None)
    if not path:
        raise LenyError('LENY_EXTERNAL_APPROVAL_MISSING','Falta registrar las versiones autorizadas para Google. Puedes usar Qwen.',503)
    try:
        from app.services.leny_document_storage import _check_path
        target=Path(path);_check_path(target)
        if not target.is_absolute() or target.stat().st_size>256*1024:raise ValueError()
        data=json.loads(target.read_text(encoding='utf-8'))
        if data['format_version']!=1 or not isinstance(data['versions'],list):raise ValueError()
        grants=set()
        for row in data['versions']:
            ids=tuple(str(UUID(str(row[key]))) for key in ('document_id','version_id','indexation_id'))
            digest=row['sha256']
            if not isinstance(digest,str) or not re.fullmatch(r'[0-9a-f]{64}',digest):raise ValueError()
            grants.add((*ids,digest))
        return grants
    except (OSError,ValueError,KeyError,TypeError):
        raise LenyError('LENY_EXTERNAL_APPROVAL_INVALID','La autorización externa no está disponible. Puedes usar Qwen.',503) from None


def require_approved(config, rows):
    grants=approved_versions(config)
    for row in rows:
        identity=tuple(str(row.get(key,'')) for key in ('document_id','version_id','indexation_id','sha256'))
        if identity not in grants:
            raise LenyError('LENY_EXTERNAL_NOT_APPROVED','La versión documental no está autorizada para Google. Inicia otra conversación con Qwen.',403)


def require_approved_ids(config,sessions,fragment_ids):
    if not fragment_ids:return
    from sqlalchemy import text
    with sessions() as db:
        rows=[dict(row) for row in db.execute(text('SELECT v.document_id,v.id version_id,i.id indexation_id,v.sha256 '
            'FROM leny.rag_fragmentos f JOIN leny.rag_indexaciones i ON i.id=f.indexation_id '
            'JOIN leny.documento_versiones v ON v.id=i.version_id WHERE f.id=ANY(CAST(:ids AS uuid[]))'),
            {'ids':list(map(str,fragment_ids))}).mappings()]
    if len(rows)!=len(set(map(str,fragment_ids))):
        raise LenyError('LENY_EXTERNAL_NOT_APPROVED','El soporte anterior ya no está disponible para Google.',403)
    require_approved(config,rows)


def evaluation_request(actor,payload,*,job_prefix=None):
    """A local ticket only adds a stricter evaluation quota, never permissions."""
    from app.services.leny_document_storage import _check_path
    base=Path(os.environ.get('LOCALAPPDATA',''))/'BAB_VDOS/leny-spec03'
    try:
        active=Path((base/'active.txt').read_text(encoding='utf-8'))
        if active.parent!=base:return False
        target=active/'review/requests'/(str(payload.request_id)+'.json');_check_path(target)
        if target.exists():
            if job_prefix is not None:return False
            if target.stat().st_size>2048:return False
            ticket=json.loads(target.read_text(encoding='utf-8'))
            return (ticket.get('user_id')==actor.user_id
                and ticket.get('conversation_id')==str(payload.conversation_id)
                and ticket.get('question_sha256')==hashlib.sha256(payload.message.encode()).hexdigest()
                and 0<=time()-ticket.get('created',0)<=7200)
        # The new runner fsyncs its protected checkpoint before POST. Ownership
        # was already checked by store.provider_for before this method is used.
        # Reading only a fresh pending request adds a limit; it grants no access.
        for target in (active/'review/results').glob('*.json'):
            _check_path(target)
            info=target.stat()
            if info.st_size>1024*1024 or not 0<=time()-info.st_mtime<=120:continue
            data=json.loads(target.read_text(encoding='utf-8'))
            if data.get('state')!='running' or data.get('provider')!='gemini':continue
            if job_prefix is not None and not str(data.get('job','')).startswith(job_prefix):continue
            for row in data.get('cases',[]):
                if (row.get('termination')=='attempt_started' and row.get('request_id')==str(payload.request_id)
                    and row.get('conversation_id')==str(payload.conversation_id) and row.get('question')==payload.message):return True
        return False
    except (OSError,ValueError,KeyError,TypeError):return False
