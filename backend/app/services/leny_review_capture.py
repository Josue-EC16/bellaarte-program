"""Opt-in private review trace; tickets grant tracing, never document access."""
import hashlib
import json
import os
from pathlib import Path
import time

from app.services.leny_document_storage import _check_path


class PrivateReview:
    def __init__(self, actor, payload):
        self.path = None
        self.data = {}
        root = Path(os.environ.get('LOCALAPPDATA', ''))/'BAB_VDOS'/'leny-original-integration'
        ticket = root/'requests'/(str(payload.request_id)+'.json')
        try:
            _check_path(ticket)
            if not ticket.is_file() or ticket.stat().st_size > 2048:
                # SPEC-03 authenticated runner fsyncs its protected checkpoint
                # before POST. This opt-in captures evidence privately only;
                # publication, ownership and ACL are still checked by LENY.
                from app.services.leny_external_scope import evaluation_request
                if evaluation_request(actor, payload):
                    base = Path(os.environ['LOCALAPPDATA'])/'BAB_VDOS/leny-spec03'
                    active = Path((base/'active.txt').read_text(encoding='utf-8'))
                    self.path = active/'review/traces'/('trace-'+str(payload.request_id)+'.json')
                    _check_path(self.path)
                    self.path.parent.mkdir(exist_ok=True)
                    self.data = {'request_id': str(payload.request_id), 'user_id': actor.user_id}
                return
            value = json.loads(ticket.read_text(encoding='utf-8'))
            if (value.get('user_id') != actor.user_id or value.get('conversation_id') != str(payload.conversation_id)
                    or value.get('question_sha256') != hashlib.sha256(payload.message.encode()).hexdigest()
                    or not 0 <= time.time()-value.get('created', 0) <= 3600):
                return
            self.path = root/'results'/('trace-'+str(payload.request_id)+'.json')
            _check_path(self.path)
            self.data = {'request_id': str(payload.request_id), 'user_id': actor.user_id}
        except (OSError, ValueError, TypeError):
            return

    def record(self, stage, data):
        if self.path is None:
            return
        try:
            self.data[stage] = data
            value = json.dumps(self.data, ensure_ascii=False, default=str)
            if len(value.encode()) > 512*1024:
                return
            temporary = self.path.with_suffix('.tmp')
            temporary.write_text(value, encoding='utf-8')
            temporary.replace(self.path)
        except (OSError, ValueError, TypeError):
            # Review cannot change authorization, results or retain a lease.
            return
