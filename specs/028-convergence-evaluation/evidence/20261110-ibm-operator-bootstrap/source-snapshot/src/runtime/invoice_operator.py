"""Explicit operator CLI; never run with the API or worker SQL identity.

Connection/credential files are private local inputs, not export payloads. This
tool performs destination writes only after --execute; obtain authorization first.
It never contacts a model or the accounting service, and never claims that a human
supplied receipt has been independently verified by this tool.
"""
import argparse
import json
import os
from pathlib import Path
import stat
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import psycopg
from psycopg.conninfo import make_conninfo
from workflow_database import initialize_database,grant_runtime_roles
from workflow_role_bootstrap import bootstrap_runtime_roles
from invoice_operations import owned_scope,purge_expired,quarantine_restored_deliveries,reconcile_completed,set_membership
from structured_output import _object

def private_json(path):
    file=Path(path)
    metadata=file.stat()
    if not stat.S_ISREG(metadata.st_mode)or metadata.st_uid!=os.geteuid()or metadata.st_mode&0o077 or metadata.st_size>20000:raise ValueError('Use an owned mode-0600 bounded JSON input file')
    value=json.loads(file.read_text(),object_pairs_hook=_object)
    if not isinstance(value,dict):raise ValueError('Use a JSON object')
    return value

def connection_settings(path):
    value=private_json(path)
    if set(value)!={'host','port','dbname','user','passwordFile','caFile'}:raise ValueError('Use the documented operator connection fields')
    secret=Path(value['passwordFile']);metadata=secret.stat()
    if not secret.is_absolute()or metadata.st_uid!=os.geteuid()or metadata.st_mode&0o077 or not stat.S_ISREG(metadata.st_mode)or not 1<=metadata.st_size<=20000:raise ValueError('Use a private separately supplied database password/token file')
    password=secret.read_text()
    ca=Path(value['caFile'])
    if not ca.is_absolute()or not ca.is_file()or b'-----BEGIN CERTIFICATE-----'not in ca.read_bytes():raise ValueError('Use the reviewed native CA bundle')
    if any(not isinstance(value[key],str)or not value[key]or '\0'in value[key]for key in ['host','dbname','user'])or type(value['port'])is not int or not 1<=value['port']<=65535:raise ValueError('Use the owned native database connection')
    if not password or '\0'in password:raise ValueError('Invalid private operator credential')
    return dict(host=value['host'],port=value['port'],dbname=value['dbname'],user=value['user'],password=password,sslmode='verify-full',sslrootcert=str(ca),ssl_min_protocol_version='TLSv1.2',connect_timeout=5,options='-c search_path=pg_catalog,workflow,pg_temp -c statement_timeout=30000 -c lock_timeout=3000')

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['initialize','membership','purge-expired','quarantine-restore','reconcile-completed'])
    parser.add_argument('--connection-file',required=True);parser.add_argument('--deployment-file',required=True);parser.add_argument('--input-file');parser.add_argument('--execute',action='store_true');parser.add_argument('--confirm-workloads-stopped',action='store_true')
    args=parser.parse_args(argv)
    deployment=private_json(args.deployment_file)
    if set(deployment)!={'provider','deploymentId','accountId','namespace','bindings','tenantId'}:raise ValueError('Use the exact documented deployment identity')
    scope={'account_id':deployment['accountId'],'namespace':deployment['namespace']}
    payload=private_json(args.input_file)if args.input_file else{}
    if not args.execute:
        print(json.dumps({'action':args.action,'willWrite':False,'next':'Review the destination, private inputs and authorization, then pass --execute. No database connection was made.'}));return
    settings=connection_settings(args.connection_file)
    if args.action=='initialize':
        # Azure's documented identity mappings run in postgres, then schema and
        # application grants run in the separate destination application database.
        with psycopg.connect(**{**settings,**({'dbname':'postgres'}if deployment['provider']=='azure'else{})})as conn:
            def passwords(purpose,principal):
                if purpose not in deployment['bindings']or principal!=deployment['bindings'][purpose]['principal']:raise ValueError('Use the exact owned native password binding')
                field=payload.get(purpose+'PasswordFile')
                if not isinstance(field,str):raise ValueError('Supply a private separate IBM role password file')
                path=Path(field);metadata=path.stat()
                if not path.is_absolute()or metadata.st_uid!=os.geteuid()or metadata.st_mode&0o077 or not 20<=metadata.st_size<=20000:raise ValueError('Use an owned private strong runtime password file')
                return path.read_text()
            bootstrap_runtime_roles(conn,provider=deployment['provider'],deployment_id=deployment['deploymentId'],bindings=deployment['bindings'],tenant_id=deployment['tenantId'],passwords=passwords if deployment['provider']=='ibm'else None)
        with psycopg.connect(**settings)as conn:
            if conn.execute("SELECT to_regnamespace('workflow')").fetchone()[0]is None:initialize_database(conn)
            owned_scope(conn,**scope)
            grant_runtime_roles(conn,deployment['bindings']['api']['name'],deployment['bindings']['worker']['name'],native_provider=deployment['provider'])
            conn.execute('INSERT INTO workflow.accounts(id)VALUES(%s)ON CONFLICT DO NOTHING',(scope['account_id'],))
        receipt={'initialized':True,'schemaVersion':1,'nativeIdentity':'Requires destination-native authentication checks; local CLI success alone is insufficient.'}
    else:
        if args.action in {'purge-expired','quarantine-restore','reconcile-completed'}and not args.confirm_workloads_stopped:raise ValueError('Pause workloads and explicitly confirm the maintenance boundary')
        with psycopg.connect(**settings)as conn:
            if args.action=='membership':
                if set(payload)!={'subject','roles','active'}:raise ValueError('Supply exact membership fields')
                receipt=set_membership(conn,**scope,**payload)
            elif args.action=='purge-expired':receipt=purge_expired(conn,**scope)
            elif args.action=='quarantine-restore':receipt=quarantine_restored_deliveries(conn,**scope,workloads_stopped=True)
            else:
                if set(payload)!={'operation_id','payload_sha256','external_id','operator'}:raise ValueError('Supply the independently verified accounting completion receipt fields')
                receipt=reconcile_completed(conn,**scope,**payload)
    print(json.dumps({'action':args.action,'committed':True,'receipt':receipt}))

if __name__=='__main__':
    try:main()
    except Exception:
        # Driver exceptions can include connection fields or SQL parameter data.
        # Keep private input details out of terminals and automated logs.
        print('Operator action failed. No success is claimed. Check the private inputs, destination permissions, current schema and workload state.',file=sys.stderr);sys.exit(1)
