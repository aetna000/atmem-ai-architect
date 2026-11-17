"""Fake GitHub protocol/failure injection. Real network acceptance is NOT inferred."""
import base64
import copy
from datetime import datetime
import json
import os
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
from server.maintenance.store import Store, Conflict, digest
from server.tests.test_maintenance_graph import frozen_campaign
from server.tests.test_maintenance_github import FakeKeychain


class FakeGitHub:
    def __init__(self, files):
        self.metadata = {'id': 100, 'full_name': 'owner/project', 'owner': {'login': 'owner'}, 'default_branch': 'main', 'archived': False}
        self.blobs, self.trees, self.commits, self.refs, self.pulls, self.writes = {}, {}, {}, {}, [], []
        self.timeout_after, self.timeout_before = None, None
        self.protect_proposals = False
        self.tags, self.tag_reads, self.move_tag_on_read = {}, 0, None
        self.append_race = False
        entries = []
        for path, text in files.items():
            sha = git_blob_sha(text.encode())
            self.blobs[sha] = text.encode()
            entries.append({'path': path, 'mode': '100644', 'type': 'blob', 'sha': sha, 'size': len(text.encode())})
        sha = tree_sha(entries)
        self.trees[sha] = entries
        self.commits['a' * 40] = {'sha': 'a' * 40, 'tree': {'sha': sha}, 'parents': [], 'message': 'baseline'}
        self.refs['main'] = 'a' * 40

    def append(self, body):
        self.writes.append(('/graphql', copy.deepcopy(body)))
        if self.timeout_before == '/graphql':
            self.timeout_before = None
            raise UncertainWrite(0)
        value = body['variables']['input'];branch = value['branch']['refName']
        parent = self.refs[branch]
        if self.append_race:
            self.append_race = False
            self.commits['c' * 40] = {'sha': 'c' * 40, 'tree': self.commits[parent]['tree'], 'parents': [{'sha': parent}], 'message': 'human change'}
            self.refs[branch] = 'c' * 40
        if self.refs[branch] != value['expectedHeadOid']:
            raise GitHubError(409)
        entries = {item['path']: dict(item) for item in self.trees[self.commits[parent]['tree']['sha']] if item['type'] != 'tree'}
        for item in value['fileChanges']['additions']:
            raw = base64.b64decode(item['contents']);sha = git_blob_sha(raw);self.blobs[sha] = raw
            entries[item['path']] = {'path': item['path'], 'mode': '100644', 'type': 'blob', 'sha': sha, 'size': len(raw)}
        for item in value['fileChanges']['deletions']:
            entries.pop(item['path'], None)
        tree = tree_sha(list(entries.values()));self.trees[tree] = list(entries.values())
        message = value['message']['headline'] + '\n\n' + value['message']['body'] + '\n'
        sha, _ = commit_object(tree, parent, message, 1700000000)
        self.commits[sha] = {'sha': sha, 'tree': {'sha': tree}, 'parents': [{'sha': parent}], 'message': message}
        self.refs[branch] = sha
        for pull in self.pulls:
            if pull['head']['ref'] == branch:pull['head']['sha'] = sha
        if self.timeout_after == '/graphql':
            self.timeout_after = None
            raise UncertainWrite(0)
        return {'data': {'data': {'createCommitOnBranch': {'commit': {'oid': sha}}}}, 'headers': {}, 'status': 200}

    def request(self, token, method, path, body=None, headers=None):
        if path == '/graphql':
            return self.append(body)
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
                    data = {**body, 'number': len(self.pulls) + 1, 'state': 'open', 'merged': False,
                            'base': {'ref': body['base'], 'repo': {'id': self.metadata['id']}},
                            'head': {'ref': body['head'], 'sha': self.refs[body['head']], 'repo': {'id': self.metadata['id']}}}
                    self.pulls.append(data)
                else:
                    raise AssertionError('Unreviewed fake mutation: ' + suffix)
                if self.timeout_after == suffix:
                    self.timeout_after = None
                    raise UncertainWrite(0)
            elif suffix.startswith('/git/ref/tags/'):
                self.tag_reads += 1
                tag = suffix.removeprefix('/git/ref/tags/')
                if tag not in self.tags:raise GitHubError(404)
                sha = 'c' * 40 if self.move_tag_on_read and self.tag_reads >= self.move_tag_on_read else self.tags[tag]
                data = {'object': {'type': 'commit', 'sha': sha}}
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
            elif suffix.startswith('/pulls/'):
                number = int(suffix.rsplit('/', 1)[1])
                data = next((p for p in self.pulls if p['number'] == number), None)
                if data is None:raise GitHubError(404)
            elif suffix == '/pulls':
                query = urllib.parse.parse_qs(parsed.query)
                head = query['head'][0].split(':', 1)[1]
                data = [p for p in self.pulls if p['head']['ref'] == head and p['base']['ref'] == query['base'][0]]
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
        self.result['digest'] = digest({k: v for k, v in self.result.items() if k != 'digest'})
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
        self.assertEqual(self.publication.poll('tenant-one', 'project-one', self.value.id)['proposals'], [])
        result = self.publish(preview, auth)
        self.assertEqual(result['status'], 'published_proposals')
        # Initial empty polling must not hide a newly confirmed PR receipt.
        self.assertFalse(self.publication.ledger.poll_due('tenant-one', 'project-one', self.value.id))
        proposals = self.publication.poll('tenant-one', 'project-one', self.value.id)['proposals']
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]['url'], 'https://github.com/owner/project/pull/1')
        self.assertIsNone(proposals[0]['merged'])
        self.assertEqual(self.remote.refs['main'], 'a' * 40)
        self.assertEqual(len(self.remote.pulls), 1);self.assertTrue(self.remote.pulls[0]['draft'])
        count = len(self.remote.writes)
        self.assertEqual(self.publish(preview, auth)['status'], 'published_proposals')
        self.assertEqual(len(self.remote.writes), count)
        self.assertEqual(sum(path == '/git/refs' for path, _ in self.remote.writes), 2)
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
        self.assertEqual(sum(path == '/git/refs' for path, _ in self.remote.writes), 2)

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


