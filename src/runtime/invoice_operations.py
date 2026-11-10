"""Separate operator authority for retention, recovery and staff membership.

Never import this module into an HTTP handler. Runtime SQL logins cannot perform
these operations. Restore/reconciliation require paused, isolated workloads.
Expired-only cleanup serializes table mutation and refuses live jobs/leases;
ordinary active and younger operations are preserved during online maintenance.
All calls require an explicit transaction; receipts contain counts, not documents.
"""
import hashlib
from pathlib import Path
import re
import uuid
from psycopg.rows import tuple_row
from psycopg.types.json import Jsonb
from durable_workflow import canonical

def owned_scope(conn,account_id,namespace):
    if conn.autocommit:raise ValueError('Use one operator transaction')
    if not isinstance(account_id,str)or str(uuid.UUID(account_id))!=account_id:raise ValueError('Use the owned canonical account UUID')
    if not isinstance(namespace,str)or not re.fullmatch(r'[a-zA-Z0-9-]{1,20}',namespace):raise ValueError('Use the owned workflow namespace')
    with conn.cursor(row_factory=tuple_row)as cur:
        authority=cur.execute("SELECT pg_has_role(current_user,nspowner,'USAGE') FROM pg_namespace WHERE nspname='workflow'").fetchone()
        version=cur.execute('SELECT version,source_sha256,queue_version FROM workflow.schema_version').fetchone()
    expected=hashlib.sha256((Path(__file__).parent/'workflow_schema.sql').read_bytes()).hexdigest()
    if not authority or authority[0]is not True:raise PermissionError('Use the separate reviewed schema-owner/operator connection')
    if version!=(1,expected,'3.10.0'):raise ValueError('Review the schema migration before operating this database')
    conn.execute('SET LOCAL search_path=pg_catalog,workflow,pg_temp')
    conn.execute("SET LOCAL lock_timeout='3s'");conn.execute("SET LOCAL statement_timeout='30s'")
    conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('atmem-invoice-operations:'+account_id+':'+namespace,))
    return namespace+'.extract',namespace+'.dispatch'

def quiescent_rows(conn,account_id,namespace,*,expired=False,restoring=False,limit=500):
    extract,dispatch=owned_scope(conn,account_id,namespace)
    if type(limit)is not int or not 1<=limit<=500:raise ValueError('Use a bounded maintenance batch')
    # One table-lock order for every operator action. A running task retains a
    # doing queue row even while its external network request is outside SQL.
    conn.execute('LOCK TABLE workflow.operations IN SHARE ROW EXCLUSIVE MODE')
    conn.execute('LOCK TABLE workflow.procrastinate_jobs IN SHARE ROW EXCLUSIVE MODE')
    with conn.cursor(row_factory=tuple_row)as cur:
        restoration_filter=" AND(state IN('approved','dispatching','processing')OR EXISTS(SELECT 1 FROM workflow.procrastinate_jobs j WHERE j.task_name=ANY(%s)AND j.args->>'operation_id'=workflow.operations.id::text))"if restoring else''
        rows=cur.execute("SELECT id FROM workflow.operations WHERE account_id=%s AND workflow_key=%s"+(" AND created_at <= clock_timestamp()-interval '90 days'"if expired else'')+restoration_filter+' ORDER BY created_at,id LIMIT %s FOR UPDATE',(account_id,extract,*([[extract,dispatch]]if restoring else[]),limit)).fetchall()
        ids=[str(row[0])for row in rows]
        if ids:
            live=cur.execute("SELECT EXISTS(SELECT 1 FROM workflow.procrastinate_jobs WHERE task_name=ANY(%s)AND args->>'operation_id'=ANY(%s)AND status='doing')OR EXISTS(SELECT 1 FROM workflow.operations WHERE id::text=ANY(%s)AND lease_until>clock_timestamp())",([extract,dispatch],ids,ids)).fetchone()[0]
            if live and not restoring:raise ValueError('Settle live execution jobs/leases before expired-record maintenance')
    return ids,extract,dispatch

def purge_expired(conn,*,account_id,namespace='invoice',limit=500):
    ids,extract,dispatch=quiescent_rows(conn,account_id,namespace,expired=True,limit=limit)
    if ids:
        # Only owned task identities and exact operation IDs. Queue event rows
        # cascade through the native library schema; no global queue truncation.
        conn.execute("DELETE FROM workflow.procrastinate_jobs WHERE task_name=ANY(%s)AND args->>'operation_id'=ANY(%s)",([extract,dispatch],ids))
        for table in ['events','results_history','operations']:
            column='id'if table=='operations'else'operation_id'
            conn.execute('DELETE FROM workflow.'+table+' WHERE account_id=%s AND '+column+'::text=ANY(%s)',(account_id,ids))
    return{'purgedOperations':len(ids),'retentionDays':90,'batchLimit':limit,'moreMayRemain':len(ids)==limit,'originalObjects':'Native private-store lifecycle; provider deletion is asynchronous. No object-read or deletion authority is conferred on this SQL tool.'}

