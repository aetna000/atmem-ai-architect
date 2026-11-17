"""Run Terraform apply emulation for every archived AWS example project.

Uses the current product generator, the real Terraform CLI and provider, and the
local emulator. No AWS credentials or cloud calls.
"""
import datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.terraform_emulation_routes import TerraformEmulationRequest, emulate_terraform  # noqa: E402


def main():
    wanted = set(sys.argv[1:])
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace(':', '-')
    root = ROOT / '.local/terraform-emulation' / stamp
    root.mkdir(parents=True)
    manifest = json.loads((ROOT / 'examples/aws/manifest.json').read_text())
    results = []
    for example in manifest['scenarios']:
        if wanted and example['id'] not in wanted:
            continue
        # The same normalized project as the real prompt run; no patched exports.
        source = ROOT / 'examples/aws' / example['id'] / 'history' / example['sourceRun'] / 'round-2/workspace.json'
        result = emulate_terraform(TerraformEmulationRequest(project=json.loads(source.read_text())), lambda event: print('  ', json.dumps(event), flush=True))
        (root / (example['id'] + '.json')).write_text(json.dumps(result, indent=2) + '\n')
        resources = result.get('resources', [])
        results.append({
            'id': example['id'], 'status': result['status'], 'message': result.get('message'),
            'planned': len(resources), 'applied': sum(bool(r.get('applied')) for r in resources),
            'sdkVerified': sum(r.get('readBack') == 'sdk' for r in resources),
            'apiCalls': result.get('apiCalls', {}).get('total', 0), 'seconds': result.get('seconds'),
        })
        print(json.dumps(results[-1]), flush=True)
    (root / 'results.json').write_text(json.dumps({'kind': 'terraform-apply-emulation', 'cloudOperations': False, 'results': results}, indent=2) + '\n')
    print('Evidence:', root)
    return 0 if results and all(r['status'] == 'passed' for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
