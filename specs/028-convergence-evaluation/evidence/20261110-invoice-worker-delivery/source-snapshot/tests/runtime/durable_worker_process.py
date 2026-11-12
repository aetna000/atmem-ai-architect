"""Task-owned crash fixture, never a generated production entrypoint."""
import asyncio
import json
from pathlib import Path
import ssl
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(Path(__file__).resolve().parent)]
from durable_postgres_acceptance import fixture_dsn
from workflow_worker import WorkflowRuntime
from approved_http_destination import ApprovedHttpDestination

if __name__=='__main__':
    config_path=Path(sys.argv[1]).resolve()
    if not config_path.is_relative_to(ROOT/'.local'):raise ValueError('Use the owned local crash fixture')
    config=json.loads(config_path.read_text());marker=Path(config['marker']).resolve()
    if not marker.is_relative_to(config_path.parent)or config['mode']not in {'hold-extract','hold-dispatch','normal'}:raise ValueError('Invalid owned process fixture')
    destination=ApprovedHttpDestination(config['destination'],lambda:'synthetic-fixture-token',destination_scope='synthetic-account',idempotency_verified=config['idempotent'],tls_context=ssl.create_default_context(cafile=config['caFile']))
    def hold(row):marker.write_text(json.dumps({'operationId':str(row['id'])}));time.sleep(120)
    def processor(row):
        if config['mode']=='hold-extract':hold(row)
        return {'supplier':'Synthetic process fixture','invoice_date':'2026-11-10','total':'42.50','currency':'AUD'}
    def deliver(row,**identity):
        receipt=destination(row,**identity)
        if config['mode']=='hold-dispatch':hold(row)
        return receipt
    # The callback wrapper has the same declared replay policy as its destination.
    runtime=WorkflowRuntime(fixture_dsn(),processor,deliver,destination_contract=destination.contract,idempotent_destination=config['idempotent'],namespace=config['namespace'],lease_seconds=10,retry_wait=0)
    asyncio.run(runtime.run(install_signal_handlers=False,fetch_job_polling_interval=.05,shutdown_graceful_timeout=2,recovery_interval=5))
