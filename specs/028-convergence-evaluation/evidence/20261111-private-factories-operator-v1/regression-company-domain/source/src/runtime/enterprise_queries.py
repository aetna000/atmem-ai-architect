"""Encrypted durable question jobs; PostgreSQL/Procrastinate, no private queue args.

Raw browser cookies, JWTs, source credentials, questions and answers never enter
queue arguments. Domain leases independently fence duplicate/stale workers. A
ready result is only internal evidence until current native sources reauthorize it.
"""
from contextlib import contextmanager
from dataclasses import dataclass,field
import hashlib
import json
from pathlib import Path
import re
import uuid
import procrastinate
from procrastinate.schema import SchemaManager
from psycopg import sql
from enterprise_identity import CompanyPrincipal
from enterprise_sources import query_text,SourceDenied,SourceUnavailable

TASK='enterprise.answer.v1'
QUEUE='enterprise-answer'

def task_identity(account_id):
    if not isinstance(account_id,str)or not re.fullmatch('[A-Za-z0-9_-]{1,128}',account_id):raise ValueError('Supply the owned company account')
    suffix=hashlib.sha256(account_id.encode()).hexdigest()[:16]
    return TASK+'.'+suffix,QUEUE+'-'+suffix


class QueryMissing(LookupError):pass
class QueryConflict(ValueError):pass
class QueryLeaseLost(SourceUnavailable):pass


def identifier(value):
    if not isinstance(value,str)or str(uuid.UUID(value))!=value:raise ValueError('Use a canonical request identity')
    return value


@dataclass(frozen=True)
class QueryLease:
    id: str
    token: str=field(repr=False)
    principal: CompanyPrincipal=field(repr=False)
    session_id: str=field(repr=False)
    question: str=field(repr=False)
    attempt: int


