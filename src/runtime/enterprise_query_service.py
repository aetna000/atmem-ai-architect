"""Native credential/engine composition for queued questions and delayed release."""
import asyncio
import threading
import logging
import procrastinate
import psycopg
from enterprise_queries import QueryLeaseLost
from enterprise_sources import SourceDenied,SourceUnavailable,SourceChanged
from public_faq import InvalidAnswer
from enterprise_knowledge import current_engine
from enterprise_audit import KnowledgeAudit


class EnterpriseAnswers:
    def __init__(self,store,connections,make_engine,*,extraction_cache=None,audit=None):
        if not isinstance(connections,dict)or not 1<=len(connections)<=20 or not callable(make_engine):raise ValueError('Supply owned native question adapters')
        if any(entry.driver.store is not store.auth for entry in connections.values()):raise ValueError('Question/source stores must use the same owned authority')
        if extraction_cache is not None and(extraction_cache.auth is not store.auth or extraction_cache.account_id!=store.account_id):raise ValueError('Extraction cache must use the same owned company and authority')
        if audit is not None and(not isinstance(audit,KnowledgeAudit)or audit.auth is not store.auth or audit.account_id!=store.account_id):raise ValueError('Question audit must use the same owned company and authority')
        self.store=store;self.connections=connections;self.make_engine=make_engine;self.extraction_cache=extraction_cache;self.audit=audit

    def engine(self,principal,authorize,*,query_id=None,attempt=None):
        engine=current_engine(self.store.auth,self.connections,principal,self.make_engine,authorize)
        if self.audit is not None:engine.audit=self.audit.bind(principal,query_id=query_id,attempt=attempt)
        if self.extraction_cache is not None:
            engine.decode=self.extraction_cache.wrap(engine.decode,lambda:engine.authorize(principal.key))
        return engine

    def execute(self,identity):
        lease=self.store.claim(identity)
        if lease is None:return
        stop=threading.Event();lost=threading.Event()
        def heartbeat():
            while not stop.wait(max(1,self.store.lease_seconds//3)):
                try:self.store.guard(lease,renew=True)
                except Exception:lost.set();return
        def authorize(subject):
            if lost.is_set():raise QueryLeaseLost('Question worker lost current authority')
            if subject!=lease.principal.key:raise SourceDenied('company_identity_required')
            self.store.guard(lease)
        thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
        try:
            authorize(lease.principal.key)
            engine=self.engine(lease.principal,authorize,query_id=lease.id,attempt=lease.attempt)
            receipt=engine.answer_receipt(lease.question,lease.principal.key)
            authorize(lease.principal.key)
            self.store.complete(lease,receipt)
        except QueryLeaseLost:return
        except SourceDenied as error:
            code='setup'if str(error)=='source_mapping_required'else'source'if str(error)in {'source_reconnection_required','source_consent_required'}else'signin'if str(error).startswith('company_')else'unavailable'
            self.store.failed(lease,code,retry=code=='unavailable')
        except InvalidAnswer:self.store.failed(lease,'answer')
        except SourceUnavailable:self.store.failed(lease,'unavailable',retry=True)
        except Exception:self.store.failed(lease,'unavailable')
        finally:stop.set();thread.join(timeout=2)

    def status(self,session,identity):
        row=self.store.get(session,identity)
        result={'id':identity,'status':row['state']}
        if row['state']=='failed':result['errorCode']=row['error_code'];return result
        if row['state']!='ready':return result
        receipt=self.store.open_result(row)
        def authorize(subject):
            if subject!=session.principal.key:raise SourceDenied('company_identity_required')
            current=self.store.get(session,identity)
            if current['state']!='ready'or current['attempt']!=row['attempt']:raise QueryLeaseLost('Question changed before release')
        try:
            engine=self.engine(session.principal,authorize,query_id=identity,attempt=row['attempt'])
            answer=engine.release(receipt,session.principal.key)
            self.store.released(session,identity,row['attempt'])
            return {**result,'result':answer}
        except SourceChanged:
            self.store.requeue(session,identity,row['attempt'])
            return {'id':identity,'status':'queued'}
        except QueryLeaseLost:
            return {'id':identity,'status':self.store.get(session,identity)['state']}


class EnterpriseQueryWorker:
    def __init__(self,dsn,service):
        self.service=service
        async def refresh():return await asyncio.to_thread(dsn)
        self.app=procrastinate.App(connector=procrastinate.PsycopgConnector(conninfo=refresh if callable(dsn)else dsn,min_size=1,max_size=4,max_lifetime=600,kwargs={'connect_timeout':5,'options':'-c search_path=pg_catalog,enterprise_queries,pg_temp -c statement_timeout=10000 -c lock_timeout=3000'}))
        async def execute(query_id):await asyncio.to_thread(service.execute,query_id)
        self.task=self.app.task(name=service.store.task.name,queue=service.store.task.queue)(execute)

    async def run(self,*,concurrency=2,**options):
        if type(concurrency)is not int or not 1<=concurrency<=4:raise ValueError('Use bounded owned query concurrency')
        async def recover():
            while True:
                try:
                    await asyncio.to_thread(self.service.store.recover)
                    if self.service.extraction_cache is not None:await asyncio.to_thread(self.service.extraction_cache.purge)
                except(psycopg.OperationalError,SourceUnavailable):logging.getLogger(__name__).warning('Question recovery is temporarily unavailable')
                await asyncio.sleep(15)
        async with self.app.open_async():
            async with asyncio.TaskGroup()as group:
                recovery=group.create_task(recover())
                await self.app.run_worker_async(queues=[self.task.queue],concurrency=concurrency,**options)
                recovery.cancel()
