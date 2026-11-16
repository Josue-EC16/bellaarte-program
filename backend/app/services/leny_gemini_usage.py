"""Durable project-wide reservations. No prompt/key/provider error bodies."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import text
from app.services.leny_llm_contracts import LenyError


class GeminiUsage:
    def __init__(self, sessions, config, *, request_id=None, conversation_id=None, user_id=None, evaluation=False):
        self.sessions, self.config = sessions, config
        self.evaluation=evaluation
        self.ids = dict(request_id=request_id, conversation_id=conversation_id, user_id=user_id)

    def reserve(self, phase, tokens):
        with self.sessions() as db, db.begin():
            db.execute(text("SET LOCAL lock_timeout='5s'"))
            db.execute(text('SELECT pg_advisory_xact_lock(83961422002)'))
            now = db.scalar(text('SELECT clock_timestamp()'))
            local = now.astimezone(ZoneInfo('America/Los_Angeles'))
            day = local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
            count = db.scalar(text('SELECT count(*) FROM leny.gemini_requests WHERE created_at>=:day'), {'day': day})
            if self.evaluation:
                used=db.scalar(text("SELECT count(*) FROM leny.gemini_requests WHERE created_at>=:day AND left(phase,5)='eval_'"),{'day':day})
                if used>=self.config.leny_spec03_evaluation_daily_calls:
                    error=LenyError('LENY_EVALUATION_QUOTA','Se completó el lote diario de evaluación; se conserva el progreso.',429)
                    error.retry_after=max(1,int(((local.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1)).astimezone(timezone.utc)-now).total_seconds())+1)
                    raise error
                phase='eval_'+phase
            blocked = db.scalar(text("SELECT EXISTS(SELECT 1 FROM leny.gemini_requests WHERE created_at>=:day AND status='daily_exhausted')"), {'day':day})
            recent = db.execute(text('SELECT created_at,reserved_tokens FROM leny.gemini_requests WHERE created_at>:minute ORDER BY created_at'),
                                {'minute': now-timedelta(seconds=60)}).all()
            wait = 0
            if blocked or count >= self.config.leny_gemini_rpd:
                next_day = (local.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1)).astimezone(timezone.utc)
                wait = max(1, int((next_day-now).total_seconds())+1)
            elif len(recent) >= self.config.leny_gemini_rpm or sum(r[1] for r in recent)+tokens>self.config.leny_gemini_tpm:
                wait = max(1, int((recent[0][0]+timedelta(seconds=60)-now).total_seconds())+1) if recent else 60
            if wait:
                error = LenyError('LENY_GEMINI_QUOTA', 'Gemini alcanzó su límite de uso. Espera o inicia otra conversación con Qwen.', 429)
                error.retry_after = wait
                raise error
            identity = uuid4()
            db.execute(text('INSERT INTO leny.gemini_requests(id,request_id,conversation_id,user_id,phase,reserved_tokens,status) '
                "VALUES(:id,:request_id,:conversation_id,:user_id,:phase,:tokens,'reserved')"),
                self.ids | dict(id=identity, phase=phase, tokens=tokens))
            return identity

    def finish(self, identity, *, metrics=None, error=None):
        metrics = metrics or {}
        with self.sessions() as db, db.begin():
            db.execute(text("UPDATE leny.gemini_requests SET finished_at=clock_timestamp(),status=:status,error_code=:error,"
                'input_tokens=:input,output_tokens=:output,thinking_tokens=:thinking WHERE id=:id'),
                dict(id=identity, status='failed' if error else 'completed', error=error,
                     input=metrics.get('prompt_eval_count'), output=metrics.get('eval_count'), thinking=metrics.get('thinking_tokens')))

    def block_daily(self):
        with self.sessions() as db, db.begin():
            now = db.scalar(text('SELECT clock_timestamp()'))
            local = now.astimezone(ZoneInfo('America/Los_Angeles'))
            until = (local.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1)).astimezone(timezone.utc)
            db.execute(text("INSERT INTO leny.gemini_requests(id,phase,reserved_tokens,status,error_code) VALUES(:id,'quota',0,'daily_exhausted','LENY_GEMINI_QUOTA')"),{'id':uuid4()})
            return max(1,int((until-now).total_seconds())+1)
