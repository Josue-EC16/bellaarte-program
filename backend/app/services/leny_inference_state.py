"""Crash-safe inference markers under the existing PostgreSQL generation lease."""
import asyncio
from time import monotonic

import anyio
from sqlalchemy import text

from app.services.leny_ollama import LenyError


class InferenceState:
    def __init__(self,sessions):self.sessions=sessions

    def start(self,lease,request_id,model,phase):
        lease.check()
        with self.sessions.begin() as db:
            db.execute(text("SET LOCAL statement_timeout='5s'"))
            if not db.scalar(text("SELECT to_regclass('leny.inferencia_estado') IS NOT NULL")):
                return False  # Rolling compatibility with migration0020.
            changed=db.execute(text("""UPDATE leny.inferencia_estado SET state='inflight',request_id=:request,
              model=:model,phase=:phase,updated_at=clock_timestamp() WHERE id=1 AND state='idle' RETURNING id"""),
              {'request':request_id,'model':model,'phase':phase}).scalar_one_or_none()
            if changed is None:raise LenyError('LENY_INFERENCE_UNCERTAIN','Una inferencia requiere reconciliación antes de continuar.',503)
            lease.check()
        return True

    def finish(self,lease,request_id,confirmed):
        lease.check()
        with self.sessions.begin() as db:
            db.execute(text("SET LOCAL statement_timeout='5s'"))
            statement=("UPDATE leny.inferencia_estado SET state='idle',request_id=NULL,model=NULL,phase=NULL,updated_at=clock_timestamp() WHERE id=1 AND request_id=:request"
                if confirmed else "UPDATE leny.inferencia_estado SET state='uncertain',updated_at=clock_timestamp() WHERE id=1 AND request_id=:request")
            db.execute(text(statement),{'request':request_id})
            lease.check()


class ManagedProvider:
    """Cancellation stops output, but drains our own request before releasing its lease."""
    def __init__(self,provider,state,lease,request_id,remaining):
        self.provider,self.state,self.lease,self.request_id,self.remaining=provider,state,lease,request_id,remaining

    def __getattr__(self,name):return getattr(self.provider,name)

    async def _start(self,model,phase):
        with anyio.CancelScope(shield=True):
            return await anyio.to_thread.run_sync(self.state.start,self.lease,self.request_id,model,phase)

    async def _finish(self,tracked,confirmed):
        if tracked:
            with anyio.CancelScope(shield=True):
                try:await anyio.to_thread.run_sync(self.state.finish,self.lease,self.request_id,confirmed)
                except Exception:
                    # An unconfirmed cleanup leaves the durable inflight marker.
                    raise LenyError('LENY_INFERENCE_UNCERTAIN','La inferencia necesita reconciliación operativa.',503) from None

    async def call(self,function,model,phase,confirmed):
        tracked=await self._start(model,phase)
        task=asyncio.create_task(function())
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            with anyio.CancelScope(shield=True):
                try:await asyncio.wait_for(asyncio.shield(task),self.remaining())
                except (Exception,asyncio.CancelledError):
                    task.cancel();await asyncio.gather(task,return_exceptions=True)
            raise
        finally:
            await self._finish(tracked,bool(confirmed()))

    async def classify(self,messages,schema):
        self.provider.inference_started=False
        self.provider.response_complete=False
        return await self.call(lambda:self.provider.classify(messages,schema),self.config.leny_model,'classifier',
                               lambda:getattr(self.provider,'response_complete',False) or not getattr(self.provider,'inference_started',True))

    async def measure_prompt(self, messages):
        self.provider.inference_started = False
        self.provider.response_complete = False
        # Reuse the existing non-user-output inference phase. No schema change.
        return await self.call(lambda: self.provider.measure_prompt(messages), self.config.leny_model, 'classifier',
            lambda: getattr(self.provider, 'response_complete', False) or not getattr(self.provider, 'inference_started', True))

    async def stream(self,messages):
        tracked=await self._start(self.config.leny_model,'generation')
        queue=asyncio.Queue(maxsize=4)
        abandoned=asyncio.Event()
        async def put(item):
            if abandoned.is_set():return
            sending=asyncio.create_task(queue.put(item));closing=asyncio.create_task(abandoned.wait())
            try:await asyncio.wait({sending,closing},return_when=asyncio.FIRST_COMPLETED)
            finally:
                for task in (sending,closing):
                    if not task.done():task.cancel()
                await asyncio.gather(sending,closing,return_exceptions=True)
        async def produce():
            failure=None
            try:
                async for value in self.provider.stream(messages):await put(('text',value))
            except BaseException as error:failure=error
            finally:
                try:await self._finish(tracked,bool(getattr(self.provider,'response_complete',False)) or not getattr(self.provider,'inference_started',True))
                except Exception as error:failure=error
                await put(('error',failure) if failure else ('done',None))
        producer=asyncio.create_task(produce())
        try:
            while True:
                kind,value=await queue.get()
                if kind=='error':raise value
                if kind=='done':break
                yield value
        finally:
            abandoned.set()
            with anyio.CancelScope(shield=True):
                try:await asyncio.wait_for(asyncio.shield(producer),self.remaining())
                except (Exception,asyncio.CancelledError):
                    producer.cancel();await asyncio.gather(producer,return_exceptions=True)
