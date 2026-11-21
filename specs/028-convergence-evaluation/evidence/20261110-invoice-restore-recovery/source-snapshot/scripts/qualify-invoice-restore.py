"""Actual local pg_dump/pg_restore drill on fresh owned synthetic databases.

Never connects to a remote Docker host or a cloud account. Does not qualify native
managed backups, PITR, RPO/RTO or accounting-service reconciliation.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict,make_conninfo
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'tests/runtime')]
from durable_postgres_acceptance import fixture_dsn
from workflow_database import initialize_database
from workflow_worker import producer_store
from workflow_contract import normalized_contract
from durable_workflow import Principal
from invoice_operations import purge_expired,quarantine_restored_deliveries,reconcile_completed,set_membership

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--docker-host',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    out=Path(args.out).resolve()
    if not out.is_relative_to(ROOT/'.local')or out.exists():raise ValueError('Use a fresh local evidence directory')
    if not args.docker_host.startswith('unix:///')or not Path(args.docker_host[7:]).is_socket():raise ValueError('Use the existing owned local Docker socket')
    config_path=Path(os.environ.get('ATMEM_WORKFLOW_TEST_CONFIG',ROOT/'.local/durable-postgres/fixture.json'));config=json.loads(config_path.read_text())
    owner=fixture_dsn();settings=conninfo_to_dict(owner);docker=shutil.which('docker')
    command=[docker,'--config',str(ROOT/'.local/qualification-docker-config'),'--host',args.docker_host]
    inspection=subprocess.run([*command,'inspect',config['name']],capture_output=True,check=True)
    details=json.loads(inspection.stdout)[0]
    if details['Config']['Image']!=config['image']or details['Config'].get('Labels',{}).get('org.atmem.purpose')!='durable-qualification'or not details['State']['Running']:raise ValueError('Owned local fixture identity changed')
    out.mkdir(parents=True);out.chmod(0o700);checks=[]
    sources={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()for path in [Path(__file__),ROOT/'src/runtime/invoice_operations.py',ROOT/'src/runtime/workflow_database.py',ROOT/'src/runtime/workflow_schema.sql',ROOT/'src/runtime/durable_workflow.py',ROOT/'src/runtime/workflow_worker.py']}
    def check(name,value):
        checks.append({'name':name,'passed':bool(value)})
        if not value:raise AssertionError(name)
    try:
        databases=['architect_qualification_'+uuid.uuid4().hex[:16]for _ in range(2)]
        with psycopg.connect(owner,autocommit=True)as conn:
            for database in databases:conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
        source=make_conninfo(**{**settings,'dbname':databases[0],'options':'-c search_path=pg_catalog,workflow,pg_temp'});restored=make_conninfo(**{**settings,'dbname':databases[1],'options':'-c search_path=pg_catalog,workflow,pg_temp'})
        with psycopg.connect(source)as conn:initialize_database(conn)
        account=str(uuid.uuid4());namespace='restore';contract=normalized_contract('https://accounting.example.test/actions','synthetic-account');staff=Principal(account,'synthetic-staff');reviewer=Principal(account,'synthetic-reviewer')
        with psycopg.connect(source)as conn:
            set_membership(conn,account_id=account,namespace=namespace,subject=staff.subject,roles=['user']);set_membership(conn,account_id=account,namespace=namespace,subject=reviewer.subject,roles=['reviewer'])
        store=producer_store(source,destination_contract=contract,namespace=namespace);operations=[]
        for index in range(3):
            operation=store.submit(staff,'document','restore-'+str(index),{'sha256':str(index)*64});lease=store.claim_extract(operation);store.record_result(operation,str(lease['lease_token']),{'supplier':'Explicit synthetic restore fixture'});store.approve(reviewer,operation,1);operations.append(operation)
        send=store.claim_dispatch(operations[0])
        processing=store.submit(staff,'document','restored-processing',{'sha256':'f'*64});store.claim_extract(processing)
        with psycopg.connect(source)as conn:
            conn.execute("UPDATE workflow.procrastinate_jobs SET status='doing'WHERE task_name='restore.dispatch'AND args->>'operation_id'=%s",(operations[0],))
            conn.execute("UPDATE workflow.operations SET created_at=clock_timestamp()-interval '91 days'WHERE id=%s",(operations[2],))
            conn.execute("UPDATE workflow.procrastinate_jobs SET status='doing'WHERE task_name='restore.extract'AND args->>'operation_id'=%s",(processing,))
            conn.execute("UPDATE workflow.operations SET created_at=clock_timestamp()-interval '91 days'WHERE id=%s",(processing,))
        dump=subprocess.run([*command,'exec',config['name'],'pg_dump','--format=custom','--no-owner','--no-privileges','--username',config['user'],databases[0]],capture_output=True,timeout=30)
        check('native-pg-dump',dump.returncode==0 and dump.stdout.startswith(b'PGDMP'))
        private=out/'synthetic-database.dump';private.write_bytes(dump.stdout);private.chmod(0o600)
        restore=subprocess.run([*command,'exec','-i',config['name'],'pg_restore','--exit-on-error','--single-transaction','--no-owner','--no-privileges','--username',config['user'],'--dbname',databases[1]],input=dump.stdout,capture_output=True,timeout=30)
        check('native-pg-restore',restore.returncode==0)
        resumed=producer_store(restored,destination_contract=contract,namespace=namespace)
        check('restored-extraction-and-approval-retained',resumed.get(staff,operations[0])['approved_hash']==store.get(staff,operations[0])['approved_hash'])
        with psycopg.connect(restored)as conn:quarantine=quarantine_restored_deliveries(conn,account_id=account,namespace=namespace,workloads_stopped=True)
        check('restored-inflight-deliveries-quarantined',quarantine['quarantinedDeliveries']==3 and all(resumed.get(staff,operation)['state']=='unknown'for operation in operations))
        check('restored-deliveries-not-replayed',all(resumed.claim_dispatch(operation)is None for operation in operations))
        check('restored-processing-leases-and-stale-jobs-fenced',quarantine['resetExtractions']==1 and resumed.get(staff,processing)['state']=='pending')
        with psycopg.connect(restored)as conn:purged=purge_expired(conn,account_id=account,namespace=namespace)
        check('expired-restored-history-purged-before-reopening',purged['purgedOperations']==2)
        row=resumed.get(staff,operations[0])
        with psycopg.connect(restored)as conn:reconcile_completed(conn,account_id=account,namespace=namespace,operation_id=operations[0],payload_sha256=row['approved_hash'],external_id='synthetic-independently-verified-receipt',operator='restore-drill')
        check('explicit-reconciliation-retains-approval-identity',resumed.get(staff,operations[0])['state']=='sent'and resumed.get(staff,operations[0])['approved_hash']==row['approved_hash'])
        check('original-database-remains-untouched',store.get(staff,operations[0])['state']=='dispatching'and store.get(staff,operations[2])['state']=='approved')
        with psycopg.connect(restored)as conn:check('no-old-dispatch-notifications-remain',conn.execute("SELECT count(*)FROM workflow.procrastinate_jobs WHERE task_name='restore.dispatch'").fetchone()[0]==0)
    except Exception as error:
        checks.append({'name':'restore-drill','passed':False,'errorType':type(error).__name__});raise
    finally:
        receipt={'kind':'local-invoice-logical-backup-restore','recordedAt':datetime.now(timezone.utc).isoformat(),'passed':bool(checks)and all(check['passed']for check in checks),'checks':checks,'sourceHashes':sources,'privateDumpRetainedLocally':True,'boundary':'Actual local PostgreSQL native logical dump/restore into fresh synthetic databases, followed by quarantine, expiry purge and synthetic operator receipt reconciliation. No managed backup/PITR, cloud IAM, object restore, external accounting verification or RPO/RTO qualification.','cloudOperations':False,'full28CaseAcceptanceComplete':False}
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':receipt['passed'],'checks':len(checks),'receipt':str(out/'receipt.json')}))

if __name__=='__main__':main()
