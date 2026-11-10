"""Read-only assessment of emitted bytes; intentionally imports no Architect generator.

This is a static and traceability assessor, not semantic, runtime or deployment proof.
No package scripts, Terraform providers or model-generated code are executed here.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

PREFIXES = {'aws': 'aws_', 'azure': ('azurerm_', 'azuread_', 'azapi_'), 'gcp': 'google_', 'ibm': 'ibm_'}
PROVIDER_SOURCES={'aws':('aws','hashicorp/aws'),'azurerm':('azure','hashicorp/azurerm'),'azuread':('azure','hashicorp/azuread'),'azapi':('azure','azure/azapi'),'google':('gcp','hashicorp/google'),'google-beta':('gcp','hashicorp/google-beta'),'ibm':('ibm','ibm-cloud/ibm')}

def assess(case):
    case = Path(case).resolve()
    root = case / 'handoff'
    findings = []
    def add(code, detail):
        findings.append({'code': code, 'detail': detail})
    def safe(name):
        p = PurePosixPath(name)
        if not isinstance(name, str) or '\\' in name or p.is_absolute() or '..' in p.parts:
            add('unsafe-path', str(name)); return None
        target = root.joinpath(*p.parts)
        if any(part.is_symlink() for part in [target, *target.parents] if part != root.parent):
            add('symlink', name); return None
        if not target.is_file():
            add('missing-file', name); return None
        return target
    def read(name):
        target = safe(name)
        if not target: return {}
        try: return json.loads(target.read_text())
        except (ValueError, UnicodeError):
            add('invalid-json', name); return {}
    manifest = read('manifest.json')
    inventory = manifest.get('files', [])
    if len(inventory) != len(set(inventory)): add('duplicate-inventory', 'Manifest has duplicate file paths')
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    for name in inventory: safe(name)
    for name in sorted(actual - set(inventory)): add('unlisted-file', name)
    if manifest.get('deploymentExecuted') is not False: add('deployment-claim', 'No cloud operation was authorized by this evaluation')
    receipt_file = case / 'export-assessment.json'
    if receipt_file.exists():
        receipt = json.loads(receipt_file.read_text())
        digests = receipt.get('digests', {})
        for name in actual:
            target = safe(name)
            if target and hashlib.sha256(target.read_bytes()).hexdigest() != digests.get(name): add('artifact-digest-mismatch', name)
        for name in set(digests) - actual: add('missing-receipted-file', name)
    else: add('missing-export-receipt', 'No original exported byte hashes')
    saved = read('project.atmem-ai-architect.json')
    source_file = case / 'project.json'
    source = json.loads(source_file.read_text()) if source_file.exists() else {}
    if saved.get('discovery', {}).get('problem') != source.get('requirements'): add('changed-raw-scope', 'Export differs from evaluated project intent')
    if saved.get('requirements', []) != source.get('needs', []): add('changed-requirements', 'Export differs from evaluated requirement records')
    design = saved.get('design', {})
    if design.get('nodes') != source.get('nodes'): add('changed-design', 'Exported components differ from evaluated project')
    expected_provider = source.get('provider')
    config = read('terraform/main.tf.json')
    for name,body in config.get('terraform',{}).get('required_providers',{}).items():
        expected=PROVIDER_SOURCES.get(name)
        if not expected or not isinstance(body,dict)or str(body.get('source','')).lower()!=expected[1]:add('unreviewed-provider-source',name)
        elif expected[0]!=expected_provider:add('wrong-provider-source',name)
    addresses = {f'{kind}.{name}' for kind, bodies in config.get('resource', {}).items() for name in bodies}
    # Independent verifier consumes reviewed lifecycle evidence, not the compiler's
    # self-reported quality result. New-client cases contain no account eligibility
    # attestation; structurally valid resources cannot waive this boundary.
    lifecycle=json.loads((Path(__file__).resolve().parents[1]/'agent-skills/service-lifecycle.json').read_text())
    for rule in lifecycle['rules']:
        if not rule['newCustomerDefaultAllowed'] and any(config.get('resource',{}).get(kind) for kind in rule['resourceTypes']):
            add('service-eligibility-unverified',rule['id']+': '+rule['requiredEvidence'])
    for kind, bodies in config.get('resource', {}).items():
        if kind != 'terraform_data' and not kind.startswith(PREFIXES.get(expected_provider, 'unsupported_')): add('wrong-provider-resource', kind)
        for name, body in bodies.items():
            if 'provisioner' in body: add('execution-hook', f'{kind}.{name}')
    if config.get('module'): add('unreviewed-module', 'Requires independent source/dependency approval')
    if any(k in config.get('data', {}) for k in ['external', 'terraform_remote_state']): add('execution-or-state-reader', 'Not admitted for this evaluation')
    for provider, body in config.get('provider', {}).items():
        for key in ['credentials','access_key','secret_key','client_secret','token','ibmcloud_api_key']:
            if body.get(key): add('embedded-credential', provider + '.' + key)
    unfinished = config.get('locals', {}).get('unfinished_work', [])
    if unfinished: add('unfinished-infrastructure', f'{len(unfinished)} unresolved compiler gates')
    if len(addresses - {'terraform_data.review_gate'}) == 0: add('no-cloud-resources', 'No implementation resources emitted')
    mapping = read('spec-kit/implementation-map.json')
    unimplemented = []
    for component in mapping.get('components', []):
        for address in component.get('terraformAddresses', []):
            if address not in addresses: add('missing-mapped-address', address)
        for name in component.get('generatedFiles', []): safe(name)
        if component.get('applicationImplementation') == 'not_established': unimplemented.append(component['id'])
        if component.get('applicationImplementation') == 'supplied_image_required':add('application-image-not-qualified',component['id']+' requires an actual source-bound application image and behavior tests')
    if unimplemented: add('unestablished-application', ', '.join(unimplemented))
    tasks = read('spec-kit/tasks.json').get('tasks', [])
    by_id = {t['id']: t for t in tasks}
    if len(by_id) != len(tasks): add('duplicate-task-id', 'Task IDs must be unique')
    visited, active = set(), set()
    def walk(key):
        if key in active: add('task-cycle', key); return
        if key in visited: return
        active.add(key)
        for dep in by_id[key].get('dependsOn', []):
            if dep not in by_id: add('missing-task-dependency', key + ' -> ' + dep)
            else: walk(dep)
        active.remove(key); visited.add(key)
    for key in by_id: walk(key)
    for task in tasks:
        for name in task.get('files', []): safe(name)
        if not task.get('acceptance'): add('missing-task-acceptance', task['id'])
    return {'version':1,'case':case.name,'assessor':'independent-emitted-byte-static-v1','filesInspected':len(actual),'resourceAddresses':len(addresses),'taskCount':len(tasks),'findings':findings,'staticChecksPassed':not findings,'semanticCoverage':'requires independent acceptance review','runtime':'not_run_by_this_assessor','cloudPlan':'not_run','nearDeploymentQualified':False,'boundary':'Artifact integrity and static traceability only. Compiler coverage flags and a short conversation cannot establish application correctness.'}

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('case');parser.add_argument('--output');args=parser.parse_args()
    result=assess(args.case);text=json.dumps(result,indent=2)+'\n'
    if args.output:Path(args.output).write_text(text)
    else:print(text,end='')