class EnterpriseQueryStore:
    def __init__(self,auth,task,account_id,*,lease_seconds=120,ttl_seconds=900):
        name,queue=task_identity(account_id)
        if task.name!=name or task.queue!=queue or getattr(task,'queueing_lock',None)is not None:raise ValueError('Use the owned query task without a queueing lock')
        if type(lease_seconds)is not int or not 15<=lease_seconds<=600 or type(ttl_seconds)is not int or not lease_seconds<=ttl_seconds<=3600:raise ValueError('Invalid owned query deadlines')
        self.auth=auth;self.task=task;self.account_id=account_id;self.lease_seconds=lease_seconds;self.ttl_seconds=ttl_seconds

    @contextmanager
    def transaction(self):
        with self.auth.transaction()as cur:
            cur.execute('SET LOCAL search_path=pg_catalog,enterprise_queries,pg_temp')
            yield cur

    def context(self,row,purpose):
        result=['knowledge-query',purpose,row['account_id'],row['principal_key'],row['session_sha256'],str(row['id'])]
        if purpose=='answer':result.append(row['attempt'])
        return result

    def _principal(self,cur,session_id):
        if not isinstance(session_id,str)or not re.fullmatch('[0-9a-f]{64}',session_id):raise SourceDenied('company_identity_required')
        row=cur.execute('SELECT s.account_id,s.principal_key,extract(epoch FROM s.expires_at)::bigint AS expires_at,m.issuer,m.subject FROM enterprise_auth.sessions s JOIN enterprise_auth.memberships m USING(account_id,principal_key)WHERE s.session_sha256=%s AND s.revoked_at IS NULL AND s.expires_at>clock_timestamp()',(session_id,)).fetchone()
        if not row:raise SourceDenied('company_identity_required')
        principal=CompanyPrincipal(row['account_id'],row['issuer'],row['subject'],row['expires_at'])
        if principal.key!=row['principal_key']or principal.account_id!=self.account_id:raise SourceDenied('company_identity_required')
        self.auth._authorize(cur,principal)
        return principal

    def _owner(self,cur,session):
        principal=self._principal(cur,session.id)
        if principal.account_id!=session.principal.account_id or principal.key!=session.principal.key:raise SourceDenied('company_identity_required')
        return principal

    def _row(self,cur,identity):
        identifier(identity)
        return cur.execute('SELECT *,expires_at>clock_timestamp()AS current,lease_until>clock_timestamp()AS leased FROM enterprise_queries.requests WHERE id=%s AND account_id=%s FOR UPDATE',(identity,self.account_id)).fetchone()

    def _event(self,cur,row,event):
        cur.execute('INSERT INTO enterprise_queries.events(query_id,account_id,principal_key,event,attempt)VALUES(%s,%s,%s,%s,%s)',(row['id'],row['account_id'],row['principal_key'],event,row['attempt']))

    def _end(self,cur,row,state,error=None):
        cur.execute('UPDATE enterprise_queries.requests SET state=%s,error_code=%s,question_ciphertext=NULL,result_ciphertext=NULL,lease_token=NULL,lease_until=NULL,updated_at=clock_timestamp()WHERE id=%s',(state,error,row['id']))
        self._event(cur,row,state)

    def _enqueue(self,cur,identity,*,delay=0):
        # No execution lock: domain leases fence duplicate notifications and allow
        # a replacement to recover an expired lease while an old worker winds down.
        scheduled=None
        if delay:
            scheduled=cur.execute('SELECT clock_timestamp()+make_interval(secs=>%s)AS at',(delay,)).fetchone()['at']
        self.task.configure(connection=cur.connection,schedule_at=scheduled).defer(query_id=str(identity))

    def submit(self,session,question,request_key):
        question=query_text(question);identifier(request_key)
        with self.transaction()as cur:
            principal=self._owner(cur,session)
            digest=self.auth.box.fingerprint(['question',principal.account_id,principal.key,session.id,request_key],question)
            cur.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('knowledge-query:'+principal.account_id+':'+principal.key,))
            existing=cur.execute('SELECT * FROM enterprise_queries.requests WHERE account_id=%s AND principal_key=%s AND session_sha256=%s AND request_key=%s FOR UPDATE',(principal.account_id,principal.key,session.id,request_key)).fetchone()
            if existing:
                if existing['question_mac']!=digest:raise QueryConflict('Request identity already refers to another question')
                return str(existing['id'])
            count=cur.execute("SELECT count(*)AS n FROM enterprise_queries.requests WHERE account_id=%s AND principal_key=%s AND state IN('queued','running')AND expires_at>clock_timestamp()",(principal.account_id,principal.key)).fetchone()['n']
            if count>=3:raise SourceUnavailable('query_capacity_reached')
            row={'id':str(uuid.uuid4()),'account_id':principal.account_id,'principal_key':principal.key,'session_sha256':session.id,'attempt':0}
            encrypted=self.auth.box.seal(self.context(row,'question'),{'question':question})
            cur.execute("INSERT INTO enterprise_queries.requests(id,account_id,principal_key,session_sha256,request_key,question_mac,question_ciphertext,state,expires_at)VALUES(%s,%s,%s,%s,%s,%s,%s,'queued',least(to_timestamp(%s),clock_timestamp()+make_interval(secs=>%s)))",(row['id'],principal.account_id,principal.key,session.id,request_key,digest,encrypted,principal.expires_at,self.ttl_seconds))
            self._enqueue(cur,row['id']);self._event(cur,row,'submitted')
            return row['id']

    def get(self,session,identity):
        with self.transaction()as cur:
            principal=self._owner(cur,session);row=self._row(cur,identity)
            if not row or row['account_id']!=principal.account_id or row['principal_key']!=principal.key or row['session_sha256']!=session.id:raise QueryMissing('Question unavailable')
            if not row['current']and row['state']!='expired':
                self._end(cur,row,'expired');row.update(state='expired',question_ciphertext=None,result_ciphertext=None)
            return row

    def cancel(self,session,identity):
        with self.transaction()as cur:
            principal=self._owner(cur,session);row=self._row(cur,identity)
            if not row or row['account_id']!=principal.account_id or row['principal_key']!=principal.key or row['session_sha256']!=session.id:raise QueryMissing('Question unavailable')
            if row['state']not in {'cancelled','expired'}:self._end(cur,row,'cancelled')

    def pending(self,session):
        with self.transaction()as cur:
            principal=self._owner(cur,session)
            rows=cur.execute("SELECT * FROM enterprise_queries.requests WHERE account_id=%s AND principal_key=%s AND session_sha256=%s AND state IN('queued','running','ready')AND expires_at>clock_timestamp()ORDER BY created_at DESC LIMIT 3",(principal.account_id,principal.key,session.id)).fetchall()
            return [{'id':str(row['id']),'status':row['state'],'question':self.auth.box.open(self.context(row,'question'),row['question_ciphertext'])['question']}for row in reversed(rows)]

    def claim(self,identity):
        with self.transaction()as cur:
            row=self._row(cur,identity)
            if not row:return None
            if not row['current']:
                if row['state']!='expired':self._end(cur,row,'expired')
                return None
            if row['state']not in {'queued','running'}or(row['state']=='running'and row['leased']):return None
            try:principal=self._principal(cur,row['session_sha256'])
            except SourceDenied:
                self._end(cur,row,'cancelled');return None
            if principal.account_id!=row['account_id']or principal.key!=row['principal_key']:self._end(cur,row,'cancelled');return None
            if row['attempt']>=3:self._end(cur,row,'failed','unavailable');return None
            question=self.auth.box.open(self.context(row,'question'),row['question_ciphertext'])['question'];query_text(question)
            if self.auth.box.fingerprint(['question',row['account_id'],row['principal_key'],row['session_sha256'],str(row['request_key'])],question)!=row['question_mac']:raise SourceDenied('query_binding_invalid')
            token=str(uuid.uuid4());row['attempt']+=1
            cur.execute("UPDATE enterprise_queries.requests SET state='running',attempt=%s,lease_token=%s,lease_until=least(expires_at,clock_timestamp()+make_interval(secs=>%s)),result_ciphertext=NULL,error_code=NULL,updated_at=clock_timestamp()WHERE id=%s",(row['attempt'],token,self.lease_seconds,identity))
            self._event(cur,row,'claimed')
            return QueryLease(identity,token,principal,row['session_sha256'],question,row['attempt'])

    def _lease(self,cur,lease):
        row=self._row(cur,lease.id)
        if not row or row['state']!='running'or not row['current']or not row['leased']or str(row['lease_token'])!=lease.token or row['attempt']!=lease.attempt:raise QueryLeaseLost('Question worker lease changed')
        principal=self._principal(cur,row['session_sha256'])
        if principal.account_id!=lease.principal.account_id or principal.key!=lease.principal.key:raise SourceDenied('company_identity_required')
        return row

    def guard(self,lease,*,renew=False):
        with self.transaction()as cur:
            row=self._lease(cur,lease)
            if renew:cur.execute('UPDATE enterprise_queries.requests SET lease_until=least(expires_at,clock_timestamp()+make_interval(secs=>%s))WHERE id=%s',(self.lease_seconds,row['id']))

    def complete(self,lease,receipt):
        if not isinstance(receipt,dict)or receipt.get('question')!=lease.question or len(json.dumps(receipt,ensure_ascii=False,allow_nan=False).encode())>500000:raise ValueError('Invalid owned answer receipt')
        with self.transaction()as cur:
            row=self._lease(cur,lease);cipher=self.auth.box.seal(self.context(row,'answer'),receipt)
            cur.execute("UPDATE enterprise_queries.requests SET state='ready',result_ciphertext=%s,lease_token=NULL,lease_until=NULL,updated_at=clock_timestamp()WHERE id=%s",(cipher,row['id']));self._event(cur,row,'ready')

    def failed(self,lease,code,*,retry=False):
        if code not in {'source','setup','signin','unavailable','answer'}:raise ValueError('Use an owned public failure code')
        with self.transaction()as cur:
            row=self._row(cur,lease.id)
            if not row or row['state']!='running'or str(row['lease_token'])!=lease.token or row['attempt']!=lease.attempt:return
            if retry and row['current']and row['attempt']<3:
                cur.execute("UPDATE enterprise_queries.requests SET state='queued',lease_token=NULL,lease_until=NULL,error_code=NULL,updated_at=clock_timestamp()WHERE id=%s",(row['id'],))
                self._enqueue(cur,row['id'],delay=5*row['attempt']);self._event(cur,row,'retry_pending')
            else:self._end(cur,row,'failed',code)

    def open_result(self,row):
        if row['state']!='ready':raise QueryConflict('Question is not ready')
        return self.auth.box.open(self.context(row,'answer'),row['result_ciphertext'])

    def released(self,session,identity,attempt):
        with self.transaction()as cur:
            principal=self._owner(cur,session);row=self._row(cur,identity)
            if not row or row['account_id']!=principal.account_id or row['principal_key']!=principal.key or row['session_sha256']!=session.id:raise QueryMissing('Question unavailable')
            if not row['current']or row['state']!='ready'or row['attempt']!=attempt:raise QueryLeaseLost('Question changed before release')
            self._event(cur,row,'released')

    def requeue(self,session,identity,attempt):
        with self.transaction()as cur:
            principal=self._owner(cur,session);row=self._row(cur,identity)
            if not row or row['account_id']!=principal.account_id or row['principal_key']!=principal.key or row['session_sha256']!=session.id:raise QueryMissing('Question unavailable')
            if row['state']!='ready'or row['attempt']!=attempt:return
            if not row['current']or row['attempt']>=3:self._end(cur,row,'failed','answer');return
            cur.execute("UPDATE enterprise_queries.requests SET state='queued',result_ciphertext=NULL,error_code=NULL,updated_at=clock_timestamp()WHERE id=%s",(identity,));self._enqueue(cur,identity);self._event(cur,row,'retry_pending')

    def recover(self,limit=50):
        if type(limit)is not int or not 1<=limit<=100:raise ValueError('Use a bounded recovery batch')
        with self.transaction()as cur:
            rows=cur.execute("SELECT r.*,expires_at>clock_timestamp()AS current FROM enterprise_queries.requests r WHERE account_id=%s AND((state!='expired'AND expires_at<clock_timestamp())OR(state='running'AND lease_until<clock_timestamp())OR(state='queued'AND NOT EXISTS(SELECT 1 FROM enterprise_queries.procrastinate_jobs j WHERE j.task_name=%s AND j.args->>'query_id'=r.id::text AND j.status IN('todo','doing'))))ORDER BY updated_at FOR UPDATE OF r SKIP LOCKED LIMIT %s",(self.account_id,self.task.name,limit)).fetchall()
            for row in rows:
                if not row['current']:self._end(cur,row,'expired')
                elif row['attempt']>=3:self._end(cur,row,'failed','unavailable')
                else:
                    cur.execute("UPDATE enterprise_queries.requests SET state='queued',lease_token=NULL,lease_until=NULL,result_ciphertext=NULL,updated_at=clock_timestamp()WHERE id=%s",(row['id'],));self._enqueue(cur,row['id']);self._event(cur,row,'retry_pending')
            return len(rows)


