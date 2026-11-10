"""Owned SQL bootstrap/enrollment/revocation; never an HTTP user operation.

Existing company/source IDs come from the approved directory/IT handoff. Do not
self-activate a source mapping by matching email strings or unverified JWT claims.
No cloud identity, database, role, replacement key or source registration is created.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hashlib
import json
import os
from psycopg.rows import dict_row
import psycopg
from enterprise_configuration import deployment,read_deployment,native_database,session_domain
from enterprise_auth_store import initialize_auth_store,grant_auth_runtime
from enterprise_audit import initialize_audit,grant_audit_writer
from enterprise_extraction_cache import initialize_extraction_cache,grant_extraction_runtime
from enterprise_queries import initialize_query_store,grant_query_runtime
from enterprise_document_jobs import initialize_document_jobs,grant_document_jobs_runtime
from enterprise_secrets import SecretFiles
from public_faq import object_pairs


def initialize(conn,api_role,worker_role):
    if conn.autocommit or not isinstance(api_role,str)or not isinstance(worker_role,str)or api_role==worker_role:
        raise ValueError('Use an operator transaction and separate existing API/worker SQL identities')
    with conn.transaction():
        existing=conn.execute("SELECT count(*)FROM pg_namespace WHERE nspname IN('enterprise_auth','enterprise_queries','enterprise_extractions','enterprise_audit','enterprise_document_jobs')").fetchone()[0]
        if existing:raise ValueError('Private schemas already exist; no adoption or implicit migration is permitted')
        initialize_auth_store(conn);initialize_query_store(conn);initialize_extraction_cache(conn);initialize_audit(conn);initialize_document_jobs(conn)
        grant_auth_runtime(conn,api_role);grant_query_runtime(conn,api_role);grant_audit_writer(conn,api_role)
        grant_auth_runtime(conn,worker_role);grant_query_runtime(conn,worker_role,worker=True)
        grant_extraction_runtime(conn,worker_role);grant_audit_writer(conn,worker_role);grant_document_jobs_runtime(conn,worker_role)


def checked_identity(metadata,subject):
    owned=deployment(metadata)
    if not isinstance(subject,str)or not 1<=len(subject.encode('utf-8'))<=255 or any(ord(c)<32 for c in subject):
        raise ValueError('Supply the existing verified company API subject from the approved directory handoff')
    key=hashlib.sha256((owned['company']['issuer']+'\0'+subject).encode()).hexdigest()
    return owned,key


def require_schema(cursor):
    for schema,filename in [('enterprise_auth','enterprise_auth_schema.sql'),('enterprise_queries','enterprise_queries_schema.sql')]:
        observed=cursor.execute('SELECT version,source_sha256 FROM '+schema+'.schema_version').fetchone()
        expected=hashlib.sha256(Path(__file__).with_name(filename).read_bytes()).hexdigest()
        if observed!={'version':1,'source_sha256':expected}:raise ValueError('Operator schema differs; use the reviewed lifecycle')


def journal(cursor,account,key,action,active,alias=None,version=None,registration_version=None,domain=None):
    cursor.execute('INSERT INTO enterprise_auth.administration_events(account_id,principal_key,action,active,source_alias,mapping_version,registration_version,registration_domain)VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',(account,key,action,active,alias,version,registration_version,domain))


def cancel_requests(cursor,account,key=None):
    suffix=' AND principal_key=%s'if key is not None else''
    rows=cursor.execute("UPDATE enterprise_queries.requests SET state='cancelled',question_ciphertext=NULL,result_ciphertext=NULL,lease_token=NULL,lease_until=NULL,error_code=NULL,updated_at=clock_timestamp()WHERE account_id=%s AND state IN('queued','running','ready')"+suffix+' RETURNING id,principal_key,attempt',(account,key)if key is not None else(account,)).fetchall()
    for row in rows:cursor.execute("INSERT INTO enterprise_queries.events(query_id,account_id,principal_key,event,attempt)VALUES(%s,%s,%s,'cancelled',%s)",(row['id'],account,row['principal_key'],row['attempt']))
    return rows


def activate(conn,metadata):
    owned=deployment(metadata);account=owned['accountId'];domain=session_domain(owned)
    if conn.autocommit:raise ValueError('Use an operator transaction')
    with conn.transaction(),conn.cursor(row_factory=dict_row)as cursor:
        require_schema(cursor)
        cursor.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('enterprise-company:'+account,))
        row=cursor.execute('SELECT session_domain,version FROM enterprise_auth.company_bindings WHERE account_id=%s FOR UPDATE',(account,)).fetchone()
        if row and row['session_domain']==domain:return {'changed':False,'registrationVersion':row['version']}
        version=row['version']+1 if row else 1
        cursor.execute('INSERT INTO enterprise_auth.company_bindings(account_id,session_domain,version)VALUES(%s,%s,%s)ON CONFLICT(account_id)DO UPDATE SET session_domain=EXCLUDED.session_domain,version=EXCLUDED.version,actor=current_user,updated_at=clock_timestamp()',(account,domain,version))
        cursor.execute('UPDATE enterprise_auth.sessions SET revoked_at=clock_timestamp()WHERE account_id=%s AND revoked_at IS NULL',(account,))
        cursor.execute('DELETE FROM enterprise_auth.attempts WHERE account_id=%s',(account,))
        cancel_requests(cursor,account)
        journal(cursor,account,None,'company_registration_updated',True,registration_version=version,domain=domain)
    return {'changed':True,'registrationVersion':version}


def require_company(cursor,owned):
    row=cursor.execute('SELECT session_domain FROM enterprise_auth.company_bindings WHERE account_id=%s FOR SHARE',(owned['accountId'],)).fetchone()
    if not row or row['session_domain']!=session_domain(owned):raise ValueError('Activate the owned company registration before changing directory membership')


def reset_source(cursor,account,key,source):
    cursor.execute("UPDATE enterprise_auth.connections SET credential_ciphertext=NULL,status='revoked',revision=revision+1,updated_at=clock_timestamp()WHERE account_id=%s AND principal_key=%s AND source_id=%s",(account,key,source))
    cursor.execute('DELETE FROM enterprise_auth.attempts WHERE account_id=%s AND principal_key=%s AND source_id=%s',(account,key,source))


def enroll(conn,metadata,subject,mappings):
    owned,key=checked_identity(metadata,subject)
    if conn.autocommit or not isinstance(mappings,dict)or set(mappings)!={'sharepoint','confluence'}or any(not isinstance(v,str)or not 1<=len(v.encode('utf-8'))<=255 or any(ord(c)<32 for c in v)for v in mappings.values()):
        raise ValueError('Supply both approved native source-account mappings in an operator transaction')
    account=owned['accountId'];sources={'sharepoint':'sharepoint:'+owned['sources']['sharepoint']['driveId'],'confluence':'confluence:'+owned['sources']['confluence']['cloudId']}
    with conn.transaction(),conn.cursor(row_factory=dict_row)as cursor:
        require_schema(cursor)
        require_company(cursor,owned)
        cursor.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('enterprise-provision:'+account+':'+key,))
        current=cursor.execute('SELECT issuer,subject,active FROM enterprise_auth.memberships WHERE account_id=%s AND principal_key=%s FOR UPDATE',(account,key)).fetchone()
        if current and(current['issuer']!=owned['company']['issuer']or current['subject']!=subject):raise ValueError('Existing company identity binding differs')
        if not current or not current['active']:
            cursor.execute('INSERT INTO enterprise_auth.memberships(account_id,principal_key,issuer,subject,active)VALUES(%s,%s,%s,%s,true)ON CONFLICT(account_id,principal_key)DO UPDATE SET active=true',(account,key,owned['company']['issuer'],subject))
            journal(cursor,account,key,'membership_enabled',True)
        changed=0
        for alias,source in sources.items():
            old=cursor.execute('SELECT source_subject,version,active FROM enterprise_auth.source_mappings WHERE account_id=%s AND principal_key=%s AND source_id=%s FOR UPDATE',(account,key,source)).fetchone()
            if old and old['active']and old['source_subject']==mappings[alias]:continue
            version=old['version']+1 if old else 1
            cursor.execute('INSERT INTO enterprise_auth.source_mappings(account_id,principal_key,source_id,source_subject,version,active)VALUES(%s,%s,%s,%s,%s,true)ON CONFLICT(account_id,principal_key,source_id)DO UPDATE SET source_subject=EXCLUDED.source_subject,version=EXCLUDED.version,active=true',(account,key,source,mappings[alias],version))
            reset_source(cursor,account,key,source)
            journal(cursor,account,key,'mapping_updated',True,alias,version);changed+=1
    return {'principalKey':key,'active':True,'mappingsChanged':changed}


def revoke(conn,metadata,subject):
    owned,key=checked_identity(metadata,subject)
    if conn.autocommit:raise ValueError('Use an operator transaction')
    account=owned['accountId']
    with conn.transaction(),conn.cursor(row_factory=dict_row)as cursor:
        require_schema(cursor)
        require_company(cursor,owned)
        cursor.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('enterprise-provision:'+account+':'+key,))
        member=cursor.execute('SELECT active FROM enterprise_auth.memberships WHERE account_id=%s AND principal_key=%s FOR UPDATE',(account,key)).fetchone()
        if not member:return {'principalKey':key,'active':False,'changed':False}
        cursor.execute('UPDATE enterprise_auth.memberships SET active=false WHERE account_id=%s AND principal_key=%s',(account,key))
        mappings=cursor.execute('UPDATE enterprise_auth.source_mappings SET active=false,version=version+1 WHERE account_id=%s AND principal_key=%s AND active RETURNING source_id,version',(account,key)).fetchall()
        sources={'sharepoint:'+owned['sources']['sharepoint']['driveId']:'sharepoint','confluence:'+owned['sources']['confluence']['cloudId']:'confluence'}
        for row in mappings:
            reset_source(cursor,account,key,row['source_id'])
            if row['source_id']in sources:journal(cursor,account,key,'mapping_updated',False,sources[row['source_id']],row['version'])
        # Also erase any older/inactive registration's remaining credential.
        cursor.execute("UPDATE enterprise_auth.connections SET credential_ciphertext=NULL,status='revoked',revision=revision+1,updated_at=clock_timestamp()WHERE account_id=%s AND principal_key=%s AND(status<>'revoked'OR credential_ciphertext IS NOT NULL)",(account,key))
        cursor.execute('UPDATE enterprise_auth.sessions SET revoked_at=clock_timestamp()WHERE account_id=%s AND principal_key=%s AND revoked_at IS NULL',(account,key))
        cursor.execute('DELETE FROM enterprise_auth.attempts WHERE account_id=%s AND principal_key=%s',(account,key))
        requests=cancel_requests(cursor,account,key)
        if member['active']:journal(cursor,account,key,'membership_disabled',False)
    return {'principalKey':key,'active':False,'changed':bool(member['active']or mappings or requests)}


def main():
    if sys.argv[1:]:raise SystemExit('Supply the owned operator command as private JSON on stdin')
    raw=sys.stdin.buffer.read(32769)
    if len(raw)>32768:raise ValueError('Operator command exceeds its boundary')
    command=json.loads(raw,object_pairs_hook=object_pairs)
    if not isinstance(command,dict):raise ValueError('Use an owned operator command')
    mode=command.get('operation')
    expected={'initialize':{'operation','apiRole','workerRole'},'activate':{'operation'},'enroll':{'operation','subject','mappings'},'revoke':{'operation','subject'}}
    if mode not in expected or set(command)!=expected[mode]:raise ValueError('Invalid owned operator command')
    owned=read_deployment()
    with SecretFiles(owned['provider'],os.environ,'operator')as secrets:
        database=native_database(owned['provider'],secrets.env,'migration',secrets)
        with psycopg.connect(database(),connect_timeout=5)as conn,conn.transaction():
            if mode=='initialize':initialize(conn,command['apiRole'],command['workerRole']);activate(conn,owned);result={'initialized':True}
            elif mode=='activate':result=activate(conn,owned)
            elif mode=='enroll':result=enroll(conn,owned,command['subject'],command['mappings'])
            else:result=revoke(conn,owned,command['subject'])
    print(json.dumps(result))


if __name__=='__main__':main()
