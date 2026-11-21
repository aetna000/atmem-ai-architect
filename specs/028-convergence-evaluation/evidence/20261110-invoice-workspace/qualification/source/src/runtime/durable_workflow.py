"""Transactional state and approval fences for owned application workflows.

The HTTP/identity adapter must construct Principal only after native verification.
Live application membership is checked here; this is not an OIDC implementation.
Workers have a separate internal API. No model text chooses a task, role or state.
No queue lock alone establishes exactly-once external side effects: dispatch must
use a verified upstream idempotency contract and preserve the operation identity.
"""
from dataclasses import dataclass
import hashlib
import json
import uuid
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from workflow_contract import reviewed_contract

class Denied(PermissionError):pass
class Missing(LookupError):pass
class Conflict(ValueError):pass
class LostLease(Conflict):pass

def identifier(value):
    if not isinstance(value,str):raise ValueError('An exact UUID is required')
    parsed=uuid.UUID(value)
    if str(parsed)!=value:raise ValueError('Use a canonical UUID')
    return value

def canonical(value,limit=64000):
    if not isinstance(value,dict) or any(not isinstance(k,str) for k in value):raise ValueError('A JSON object is required')
    try:raw=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
    except (ValueError,TypeError,UnicodeError,RecursionError):raise ValueError('Invalid bounded JSON') from None
    if len(raw)>limit:raise ValueError('JSON exceeds its boundary')
    return raw

@dataclass(frozen=True)
class Principal:
    account_id:str
    subject:str
    def __post_init__(self):
        identifier(self.account_id)
        if not isinstance(self.subject,str) or not 1<=len(self.subject.encode('utf-8'))<=500 or any(ord(c)<32 for c in self.subject):raise ValueError('Invalid verified subject')

