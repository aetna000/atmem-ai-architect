"""Bind a current shared runtime snapshot and run independent private SQL checks."""
import argparse, hashlib, io, json, sys, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]; sys.path.insert(0, str(ROOT))
from server.local_validation import DockerValidationWorker, ValidationSpec
parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--regressions', action='store_true')
parser.add_argument('--counterexample', choices=['semantics','inspection','owner'])
args = parser.parse_args(); out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
files = {'src/runtime/'+p.name: p.read_bytes() for p in (ROOT/'src/runtime').iterdir() if p.suffix in {'.py', '.sql'}}
files.update({'tests/runtime/'+p.name: p.read_bytes() for p in (ROOT/'tests/runtime').glob('*.py')})
modules = ['workflow_review_acceptance']
if args.regressions:
    modules += ['durable_postgres_acceptance','durable_privileges_acceptance','durable_worker_acceptance',
        'durable_recovery_acceptance','durable_http_acceptance','workflow_payload_acceptance',
        'durable_native_grants_acceptance','durable_bootstrap_acceptance','durable_credentials_acceptance',
        'durable_restricted_worker_acceptance','workflow_http_acceptance','workflow_application_acceptance',
        'workflow_bindings_acceptance']
controller = Path(__file__).with_name('run-suites.py').read_text()
files['test_regressions.py'] = controller.replace("modules = json.loads(os.environ['ATMEM_REVIEW_MODULES'])", 'modules = '+repr(modules)).encode()
counterexample = None
if args.counterexample:
    changes = {
        'semantics': ('src/runtime/workflow_review.py', 'returned = self._validator(original, value)', 'returned = None', 'test_wrong_semantics_cannot_record_edit_approve_or_dispatch'),
        'inspection': ('src/runtime/durable_workflow.py', "ttl=self.review_policy.data['inspectionTtlSeconds']if self.review_policy else None", 'ttl=None', 'test_inspection_is_actor_revision_hash_time_and_live_role_bound'),
        'owner': ('src/runtime/durable_workflow.py', "return bool(self.review_policy and self.review_policy.data['readScope']=='owner'and not roles.intersection({'reviewer','supervisor','owner'}))", 'return False', 'test_owner_read_policy_applies_to_get_list_cursor_history_events_and_live_roles')}
    name, before, after, failure = changes[args.counterexample]
    original = files[name]; assert original.decode().count(before) == 1
    files[name] = original.decode().replace(before,after).encode()
    counterexample = {'mutation':args.counterexample,'changedFile':name,'originalSha256':hashlib.sha256(original).hexdigest(),
                     'mutatedSha256':hashlib.sha256(files[name]).hexdigest(),'requiredFailedTest':failure,
                     'testSourceHashes':{name:hashlib.sha256(raw).hexdigest() for name,raw in files.items() if name.startswith('tests/')}}
stream = io.BytesIO()
with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name, raw in files.items(): archive.writestr(name, raw)
raw = stream.getvalue(); digest = hashlib.sha256(raw).hexdigest(); (out/'source.zip').write_bytes(raw)
entry = next(x for x in json.loads((ROOT/'.local/external-artifacts/provider-sql-validation/v1/validators-observed.json').read_text()) if x['id']=='python-sql-azure-tests')
command = ('/usr/local/bin/python3', '-I', '/opt/atmem/sql_validation.py', '-m', 'unittest', '-v', 'test_regressions')
spec = ValidationSpec('review-policy-transfer', entry['image'], command,
    isolation_profile='postgresql-local-v1', platform='linux/amd64', timeout_seconds=300)
result = DockerValidationWorker('unix:///Users/javadtaghia/.avm/c/engine/docker.sock').run(raw, digest, spec)
(out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
(out/'source-hashes.json').write_text(json.dumps({name: hashlib.sha256(value).hexdigest() for name, value in files.items()}, indent=2)+'\n')
print(json.dumps({key: result.get(key) for key in ['status', 'testsReported', 'skipped', 'durationSeconds']}))
print(result['output'][-4500:])
if counterexample:
    counterexample['detected'] = (result['status']=='failed' and result.get('testsReported',0)>=15 and
        result.get('skipped')==0 and 'FAIL: '+counterexample['requiredFailedTest'] in result['output'])
    counterexample['scope'] = 'Isolated source archive mutation only; original product files and frozen client exports unchanged'
    (out/'counterexample.json').write_text(json.dumps(counterexample,indent=2)+'\n')
    raise SystemExit(0 if counterexample['detected'] else 1)
raise SystemExit(0 if result['status']=='passed' else 1)