@unittest.skipUnless(os.getenv('ATMEM_MAINTENANCE_TEST_CONFIG'), 'Explicit qualified offline worker required')
class AuthenticatedReleaseChecks(unittest.TestCase):
    setUp = PublicationProtocolTests.setUp
    def test_fake_authenticated_tag_with_real_consumer_checks_keeps_proof_private(self):
        from server.maintenance.workers import MaintenanceWorker
        from server.maintenance.patches import apply_candidate
        from server.maintenance.models import Candidate
        from server.maintenance.planner import content_digest
        self.service.worker = MaintenanceWorker.from_file(Path(os.environ['ATMEM_MAINTENANCE_TEST_CONFIG']))
        self.assertEqual(self.service.worker.identity, self.result['workerIdentity'])
        released = apply_candidate(self.result['moduleBefore'], Candidate.model_validate(self.result['moduleCandidate']))
        entries = []
        for path, text in released.items():
            sha = git_blob_sha(text.encode());self.remote.blobs[sha] = text.encode()
            entries.append({'path': path, 'type': 'blob', 'mode': '100644', 'sha': sha, 'size': len(text.encode())})
        tree = tree_sha(entries);self.remote.trees[tree] = entries
        self.remote.commits['b' * 40] = {'sha': 'b' * 40, 'tree': {'sha': tree}, 'parents': [{'sha': 'a' * 40}], 'message': 'Operator release'}
        self.remote.tags['v2.0.0'] = 'b' * 40
        current = self.service.get('tenant-one', self.value.id)
        self.publication.observe_release('tenant-one', 'project-one', current.id, expected_revision=current.revision,
            graph_digest=current.graph['digest'], key='request-release', compute_confirmed=True,
            connection=self.connection.id, repository='owner/project', tag='v2.0.0')
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            checked = self.service.get('tenant-one', current.id)
            if checked.status != 'checking':break
            time.sleep(.1)
        self.assertEqual(checked.status, 'local_release_checked', checked.error)
        self.assertEqual(checked.result['release']['observation'], 'github_authenticated_tag')
        self.assertIn('?ref=' + 'b' * 40, checked.result['release']['source'])
        proof = self.publication._release_current('tenant-one', 'project-one', checked)
        self.assertEqual(proof['moduleArtifactDigest'], content_digest(released))
        self.assertTrue(all(r['status'] == 'passed' and r['cleanupConfirmed'] for r in checked.result['releaseChecks']))
        exported = self.service.export('tenant-one', checked.id)
        imported = self.service.import_record('tenant-one', 'project-one', 'actor-one', exported)
        with self.assertRaises(PermissionError):
            self.publication._release_current('tenant-one', 'project-one', imported)
        self.remote.tags['v2.0.0'] = 'c' * 40
        with self.assertRaises(Conflict):
            self.publication._release_current('tenant-one', 'project-one', checked)