class WorkflowStore:
    def __init__(self,dsn,extract_task,dispatch_task,*,destination_contract,max_attempts=5,lease_seconds=600):
        self.destination_contract=reviewed_contract(destination_contract)
        if not callable(dsn)and(not isinstance(dsn,str) or not dsn):raise ValueError('Supply an operator-managed PostgreSQL connection or trusted credential factory')
        if type(max_attempts)is not int or not 1<=max_attempts<=10 or type(lease_seconds)is not int or not 10<=lease_seconds<=1800:raise ValueError('Invalid owned workflow limits')
        for task in [extract_task,dispatch_task]:
            queue=getattr(task,'queue',None)
            if not isinstance(queue,str) or not 1<=len(queue.encode('utf-8'))<=40:raise ValueError('Owned queue names must fit PostgreSQL notification channels')
            if getattr(task,'queueing_lock',None)is not None:raise ValueError('Domain-fenced workflow tasks must not inherit a queueing lock')
        self.workflow_key=extract_task.name
        if not isinstance(self.workflow_key,str) or not 1<=len(self.workflow_key.encode())<=128:raise ValueError('Invalid owned workflow identity')
        self.dsn=dsn;self.tasks={'extract':extract_task,'dispatch':dispatch_task};self.max_attempts=max_attempts;self.lease_seconds=lease_seconds
    def connect(self):
        value=self.dsn()if callable(self.dsn)else self.dsn
        if not isinstance(value,str)or not value:raise ValueError('Database credential factory did not return an owned connection')
        return psycopg.connect(value,connect_timeout=5,row_factory=dict_row,options='-c search_path=pg_catalog,workflow,pg_temp -c statement_timeout=10000 -c lock_timeout=3000')
    def _actor(self,conn,actor,roles):
        if not isinstance(actor,Principal):raise Denied('Verified application identity required')
        row=conn.execute('SELECT active,roles FROM workflow.memberships WHERE account_id=%s AND subject=%s FOR SHARE',(actor.account_id,actor.subject)).fetchone()
        if not row or not row['active'] or not set(row['roles']).intersection(roles):raise Denied('Current application membership does not authorize this operation')
    def _row(self,conn,operation_id,account_id=None,*,lock=True):
        identifier(operation_id)
        query='SELECT * FROM workflow.operations WHERE id=%s AND workflow_key=%s';params=[operation_id,self.workflow_key]
        if account_id is not None:query+=' AND account_id=%s';params.append(account_id)
        if lock:query+=' FOR UPDATE'
        row=conn.execute(query,params).fetchone()
        if not row:raise Missing('Operation unavailable')
        return row
    def _event(self,conn,row,event,actor,detail=None):
        if event not in {'submitted','claimed','result_ready','edited','approved','dispatch_claimed','sent','retry_pending','outcome_unknown','dead','recovered','approval_revoked'}:raise ValueError('Unknown owned audit event')
        detail=detail or {};canonical(detail,1500)
        conn.execute('INSERT INTO workflow.events(operation_id,account_id,event,actor,detail) VALUES(%s,%s,%s,%s,%s)',(row['id'],row['account_id'],event,actor,Jsonb(detail)))
    def _enqueue(self,conn,kind,operation_id):
        # Library API executes the queue INSERT on this exact transaction/connection.
        # Args contain identity only, never raw documents, prompts or credentials.
        # Domain row locks/unique identities already deduplicate submissions and
        # approvals. A queueing_lock could prevent retrying a stalled doing job
        # when a recovery notification is already todo, trapping both behind its
        # execution lock. Duplicate notifications are harmless; domain leases and
        # immutable approvals fence them independently of the queue's job status.
        return self.tasks[kind].configure(connection=conn,lock=str(operation_id)).defer(operation_id=str(operation_id))
    def submit(self,actor,kind,dedup_key,source_ref):
        if kind not in {'document','draft','account_change'}:raise ValueError('Unsupported owned operation kind')
        if not isinstance(dedup_key,str) or not 1<=len(dedup_key.encode())<=200:raise ValueError('Invalid stable operation identity')
        canonical(source_ref)
        with self.connect()as conn:
            self._actor(conn,actor,{'user','reviewer','supervisor','owner'})
            new=str(uuid.uuid4())
            row=conn.execute("INSERT INTO workflow.operations(id,account_id,workflow_key,kind,dedup_key,created_by,source_ref,destination_contract,state) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'pending') ON CONFLICT(account_id,workflow_key,kind,dedup_key) DO NOTHING RETURNING *",(new,actor.account_id,self.workflow_key,kind,dedup_key,actor.subject,Jsonb(source_ref),Jsonb(self.destination_contract))).fetchone()
            if not row:
                row=conn.execute('SELECT * FROM workflow.operations WHERE account_id=%s AND workflow_key=%s AND kind=%s AND dedup_key=%s',(actor.account_id,self.workflow_key,kind,dedup_key)).fetchone()
                if canonical(row['source_ref'])!=canonical(source_ref):raise Conflict('Stable identity cannot refer to a changed source')
                if row['destination_contract']!=self.destination_contract:raise Conflict('Stable identity cannot silently move to another destination contract')
                return str(row['id'])
            job=self._enqueue(conn,'extract',row['id']);conn.execute('UPDATE workflow.operations SET queue_job_id=%s WHERE id=%s',(job,row['id']));self._event(conn,row,'submitted',actor.subject)
            return str(row['id'])
    def get(self,actor,operation_id):
        with self.connect()as conn:
            self._actor(conn,actor,{'user','reviewer','supervisor','owner'});return self._row(conn,operation_id,actor.account_id,lock=False)
    def authorize(self,actor):
        with self.connect()as conn:
            self._actor(conn,actor,{'user','reviewer','supervisor','owner'})
            return conn.execute('SELECT roles FROM workflow.memberships WHERE account_id=%s AND subject=%s',(actor.account_id,actor.subject)).fetchone()['roles']
    def list(self,actor,*,before=None,limit=25):
        if type(limit)is not int or not 1<=limit<=50:raise ValueError('Invalid bounded review page')
        with self.connect()as conn:
            self._actor(conn,actor,{'user','reviewer','supervisor','owner'})
            query='SELECT * FROM workflow.operations WHERE account_id=%s AND workflow_key=%s';params=[actor.account_id,self.workflow_key]
            if before is not None:
                anchor=self._row(conn,before,actor.account_id,lock=False)
                query+=' AND (created_at,id)<(%s,%s)';params.extend([anchor['created_at'],anchor['id']])
            return conn.execute(query+' ORDER BY created_at DESC,id DESC LIMIT %s',params+[limit]).fetchall()
    def events(self,actor,operation_id):
        with self.connect()as conn:
            self._actor(conn,actor,{'user','reviewer','supervisor','owner'});self._row(conn,operation_id,actor.account_id,lock=False)
            return conn.execute('SELECT sequence,event,actor,detail,created_at FROM workflow.events WHERE operation_id=%s AND account_id=%s ORDER BY sequence',(operation_id,actor.account_id)).fetchall()
    def result_history(self,actor,operation_id,*,after_revision=0,limit=50):
        if type(after_revision)is not int or not 0<=after_revision<=2147483647 or type(limit)is not int or not 1<=limit<=50:raise ValueError('Use a bounded result history page')
        with self.connect()as conn:
            self._actor(conn,actor,{'user','reviewer','supervisor','owner'});self._row(conn,operation_id,actor.account_id,lock=False)
            return conn.execute('SELECT revision,result,actor,created_at FROM workflow.results_history WHERE operation_id=%s AND account_id=%s AND revision>%s ORDER BY revision LIMIT %s',(operation_id,actor.account_id,after_revision,limit)).fetchall()
    def _result_history(self,conn,row,actor):
        conn.execute('INSERT INTO workflow.results_history(operation_id,account_id,revision,result,actor)VALUES(%s,%s,%s,%s,%s)',(row['id'],row['account_id'],row['result_revision'],Jsonb(row['result']),actor))
    def _fingerprint(self,row,result=None):
        payload={'kind':row['kind'],'source':row['source_ref'],'destination':row['destination_contract'],'result':row['result']if result is None else result,'revision':row['result_revision']}
        return hashlib.sha256(canonical(payload,140000)).hexdigest()
    def _lease(self,conn,row,state,event):
        token=str(uuid.uuid4())
        updated=conn.execute('UPDATE workflow.operations SET state=%s,lease_token=%s,lease_until=clock_timestamp()+make_interval(secs=>%s),execution_epoch=execution_epoch+1,attempts=attempts+1,updated_at=clock_timestamp() WHERE id=%s RETURNING *',(state,token,self.lease_seconds,row['id'])).fetchone()
        self._event(conn,updated,event,'worker',{'executionEpoch':updated['execution_epoch']});return updated
    def claim_extract(self,operation_id):
        with self.connect()as conn:
            row=self._row(conn,operation_id)
            live=conn.execute('SELECT %s::timestamptz>clock_timestamp() AS live',(row['lease_until'],)).fetchone()['live']
            if row['state']not in {'pending','processing'} or (row['state']=='processing'and live):return None
            if row['attempts']>=self.max_attempts:
                conn.execute("UPDATE workflow.operations SET state='dead',lease_token=NULL,lease_until=NULL WHERE id=%s",(row['id'],));self._event(conn,row,'dead','worker',{'reason':'attempts_exhausted'});return None
            return self._lease(conn,row,'processing','claimed')
    def _check_lease(self,conn,row,token,state):
        identifier(token)
        live=conn.execute('SELECT %s::timestamptz>clock_timestamp() AS live',(row['lease_until'],)).fetchone()['live']
        if row['state']!=state or str(row['lease_token'])!=token or not live:raise LostLease('The operation lease is no longer current')
    def record_result(self,operation_id,token,result):
        canonical(result)
        with self.connect()as conn:
            row=self._row(conn,operation_id);self._check_lease(conn,row,token,'processing')
            updated=conn.execute("UPDATE workflow.operations SET result=%s,result_revision=result_revision+1,state='review',approved_hash=NULL,approved_by=NULL,lease_token=NULL,lease_until=NULL,attempts=0,updated_at=clock_timestamp() WHERE id=%s RETURNING *",(Jsonb(result),row['id'])).fetchone();self._result_history(conn,updated,'worker');self._event(conn,updated,'result_ready','worker',{'revision':updated['result_revision']});return updated
    def edit_result(self,actor,operation_id,expected_revision,result):
        canonical(result)
        if type(expected_revision)is not int:raise ValueError('An exact revision is required')
        with self.connect()as conn:
            self._actor(conn,actor,{'reviewer','supervisor','owner'});row=self._row(conn,operation_id,actor.account_id)
            if row['state']!='review' or row['result_revision']!=expected_revision:raise Conflict('Reload the current review before editing')
            updated=conn.execute('UPDATE workflow.operations SET result=%s,result_revision=result_revision+1,approved_hash=NULL,approved_by=NULL,updated_at=clock_timestamp() WHERE id=%s RETURNING *',(Jsonb(result),row['id'])).fetchone();self._result_history(conn,updated,actor.subject);self._event(conn,updated,'edited',actor.subject,{'revision':updated['result_revision']});return updated
    def approve(self,actor,operation_id,expected_revision):
        if type(expected_revision)is not int:raise ValueError('An exact revision is required')
        # Read ownership/kind without a row lock, then lock membership before the
        # operation everywhere human authorization is involved (consistent order).
        with self.connect()as conn:
            initial=self._row(conn,operation_id,actor.account_id,lock=False)
            if initial['destination_contract']!=self.destination_contract:raise Conflict('Destination contract changed; review its migration without replaying prior actions')
            roles={'supervisor','owner'}if initial['kind']=='account_change'else{'reviewer','supervisor','owner'}
            self._actor(conn,actor,roles);row=self._row(conn,operation_id,actor.account_id)
            if row['result_revision']!=expected_revision or not row['result']:raise Conflict('Review the current result before approving')
            if row['state']in {'approved','dispatching','unknown','sent'}:
                if row['approved_hash']!=self._fingerprint(row):raise Conflict('Approved content changed')
                return row
            if row['state']!='review':raise Conflict('The operation is not awaiting approval')
            digest=self._fingerprint(row);job=self._enqueue(conn,'dispatch',row['id'])
            updated=conn.execute("UPDATE workflow.operations SET state='approved',approved_hash=%s,approved_by=%s,queue_job_id=%s,attempts=0,updated_at=clock_timestamp() WHERE id=%s RETURNING *",(digest,actor.subject,job,row['id'])).fetchone();self._event(conn,updated,'approved',actor.subject,{'revision':row['result_revision'],'payloadSha256':digest});return updated
    def claim_dispatch(self,operation_id,*,verified_idempotent_replay=False):
        if type(verified_idempotent_replay)is not bool:raise ValueError('An explicit owned replay policy is required')
        with self.connect()as conn:
            initial=self._row(conn,operation_id,lock=False)
            if initial['destination_contract']!=self.destination_contract:raise Conflict('Approved destination contract no longer matches this worker')
            if not initial['approved_by']:return None
            actor=Principal(str(initial['account_id']),initial['approved_by']);roles={'supervisor','owner'}if initial['kind']=='account_change'else{'reviewer','supervisor','owner'}
            try:self._actor(conn,actor,roles)
            except Denied:
                row=self._row(conn,operation_id)
                # Unknown means an external effect may already exist. Revocation
                # cannot turn it back into a fresh review/approval/send cycle.
                if row['state']=='approved':
                    conn.execute("UPDATE workflow.operations SET state='review',approved_by=NULL,approved_hash=NULL WHERE id=%s",(row['id'],));self._event(conn,row,'approval_revoked','worker')
                return None
            row=self._row(conn,operation_id)
            if row['approved_by']!=initial['approved_by']:raise Conflict('Reload the current approval identity')
            live=conn.execute('SELECT %s::timestamptz>clock_timestamp() AS live',(row['lease_until'],)).fetchone()['live']
            if row['state']=='dispatching'and live:return None
            if row['state']not in {'approved','unknown','dispatching'}:return None
            # An expired worker may have completed its network side effect. Do not
            # infer that an expired lease means the external action never happened.
            if row['state']in {'unknown','dispatching'}and not verified_idempotent_replay:return None
            if row['approved_hash']!=self._fingerprint(row):raise Conflict('Approved payload no longer matches its immutable snapshot')
            if row['attempts']>=self.max_attempts:
                conn.execute("UPDATE workflow.operations SET state='dead',lease_token=NULL,lease_until=NULL WHERE id=%s",(row['id'],));self._event(conn,row,'dead','worker',{'reason':'dispatch_attempts_exhausted'});return None
            return self._lease(conn,row,'dispatching','dispatch_claimed')
    def record_sent(self,operation_id,token,receipt):
        canonical(receipt,1500)
        with self.connect()as conn:
            row=self._row(conn,operation_id);self._check_lease(conn,row,token,'dispatching')
            updated=conn.execute("UPDATE workflow.operations SET state='sent',receipt=%s,lease_token=NULL,lease_until=NULL,updated_at=clock_timestamp() WHERE id=%s RETURNING *",(Jsonb(receipt),row['id'])).fetchone();self._event(conn,updated,'sent','worker',{'payloadSha256':row['approved_hash']});return updated
    def recover_expired(self,*,limit=50):
        """Owned worker reconciliation, independent of a queue notification's fate.

        Crash recovery never resets attempt counts or assumes a lost network
        response means an action did not happen. Upstream stalled-job recovery is
        also required to release the queue's abandoned execution locks.
        """
        if type(limit)is not int or not 1<=limit<=100:raise ValueError('Invalid recovery batch')
        recovered=[]
        with self.connect()as conn:
            rows=conn.execute("SELECT * FROM workflow.operations WHERE workflow_key=%s AND state IN ('processing','dispatching') AND lease_until<=clock_timestamp() ORDER BY lease_until FOR UPDATE SKIP LOCKED LIMIT %s",(self.workflow_key,limit)).fetchall()
            for row in rows:
                state='unknown'if row['state']=='dispatching'else'dead'if row['attempts']>=self.max_attempts else'pending'
                job=self._enqueue(conn,'extract',row['id'])if state=='pending'else row['queue_job_id']
                conn.execute('UPDATE workflow.operations SET state=%s,execution_epoch=execution_epoch+1,lease_token=NULL,lease_until=NULL,queue_job_id=%s,updated_at=clock_timestamp() WHERE id=%s',(state,job,row['id']))
                self._event(conn,row,'outcome_unknown'if state=='unknown'else'dead'if state=='dead'else'retry_pending','recovery',{'reason':'worker_interrupted'});recovered.append(str(row['id']))
        return recovered
    def reconcile_notifications(self,*,limit=50):
        """Resume a safe pre-execution state whose queue notification was lost.

        A queue failure before a domain lease must not strand a pending invoice.
        Unknown external outcomes are deliberately excluded. This does not reset
        business attempt limits, approval identity, payload or destination.
        """
        if type(limit)is not int or not 1<=limit<=100:raise ValueError('Invalid reconciliation batch')
        repaired=[]
        with self.connect()as conn:
            rows=conn.execute("SELECT o.* FROM workflow.operations o WHERE workflow_key=%s AND state IN ('pending','approved') AND NOT EXISTS(SELECT 1 FROM workflow.procrastinate_jobs j WHERE j.task_name=CASE WHEN o.state='pending' THEN %s ELSE %s END AND j.args->>'operation_id'=o.id::text AND j.status IN ('todo','doing')) ORDER BY updated_at FOR UPDATE OF o SKIP LOCKED LIMIT %s",(self.workflow_key,self.tasks['extract'].name,self.tasks['dispatch'].name,limit)).fetchall()
            for row in rows:
                kind='extract'if row['state']=='pending'else'dispatch';task=self.tasks[kind]
                # Recheck after the row lock: another reconciler may have committed
                # a notification after the selecting statement's MVCC snapshot.
                active=conn.execute("SELECT 1 FROM workflow.procrastinate_jobs WHERE task_name=%s AND args->>'operation_id'=%s AND status IN ('todo','doing') LIMIT 1",(task.name,str(row['id']))).fetchone()
                if active:continue
                job=self._enqueue(conn,kind,row['id']);conn.execute('UPDATE workflow.operations SET queue_job_id=%s,updated_at=clock_timestamp()WHERE id=%s',(job,row['id']));self._event(conn,row,'retry_pending','recovery',{'reason':'queue_notification_interrupted'});repaired.append(str(row['id']))
        return repaired
    def fail(self,operation_id,token,reason,*,retryable=False,ambiguous=True):
        if type(retryable)is not bool or type(ambiguous)is not bool:raise ValueError('Explicit worker failure decisions are required')
        if reason not in {'source_unavailable','invalid_result','model_unavailable','destination_unavailable','destination_rejected','worker_interrupted'}:raise ValueError('Use an owned error category, never raw provider/input text')
        with self.connect()as conn:
            row=self._row(conn,operation_id)
            if row['state']not in {'processing','dispatching'}:raise LostLease('Operation is not executing')
            self._check_lease(conn,row,token,row['state'])
            state='unknown'if row['state']=='dispatching'and ambiguous else ('pending'if row['state']=='processing'else'approved')if retryable and row['attempts']<self.max_attempts else'dead'
            updated=conn.execute('UPDATE workflow.operations SET state=%s,lease_token=NULL,lease_until=NULL,updated_at=clock_timestamp() WHERE id=%s RETURNING *',(state,row['id'])).fetchone();self._event(conn,updated,'outcome_unknown'if state=='unknown'else'dead'if state=='dead'else'retry_pending','worker',{'reason':reason});return updated
    def recover_extraction(self,actor,operation_id):
        with self.connect()as conn:
            self._actor(conn,actor,{'supervisor','owner'});row=self._row(conn,operation_id,actor.account_id)
            if row['state']!='dead' or row['approved_hash']:raise Conflict('Only a failed pre-approval extraction can be explicitly recovered here')
            job=self._enqueue(conn,'extract',row['id']);updated=conn.execute("UPDATE workflow.operations SET state='pending',attempts=0,execution_epoch=execution_epoch+1,lease_token=NULL,lease_until=NULL,queue_job_id=%s,updated_at=clock_timestamp() WHERE id=%s RETURNING *",(job,row['id'])).fetchone();self._event(conn,updated,'recovered',actor.subject);return updated
