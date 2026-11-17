"""Exact-wave publication coordinator; remote acceptance remains a separate gate.

Only fixed Git object/ref/PR operations exist. No merge, tag creation, force push,
protected/default branch update, arbitrary commands or workflow file mutation.
"""
import base64
import hashlib
from pathlib import Path
import json
import time
import urllib.parse
from uuid import uuid4

from .git_objects import tree_sha, commit_object
from .github_adapter import GitHubError, UncertainWrite, git_blob_sha
from .inventory import AUTOMATION, inventory
from .models import Candidate
from .patches import apply_candidate, check_patch
from .planner import planner_digest, content_digest
from .publication_store import PublicationStore
from .store import Conflict, digest
from .verification import oracle_digest, policy_digest
from .recipes import recipe_digest


_POLICY_FILES = [Path(__file__), *[Path(__file__).with_name(name) for name in
                 ('publication_store.py', 'github_adapter.py', 'credential_store.py', 'git_objects.py')]]
_LOADED_POLICY = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in _POLICY_FILES}


def publication_policy_digest():
    current = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in _POLICY_FILES}
    if current != _LOADED_POLICY:
        raise Conflict('Publication code changed; restart the helper and review fresh evidence')
    return digest({'coordinator': current, 'campaignPolicy': planner_digest(), 'contract': 'publication-v1'})