class MultiGitHub:
    def __init__(self, sources):
        self.repositories = {}
        for index, (name, files) in enumerate(sources.items(), 101):
            remote = FakeGitHub(files)
            remote.metadata.update(id=index, full_name=name)
            self.repositories[name] = remote
    def request(self, token, method, path, body=None, headers=None):
        if path == '/user':
            return {'data': {'id': 7, 'login': 'customer'}, 'headers': {}, 'status': 200}
        if path == '/graphql':
            repository = body['variables']['input']['branch']['repositoryNameWithOwner']
            return self.repositories[repository].request(token, method, path, body, headers)
        parts = path.split('/', 4)
        repository = parts[2] + '/' + parts[3]
        if repository not in self.repositories:raise GitHubError(404)
        suffix = '/' + parts[4] if len(parts) == 5 else ''
        return self.repositories[repository].request(token, method, '/repos/owner/project' + suffix, body, headers)


@unittest.skipUnless(os.getenv('ATMEM_MAINTENANCE_TEST_CONFIG'), 'Explicit qualified offline worker required')
class RealCheckedConsumerWaveTests(unittest.TestCase):
    def test_separate_actual_tag_wave_confirmation_with_real_checks_and_fake_github(self):
        from server.maintenance.workers import MaintenanceWorker
        with tempfile.TemporaryDirectory() as folder:
            db = Store(Path(folder) / 'maintenance.sqlite')
            evidence = Path(__file__).resolve().parents[2] / 'specs/032-infrastructure-upgrades/evidence/r2.json'
            recorded = json.loads(evidence.read_text())['primary']
            worker = MaintenanceWorker.from_file(Path(os.environ['ATMEM_MAINTENANCE_TEST_CONFIG']))
            service = CampaignService(db, worker)
            self.addCleanup(service.close)
            sources, roots, bindings = frozen_campaign()
            campaign = service.create('tenant-one', 'project-one', 'actor-one', sources, roots, bindings)
            recorded['graphDigest'] = campaign.graph['digest'];recorded['plannerDigest'] = planner_digest()
            recorded['digest'] = digest({k: v for k, v in recorded.items() if k != 'digest'})
            campaign.status = 'module_release_pending';campaign.result = recorded
            campaign = service.store.put(campaign, 0)
            remote = MultiGitHub({'owner/shared': recorded['moduleBefore'],
                                 'owner/consumer-a': recorded['consumers']['root-consumer-a']['before'],
                                 'owner/consumer-b': recorded['consumers']['root-consumer-b']['before']})
            broker = GitHubBroker(db, FakeKeychain(), remote)
            connection = broker.register('tenant-one', ['project-one'], 'owner', list(remote.repositories),
                'github_pat_' + 'x' * 30, int(time.time()) + 3600)
            publication = Publication(db, service, broker)
            module = publication.preview('tenant-one', 'project-one', campaign.id,
                [{'root': 'root-shared', 'repository': 'owner/shared', 'connection': connection.id}])
            module_auth = publication.authorize('tenant-one', 'project-one', module['id'], module['digest'], True)
            self.assertEqual(publication.publish('tenant-one', 'project-one', module['id'], module_auth['id'], module['digest'])['status'], 'published_proposals')
            shared = remote.repositories['owner/shared']
            # Explicit fake owner action: product code has no merge or tag capability.
            released_commit = module['targets'][0]['proposalCommit']
            shared.refs['main'] = released_commit;shared.tags['v2.0.0'] = released_commit
            shared.pulls[0].update(merged=True, state='closed')
            current = service.get('tenant-one', campaign.id)
            publication.observe_release('tenant-one', 'project-one', current.id, expected_revision=current.revision,
                graph_digest=current.graph['digest'], key='request-actual-release', compute_confirmed=True,
                connection=connection.id, repository='owner/shared', tag='v2.0.0')
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                checked = service.get('tenant-one', campaign.id)
                if checked.status != 'checking':break
                time.sleep(.1)
            self.assertEqual(checked.status, 'local_release_checked', checked.error)
            targets = [{'root': 'root-' + name, 'repository': 'owner/' + name, 'connection': connection.id}
                       for name in ['consumer-a', 'consumer-b']]
            consumer = publication.preview('tenant-one', 'project-one', campaign.id, targets, wave='consumers')
            self.assertEqual(consumer['wave'], 'consumers')
            with self.assertRaises(PermissionError):
                publication.publish('tenant-one', 'project-one', consumer['id'], module_auth['id'], consumer['digest'])
            self.assertTrue(all(not remote.repositories['owner/' + name].writes for name in ['consumer-a', 'consumer-b']))
            fresh = publication.authorize('tenant-one', 'project-one', consumer['id'], consumer['digest'], True)
            state = publication.publish('tenant-one', 'project-one', consumer['id'], fresh['id'], consumer['digest'])
            self.assertEqual(state['status'], 'published_proposals')
            for name in ['consumer-a', 'consumer-b']:
                repository = remote.repositories['owner/' + name]
                self.assertEqual(repository.refs['main'], 'a' * 40)
                self.assertEqual(len(repository.pulls), 1)
                candidate = checked.result['consumers']['root-' + name]['releasedCandidate']
                self.assertTrue(any('?ref=' + released_commit in c['after'] for c in candidate['changes']))
                self.assertEqual(sum(p == '/git/refs' for p, _ in repository.writes), 1)
            self.assertEqual(len(shared.pulls), 1)
            self.assertEqual(sum(p == '/git/refs' for p, _ in shared.writes), 2)
            # Authenticated fake owner merge: only the remaining consumer is rechecked.
            first = remote.repositories['owner/consumer-a']
            first.pulls[0].update(merged=True, state='closed');first.refs['main'] = first.pulls[0]['head']['sha']
            observed = publication.poll('tenant-one', 'project-one', campaign.id, force=True)
            self.assertEqual(observed['observedMergedConsumers'], ['root-consumer-a'])
            remaining = service.get('tenant-one', campaign.id)
            self.assertEqual(remaining.phase, 'remaining_consumer_checks_required')
            self.assertFalse(remaining.result['releaseChecks'])
            self.assertNotIn('releasedCandidate', remaining.result['consumers']['root-consumer-b'])
            with self.assertRaises(Conflict):
                publication.publish('tenant-one', 'project-one', consumer['id'], fresh['id'], consumer['digest'])
            publication.observe_release('tenant-one', 'project-one', remaining.id, expected_revision=remaining.revision,
                graph_digest=remaining.graph['digest'], key='request-remaining-release', compute_confirmed=True,
                connection=connection.id, repository='owner/shared', tag='v2.0.0')
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                remaining = service.get('tenant-one', campaign.id)
                if remaining.status != 'checking':break
                time.sleep(.1)
            self.assertEqual(remaining.status, 'local_release_checked', remaining.error)
            self.assertEqual([r['consumer'] for r in remaining.result['releaseChecks']], ['root-consumer-b'])
            final_preview = publication.preview('tenant-one', 'project-one', campaign.id, [targets[1]], wave='consumers')
            final_auth = publication.authorize('tenant-one', 'project-one', final_preview['id'], final_preview['digest'], True)
            self.assertEqual(publication.publish('tenant-one', 'project-one', final_preview['id'], final_auth['id'], final_preview['digest'])['status'], 'published_proposals')
            self.assertEqual(len(remote.repositories['owner/consumer-b'].pulls), 1)
            last = remote.repositories['owner/consumer-b']
            last.pulls[0].update(merged=True, state='closed');last.refs['main'] = last.pulls[0]['head']['sha']
            complete = publication.poll('tenant-one', 'project-one', campaign.id, force=True)
            self.assertEqual(complete['status'], 'proposals_merged')


