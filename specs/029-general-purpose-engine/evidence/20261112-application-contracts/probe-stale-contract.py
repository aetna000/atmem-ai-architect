"""Independent old/new pending-work probe; synthetic owned fixture, no send."""
import hashlib
import json
from pathlib import Path
import sys
import uuid

ROOT=Path(__file__).resolve().parents[4]
runtime=Path(sys.argv[1]).resolve()
sys.path[:0]=[str(runtime),str(ROOT/'tests/runtime')]
from durable_workflow import WorkflowStore,Principal,Conflict
from durable_fixture_tasks import fixture_tasks,FIXTURE_CONTRACT
from durable_postgres_acceptance import fixture_dsn

dsn=fixture_dsn();namespace=uuid.uuid4().hex;account=str(uuid.uuid4())
app,extract,dispatch=fixture_tasks(dsn,namespace)
store=WorkflowStore(dsn,extract,dispatch,destination_contract=FIXTURE_CONTRACT)
actor=Principal(account,'synthetic-member')
with store.connect()as conn:
    conn.execute('INSERT INTO workflow.accounts(id) VALUES(%s)',(account,))
    conn.execute('INSERT INTO workflow.memberships(account_id,subject,roles) VALUES(%s,%s,%s)',(account,actor.subject,['user']))
source={'articleId':'synthetic-community-update','revision':4}
operation=store.submit(actor,'draft','stable-operation',source)
store.destination_contract={**FIXTURE_CONTRACT,'endpointSha256':'f'*64}
try:
    lease=store.claim_extract(operation)
except Conflict:
    outcome='blocked_contract_mismatch'
else:
    assert lease is not None
    outcome='claimed_under_changed_contract'
row=store.get(actor,operation)
assert row['destination_contract']==FIXTURE_CONTRACT
report={'runtime':str(runtime),'runtimeSha256':hashlib.sha256((runtime/'durable_workflow.py').read_bytes()).hexdigest(),
        'inputSha256':hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest(),
        'outcome':outcome,'persistedState':row['state'],'destinationExecuted':False,
        'boundary':'Real PostgreSQL pending-work claim only; no worker processor or external destination invoked'}
Path(sys.argv[2]).write_text(json.dumps(report,indent=2)+'\n')
print(outcome)
