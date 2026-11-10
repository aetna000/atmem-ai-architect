"""Independent runtime consumption of a real native mock-plan output.

No Google SDK constructor or native account operation is invoked. The pinned
public discovery schema independently checks the resulting Batch request.
"""
from pathlib import Path
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src/runtime'), str(ROOT / 'tests/runtime'), str(ROOT / '.local/azure-runtime-sdk')]
from enterprise_google_jobs import configuration, job_spec, GoogleBatchDocuments
from enterprise_document_job import request
from enterprise_google_jobs_acceptance import discovery_check


def verify(path):
    path = path.resolve()
    if not path.is_relative_to(ROOT / '.local'): raise ValueError('Use an owned local provider qualification')
    receipt = json.loads((path / 'receipt.json').read_text())
    if not receipt['passed'] or receipt['cloudOperations']: raise ValueError('Require a passed local provider mock qualification')
    for name, digest in receipt['sourceHashes'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest: raise ValueError('Qualification source changed')
    for name, digest in receipt['emittedHashes'].items():
        if hashlib.sha256((path / name).read_bytes()).hexdigest() != digest: raise ValueError('Emitted qualification bytes changed')
    configurations = json.loads((path / 'runtime-configurations.json').read_text())
    if not isinstance(configurations, list) or not configurations: raise ValueError('Missing baseline native plan outputs')
    log = (path / 'mock-plans.log').read_bytes()
    baseline, summary = [], None
    for line in log.splitlines():
        try: event = json.loads(line)
        except ValueError: continue
        if event.get('test_summary'): summary = event['test_summary']
        if event.get('@testrun') == 'private_document_substrate' and event.get('test_plan'):
            value = event['test_plan'].get('output_changes', {}).get('document_job_configuration', {}).get('after')
            if value is not None: baseline.append(value)
    if configurations != baseline or not summary or summary.get('status') != 'pass' or summary.get('passed') != 11 or any(summary.get(key, 0) for key in ['failed', 'errored', 'skipped']):
        raise ValueError('Configuration must come from the actual positive plan and all eleven native tests must run')
    schema = ROOT / 'tests/fixtures/providers/google-batch-v1-discovery-20261111.json'
    provenance = json.loads(schema.with_suffix('.provenance.json').read_text())
    if hashlib.sha256(schema.read_bytes()).hexdigest() != provenance['sha256']: raise ValueError('Public native schema changed')
    schemas = json.loads(schema.read_text())['schemas']; plans = []
    for value in configurations:
        owned = configuration(value)
        if owned != value: raise ValueError('Runtime normalized or lost an emitted field')
        # Fixed reviewed fixture intent, not values copied out of the generated
        # destination: catch a compiler that silently substitutes another target.
        bound = GoogleBatchDocuments(owned, api=object())
        bound.bind_runtime('gcp', {'PROJECT_ID': 'reviewed-project', 'REGION': 'australia-southeast1',
                                 'DATABASE_SERVICE_ACCOUNT': 'owned-worker@reviewed-project.iam.gserviceaccount.com'})
        spec = job_spec(owned, request(b'Owned synthetic document.', 'text/plain', 'a' * 64), '123')
        discovery_check(spec, schemas['Job'], schemas)
        if spec['allocationPolicy']['location']['allowedLocations'] != ['regions/' + owned['region']]: raise ValueError('Selected placement drifted')
        plans.append({'configurationSha256': hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest(),
            'requestSha256': hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest(), 'region': owned['region']})
    return {'passed': True, 'outputsChecked': len(plans), 'plans': plans, 'cloudOperations': False,
            'nativeMockTests': summary['passed'], 'runtimeOwnershipBound': True, 'nativeLogSha256': hashlib.sha256(log).hexdigest(),
            'runtimeConfigurationsSha256': hashlib.sha256((path / 'runtime-configurations.json').read_bytes()).hexdigest(),
            'verifierSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'scope': 'Actual emitted Terraform mock-plan output consumed by runtime configuration and validated against pinned public Batch schema. Not account IAM/network or deployment.'}


if __name__ == '__main__':
    if len(sys.argv) != 2: raise SystemExit('Supply the owned local qualification directory')
    print(json.dumps(verify(Path(sys.argv[1])), indent=2))