@unittest.skipUnless(os.getenv('ATMEM_MAINTENANCE_TEST_CONFIG'), 'Explicit qualified offline worker required')
class CheckedRefreshTests(unittest.TestCase):
    setUp = PublicationProtocolTests.setUp

    def refreshed(self):
        from server.maintenance.workers import MaintenanceWorker
        from server.maintenance.patches import apply_candidate, build_candidate, check_patch
        from server.maintenance.models import Candidate
        from server.maintenance.planner import content_digest
        self.service.worker = MaintenanceWorker.from_file(Path(os.environ['ATMEM_MAINTENANCE_TEST_CONFIG']))
        initial = self.publication.preview('tenant-one', 'project-one', self.value.id, self.targets)
        authorization = self.publication.authorize('tenant-one', 'project-one', initial['id'], initial['digest'], True)
        self.publication.publish('tenant-one', 'project-one', initial['id'], authorization['id'], initial['digest'])
        current = self.service.get('tenant-one', self.value.id)
        before = current.result['moduleBefore']
        after = apply_candidate(before, Candidate.model_validate(current.result['moduleCandidate']))
        after['main.tf'] += '\n'
        patch = build_candidate(before, after)
        self.assertFalse(check_patch(before, patch, approved_lock=after['.terraform.lock.hcl']))
        checked = self.service.worker.check(after, kind='candidate')
        self.assertEqual(checked['status'], 'passed');self.assertTrue(checked['cleanupConfirmed'])
        self.assertEqual(checked['report']['lock'], after['.terraform.lock.hcl'])
        receipt = copy.deepcopy(current.result['moduleReceipts'][-1])
        receipt['binding']['patchDigest'] = patch.digest
        receipt.update(artifactDigest=checked['artifactSha256'], output=checked['output'], durationSeconds=checked['durationSeconds'])
        current.result['moduleReceipts'].append(receipt)
        current.result['moduleCandidate'] = patch.model_dump()
        current.result['moduleArtifactDigest'] = content_digest(after)
        current.result['digest'] = digest({k: v for k, v in current.result.items() if k != 'digest'})
        self.service.store.put(current, current.revision)
        preview = self.publication.preview('tenant-one', 'project-one', current.id, self.targets)
        auth = self.publication.authorize('tenant-one', 'project-one', preview['id'], preview['digest'], True)
        self.assertEqual([a['kind'] for a in preview['actions']], ['append', 'pull'])
        return initial, preview, auth

    def test_checked_refresh_uses_expected_head_and_recovers_lost_response_without_force(self):
        initial, preview, auth = self.refreshed()
        branch = preview['targets'][0]['branch'];old = self.remote.refs[branch]
        self.remote.timeout_after = '/graphql'
        state = self.publication.publish('tenant-one', 'project-one', preview['id'], auth['id'], preview['digest'])
        self.assertEqual(state['status'], 'reconciliation_required')
        self.assertNotEqual(self.remote.refs[branch], old)
        self.assertEqual(self.publication.publish('tenant-one', 'project-one', preview['id'], auth['id'], preview['digest'])['status'], 'published_proposals')
        self.assertEqual(sum(path == '/graphql' for path, _ in self.remote.writes), 1)
        self.assertEqual(len(self.remote.pulls), 1)
        self.assertEqual(self.remote.refs['main'], 'a' * 40)
        appended = next(body for path, body in self.remote.writes if path == '/graphql')['variables']['input']
        self.assertEqual(appended['expectedHeadOid'], old)
        self.assertNotIn('force', str(appended))
        claim = self.publication.ledger.owned('tenant-one', 'project-one', self.value.graph['digest'], 100, branch)
        self.assertEqual(claim['head'], self.remote.refs[branch])
        with self.assertRaises(Conflict):
            self.publication.ledger.claim('tenant-one', 'project-one', self.value.graph['digest'], 100, branch,
                                           claim['nonce'], old, expected_head=old)

    def test_human_commit_racing_conditional_append_is_preserved(self):
        _, preview, auth = self.refreshed()
        branch = preview['targets'][0]['branch'];self.remote.append_race = True
        with self.assertRaises(GitHubError):
            self.publication.publish('tenant-one', 'project-one', preview['id'], auth['id'], preview['digest'])
        self.assertEqual(self.remote.refs[branch], 'c' * 40)
        with self.assertRaises(Conflict):
            self.publication.publish('tenant-one', 'project-one', preview['id'], auth['id'], preview['digest'])
        self.assertEqual(sum(path == '/graphql' for path, _ in self.remote.writes), 1)
        self.assertEqual(self.remote.refs['main'], 'a' * 40)

