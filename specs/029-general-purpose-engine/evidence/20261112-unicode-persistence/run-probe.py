"""Bind a current shared runtime snapshot and run independent private SQL checks."""
import argparse, hashlib, io, json, sys, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]; sys.path.insert(0, str(ROOT))
from server.local_validation import DockerValidationWorker, ValidationSpec
parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--regressions', action='store_true')
args = parser.parse_args(); out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
files = {'runtime/'+p.name: p.read_bytes() for p in (ROOT/'src/runtime').iterdir() if p.suffix in {'.py', '.sql'}}
files['oracle/test_persistence.py'] = Path(__file__).with_name('test_persistence.py').read_bytes()
files['oracle/durable_fixture_tasks.py'] = (ROOT/'tests/runtime/durable_fixture_tasks.py').read_bytes()
files['oracle/test_worker_admission.py'] = Path(__file__).with_name('test_worker_admission.py').read_bytes()
if args.regressions:
    files = {'src/runtime/'+p.name: p.read_bytes() for p in (ROOT/'src/runtime').iterdir() if p.suffix in {'.py', '.sql'}}
    files.update({'tests/runtime/'+p.name: p.read_bytes() for p in (ROOT/'tests/runtime').glob('*.py')})
    files['test_regressions.py'] = Path(__file__).with_name('run-regressions.py').read_bytes()
stream = io.BytesIO()
with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name, raw in files.items(): archive.writestr(name, raw)
raw = stream.getvalue(); digest = hashlib.sha256(raw).hexdigest(); (out/'source.zip').write_bytes(raw)
entry = next(x for x in json.loads((ROOT/'.local/external-artifacts/provider-sql-validation/v1/validators-observed.json').read_text()) if x['id']=='python-sql-azure-tests')
command = ('/usr/local/bin/python3', '-I', '/opt/atmem/sql_validation.py')
command += ('-m', 'unittest', '-v', 'test_regressions') if args.regressions else ('-m', 'unittest', 'discover', '-s', 'oracle', '-v')
spec = ValidationSpec('unicode-persistence', entry['image'], command,
    isolation_profile='postgresql-local-v1', platform='linux/amd64', timeout_seconds=300 if args.regressions else 120)
result = DockerValidationWorker('unix:///Users/javadtaghia/.avm/c/engine/docker.sock').run(raw, digest, spec)
(out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
(out/'source-hashes.json').write_text(json.dumps({name: hashlib.sha256(value).hexdigest() for name, value in files.items()}, indent=2)+'\n')
print(json.dumps({key: result.get(key) for key in ['status', 'testsReported', 'skipped', 'durationSeconds']}))
print(result['output'][-4500:])
raise SystemExit(0 if result['status']=='passed' else 1)
