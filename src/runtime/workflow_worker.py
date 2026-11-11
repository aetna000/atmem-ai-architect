"""Owned queue integration; concrete processors/HTTP adapters remain separate.

Task arguments contain an operation UUID only. Callbacks are trusted source wired
by the compiler/bootstrap, never model-provided paths, tools or Python code.
"""
import asyncio
import logging
import time
import procrastinate
import psycopg
from durable_workflow import WorkflowStore,LostLease
from workflow_connection import DatabaseCredentialUnavailable
from workflow_errors import TemporaryWork,PermanentWork,ExternalOutcomeUnknown,DestinationNotAttempted,InvalidDispatch
from workflow_contract import bind_payload_contract

def _transient_database_error(error,depth=0):
    # ConnectorException and TaskGroup wrappers retain the native cause. Never
    # retry a mixed group containing a programming/schema/authorization failure.
    if depth>12:return False
    if isinstance(error,BaseExceptionGroup):return bool(error.exceptions)and all(_transient_database_error(child,depth+1)for child in error.exceptions)
    if isinstance(error,DatabaseCredentialUnavailable):return True
    if isinstance(error,psycopg.OperationalError):
        state=error.sqlstate
        return state is None or state.startswith('08')or state in {'57P01','57P02','57P03'}
    if error.__cause__ is not None:return _transient_database_error(error.__cause__,depth+1)
    return False

def _namespace(value):
    if not isinstance(value,str)or not value.isascii()or not value.replace('-','').isalnum()or not 1<=len(value)<=20:raise ValueError('Invalid owned workflow namespace')
    return value

def producer_store(dsn,*,destination_contract,namespace='workflow',lease_seconds=600,payload_contract=None,operation_kind=None):
    """API-side store: synchronous outbox, no worker/model credentials needed."""
    namespace=_namespace(namespace)
    app=procrastinate.App(connector=procrastinate.SyncPsycopgConnector(conninfo=dsn,kwargs={'connect_timeout':5,'options':'-c search_path=pg_catalog,workflow,pg_temp'}))
    def worker_only(operation_id):raise PermanentWork('Run the dedicated owned worker, not an API-side producer')
    extract=app.task(name=namespace+'.extract',queue=namespace+'-extract')(worker_only)
    dispatch=app.task(name=namespace+'.dispatch',queue=namespace+'-dispatch')(worker_only)
    return WorkflowStore(dsn,extract,dispatch,destination_contract=destination_contract,lease_seconds=lease_seconds,payload_contract=payload_contract,operation_kind=operation_kind)