@unittest.skipUnless(os.getenv('ATMEM_MAINTENANCE_TEST_CONFIG'), 'Explicit qualified offline worker required')
class AutomationDisclosureChecks(unittest.TestCase):
    def test_real_checked_campaign_preserves_ci_and_discloses_it_before_fake_publication(self):
        from server.maintenance.inventory import snapshot
        from server.maintenance.planner import prepare_campaign
        from server.maintenance.workers import MaintenanceWorker
        worker = MaintenanceWorker.from_file(Path(os.environ['ATMEM_MAINTENANCE_TEST_CONFIG']))
        sources, roots, bindings = frozen_campaign()
        workflow_path = '.github/workflows/review.yml'
        workflow = 'name: Migration review\non: [push, pull_request]\njobs: {}\n'
        original = sources[0]
        selected = snapshot({**{f.path: f.text for f in original.files}, workflow_path: workflow},
                            original.repositoryId, commit=original.commit).model_copy(update={'id': original.id})
        sources[0] = selected
        bindings = [b.model_copy(update={'targetTreeDigest': selected.treeDigest}) for b in bindings]
        graph = __import__('server.maintenance.graph', fromlist=['discover']).discover(sources, roots, bindings)
        result = prepare_campaign(sources, roots, graph, 'root-shared', worker)
        self.assertEqual(result['status'], 'module_release_pending', result.get('findings'))
        self.assertEqual(result['moduleBefore'][workflow_path], workflow)
        self.assertNotIn(workflow_path, [c['path'] for c in result['moduleCandidate']['changes']])
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'maintenance.sqlite')
            service = CampaignService(store, worker);self.addCleanup(service.close)
            value = service.create('tenant-one', 'project-one', 'actor-one', sources, roots, bindings)
            value.status = result['status'];value.result = result
            value = service.store.put(value, value.revision)
            remote = FakeGitHub(result['moduleBefore'])
            broker = GitHubBroker(store, FakeKeychain(), remote)
            connection = broker.register('tenant-one', ['project-one'], 'owner', ['owner/project'],
                                         'github_pat_' + 'x' * 30, int(time.time()) + 3600)
            publication = Publication(store, service, broker)
            preview = publication.preview('tenant-one', 'project-one', value.id,
                [{'root': 'root-shared', 'repository': 'owner/project', 'connection': connection.id}])
            self.assertFalse(remote.writes)
            self.assertIn(workflow_path, preview['automation'][0]['detectedAutomation'])
            grant = publication.authorize('tenant-one', 'project-one', preview['id'], preview['digest'], True)
            self.assertEqual(publication.publish('tenant-one', 'project-one', preview['id'], grant['id'], preview['digest'])['status'],
                             'published_proposals')
            proposal = preview['targets'][0]
            head = remote.refs[proposal['branch']]
            retained = next(item for item in remote.trees[remote.commits[head]['tree']['sha']] if item['path'] == workflow_path)
            self.assertEqual(remote.blobs[retained['sha']].decode(), workflow)
