"""Independently execute the exact captured native-engineering Python artifacts.

Run from repository root. This does not invoke a model or a cloud service.
"""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

OUT = Path(__file__).resolve().parent
receipt_path = OUT / 'native-engineering-receipt.json'
receipt = json.loads(receipt_path.read_text())
with tempfile.TemporaryDirectory(prefix='atmem-independent-session-') as folder:
    root = Path(folder)
    for name, artifact in receipt['artifacts'].items():
        assert Path(name).name == name and name.endswith('.py'), name
        contents = artifact['text'].encode()
        assert hashlib.sha256(contents).hexdigest() == artifact['sha256'], name
        (root / name).write_bytes(contents)
    suite = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-v'],
                           cwd=root, text=True, capture_output=True, timeout=30)
    oracle = '''import reservations as r
assert r.reserve(8, 2, 6) == 8
assert r.reserve(0, 0, 0) == 0
assert r.release(8, 8) == 0
assert r.release(8, 0) == 8
checks = 4
for args in [(8,7,2),(8,9,0),(-1,0,0),(8,0,-1),(8,True,1),(8,0,1.5),('8',0,1)]:
 try: r.reserve(*args)
 except ValueError: pass
 else: raise AssertionError(('reserve', args))
 checks += 1
for args in [(1,2),(True,0),(1,-1),(1,0.2),('2',1)]:
 try: r.release(*args)
 except ValueError: pass
 else: raise AssertionError(('release', args))
 checks += 1
print(f'{checks} independent behavioral checks passed')
'''
    checked = subprocess.run([sys.executable, '-c', oracle], cwd=root,
                             text=True, capture_output=True, timeout=30)
    result = {
        'timestampUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'receiptSha256': hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        'artifactDigestsVerified': True,
        'generatedSuite': {'command': [sys.executable, '-m', 'unittest', 'discover', '-v'],
                           'exitCode': suite.returncode, 'stdout': suite.stdout, 'stderr': suite.stderr},
        'independentOracle': {'source': oracle, 'exitCode': checked.returncode,
                              'stdout': checked.stdout, 'stderr': checked.stderr},
        'passed': suite.returncode == checked.returncode == 0,
        'boundary': 'Local captured Python artifact behavior only; no Terraform, hosted isolation or cloud proof.'
    }
    (OUT / 'independent-artifact-check.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    assert result['passed']