class WorkflowRuntime:
    def __init__(self,dsn,processor,deliver,*,destination_contract=None,idempotent_destination=False,namespace='workflow',lease_seconds=600,retry_wait=5,payload_contract=None,operation_kind=None):
        if type(idempotent_destination)is not bool:raise ValueError('Invalid owned worker configuration')
        namespace=_namespace(namespace)
        if type(retry_wait)is not int or not 0<=retry_wait<=300:raise ValueError('Invalid retry policy')
        for stage in [processor,deliver]:
            if hasattr(stage,'timeout_seconds')and stage.timeout_seconds+5>=lease_seconds:raise ValueError('A stage deadline must leave room to commit inside the domain lease')
        if hasattr(deliver,'idempotency_verified')and deliver.idempotency_verified!=idempotent_destination:raise ValueError('Worker replay policy must match the reviewed destination contract')
        if destination_contract is None:destination_contract=getattr(deliver,'contract',None)
        elif hasattr(deliver,'contract')and deliver.contract!=bind_payload_contract(destination_contract,payload_contract):raise ValueError('Worker and destination integration identities must match')
        self.processor=processor;self.deliver=deliver;self.idempotent_destination=idempotent_destination
        async def refreshed_connection():return await asyncio.to_thread(dsn)
        self.app=procrastinate.App(connector=procrastinate.PsycopgConnector(conninfo=refreshed_connection if callable(dsn)else dsn,min_size=1,max_size=8,max_lifetime=600,kwargs={'connect_timeout':5,'options':'-c search_path=pg_catalog,workflow,pg_temp -c statement_timeout=10000 -c lock_timeout=3000'}))
        retry=procrastinate.RetryStrategy(max_attempts=5,wait=retry_wait,retry_exceptions=[TemporaryWork])
        self.extract=self.app.task(name=namespace+'.extract',queue=namespace+'-extract',retry=retry)(self._extract)
        self.dispatch=self.app.task(name=namespace+'.dispatch',queue=namespace+'-dispatch',retry=retry)(self._dispatch)
        # The domain transaction is a synchronous psycopg connection. Keep its
        # producer connector synchronous even while the async worker pool is open;
        # never accidentally bridge that connection into an async cursor context.
        self.store=producer_store(dsn,destination_contract=destination_contract,namespace=namespace,lease_seconds=lease_seconds,payload_contract=payload_contract,operation_kind=operation_kind)
    async def _fail(self,row,reason,*,retryable=False,ambiguous=True):
        try:await asyncio.to_thread(self.store.fail,str(row['id']),str(row['lease_token']),reason,retryable=retryable,ambiguous=ambiguous)
        except LostLease:return
    async def _extract(self,operation_id):
        try:row=await asyncio.to_thread(self.store.claim_extract,operation_id)
        except psycopg.OperationalError:raise TemporaryWork('Database connection temporarily unavailable before processing')from None
        if row is None:return
        try:
            result=await asyncio.to_thread(self.processor,row)
            await asyncio.to_thread(self.store.record_result,operation_id,str(row['lease_token']),result)
        except LostLease:return
        except TemporaryWork:
            await self._fail(row,'model_unavailable',retryable=True);raise TemporaryWork('Processing temporarily unavailable')from None
        except BaseException as error:
            if isinstance(error,asyncio.CancelledError):raise
            await self._fail(row,'invalid_result');raise PermanentWork('Processing requires review or recovery')from None
    async def _dispatch(self,operation_id):
        try:row=await asyncio.to_thread(self.store.claim_dispatch,operation_id,verified_idempotent_replay=self.idempotent_destination)
        except psycopg.OperationalError:raise TemporaryWork('Database connection temporarily unavailable before dispatch')from None
        if row is None:return
        try:
            receipt=await asyncio.to_thread(self.deliver,row,idempotency_key=str(row['id']),payload_sha256=row['approved_hash'])
            await asyncio.to_thread(self.store.record_sent,operation_id,str(row['lease_token']),receipt)
        except LostLease:return
        except DestinationNotAttempted:
            await self._fail(row,'destination_unavailable',retryable=True,ambiguous=False);raise TemporaryWork('Destination credential temporarily unavailable; no request was made')from None
        except InvalidDispatch:
            await self._fail(row,'destination_rejected',ambiguous=False);raise PermanentWork('Approved dispatch integrity requires review; no request was made')from None
        except ExternalOutcomeUnknown:
            await self._fail(row,'destination_unavailable',retryable=True,ambiguous=True)
            if self.idempotent_destination:raise TemporaryWork('Destination acknowledgement unavailable; stable replay contract applies')from None
            raise PermanentWork('External outcome requires reconciliation before another attempt')from None
        except BaseException as error:
            if isinstance(error,asyncio.CancelledError):raise
            # An unexpected exception can happen after the external service
            # accepted the request, including while committing its receipt.
            await self._fail(row,'destination_unavailable',ambiguous=True)
            raise PermanentWork('External outcome requires reconciliation')from None
    async def recover_once(self):
        # Native heartbeat-based stale detection, never duration-only retry of an
        # actively heartbeating worker. Domain fencing protects resumed callbacks.
        for owned_task in [self.extract,self.dispatch]:
            stalled=await self.app.job_manager.get_stalled_jobs(task_name=owned_task.name,seconds_since_heartbeat=60)
            for job in stalled:await self.app.job_manager.retry_job(job)
        expired=await asyncio.to_thread(self.store.recover_expired)
        repaired=await asyncio.to_thread(self.store.reconcile_notifications)
        return list(dict.fromkeys([*expired,*repaired]))
    async def run(self,*,concurrency=2,recovery_interval=30,**options):
        if type(concurrency)is not int or not 1<=concurrency<=10 or type(recovery_interval)is not int or not 5<=recovery_interval<=300:raise ValueError('Invalid bounded worker options')
        delay=1
        while True:
            started=time.monotonic()
            try:
                # Close even when the initial pool wait fails: retaining a
                # partially opened pool would bypass fresh credentials on retry.
                try:
                    # Admit the exact owned schema before queue registration,
                    # heartbeat/recovery writes or fetching a notification.
                    def admit():
                        with self.store.connect():pass
                    await asyncio.to_thread(admit)
                    await self.app.open_async()
                    async def recovery():
                        while True:
                            await self.recover_once();await asyncio.sleep(recovery_interval)
                    worker_options={'update_heartbeat_interval':10.0,'stalled_worker_timeout':90.0,**options}
                    async with asyncio.TaskGroup()as group:
                        task=group.create_task(recovery())
                        worker=group.create_task(self.app.run_worker_async(queues=[self.extract.queue,self.dispatch.queue],concurrency=concurrency,**worker_options))
                        try:await worker
                        finally:task.cancel()
                finally:await self.app.close_async()
                return
            except Exception as error:
                if not _transient_database_error(error):raise
                # Domain leases, approval hashes and uncertain-delivery rules
                # remain authoritative. Reopening a queue pool cannot resend an
                # external action or reset an operation's attempts/lease.
                logging.getLogger(__name__).warning('Queue database connection interrupted; reconnecting with fresh workload credentials')
                if time.monotonic()-started>=30:delay=1
                await asyncio.sleep(delay);delay=min(delay*2,30)
