"""Frozen dependency oracle and changed-composition tests; no network/model calls."""
import hashlib
import json
from pathlib import Path
import time
import unittest

from server.maintenance.graph import Root, ModuleBinding, discover, affected_waves
from server.maintenance.inventory import snapshot

FIXTURES = Path(__file__).resolve().parents[2] / 'tests/maintenance/fixtures/campaign'


def root_id(name):
    return 'root-' + name.replace('/', '-')


def fixture(name, *, commit='a' * 40):
    files = {p.relative_to(FIXTURES / name).as_posix(): p.read_text()
             for p in (FIXTURES / name).rglob('*.tf')}
    return snapshot(files, 'repository-' + name, commit=commit)


def frozen_campaign():
    snapshots = [fixture(n) for n in ['shared', 'consumer-a', 'consumer-b', 'unrelated']]
    roots = [Root(id=root_id(n), snapshotId=s.id) for n, s in zip(['shared', 'consumer-a', 'consumer-b', 'unrelated'], snapshots)]
    bindings = [ModuleBinding(consumer=root_id(n), module='queue' if n == 'consumer-a' else 'archive', target=root_id('shared'),
                             source='git::https://example.invalid/shared-batch.git?ref=v1.0.0',
                             targetTreeDigest=snapshots[0].treeDigest, resolvedCommit='a' * 40)
                for n in ['consumer-a', 'consumer-b']]
    return snapshots, roots, bindings


