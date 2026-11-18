#!/usr/bin/env python3
"""Staged real-GitHub acceptance driver; default is a local, read-only plan.

Seeding, owner merges/tags, protection changes, token provisioning/revocation and
cleanup are explicit operator actions. This driver never gains those capabilities.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.maintenance.campaigns import CampaignService
from server.maintenance.github_adapter import GitHubBroker, REPOSITORY
from server.maintenance.graph import Root, ModuleBinding
from server.maintenance.publication import Publication
from server.maintenance.store import Store, digest
from server.maintenance.workers import MaintenanceWorker

TENANT = 'local-owner'
PROJECT = 'r3-disposable-acceptance'


def scope(owner):
    if not REPOSITORY.fullmatch(owner + '/acceptance') or '/' in owner:
        raise ValueError('Select one exact GitHub resource owner')
    module = owner + '/atmem-maintenance-r3-module'
    roles = [('shared', 'root-shared', module),
             ('consumer-a', 'root-consumer-a', owner + '/atmem-maintenance-r3-consumer-a'),
             ('consumer-b', 'root-consumer-b', owner + '/atmem-maintenance-r3-consumer-b'),
             ('unrelated', 'root-unrelated', owner + '/atmem-maintenance-r3-unprotected')]
    repositories = []
    for fixture, root, repository in roles:
        text = (ROOT / 'tests/maintenance/fixtures/campaign' / fixture / 'main.tf').read_text()
        text = text.replace('git::https://example.invalid/shared-batch.git?ref=v1.0.0',
                            'git::https://github.com/' + module + '.git?ref=v1.0.0')
        files = {'main.tf': text}
        if fixture == 'shared':
            files['.github/workflows/review.yml'] = (
                'name: Disposable acceptance\non: [push, pull_request]\npermissions:\n  contents: read\n'
                'jobs:\n  review:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo "AtMem disposable acceptance only"\n')
        repositories.append({'role': fixture, 'root': root, 'repository': repository, 'visibility': 'private',
                             'files': files, 'fileDigests': {p: hashlib.sha256(t.encode()).hexdigest() for p, t in files.items()}})
    plan = {'schemaVersion': 1, 'projectId': PROJECT, 'owner': owner, 'repositories': repositories,
            'automation': 'One inert echo workflow may run on push/PR. GitHub Actions usage can bill.',
            'productWrites': ['Git blobs/trees/commits', 'atmem-upgrades/* refs', 'draft pull requests'],
            'operatorOnly': ['Create and seed the four new private repositories', 'Create initial module tag v1.0.0',
                             'Merge/tag disposable module and merge disposable consumers',
                             'Configure a protected proposal branch for denial testing',
                             'Inject a human commit race', 'Revoke disposable fine-grained token',
                             'Confirm cleanup separately; no automatic deletion'],
            'excluded': ['Existing application repositories', 'Cloud access or deployment', 'Public release/npm publication'],
            'remainingManualGates': ['Interruption/timeout injection and restart reconciliation',
                                     'Revocation/expiry and protected/default/unowned branch denial',
                                     'Conditional append versus a human commit', 'Cross-install ownership conflict',
                                     'Actual module release and separate consumer wave', 'Retain sanitized evidence for every gate']}
    return {**plan, 'scopeDigest': digest(plan)}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix('.pending')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, indent=2);stream.write('\n')
    os.replace(temporary, path)


def wait(service, ident):
    deadline = time.monotonic() + 1250
    while time.monotonic() < deadline:
        value = service.get(TENANT, ident)
        if value.status != 'checking':
            if value.status not in {'module_release_pending', 'local_release_checked'}:
                raise ValueError('Checks did not qualify: ' + value.status + '; inspect the retained campaign')
            return value
        time.sleep(.25)
    raise ValueError('Acceptance wait expired; inspect retained state before retrying')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', default='plan', choices=['plan', 'prepare', 'preview', 'publish', 'observe-release', 'status', 'reconcile'])
    parser.add_argument('--owner', default='aetna000')
    parser.add_argument('--home', type=Path)
    parser.add_argument('--worker-config', type=Path)
    parser.add_argument('--connection', help='Existing OS-keychain connection ID; never a token')
    parser.add_argument('--approved-scope', help='Exact reviewed plan digest; not a publication confirmation')
    parser.add_argument('--confirm-preview', help='Exact separately reviewed preview digest for this wave')
    parser.add_argument('--tag', help='Existing operator-created actual module release tag')
    args = parser.parse_args();plan = scope(args.owner)
    if args.action == 'plan':
        print(json.dumps(plan, indent=2));return
    if args.approved_scope != plan['scopeDigest'] or args.home is None or args.worker_config is None:
        raise ValueError('Supply the approved disposable scope digest, private home and qualified worker configuration')
    if not args.connection:
        raise ValueError('Connect only these disposable repositories through the interactive keychain CLI first')
    home = args.home.expanduser().resolve();state_path = home / 'r3-acceptance.json'
    db = Store(home / 'maintenance.sqlite')
    broker = GitHubBroker(db)
    connection = broker.connection(TENANT, PROJECT, args.connection)
    expected = {r['repository'] for r in plan['repositories']}
    if connection.resourceOwner != args.owner or set(connection.repositories) != expected:
        raise ValueError('Acceptance requires a connection scoped to exactly the four disposable repositories')
    worker = MaintenanceWorker.from_file(args.worker_config)
    service = CampaignService(db, worker)
    publication = Publication(db, service, broker)
    try:
        if args.action == 'prepare':
            if state_path.exists():
                raise ValueError('Acceptance state already exists; inspect it rather than replacing audit history')
            sources, roots, revisions = [], [], {}
            for item in plan['repositories']:
                repository = item['repository']
                metadata = broker.repository_metadata(TENANT, PROJECT, args.connection, repository)
                if metadata.get('private') is not True:
                    raise ValueError('All disposable repositories must be private')
                base = metadata['default_branch']
                branch = broker.request(TENANT, PROJECT, args.connection, repository, 'GET', '/branches/' + base)['data']
                commit = branch['commit']['sha']
                source = broker.materialize(TENANT, PROJECT, args.connection, repository, commit, list(item['files']))
                if {f.path: f.text for f in source.files} != item['files']:
                    raise ValueError('Disposable fixture bytes differ from the exact reviewed plan')
                sources.append(source);roots.append(Root(id=item['root'], snapshotId=source.id))
                revisions[item['root']] = commit
            bindings = [ModuleBinding(consumer='root-' + name, module='queue' if name == 'consumer-a' else 'archive',
                target='root-shared', source='git::https://github.com/' + plan['repositories'][0]['repository'] + '.git?ref=v1.0.0',
                targetTreeDigest=sources[0].treeDigest, resolvedCommit=revisions['root-shared']) for name in ['consumer-a', 'consumer-b']]
            value = service.create(TENANT, PROJECT, 'acceptance-operator', sources, roots, bindings)
            state = {'scopeDigest': plan['scopeDigest'], 'campaignId': value.id, 'previews': [], 'evidenceLevel': 'real_github_reads_and_real_local_checks'}
            save(state_path, state)
            service.start(TENANT, value.id, value.revision, value.graph['digest'], 'acceptance-prepare', True, module='root-shared')
            value = wait(service, value.id)
            save(home / 'r3-checked-campaign.json', service.export(TENANT, value.id))
            print(json.dumps({'campaignId': value.id, 'status': value.status, 'next': 'preview'}, indent=2));return
        state = json.loads(state_path.read_text())
        if state['scopeDigest'] != plan['scopeDigest']:
            raise ValueError('Scope changed; existing acceptance state cannot be reused')
        value = service.get(TENANT, state['campaignId'])
        if args.action == 'preview':
            wave = 'consumers' if value.status == 'local_release_checked' else 'module'
            merged = set((value.result or {}).get('observedMergedConsumers', []))
            selected = plan['repositories'][1:3] if wave == 'consumers' else plan['repositories'][:1]
            targets = [{'root': r['root'], 'repository': r['repository'], 'connection': args.connection} for r in selected if r['root'] not in merged]
            preview = publication.preview(TENANT, PROJECT, value.id, targets, wave=wave)
            save(home / ('r3-preview-' + preview['id'] + '.json'), preview)
            state['previews'].append(preview['id']);save(state_path, state)
            print(json.dumps({'previewId': preview['id'], 'previewDigest': preview['digest'], 'wave': wave,
                              'next': 'Review the exact saved preview and automation before confirming this digest.'}, indent=2))
        elif args.action == 'observe-release':
            if not args.tag:
                raise ValueError('Supply an existing operator-created module release tag')
            publication.observe_release(TENANT, PROJECT, value.id, expected_revision=value.revision,
                graph_digest=value.graph['digest'], key='release-' + digest({'tag': args.tag, 'revision': value.revision}),
                compute_confirmed=True, connection=args.connection, repository=plan['repositories'][0]['repository'], tag=args.tag)
            checked = wait(service, value.id)
            save(home / 'r3-checked-release.json', service.export(TENANT, value.id))
            print(json.dumps({'status': checked.status, 'next': 'preview a new consumer wave'}, indent=2))
        elif args.action in {'publish', 'reconcile'}:
            if not state['previews']:
                raise ValueError('Prepare and review an exact publication preview first')
            preview = publication.ledger.preview(TENANT, PROJECT, state['previews'][-1])
            if args.action == 'publish':
                if args.confirm_preview != preview['digest']:
                    raise ValueError('Exact preview digest confirmation required; each wave is separate')
                grant = publication.authorize(TENANT, PROJECT, preview['id'], preview['digest'], True)
                result = publication.publish(TENANT, PROJECT, preview['id'], grant['id'], preview['digest'])
            else:
                result = publication.reconcile(TENANT, PROJECT, preview['id'])
            save(home / ('r3-result-' + preview['id'] + '.json'), result)
            print(json.dumps({'status': result.get('status'), 'previewId': preview['id']}, indent=2))
        else:
            result = publication.poll(TENANT, PROJECT, value.id)
            save(home / 'r3-pr-observations.json', result)
            print(json.dumps(result, indent=2))
    finally:
        service.close()


if __name__ == '__main__':
    try:
        main()
    except (ValueError, PermissionError, RuntimeError, OSError) as error:
        print('Acceptance stopped: ' + str(error), file=sys.stderr)
        sys.exit(1)