def producer_queries(auth,dsn,account_id):
    app=procrastinate.App(connector=procrastinate.SyncPsycopgConnector(conninfo=dsn,kwargs={'connect_timeout':5,'options':'-c search_path=pg_catalog,enterprise_queries,pg_temp'}))
    def worker_only(query_id):raise RuntimeError('Run the owned dedicated query worker')
    name,queue=task_identity(account_id)
    task=app.task(name=name,queue=queue)(worker_only)
    return EnterpriseQueryStore(auth,task,account_id)


def initialize_query_store(conn):
    if procrastinate.__version__!='3.10.0' or conn.autocommit:raise ValueError('Use the reviewed queue version and an operator transaction')
    body=Path(__file__).with_name('enterprise_queries_schema.sql').read_bytes()
    conn.execute('CREATE SCHEMA enterprise_queries');conn.execute('SET LOCAL search_path=enterprise_queries,pg_catalog')
    conn.execute(SchemaManager.get_schema());conn.execute(body.decode())
    conn.execute('INSERT INTO enterprise_queries.schema_version VALUES(1,%s,%s)',(hashlib.sha256(body).hexdigest(),procrastinate.__version__))
    for objects in ['TABLES','SEQUENCES','FUNCTIONS']:conn.execute('REVOKE ALL ON ALL '+objects+' IN SCHEMA enterprise_queries FROM PUBLIC')
    conn.execute('REVOKE ALL ON SCHEMA enterprise_queries FROM PUBLIC')