class GraphTests(unittest.TestCase):
    def test_frozen_affected_oracle_order_and_unrelated_preserved(self):
        frozen = json.loads((FIXTURES / 'manifest.json').read_text())
        for path, expected in frozen['files'].items():
            self.assertEqual(hashlib.sha256((FIXTURES / path).read_bytes()).hexdigest(), expected)
        snapshots, roots, bindings = frozen_campaign()
        graph = discover(snapshots, roots, bindings)
        self.assertEqual(sorted((e['consumer'], e['dependency']) for e in graph['edges']),
                         sorted((root_id(a), root_id(b)) for a, b in frozen['expected']['edges']))
        scope = affected_waves(graph, [root_id('shared')])
        self.assertEqual(scope['affected'], sorted(root_id(n) for n in frozen['expected']['affected']))
        self.assertEqual(scope['waves'], [[root_id(n) for n in wave] for wave in frozen['expected']['order']])
        self.assertEqual(scope['status'], 'discovered')
        self.assertNotIn(root_id('unrelated'), scope['affected'])
        self.assertTrue(all(e['end'] > e['start'] and e['line'] > 0 for e in graph['edges']))
        self.assertEqual(graph['digest'], discover(list(reversed(snapshots)), list(reversed(roots)), list(reversed(bindings)))['digest'])

    def test_holdout_local_monorepo_and_cycle_without_fetch(self):
        selected = fixture('holdout-monorepo')
        roots = [Root(id='root-ingest', snapshotId=selected.id, directory='apps/ingest'),
                 Root(id='root-module', snapshotId=selected.id, directory='modules/queue')]
        graph = discover([selected], roots)
        self.assertEqual([(e['consumer'], e['dependency']) for e in graph['edges']], [('root-ingest', 'root-module')])
        self.assertEqual(affected_waves(graph, ['root-module'])['waves'], [['root-module'], ['root-ingest']])
        files = {n + '/main.tf': (FIXTURES / n / 'main.tf').read_text() for n in ['cycle-a', 'cycle-b']}
        selected = snapshot(files, 'repository-cycle')
        graph = discover([selected], [Root(id=root_id(n), snapshotId=selected.id, directory=n) for n in ['cycle-a', 'cycle-b']])
        self.assertEqual(graph['cycles'], [['root-cycle-a', 'root-cycle-b']])
        self.assertEqual(affected_waves(graph, ['root-cycle-a'])['status'], 'blocked')

    def test_dynamic_registry_ranges_missing_materialization_and_stale_binding(self):
        for name, reason in [('dynamic-consumer', 'dynamic_or_missing_source'),
                             ('range-consumer', 'remote_module_requires_materialization')]:
            selected = fixture(name)
            graph = discover([selected], [Root(id=root_id(name), snapshotId=selected.id)])
            self.assertEqual(graph['unknowns'][0]['reason'], reason)
            self.assertEqual(affected_waves(graph, [root_id(name)])['status'], 'blocked')
        snapshots, roots, bindings = frozen_campaign()
        for field, value in [('targetTreeDigest', 'b' * 64), ('resolvedCommit', 'b' * 40),
                             ('source', 'git::https://unapproved.invalid/module?ref=v9'), ('version', '>= 1.0')]:
            changed = bindings[0].model_copy(update={field: value})
            graph = discover(snapshots, roots, [changed, bindings[1]])
            self.assertEqual(graph['unknowns'][0]['reason'], 'dependency_binding_stale')
            self.assertEqual(affected_waves(graph, [root_id('shared')])['status'], 'blocked')

    def test_provider_aliases_constraints_and_mappings_retained_not_solved(self):
        selected = snapshot({'main.tf': '''terraform {
 required_providers { aws = { source = "hashicorp/aws", version = ">= 5.0, < 6.0", configuration_aliases = [aws.secondary] } }
}
provider "aws" { alias = "secondary" }
module "private" { source = "company/private/aws" version = "~> 1.2" providers = { aws = aws.secondary } }
'''}, 'repository-aliases')
        graph = discover([selected], [Root(id='root-aliases', snapshotId=selected.id)])
        self.assertEqual(graph['nodes'][0]['aliases'][0]['alias'], 'secondary')
        self.assertIn('configuration_aliases', graph['nodes'][0]['providers'][0]['expression'])
        self.assertIn('aws.secondary', graph['unknowns'][0]['providerMapping'])
        self.assertEqual(graph['unknowns'][0]['version'], '~> 1.2')

    def test_provider_lock_identity_is_recorded_without_inferring_module_resolution(self):
        selected = snapshot({'main.tf': 'module "private" { source = "company/queue/aws" version = "~> 1.0" }',
                             '.terraform.lock.hcl': 'provider "registry.terraform.io/hashicorp/aws" { version = "5.100.0" hashes = ["h1:example"] }'},
                            'repository-locks')
        graph = discover([selected], [Root(id='root-locks', snapshotId=selected.id)])
        lock = graph['nodes'][0]['locks'][0]
        self.assertEqual(lock['path'], '.terraform.lock.hcl')
        self.assertEqual(lock['sha256'], selected.files[0].sha256)
        self.assertEqual(lock['selection'][0]['registry.terraform.io/hashicorp/aws']['version'], '5.100.0')
        self.assertEqual(graph['unknowns'][0]['reason'], 'remote_module_requires_materialization')

    def test_escape_ambiguity_unused_bindings_and_digest_tampering_denied(self):
        selected = snapshot({'main.tf': 'module "outside" { source = "../outside" }'}, 'repository-outside')
        root = Root(id='root-outside', snapshotId=selected.id)
        graph = discover([selected], [root])
        self.assertEqual(graph['unknowns'][0]['reason'], 'local_source_outside_selected_repository')
        graph['unknowns'].clear()
        with self.assertRaisesRegex(ValueError, 'identity'):
            affected_waves(graph, [root.id])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            discover([selected], [root, root.model_copy(update={'id': 'root-second'})])
        snapshots, roots, bindings = frozen_campaign()
        with self.assertRaisesRegex(ValueError, 'Unused'):
            discover(snapshots, roots, bindings + [bindings[0].model_copy(update={'module': 'absent'})])
        with self.assertRaises(ValueError):
            Root(id='root-escape', snapshotId=selected.id, directory='../private')

    def test_30_materialized_snapshot_discovery_budget(self):
        selected = [snapshot({'main.tf': 'terraform { required_providers { aws = { source = "hashicorp/aws", version = "6.0.0" } } }'},
                             f'repository-scale-{i}') for i in range(30)]
        roots = [Root(id=f'root-scale-{i:02}', snapshotId=s.id) for i, s in enumerate(selected)]
        started = time.monotonic()
        graph = discover(selected, roots)
        elapsed = time.monotonic() - started
        self.assertEqual(len(graph['nodes']), 30)
        self.assertFalse(graph['unknowns'])
        self.assertLess(elapsed, 300)
