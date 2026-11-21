"""Fixed bounded operating jobs; trusted operator authority, no HTTP/model input.

SQL cleanup affects only expired records in the exact account/task namespace.
Original-object expiry remains the native private-store lifecycle. Monitoring
reports counts, never source documents, identities, amounts or delivery payloads.
"""
from psycopg.rows import tuple_row
from invoice_operator_core import validate_deployment
from invoice_operations import owned_scope,purge_expired

def maintain(connect,deployment,*,batch_limit=500,max_batches=20):
    scope=validate_deployment(deployment)
    if type(batch_limit)is not int or not 1<=batch_limit<=500 or type(max_batches)is not int or not 1<=max_batches<=20:raise ValueError('Use a bounded maintenance execution')
    count=0
    for batch in range(max_batches):
        with connect(None)as conn:receipt=purge_expired(conn,**scope,limit=batch_limit)
        count+=receipt['purgedOperations']
        if not receipt['moreMayRemain']:
            return {'status':'ok','purgedOperations':count,'batches':batch+1,'retentionDays':90}
    # A full final batch is not proof of a backlog (it may be the last batch).
    # Read an exact scoped existence check rather than misreporting success or
    # escalating an empty boundary after a multiple of batch_limit records.
    with connect(None)as conn:
        extract,_=owned_scope(conn,**scope)
        with conn.cursor(row_factory=tuple_row)as cursor:
            remaining=cursor.execute("SELECT EXISTS(SELECT 1 FROM workflow.operations WHERE account_id=%s AND workflow_key=%s AND created_at<=clock_timestamp()-interval '90 days')",(scope['account_id'],extract)).fetchone()[0]
    return {'status':'backlog'if remaining else'ok','purgedOperations':count,'batches':max_batches,'retentionDays':90}

def monitor(connect,deployment,*,stalled_seconds=7200):
    scope=validate_deployment(deployment)
    if type(stalled_seconds)is not int or not 600<=stalled_seconds<=86400:raise ValueError('Use a reviewed operational threshold')
    with connect(None)as conn:
        if conn.autocommit:raise ValueError('Use one read-only monitoring transaction')
        conn.execute('SET TRANSACTION READ ONLY')
        extract,_=owned_scope(conn,**scope)
        with conn.cursor(row_factory=tuple_row)as cursor:
            rows=cursor.execute('SELECT state,count(*)FROM workflow.operations WHERE account_id=%s AND workflow_key=%s GROUP BY state',(scope['account_id'],extract)).fetchall()
            stalled,expired_leases,overdue=cursor.execute("SELECT count(*)FILTER(WHERE state IN('pending','approved') AND updated_at<=clock_timestamp()-make_interval(secs=>%s)),count(*)FILTER(WHERE state IN('processing','dispatching') AND lease_until<=clock_timestamp()),count(*)FILTER(WHERE created_at<=clock_timestamp()-interval '92 days') FROM workflow.operations WHERE account_id=%s AND workflow_key=%s",(stalled_seconds,scope['account_id'],extract)).fetchone()
    states=dict(rows)
    return {'status':'attention'if stalled or expired_leases or overdue or states.get('unknown',0)or states.get('dead',0)else'ok','states':states,'stalledWork':stalled,'expiredLeases':expired_leases,'retentionOverdue':overdue,'stalledSeconds':stalled_seconds,'retentionGraceDays':2}
