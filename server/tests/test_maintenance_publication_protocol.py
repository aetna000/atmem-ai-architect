"""Fake GitHub protocol/failure injection. Real network acceptance is NOT inferred."""
import base64
import copy
from datetime import datetime
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import urllib.parse
import time

from server.maintenance.campaigns import CampaignService
from server.maintenance.git_objects import tree_sha, commit_object
from server.maintenance.github_adapter import GitHubBroker, GitHubError, UncertainWrite, git_blob_sha
from server.maintenance.planner import planner_digest
from server.maintenance.publication import Publication
from server.maintenance.store import Store, Conflict
from server.tests.test_maintenance_graph import frozen_campaign
from server.tests.test_maintenance_github import FakeKeychain


class FakeGitHub:
    def __init__(self, files):
        self.metadata = {'id': 100, 'full_name': 'owner/project', 'owner': {'login': 'owner'}, 'default_branch': 'main', 'archived': False}
        self.blobs, self.trees, self.commits, self.refs, self.pulls, self.writes = {}, {}, {}, {}, [], []
        self.timeout_after, self.timeout_before = None, None
        self.protect_proposals = False
        entries = []
        for path, text in files.items():
            sha = git_blob_sha(text.encode())
            self.blobs[sha] = text.encode()
            entries.append({'path': path, 'mode': '100644', 'type': 'blob', 'sha': sha, 'size': len(text.encode())})
        sha = tree_sha(entries)
        self.trees[sha] = entries
        self.commits['a' * 40] = {'sha': 'a' * 40, 'tree': {'sha': sha}, 'parents': [], 'message': 'baseline'}
        self.refs['main'] = 'a' * 40

    def request(self, token, method, path, body=None, headers=None):
        parsed = urllib.parse.urlsplit(path);route = parsed.path
        if route == '/user':
            data = {'id': 7, 'login': 'customer'}
        elif route == '/repos/owner/project':
            data = self.metadata
        else:
            prefix = '/repos/owner/project'
            if not route.startswith(prefix):
                raise AssertionError('Unexpected repository')
            suffix = urllib.parse.unquote(route[len(prefix):])
            if method == 'POST':
                self.writes.append((suffix, copy.deepcopy(body)))
                if self.timeout_before == suffix:
                    self.timeout_before = None
                    raise UncertainWrite(0)
                if suffix == '/git/blobs':
                    raw = base64.b64decode(body['content']);sha = git_blob_sha(raw);self.blobs[sha] = raw;data = {'sha': sha}
                elif suffix == '/git/trees':
                    entries = {item['path']: dict(item) for item in self.trees[body['base_tree']] if item['type'] != 'tree'}
                    for item in body['tree']:
                        entries[item['path']] = {**item, 'size': len(self.blobs[item['sha']])}
                    sha = tree_sha(list(entries.values()));self.trees[sha] = list(entries.values());data = {'sha': sha}
                elif suffix == '/git/commits':
                    stamp = int(datetime.fromisoformat(body['author']['date']).timestamp())
                    sha, _ = commit_object(body['tree'], body['parents'][0], body['message'], stamp)
                    data = {'sha': sha, 'tree': {'sha': body['tree']}, 'parents': [{'sha': body['parents'][0]}], 'message': body['message']}
                    self.commits[sha] = data
                elif suffix == '/git/refs':
                    branch = body['ref'].removeprefix('refs/heads/')
                    if branch in self.refs:
                        raise GitHubError(422)
                    self.refs[branch] = body['sha'];data = {'ref': body['ref'], 'object': {'sha': body['sha']}}
                elif suffix == '/pulls':
                    if any(p['head']['ref'] == body['head'] and p['state'] == 'open' for p in self.pulls):
                        raise GitHubError(422)
                    data = {**body, 'number': len(self.pulls) + 1, 'state': 'open',
                            'head': {'ref': body['head'], 'sha': self.refs[body['head']]}}
                    self.pulls.append(data)
                else:
                    raise AssertionError('Unreviewed fake mutation: ' + suffix)
                if self.timeout_after == suffix:
                    self.timeout_after = None
                    raise UncertainWrite(0)
            elif suffix.startswith('/git/ref/heads/'):
                branch = suffix.removeprefix('/git/ref/heads/')
                if branch not in self.refs:raise GitHubError(404)
                data = {'object': {'sha': self.refs[branch]}}
            elif suffix.startswith('/branches/'):
                branch = suffix.removeprefix('/branches/')
                if branch not in self.refs:raise GitHubError(404)
                data = {'name': branch, 'commit': {'sha': self.refs[branch]}, 'protected': self.protect_proposals and branch != 'main'}
            elif suffix.startswith('/rules/branches/'):
                data = [{'type': 'update'}] if self.protect_proposals else []
            elif suffix.startswith('/commits/'):
                sha = suffix.rsplit('/', 1)[1]
                if sha not in self.commits:raise GitHubError(404)
                data = {'sha': sha, 'commit': {'tree': self.commits[sha]['tree']}}
            elif suffix.startswith('/git/commits/'):
                sha = suffix.rsplit('/', 1)[1]
                if sha not in self.commits:raise GitHubError(404)
                data = self.commits[sha]
            elif suffix.startswith('/git/trees/'):
                sha = suffix.rsplit('/', 1)[1]
                if sha not in self.trees:raise GitHubError(404)
                data = {'sha': sha, 'tree': self.trees[sha], 'truncated': False}
            elif suffix.startswith('/git/blobs/'):
                sha = suffix.rsplit('/', 1)[1]
                if sha not in self.blobs:raise GitHubError(404)
                raw = self.blobs[sha];data = {'sha': sha, 'encoding': 'base64', 'content': base64.b64encode(raw).decode()}
            elif suffix == '/pulls':
                query = urllib.parse.parse_qs(parsed.query)
                head = query['head'][0].split(':', 1)[1]
                data = [p for p in self.pulls if p['head']['ref'] == head and p['base'] == query['base'][0]]
            else:
                raise AssertionError('Unexpected fake read: ' + suffix)
        return {'data': copy.deepcopy(data), 'headers': {}, 'status': 200}


class PublicationProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.db = Store(root / 'maintenance.sqlite')
        frozen = Path(__file__).resolve().parents[2] / 'specs/032-infrastructure-upgrades/evidence/r2.json'
        self.result = json.loads(frozen.read_text())['primary']
        self.service = CampaignService(self.db, SimpleNamespace(identity=self.result['workerIdentity']))
        self.addCleanup(self.service.close)
        sources, roots, bindings = frozen_campaign()
        value = self.service.create('tenant-one', 'project-one', 'actor-one', sources, roots, bindings)
        self.result['graphDigest'] = value.graph['digest'];self.result['plannerDigest'] = planner_digest()
        value.status = 'module_release_pending';value.result = self.result
        self.value = self.service.store.put(value, value.revision)
        self.remote = FakeGitHub(self.result['moduleBefore'])
        self.broker = GitHubBroker(self.db, FakeKeychain(), self.remote)
        self.connection = self.broker.register('tenant-one', ['project-one'], 'owner', ['owner/project'], 'github_pat_' + 'x' * 30, int(time.time()) + 3600)
        self.publication = Publication(self.db, self.service, self.broker)
        self.targets = [{'root': 'root-shared', 'repository': 'owner/project', 'connection': self.connection.id}]

    def preview(self):
        return self.publication.preview('tenant-one', 'project-one', self.value.id, self.targets)

    def authorized(self):
        preview = self.preview()
        auth = self.publication.authorize('tenant-one', 'project-one', preview['id'], preview['digest'], True)
        return preview, auth

    def publish(self, preview, auth):
        return self.publication.publish('tenant-one', 'project-one', preview['id'], auth['id'], preview['digest'])

    def test_exact_module_wave_reconciles_without_duplicates_and_preserves_default(self):
        preview, auth = self.authorized()
        self.assertFalse(self.remote.writes)
        result = self.publish(preview, auth)
        self.assertEqual(result['status'], 'published_proposals')
        self.assertEqual(self.remote.refs['main'], 'a' * 40)
        self.assertEqual(len(self.remote.pulls), 1);self.assertTrue(self.remote.pulls[0]['draft'])
        count = len(self.remote.writes)
        self.assertEqual(self.publish(preview, auth)['status'], 'published_proposals')
        self.assertEqual(len(self.remote.writes), count)
        self.assertEqual(sum(path == '/git/refs' for path, _ in self.remote.writes), 1)
        self.assertEqual(sum(path == '/pulls' for path, _ in self.remote.writes), 1)
        # A newly reviewed identical wave recognizes its own exact branch/PR.
        second, new_auth = self.authorized()
        self.assertEqual([a['kind'] for a in second['actions']], ['pull'])
        self.assertEqual(self.publish(second, new_auth)['status'], 'published_proposals')
        self.assertEqual(len(self.remote.writes), count)

    def test_uncertain_ref_response_recovers_existing_object_once(self):
        preview, auth = self.authorized();self.remote.timeout_after = '/git/refs'
        self.assertEqual(self.publish(preview, auth)['status'], 'reconciliation_required')
        self.assertEqual(self.publish(preview, auth)['status'], 'published_proposals')
        self.assertEqual(len(self.remote.pulls), 1)
        self.assertEqual(sum(path == '/git/refs' for path, _ in self.remote.writes), 1)

    def test_uncertain_pr_response_recovers_existing_pr_once(self):
        preview, auth = self.authorized();self.remote.timeout_after = '/pulls'
        self.assertEqual(self.publish(preview, auth)['status'], 'reconciliation_required')
        self.assertEqual(self.publish(preview, auth)['status'], 'published_proposals')
        self.assertEqual(len(self.remote.pulls), 1)
        self.assertEqual(sum(path == '/pulls' for path, _ in self.remote.writes), 1)

    def test_pr_timeout_without_observable_result_is_not_permission_to_repeat(self):
        preview, auth = self.authorized();self.remote.timeout_before = '/pulls'
        self.assertEqual(self.publish(preview, auth)['status'], 'reconciliation_required')
        writes = len(self.remote.writes)
        self.assertEqual(self.publish(preview, auth)['status'], 'reconciliation_required')
        self.assertEqual(len(self.remote.writes), writes)

    def test_protection_default_head_drift_human_edits_and_competing_installation_stop(self):
        self.remote.protect_proposals = True
        with self.assertRaises(PermissionError):self.preview()
        self.remote.protect_proposals = False
        preview, auth = self.authorized()
        branch = preview['targets'][0]['branch']
        self.remote.refs[branch] = 'c' * 40
        with self.assertRaises(Conflict):self.publish(preview, auth)
        self.assertFalse(self.remote.writes)
        self.remote.refs.pop(branch)
        self.remote.refs['main'] = 'c' * 40
        with self.assertRaises(Conflict):self.publish(preview, auth)
        self.assertFalse(self.remote.writes)
        self.remote.refs['main'] = 'a' * 40
        preview, auth = self.authorized()
        self.remote.timeout_after = '/git/refs'
        self.assertEqual(self.publish(preview, auth)['status'], 'reconciliation_required')
        other_db = Store(Path(self.temp.name) / 'another-install.sqlite')
        other = Publication(other_db, self.service, self.broker)
        with self.assertRaisesRegex(Conflict, 'unowned'):
            other.preview('tenant-one', 'project-one', self.value.id, self.targets)
        self.assertEqual(sum(path == '/git/refs' for path, _ in self.remote.writes), 1)

    def test_consumer_simulation_cannot_authorize_remote_wave_and_default_denied_even_unprotected(self):
        with self.assertRaisesRegex(Conflict, 'Authenticated'):
            self.publication.preview('tenant-one', 'project-one', self.value.id, self.targets, wave='consumers')
        branch = 'atmem-upgrades/' + self.value.graph['digest'][:32] + '/root-shared'
        self.remote.metadata['default_branch'] = branch;self.remote.refs[branch] = 'a' * 40
        with self.assertRaises(PermissionError):self.preview()
        self.assertFalse(self.remote.writes)