def quarantine_restored_deliveries(conn,*,account_id,workloads_stopped,namespace='invoice',limit=500):
    # This explicit assertion is operator authorization, not a software proof
    # that a cloud workload is stopped. Run only against the isolated restored
    # database before changing application endpoints or starting any worker.
    if workloads_stopped is not True:raise ValueError('Confirm workloads are stopped and the restored database is isolated')
    ids,extract,dispatch=quiescent_rows(conn,account_id,namespace,restoring=True,limit=limit)
    if not ids:return{'quarantinedDeliveries':0,'resetExtractions':0,'batchLimit':limit,'moreMayRemain':False}
    # Keep payload and approval hashes. A restored database cannot know what the
    # destination accepted after its recovery point; never infer no side effect.
    with conn.cursor(row_factory=tuple_row)as cur:
        rows=cur.execute("UPDATE workflow.operations SET state='unknown',lease_token=NULL,lease_until=NULL,execution_epoch=execution_epoch+1,updated_at=clock_timestamp() WHERE account_id=%s AND id::text=ANY(%s)AND state IN('approved','dispatching') RETURNING id,approved_hash",(account_id,ids)).fetchall()
    for operation,digest in rows:
        conn.execute("INSERT INTO workflow.events(operation_id,account_id,event,actor,detail)VALUES(%s,%s,'outcome_unknown','operator:restore',%s)",(operation,account_id,Jsonb({'reason':'database_restored','payloadSha256':digest})))
    with conn.cursor(row_factory=tuple_row)as cur:
        processing=cur.execute("UPDATE workflow.operations SET state='pending',lease_token=NULL,lease_until=NULL,execution_epoch=execution_epoch+1,updated_at=clock_timestamp() WHERE account_id=%s AND id::text=ANY(%s)AND state='processing' RETURNING id",(account_id,ids)).fetchall()
    for operation, in processing:
        conn.execute("INSERT INTO workflow.events(operation_id,account_id,event,actor,detail)VALUES(%s,%s,'recovered','operator:restore',%s)",(operation,account_id,Jsonb({'reason':'restored_extraction_fenced'})))
    # All restored notifications may carry stale native doing/worker state.
    # Pending extraction intent is reconstructed by reconcile_notifications after
    # expiry cleanup. Unknown delivery intent is never automatically requeued.
    conn.execute("DELETE FROM workflow.procrastinate_jobs WHERE task_name=ANY(%s)AND args->>'operation_id'=ANY(%s)",([extract,dispatch],ids))
    return{'quarantinedDeliveries':len(rows),'resetExtractions':len(processing),'batchLimit':limit,'moreMayRemain':len(ids)==limit}

def reconcile_completed(conn,*,account_id,operation_id,payload_sha256,external_id,operator,namespace='invoice'):
    extract,dispatch=owned_scope(conn,account_id,namespace)
    if not isinstance(operation_id,str)or str(uuid.UUID(operation_id))!=operation_id:raise ValueError('Use the exact operation identity')
    if not isinstance(payload_sha256,str)or not re.fullmatch(r'[0-9a-f]{64}',payload_sha256):raise ValueError('Use the independently checked approval digest')
    if not isinstance(external_id,str)or not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,200}',external_id):raise ValueError('Use the independently verified accounting receipt identity')
    if not isinstance(operator,str)or not re.fullmatch(r'[A-Za-z0-9_.@:/-]{1,200}',operator):raise ValueError('Record the accountable operator')
    conn.execute('LOCK TABLE workflow.operations IN SHARE ROW EXCLUSIVE MODE');conn.execute('LOCK TABLE workflow.procrastinate_jobs IN SHARE ROW EXCLUSIVE MODE')
    with conn.cursor(row_factory=tuple_row)as cur:
        row=cur.execute('SELECT state,approved_hash,kind,source_ref,destination_contract,result,result_revision,lease_until FROM workflow.operations WHERE account_id=%s AND id=%s AND workflow_key=%s FOR UPDATE',(account_id,operation_id,extract)).fetchone()
        active=cur.execute("SELECT EXISTS(SELECT 1 FROM workflow.procrastinate_jobs WHERE task_name=%s AND args->>'operation_id'=%s AND status='doing')",(dispatch,operation_id)).fetchone()[0]
    if not row or row[0]not in {'unknown','dead'}or row[1]!=payload_sha256 or active or row[7]is not None:raise ValueError('Reconcile only an inactive uncertain delivery with its exact approval digest')
    snapshot={'kind':row[2],'source':row[3],'destination':row[4],'result':row[5],'revision':row[6]}
    if hashlib.sha256(canonical(snapshot,140000)).hexdigest()!=payload_sha256:raise ValueError('Approved snapshot changed; do not invent completion')
    receipt={'externalId':external_id,'operationId':operation_id,'payloadSha256':payload_sha256,'reconciledBy':operator}
    conn.execute("UPDATE workflow.operations SET state='sent',receipt=%s,updated_at=clock_timestamp() WHERE id=%s",(Jsonb(receipt),operation_id))
    conn.execute("INSERT INTO workflow.events(operation_id,account_id,event,actor,detail)VALUES(%s,%s,'sent',%s,%s)",(operation_id,account_id,'operator:'+operator,Jsonb({'payloadSha256':payload_sha256,'reconciled':True})))
    conn.execute("DELETE FROM workflow.procrastinate_jobs WHERE task_name=%s AND args->>'operation_id'=%s",(dispatch,operation_id))
    return{'state':'sent','receipt':receipt}

def set_membership(conn,*,account_id,subject,roles,active=True,namespace='invoice'):
    owned_scope(conn,account_id,namespace)
    if not isinstance(subject,str)or not 1<=len(subject.encode())<=500 or any(ord(c)<32 for c in subject):raise ValueError('Use the verified native login subject, never a display-name guess')
    if type(active)is not bool or not isinstance(roles,list)or not roles or len(set(roles))!=len(roles)or not set(roles)<={'user','reviewer','supervisor','owner'}:raise ValueError('Use an explicit reviewed role set')
    conn.execute('INSERT INTO workflow.accounts(id)VALUES(%s)ON CONFLICT DO NOTHING',(account_id,))
    conn.execute('INSERT INTO workflow.memberships(account_id,subject,roles,active)VALUES(%s,%s,%s,%s)ON CONFLICT(account_id,subject)DO UPDATE SET roles=excluded.roles,active=excluded.active',(account_id,subject,roles,active))
    return{'active':active,'roles':roles}