class Publication:
    def __init__(self, store, campaigns, broker):
        self.ledger, self.campaigns, self.broker = PublicationStore(store), campaigns, broker

    def _read(self, tenant, project, target, suffix):
        return self.broker.request(tenant, project, target['connection'], target['repository'], 'GET', suffix)['data']

    def _optional(self, tenant, project, target, suffix):
        try:
            return self._read(tenant, project, target, suffix)
        except GitHubError as error:
            if error.status == 404:
                return None
            raise

    def _current(self, tenant, project, target):
        metadata = self.broker.repository_metadata(tenant, project, target['connection'], target['repository'])
        if metadata['id'] != target['repositoryId'] or metadata.get('default_branch') != target['base']:
            raise Conflict('Repository identity or default branch changed')
        current = self._read(tenant, project, target, '/git/ref/heads/' + urllib.parse.quote(target['base'], safe=''))
        if current.get('object', {}).get('sha') != target['baseCommit']:
            raise Conflict('Source base changed; materialize and check fresh source')
        if target['branch'] == target['base'] or not target['branch'].startswith('atmem-upgrades/'):
            raise PermissionError('Default and non-proposal refs are forbidden')
        # GitHub applies its own rules as well. Unknown policy never means writable.
        rules = self._read(tenant, project, target, '/rules/branches/' + urllib.parse.quote(target['branch'], safe=''))
        if not isinstance(rules, list) or rules:
            raise PermissionError('Proposal branch rules are protected or unresolved')
        existing = self._optional(tenant, project, target, '/branches/' + urllib.parse.quote(target['branch'], safe=''))
        if existing and existing.get('protected') is not False:
            raise PermissionError('Protected proposal branches cannot be changed')
        return metadata, existing

    def preview(self, tenant, project, campaign_id, targets, *, wave='module'):
        """Only persisted currently checked candidates may generate exact actions."""
        value = self.campaigns.get(tenant, campaign_id)
        if value.projectId != project or value.result is None or value.result.get('plannerDigest') != planner_digest() or value.result.get('graphDigest') != value.graph['digest']:
            raise Conflict('Prepare fresh campaign checks before publication')
        if wave != 'module':
            # A local operator release simulation is deliberately insufficient.
            raise Conflict('Authenticated released-module observation is required for a consumer wave')
        result = value.result
        if value.status != 'module_release_pending' or len(targets) != 1 or targets[0]['root'] != result.get('module'):
            raise Conflict('Select the checked shared-module wave only')
        patch = Candidate.model_validate(result['moduleCandidate'])
        before = result['moduleBefore']
        approved = next((c.after for c in patch.changes if c.path == '.terraform.lock.hcl'), before.get('.terraform.lock.hcl'))
        if check_patch(before, patch, approved_lock=approved):
            raise PermissionError('Independent module patch policy failed')
        checks = result.get('moduleReceipts', [])
        if (not checks or checks[-1]['status'] != 'passed' or not checks[-1].get('cleanupConfirmed')
            or checks[-1]['binding']['patchDigest'] != patch.digest
            or checks[-1]['binding']['sourceDigest'] != content_digest(before)
            or checks[-1]['binding']['toolDigest'] != result['workerIdentity']
            or checks[-1]['binding']['policyDigest'] != policy_digest()
            or checks[-1]['binding']['recipeDigest'] != recipe_digest()
            or checks[-1]['binding']['oracleDigest'] != oracle_digest()):
            raise Conflict('Exact module patch lacks a current independent receipt')
        ident, created = str(uuid4()), int(time.time())
        actions, selected, automation = [], [], []
        for selection in targets:
            action_start = len(actions)
            root = next((r for r in value.roots if r.id == selection['root']), None)
            if root is None:
                raise ValueError('Unknown campaign root')
            source = next(s for s in value.snapshots if s.id == root.snapshotId)
            metadata = self.broker.repository_metadata(tenant, project, selection['connection'], selection['repository'])
            base = metadata.get('default_branch')
            if not base or not source.commit:
                raise Conflict('Materialize the current immutable default-branch source first')
            fetched = self.broker.materialize(tenant, project, selection['connection'], selection['repository'], source.commit,
                                             [f.path for f in source.files])
            if fetched.treeDigest != source.treeDigest:
                raise Conflict('Selected repository bytes differ from the checked source')
            branch = 'atmem-upgrades/' + value.graph['digest'][:32] + '/' + root.id
            nonce = digest({'installation': self.ledger.installation, 'preview': ident, 'root': root.id})
            target = {**selection, 'repositoryId': metadata['id'], 'base': base, 'baseCommit': source.commit,
                      'branch': branch, 'nonce': nonce, 'graphDigest': value.graph['digest']}
            _, existing = self._current(tenant, project, target)
            if existing:
                # No reset, takeover or implicit rebase. Existing ownership is
                # inspectable, but refresh needs a separately checked delta.
                claim = self.ledger.owned(tenant, project, value.graph['digest'], metadata['id'], branch)
                if claim is None or existing.get('commit', {}).get('sha') != claim['head']:
                    raise Conflict('Proposal branch is unowned or contains unknown human commits')
                target['nonce'] = claim['nonce']
                target['existingHead'] = claim['head']
            commit = self._read(tenant, project, target, '/git/commits/' + source.commit)
            base_tree = commit['tree']['sha']
            tree = self._read(tenant, project, target, '/git/trees/' + base_tree + '?recursive=1')
            if tree.get('truncated') or tree.get('sha') != base_tree or tree_sha(tree['tree']) != base_tree:
                raise ValueError('Complete immutable base tree could not be verified')
            entries = {entry['path']: entry for entry in tree['tree']}
            prefix = '' if root.directory == '.' else root.directory + '/'
            edits, tree_changes = [], {}
            for change in patch.changes:
                path = prefix + change.path
                if AUTOMATION.search(path) or not path.endswith(('.tf', '.lock.hcl')):
                    raise PermissionError('Automation and unapproved file changes are forbidden')
                old = entries.get(path)
                if (change.operation == 'create') != (old is None):
                    raise Conflict('Patch no longer matches the current repository tree')
                if old and old['sha'] != git_blob_sha(before[change.path].encode()):
                    raise Conflict('Source Git blob differs from the checked baseline')
                mode = old['mode'] if old else '100644'
                sha = git_blob_sha(change.after.encode())
                tree_changes[path] = (mode, sha)
                body = {'encoding': 'base64', 'content': base64.b64encode(change.after.encode()).decode()}
                actions.append({'kind': 'blob', 'target': target, 'expected': sha, 'body': body})
                edits.append({'path': path, 'mode': mode, 'type': 'blob', 'sha': sha})
            expected_tree = tree_sha(tree['tree'], tree_changes)
            actions.append({'kind': 'tree', 'target': target, 'expected': expected_tree, 'body': {'base_tree': base_tree, 'tree': edits}})
            nonce = target['nonce']
            message = 'Prepare infrastructure upgrade\n\nAtMem-Operation: ' + nonce + '\nPatch: ' + patch.digest + '\n'
            expected_commit, body = commit_object(expected_tree, source.commit, message, created)
            target['proposalCommit'] = expected_commit
            # All actions share the final immutable target; body identity is bound by preview.
            actions.append({'kind': 'commit', 'target': target, 'expected': expected_commit, 'body': body})
            actions.append({'kind': 'ref', 'target': target, 'expected': expected_commit,
                            'body': {'ref': 'refs/heads/' + branch, 'sha': expected_commit}})
            if existing:
                owned_commit = self._read(tenant, project, target, '/git/commits/' + target['existingHead'])
                if owned_commit.get('tree', {}).get('sha') != expected_tree:
                    raise Conflict('Existing proposal needs an explicit checked refresh delta; automatic reset is forbidden')
                del actions[action_start:]
                target['proposalCommit'] = target['existingHead']
            known = [f.path for f in source.files if AUTOMATION.search(f.path)]
            disclosure = {'repository': selection['repository'], 'detectedAutomation': known,
                          'unknownAutomation': True, 'sideEffects': ['Creating proposal refs/PRs may run repository or external automation.']}
            automation.append(disclosure)
            marker = '<!-- atmem-operation:' + nonce + ' -->'
            text = ('Prepares the checked AWS Batch provider migration from 5.100.0 to 6.0.0.\n\n'
                    'Evidence: offline configuration/schema checks only; baseline passed, version-only schema control failed as expected, candidate passed. '
                    'No account plan, state operation or deployment was performed. Review destination-specific state and rollout requirements before merging.\n\n'
                    'Module wave: publish and independently observe an actual matching module release before consumer proposals.\n\n'
                    'Detected repository automation: ' + (', '.join(known) if known else 'none in selected source') + '. External/unknown automation may still run.\n\n' + marker)
            actions.append({'kind': 'pull', 'target': target, 'expected': nonce,
                            'body': {'title': 'Prepare AWS Batch provider 6.0 migration', 'head': branch, 'base': base, 'body': text, 'draft': True}})
            selected.append({**target, 'patchDigest': patch.digest, 'files': [e['path'] for e in edits], 'changedFiles': len(edits),
                             'expectedTree': expected_tree, 'moduleArtifactDigest': content_digest(apply_candidate(before, patch))})
        payload = {'id': ident, 'tenant': tenant, 'project': project, 'campaign': campaign_id, 'graphDigest': value.graph['digest'],
                   'wave': wave, 'createdAt': created, 'plannerDigest': planner_digest(), 'publicationPolicyDigest': publication_policy_digest(), 'targets': selected, 'actions': actions,
                   'automation': automation, 'permissions': 'No merge, release/tag, protected/default branch, workflow change or deployment.',
                   'sideEffects': 'Creates content-addressed Git objects, a proposal ref and a draft PR; repository automation may run.'}
        return self.ledger.save_preview(tenant, project, campaign_id, payload)

    def authorize(self, tenant, project, preview_id, expected_digest, automation_accepted):
        # A fresh preview must still reference the same source/policy at confirmation.
        preview = self.ledger.preview(tenant, project, preview_id)
        self._campaign_current(tenant, project, preview)
        return self.ledger.authorize(tenant, project, preview_id, expected_digest, automation_accepted=automation_accepted)

    def _campaign_current(self, tenant, project, preview):
        campaign = self.campaigns.get(tenant, preview['campaign'])
        if (campaign.projectId != project or campaign.graph['digest'] != preview['graphDigest']
            or preview['plannerDigest'] != planner_digest() or preview.get('publicationPolicyDigest') != publication_policy_digest() or campaign.result is None
            or campaign.result.get('plannerDigest') != planner_digest() or campaign.status != 'module_release_pending'):
            raise Conflict('Campaign source, checks or policy changed; review a fresh preview')
        return campaign

    def _reconcile(self, tenant, project, action):
        target, kind, expected = action['target'], action['kind'], action['expected']
        if kind in {'blob', 'tree', 'commit'}:
            plural = {'blob': 'blobs', 'tree': 'trees', 'commit': 'commits'}[kind]
            item = self._optional(tenant, project, target, '/git/' + plural + '/' + expected)
            if item is None:
                return None
            if item.get('sha') != expected:
                raise Conflict('Remote Git object differs from the exact proposal')
            return {'sha': expected}
        if kind == 'ref':
            item = self._optional(tenant, project, target, '/git/ref/heads/' + urllib.parse.quote(target['branch'], safe=''))
            if item is None:
                return None
            if item.get('object', {}).get('sha') != expected:
                raise Conflict('Proposal ref contains an unknown or competing commit')
            return {'sha': expected, 'ref': 'refs/heads/' + target['branch']}
        if kind == 'pull':
            query = urllib.parse.urlencode({'state': 'all', 'head': target['repository'].split('/')[0] + ':' + target['branch'], 'base': target['base'], 'per_page': 100})
            items = self._read(tenant, project, target, '/pulls?' + query)
            if not isinstance(items, list) or len(items) >= 100:
                raise Conflict('PR reconciliation is incomplete')
            matching = [p for p in items if '<!-- atmem-operation:' + expected + ' -->' in p.get('body', '')]
            if not matching:
                if items:
                    raise Conflict('An unowned or human-created proposal already uses this branch')
                return None
            if len(matching) != 1 or matching[0].get('head', {}).get('sha') != target['proposalCommit']:
                raise Conflict('Existing proposal contains unknown commits or duplicate identities')
            item = matching[0]
            return {'number': item['number'], 'url': 'https://github.com/' + target['repository'] + '/pull/' + str(item['number']),
                    'head': target['proposalCommit'], 'state': item['state']}
        raise ValueError('Unknown publication action')

    def publish(self, tenant, project, preview_id, authorization, expected_digest):
        preview = self.ledger.preview(tenant, project, preview_id)
        self._campaign_current(tenant, project, preview)
        if preview['digest'] != expected_digest:
            raise Conflict('Exact preview changed')
        lease = self.ledger.acquire(tenant, project, preview_id, authorization, expected_digest)
        try:
            for index, action in enumerate(preview['actions']):
                operation = self.ledger.operation(tenant, project, preview_id, index)
                if operation['state'] == 'confirmed':
                    continue
                observed = self._reconcile(tenant, project, action)
                if observed is not None:
                    self.ledger.result(preview_id, operation, 'confirmed', observed)
                    self._record_claim(tenant, project, preview, action, observed)
                    continue
                if operation['state'] in {'in_flight', 'uncertain'} and action['kind'] == 'pull':
                    return {**self.ledger.status(tenant, project, preview_id), 'status': 'reconciliation_required'}
                target = action['target']
                def guard(metadata):
                    self._campaign_current(tenant, project, preview)
                    _, branch = self._current(tenant, project, target)
                    if action['kind'] == 'pull':
                        if branch is None or branch.get('commit', {}).get('sha') != target['proposalCommit']:
                            raise Conflict('Proposal head changed; human edits are never overwritten')
                    elif branch is not None:
                        raise Conflict('Proposal branch appeared before its exact creation; reconcile it first')
                    self.ledger.before_write(tenant, project, preview_id, authorization, expected_digest, lease, operation)
                try:
                    self.broker.publication_write(tenant, project, target['connection'], target['repository'], action['kind'], action['body'], guard)
                    observed = self._reconcile(tenant, project, action)
                    if observed is None:
                        self.ledger.result(preview_id, operation, 'uncertain')
                        return {**self.ledger.status(tenant, project, preview_id), 'status': 'reconciliation_required'}
                    self.ledger.result(preview_id, operation, 'confirmed', observed)
                    self._record_claim(tenant, project, preview, action, observed)
                except UncertainWrite:
                    self.ledger.result(preview_id, operation, 'uncertain')
                    return {**self.ledger.status(tenant, project, preview_id), 'status': 'reconciliation_required'}
                except (GitHubError, PermissionError, Conflict):
                    # Read reconciliation remains available; no blind mutation replay.
                    saved = self.ledger.operation(tenant, project, preview_id, index)
                    self.ledger.result(preview_id, operation, 'uncertain' if saved['state'] == 'in_flight' else 'blocked')
                    raise
            return {**self.ledger.status(tenant, project, preview_id), 'status': 'published_proposals'}
        finally:
            self.ledger.release(preview_id, lease)

    def reconcile(self, tenant, project, preview_id, credential_overrides=None):
        """Read-only reconciliation may use a newly approved matching connection.

        It records observed outcomes and never renews an authorization or issues a
        mutation. This remains available after cancellation or token revocation.
        """
        preview = self.ledger.preview(tenant, project, preview_id)
        overrides = credential_overrides or {}
        if set(overrides) - {t['repository'] for t in preview['targets']}:
            raise PermissionError('Replacement connection is outside this exact wave')
        for index, action in enumerate(preview['actions']):
            operation = self.ledger.operation(tenant, project, preview_id, index)
            if operation['state'] == 'confirmed':
                continue
            reading = {**action, 'target': dict(action['target'])}
            if reading['target']['repository'] in overrides:
                reading['target']['connection'] = overrides[reading['target']['repository']]
                metadata = self.broker.repository_metadata(tenant, project, reading['target']['connection'], reading['target']['repository'])
                if metadata['id'] != action['target']['repositoryId']:
                    raise PermissionError('Replacement connection does not match the original repository')
            observed = self._reconcile(tenant, project, reading)
            if observed is not None:
                self.ledger.result(preview_id, operation, 'confirmed', observed)
                self._record_claim(tenant, project, preview, action, observed)
        return self.ledger.status(tenant, project, preview_id)

    def _record_claim(self, tenant, project, preview, action, observed):
        if action['kind'] == 'ref':
            target = action['target']
            self.ledger.claim(tenant, project, preview['graphDigest'], target['repositoryId'], target['branch'], target['nonce'], observed['sha'])
