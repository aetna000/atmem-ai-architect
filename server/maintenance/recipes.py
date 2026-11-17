"""Explicit version-qualified adapter; general authoring never widens its scope."""
import json
from pathlib import Path

from .inventory import inventory, walk
from .models import Finding
from .patches import build_candidate, source_map
from .store import digest


def recipe():
    return json.loads((Path(__file__).parent / 'catalog/aws-batch-queue-v6.json').read_text())


def recipe_digest():
    import hashlib
    return digest({'catalog': recipe(), 'authoring': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})


def applicability(snapshot):
    report = inventory(snapshot)
    findings = [Finding.model_validate(f) for f in report['findings'] if f['severity'] == 'blocked']
    if recipe()['withdrawn']:
        findings.append(Finding(code='recipe_withdrawn', message='This recipe is withdrawn.'))
    if findings:
        return report, findings
    if report['modules']:
        findings.append(Finding(code='module_resolution_required', message='Resolve module dependencies before preparing this root.'))
    provider_count, queue_count = 0, 0
    for path, document in report['files'].items():
        for block in document['semantic'].get('terraform', []):
            for required in block.get('required_providers', []):
                for selection in required.values():
                    provider_count += 1
                    if not isinstance(selection, dict) or selection.get('source') != 'hashicorp/aws' or selection.get('version') != '5.100.0':
                        findings.append(Finding(code='unsupported_provider_selection', path=path, message='Select exact reviewed AWS provider 5.100.0.'))
        for ref in document['traversals']:
            if '.compute_environments' in ref:
                findings.append(Finding(code='old_attribute_reference', path=path, message='Old queue attribute references require separate migration review.'))
        for block in walk(document['blocks']):
            if block['type'] == 'resource' and block['labels'][0] == 'aws_batch_job_queue':
                attrs = {a['name']: a for a in block['attributes']}
                old = attrs.get('compute_environments')
                if old:
                    queue_count += 1
                    if not old.get('tuple') or any(b['type'] in {'dynamic', 'compute_environment_order'} for b in block['blocks']):
                        findings.append(Finding(code='unsupported_queue_expression', path=path, line=old['line'], message='Use an explicit nonempty list without conflicting order blocks.'))
        # R1 is one root; nested roots are inventoried but cannot be silently skipped.
        if '/' in path and path.endswith('.tf'):
            findings.append(Finding(code='multiple_roots_require_campaign', path=path, message='Nested Terraform roots require a coordinated campaign.'))
    if not provider_count:
        findings.append(Finding(code='provider_version_missing', message='An explicit reviewed provider version is required.'))
    if not queue_count:
        findings.append(Finding(code='no_applicable_change', message='No supported Batch queue migration was found.'))
    return report, findings


def propose(snapshot, *, control=False):
    report, findings = applicability(snapshot)
    if findings:
        return None, findings
    before, after = source_map(snapshot), source_map(snapshot)
    for path, document in report['files'].items():
        edits = []
        for block in walk(document['blocks']):
            if block['type'] == 'required_providers':
                for attr in block['attributes']:
                    for member in attr.get('members', []):
                        if member['name'] == 'version':
                            edits.append((member['start'], member['end'], '"6.0.0"'))
            if not control and block['type'] == 'resource' and block['labels'][0] == 'aws_batch_job_queue':
                for attr in block['attributes']:
                    if attr['name'] != 'compute_environments':
                        continue
                    start, end = attr['start'], attr['end']
                    line_start = before[path].rfind('\n', 0, start) + 1
                    prefix = before[path][line_start:start]
                    indent = prefix if not prefix.strip() else '  '
                    blocks = []
                    for i, item in enumerate(attr['tuple']):
                        blocks.append('compute_environment_order {\n' + indent + '  compute_environment = ' + item['text'] +
                                      '\n' + indent + '  order = ' + str(i) + '\n' + indent + '}')
                    # Preserve every original comment from the replaced range, including tuple comments.
                    comments = [c['text'].strip() for c in document['comments']
                                if c['start'] >= start and c['end'] <= end and c['text'].strip()]
                    replacement = ('\n' + indent).join([*comments, *blocks])
                    edits.append((start, end, replacement))
        for start, end, replacement in sorted(edits, reverse=True):
            after[path] = after[path][:start] + replacement + after[path][end:]
    steps = ['Review the exact patch and provider state-upgrade behavior before merging.',
             'Run an authorized destination-specific plan and review rollback before deployment.']
    return build_candidate(before, after, manual_steps=steps), []
