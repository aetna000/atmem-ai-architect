"""Independent frozen client cases against immutable generated modules and child.

No generated tests are imported. The original archive is not modified. This probes
domain/child components, not HTTP, persistence, deployment or complete acceptance.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from server.local_validation import DockerValidationWorker, ValidationSpec

HERE = Path(__file__).resolve().parent
BULK = ROOT / '.local/external-artifacts/native-azure-labels/v1'
EXPECTED = '22d35c9d11612c91094b4b1e89b1a429000e5ae0be9dc3a6697758ab8843f7ab'
cases = (HERE / 'requirements-cases-v1.json').read_text()
code = r'''
import copy, hashlib, json, os, pathlib, subprocess, sys
sys.path.insert(0, '/work/source/application')
import labels
cases = json.loads(sys.argv[1])
assert os.getuid() == 65532
counts = {'validSources': 0, 'invalidSources': 0, 'validReviewEdits': 0,
          'invalidReviewEdits': 0, 'childValid': 0, 'childInvalid': 0}
def denied(call):
    try: call()
    except ValueError: return
    raise AssertionError('Expected rejection')
def child(source):
    # Explicit isolated interpreter with only this immutable application's path.
    script = "import runpy,sys;sys.path.insert(0,'/work/source/application');runpy.run_path('/work/source/application/processor_child.py',run_name='__main__')"
    reply = subprocess.run([sys.executable, '-I', '-c', script],
        input=json.dumps({'operation': {'source_ref': source}}),
        text=True, capture_output=True, timeout=15, check=True)
    return json.loads(reply.stdout)
for case in cases['validSourceCases']:
    source, expected = case['source'], case['expectedResult']
    original = copy.deepcopy(source)
    assert labels.source(source) == source
    assert labels.process(source) == expected
    assert source == original
    counts['validSources'] += 1
    assert child(source) == {'status': 'ok', 'result': expected}
    counts['childValid'] += 1
    edited = dict(expected, displayCaption=cases['reviewCases']['validEdit']['displayCaption'])
    assert labels.result(edited, source) == edited
    counts['validReviewEdits'] += 1
    invalid = [dict(edited, needsCurator=not source['sensitive']),
               dict(edited, displayCaption=''), dict(edited, displayCaption='🙂' * 129),
               dict(edited, provider='aws'), dict(edited, needsCurator=int(source['sensitive']))]
    for value in invalid:
        denied(lambda: labels.result(value, source))
        counts['invalidReviewEdits'] += 1
for case in cases['invalidSourceCases'] + [cases['whitespaceOnlySource']]:
    source = case['source']
    denied(lambda: labels.source(source))
    denied(lambda: labels.process(source))
    counts['invalidSources'] += 1
    assert child(source) == {'status': 'permanent', 'result': {}}
    counts['childInvalid'] += 1
files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
         for p in pathlib.Path('/work/source/application').glob('*.py')}
print(json.dumps({'passed': True, 'counts': counts, 'python': sys.version,
      'uid': os.getuid(), 'moduleHashes': files, 'cloudOperations': False,
      'boundary': 'Independent frozen domain inputs, review validation and actual isolated processing child; no HTTP/SQL/queue/identity/provider/receiving-image/full-system acceptance.'}))
'''
archive = (BULK / 'artifact.zip').read_bytes()
assert hashlib.sha256(archive).hexdigest() == EXPECTED
entry = next(e for e in json.loads((BULK / 'validators-scratch-observed.json').read_text())
             if e['id'] == 'python-sql-azure-tests')
spec = ValidationSpec('independent-label-cases', entry['image'],
    ('/usr/local/bin/python3', '-I', '-c', code, cases),
    platform='linux/amd64', timeout_seconds=120)
result = DockerValidationWorker('unix:///Users/javadtaghia/.avm/c/engine/docker.sock').run(
    archive, EXPECTED, spec)
(BULK / 'independent-client-cases-v1.json').write_text(json.dumps(result, indent=2) + '\n')
assert result['status'] == 'passed', result
print(result['output'])