def grant_query_runtime(conn,role,*,worker=False):
    if conn.autocommit or not isinstance(role,str)or not re.fullmatch('[A-Za-z0-9_.@-]{1,63}',role)or type(worker)is not bool:raise ValueError('Use an owned runtime role and operator transaction')
    expected=hashlib.sha256(Path(__file__).with_name('enterprise_queries_schema.sql').read_bytes()).hexdigest()
    if conn.execute('SELECT version,source_sha256,queue_version FROM enterprise_queries.schema_version').fetchone()!=(1,expected,'3.10.0'):raise ValueError('Review the exact fresh query schema before granting access')
    flags=conn.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls,rolcanlogin FROM pg_roles WHERE rolname=%s',(role,)).fetchone()
    if not flags or any(flags[:5])or not flags[5]or conn.execute("SELECT has_schema_privilege(%s,'enterprise_queries','CREATE')",(role,)).fetchone()[0]:raise ValueError('Use a nonadministrative role that does not own the query schema')
    for table in ['memberships','source_mappings','schema_version']:
        if conn.execute('SELECT has_table_privilege(%s,%s,%s)',(role,'enterprise_auth.'+table,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER,REFERENCES')).fetchone()[0]:raise ValueError('Question runtime must not inherit authority-table write privileges')
    target=sql.Identifier(role)
    conn.execute(sql.SQL('GRANT USAGE ON SCHEMA enterprise_queries TO {}').format(target))
    conn.execute(sql.SQL('GRANT SELECT ON enterprise_queries.schema_version TO {}').format(target))
    conn.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE ON enterprise_queries.requests TO {}').format(target))
    conn.execute(sql.SQL('GRANT INSERT ON enterprise_queries.events TO {}').format(target))
    conn.execute(sql.SQL('GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA enterprise_queries TO {}').format(target))
    conn.execute(sql.SQL('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA enterprise_queries TO {}').format(target))
    conn.execute(sql.SQL('GRANT SELECT,INSERT ON enterprise_queries.procrastinate_jobs,enterprise_queries.procrastinate_events TO {}').format(target))
    if worker:
        for table in ['procrastinate_jobs','procrastinate_events','procrastinate_workers','procrastinate_periodic_defers']:
            conn.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE ON enterprise_queries.{} TO {}').format(sql.Identifier(table),target))
