"""Independent evidence aggregator. Imports no Architect generator or application.

This verifies coverage, receipt levels and byte bindings; it does not replace the
independent semantic assessors that author receipts. A valid receipt is a claim
with traceable evidence, not a cryptographic guarantee of assessor correctness.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / 'benchmarks/engine/evaluation-contract.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bound_file(folder, evidence):
    name = evidence.get('path')
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        return False
    candidate = folder / name
    resolved = candidate.resolve()
    if not resolved.is_relative_to(folder.resolve()) or not resolved.is_file():
        return False
    # Receipts cannot rely on mutable symlinks, including an in-tree parent link.
    current = candidate
    while current != folder:
        if current.is_symlink():
            return False
        current = current.parent
    return resolved.stat().st_size > 0 and sha(resolved) == evidence.get('sha256')


def assess_case(folder, case, rules):
    record = folder / 'acceptance.json'
    if not record.is_file():
        return {'case': case['case'], 'provider': case['provider'], 'difficulty': case['difficulty'],
                'qualified': False, 'reason': 'No independent acceptance record',
                'checks': [{'id': r['id'], 'critical': r['critical'], 'passed': False, 'status': 'untested'} for r in rules]}
    raw = json.loads(record.read_text())
    claims = raw.get('checks', [])
    if not isinstance(claims, list) or any(not isinstance(c, dict) for c in claims):
        raise ValueError('Invalid check records')
    ids = [c.get('id') for c in claims]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate check records')
    if raw.get('case') != case['case'] or raw.get('provider') != case['provider']:
        raise ValueError('Case/provider identity mismatch')
    artifact = raw.get('artifact', {})
    artifact_valid = bound_file(folder, artifact)
    checks = []
    for rule in rules:
        claim = next((c for c in claims if c.get('id') == rule['id']), {})
        verifier = claim.get('verifier', {})
        digest = verifier.get('sha256')
        verifier_valid = (isinstance(verifier.get('id'), str) and bool(verifier['id'].strip())
                          and isinstance(digest, str) and len(digest) == 64
                          and all(c in '0123456789abcdef' for c in digest))
        evidence = claim.get('evidence', {})
        passed = (claim.get('status') == 'passed' and claim.get('level') in rule['levels']
                  and artifact_valid and verifier_valid and bound_file(folder, evidence)
                  and evidence.get('artifactSha256') == artifact.get('sha256'))
        checks.append({'id': rule['id'], 'critical': rule['critical'], 'passed': bool(passed),
                       'status': claim.get('status', 'untested'), 'level': claim.get('level'),
                       'bindingValid': bool(artifact_valid and verifier_valid and bound_file(folder, evidence))})
    return {'case': case['case'], 'provider': case['provider'], 'difficulty': case['difficulty'],
            'qualified': all(c['passed'] for c in checks if c['critical']), 'checks': checks}


def assess(root, contract_path=CONTRACT):
    contract = json.loads(contract_path.read_text())
    corpus_path = ROOT / contract['originalCorpus']
    if sha(corpus_path) != contract['originalCorpusSha256']:
        raise ValueError('Frozen original corpus changed; version the evaluation protocol first')
    corpus = json.loads(corpus_path.read_text())
    expected = [{'case': f"{provider}-{scenario['id']}", 'provider': provider, 'difficulty': scenario['difficulty']}
                for provider in contract['providers'] for scenario in corpus['scenarios']]
    assert len(expected) == contract['expectedOriginalCases']
    results = []
    for case in expected:
        try:
            result = assess_case(root / case['case'], case, contract['requiredChecks'])
        except (ValueError, TypeError, OSError) as error:
            result = {'**invalid**': True, **case, 'qualified': False,
                      'reason': type(error).__name__, 'checks': []}
        results.append(result)
    strata = []
    for provider in contract['providers']:
        for difficulty, count in contract['difficultyCountsPerProvider'].items():
            cases = [r for r in results if r['provider'] == provider and r['difficulty'] == difficulty]
            required_noncritical = sum(not r['critical'] for r in contract['requiredChecks']) * count
            noncritical_passed = sum(c['passed'] for r in cases for c in r['checks'] if not c['critical'])
            fraction = noncritical_passed / required_noncritical if required_noncritical else 0
            accepted = (len(cases) == count and all(r['qualified'] for r in cases)
                        and fraction >= contract['scoring']['noncriticalThreshold'])
            strata.append({'provider': provider, 'difficulty': difficulty, 'expectedCases': count,
                           'qualifiedCases': sum(r['qualified'] for r in cases),
                           'noncriticalPassed': noncritical_passed, 'noncriticalRequired': required_noncritical,
                           'noncriticalFraction': fraction, 'accepted': accepted})
    return {'contractSha256': sha(contract_path), 'corpusSha256': sha(corpus_path),
            'expectedCases': len(expected), 'qualifiedCases': sum(r['qualified'] for r in results),
            'accepted': all(s['accepted'] for s in strata), 'strata': strata, 'cases': results,
            'boundary': 'Independent receipt coverage/level/hash aggregation only. No model, Terraform or runtime test is executed by this aggregator; receipt authors remain responsible for semantic correctness. No quality claim over unseen systems.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('cases', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = assess(args.cases.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(f"{report['qualifiedCases']}/{report['expectedCases']} complete projects qualified; accepted={report['accepted']}")
