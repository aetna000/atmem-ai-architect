"""Exact-wave publication coordinator; remote acceptance remains a separate gate.

Only fixed Git object/ref/PR operations exist. No merge, tag creation, force push,
protected/default branch update, arbitrary commands or workflow file mutation.
"""
import base64
import copy
import hashlib
from pathlib import Path
import json
import time
import urllib.parse
from uuid import uuid4

from .git_objects import tree_sha, commit_object
from .github_adapter import GitHubError, UncertainWrite, git_blob_sha
from .inventory import AUTOMATION, inventory, parse_files, secret_findings
from .models import Candidate
from .patches import apply_candidate, check_patch, _expected_semantics
from .planner import planner_digest, content_digest, overlay, root_files
from .publication_store import PublicationStore
from .store import Conflict, digest
from .verification import oracle_digest, policy_digest
from .recipes import recipe_digest


_POLICY_FILES = [Path(__file__), *[Path(__file__).with_name(name) for name in
                 ('publication_store.py', 'github_adapter.py', 'credential_store.py', 'git_objects.py')]]
_POLICY_FILES.append(Path(__file__).parents[1] / 'maintenance_publication_routes.py')
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

    def _anchor(self, tenant, project, target, graph_digest, *, required=False):
        anchor = target.get('anchor') or target
        branch = 'atmem-upgrades/' + graph_digest[:32] + '/campaign-owner'
        metadata = self.broker.repository_metadata(tenant, project, anchor['connection'], anchor['repository'])
        if metadata['id'] != anchor['repositoryId'] or metadata.get('default_branch') == branch:
            raise PermissionError('Campaign ownership ref cannot be the default branch')
        item = self._optional(tenant, project, anchor, '/branches/' + urllib.parse.quote(branch, safe=''))
        owned = self.ledger.owned(tenant, project, graph_digest, metadata['id'], branch)
        if item is None:
            if required or owned is not None:
                raise Conflict('Campaign ownership ref is missing; original installation must reconcile it')
            return False
        if (owned is None or owned['nonce'] != digest({'installation': self.ledger.installation, 'graph': graph_digest})
            or item.get('commit', {}).get('sha') != owned['head']):
            raise Conflict('Campaign ownership ref is unowned or changed by another installation')
        if item.get('protected') is not False:
            raise PermissionError('Campaign ownership ref became protected')
        return True

    def preview(self, tenant, project, campaign_id, targets, *, wave='module'):
        """Only persisted currently checked candidates may generate exact actions."""
        if not isinstance(targets, list) or not 1 <= len(targets) <= 30 or any(not isinstance(t, dict) or set(t) != {'root', 'repository', 'connection'} for t in targets):
            raise ValueError('Select exact root, repository and connection mappings')
        value = self.campaigns.get(tenant, campaign_id)
        if value.projectId != project or value.result is None or value.result.get('plannerDigest') != planner_digest() or value.result.get('graphDigest') != value.graph['digest']:
            raise Conflict('Prepare fresh campaign checks before publication')
        result = value.result
        if result.get('digest') != digest({k: v for k, v in result.items() if k != 'digest'}):
            raise Conflict('Retained campaign result integrity mismatch')
        release_proof = None
        if wave == 'module':
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
            choices = {result['module']: (patch, before)}
        elif wave == 'consumers':
            if value.status != 'local_release_checked' or result.get('simulatedMergedConsumers'):
                raise Conflict('Authenticated released-module observation is required for a consumer wave')
            release_proof = self._release_current(tenant, project, value)
            expected_roots = set(result['consumers']) - set(result.get('observedMergedConsumers', []))
            if len(targets) != len(expected_roots) or {t['root'] for t in targets} != expected_roots:
                raise Conflict('Review the complete current remaining consumer wave')
            choices = {name: self._consumer_current(value, name, release_proof) for name in expected_roots}
        else:
            raise ValueError('Select a module or consumer publication wave')
        ident, created = str(uuid4()), int(time.time())
        actions, selected, automation = [], [], []
        for selection in targets:
            action_start = len(actions)
            patch, before = choices[selection['root']]
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
            if release_proof is not None:
                target['anchor'] = {'repository': release_proof['repository'], 'repositoryId': release_proof['repositoryId'],
                                    'connection': release_proof['connection']}
            anchor_exists = self._anchor(tenant, project, target, value.graph['digest'], required=wave=='consumers')
            _, existing = self._current(tenant, project, target)
            if existing:
                # No reset, takeover or implicit rebase. Existing ownership is
                # inspectable, but refresh needs a separately checked delta.
                claim = self.ledger.owned(tenant, project, value.graph['digest'], metadata['id'], branch)
                if claim is None or existing.get('commit', {}).get('sha') != claim['head']:
                    raise Conflict('Proposal branch is unowned or contains unknown human commits')
                target['appendNonce'] = target['nonce']
                target['nonce'] = claim['nonce']
                target['existingManifest'] = claim.get('manifest')
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
            target.update(expectedTree=expected_tree, files=[e['path'] for e in edits], patchDigest=patch.digest)
            actions.append({'kind': 'tree', 'target': target, 'expected': expected_tree, 'body': {'base_tree': base_tree, 'tree': edits}})
            nonce = target['nonce']
            message = 'Prepare infrastructure upgrade\n\nAtMem-Operation: ' + nonce + '\nPatch: ' + patch.digest + '\n'
            expected_commit, body = commit_object(expected_tree, source.commit, message, created)
            target['proposalCommit'] = expected_commit
            # All actions share the final immutable target; body identity is bound by preview.
            actions.append({'kind': 'commit', 'target': target, 'expected': expected_commit, 'body': body})
            if not anchor_exists:
                anchor_branch = 'atmem-upgrades/' + value.graph['digest'][:32] + '/campaign-owner'
                anchor_target = {**target, 'branch': anchor_branch, 'role': 'campaign_anchor',
                                 'nonce': digest({'installation': self.ledger.installation, 'graph': value.graph['digest']})}
                actions.append({'kind': 'ref', 'target': anchor_target, 'expected': expected_commit,
                                'body': {'ref': 'refs/heads/' + anchor_branch, 'sha': expected_commit}})
            actions.append({'kind': 'ref', 'target': target, 'expected': expected_commit,
                            'body': {'ref': 'refs/heads/' + branch, 'sha': expected_commit}})
            if existing:
                owned_commit = self._read(tenant, project, target, '/git/commits/' + target['existingHead'])
                del actions[action_start:]
                target['proposalCommit'] = target['existingHead']
                if owned_commit.get('tree', {}).get('sha') != expected_tree:
                    manifest = target.get('existingManifest')
                    if manifest is None or manifest.get('tree') != owned_commit.get('tree', {}).get('sha') or manifest.get('baseCommit') != source.commit:
                        raise Conflict('Owned proposal manifest differs from the current exact head')
                    old_tree = self._read(tenant, project, target, '/git/trees/' + manifest['tree'] + '?recursive=1')
                    if old_tree.get('truncated') or tree_sha(old_tree['tree']) != manifest['tree']:
                        raise Conflict('Owned proposal tree is incomplete')
                    old_entries = {item['path']: item for item in old_tree['tree'] if item['type'] != 'tree'}
                    additions, deletions, delta = [], [], {}
                    after = apply_candidate(before, patch)
                    for path in sorted(set(manifest['paths']) | set(tree_changes)):
                        desired = tree_changes.get(path)
                        if desired is None and path in entries:
                            desired = (entries[path]['mode'], entries[path]['sha'])
                        old = old_entries.get(path)
                        if desired == ((old['mode'], old['sha']) if old else None):
                            continue
                        if desired is None:
                            if path not in manifest['paths'] or path in entries:
                                raise PermissionError('Only obsolete proposal-created files can be removed')
                            deletions.append({'path': path});delta[path] = None
                        else:
                            if desired[0] != '100644' or old and old['mode'] != '100644' or not path.startswith(prefix):
                                raise PermissionError('This conditional refresh supports regular owned text files only')
                            relative = path[len(prefix):]
                            text = after.get(relative, before.get(relative))
                            if text is None or git_blob_sha(text.encode()) != desired[1]:
                                raise Conflict('Refresh bytes differ from the independently checked target')
                            additions.append({'path': path, 'contents': base64.b64encode(text.encode()).decode()})
                            delta[path] = desired
                    if not additions and not deletions or tree_sha(old_tree['tree'], delta) != expected_tree:
                        raise Conflict('Refresh delta differs from the complete checked target tree')
                    target['appendParent'], target['proposalCommit'] = target['existingHead'], None
                    body = {'branch': {'repositoryNameWithOwner': selection['repository'], 'refName': branch},
                            'expectedHeadOid': target['appendParent'], 'fileChanges': {'additions': additions, 'deletions': deletions},
                            'message': {'headline': 'Refresh checked infrastructure upgrade',
                                        'body': 'AtMem-Operation: ' + target['appendNonce'] + '\nPatch: ' + patch.digest}}
                    actions.append({'kind': 'append', 'target': target, 'expected': expected_tree, 'body': body})
            known = [f.path for f in source.files if AUTOMATION.search(f.path)]
            disclosure = {'repository': selection['repository'], 'detectedAutomation': known,
                          'unknownAutomation': True, 'sideEffects': ['Creating proposal refs/PRs may run repository or external automation.']}
            automation.append(disclosure)
            marker = '<!-- atmem-operation:' + nonce + ' -->'
            text = ('Prepares the checked AWS Batch provider migration from 5.100.0 to 6.0.0.\n\n'
                    'Evidence: offline configuration/schema checks only; baseline passed, version-only schema control failed as expected, candidate passed. '
                    'No account plan, state operation or deployment was performed. Review destination-specific state and rollout requirements before merging.\n\n' +
                    ('Module wave: publish and independently observe an actual matching module release before consumer proposals.\n\n' if wave=='module' else
                     'Consumer wave: source is pinned to the authenticated module release commit in the patch; current check details remain in AtMem.\n\n') +
                    'Detected repository automation: ' + (', '.join(known) if known else 'none in selected source') + '. External/unknown automation may still run.\n\n' + marker)
            actions.append({'kind': 'pull', 'target': target, 'expected': nonce,
                            'body': {'title': 'Prepare AWS Batch provider 6.0 migration', 'head': branch, 'base': base, 'body': text, 'draft': True}})
            selected.append({**target, 'patchDigest': patch.digest, 'files': [e['path'] for e in edits], 'changedFiles': len(edits),
                             'expectedTree': expected_tree, 'candidateArtifactDigest': content_digest(apply_candidate(before, patch)),
                             'moduleArtifactDigest': result['moduleArtifactDigest']})
        payload = {'id': ident, 'tenant': tenant, 'project': project, 'campaign': campaign_id, 'graphDigest': value.graph['digest'],
                   'wave': wave, 'resultDigest': result['digest'], 'releaseObservationId': result.get('releaseObservationId'),
                   'createdAt': created, 'plannerDigest': planner_digest(), 'publicationPolicyDigest': publication_policy_digest(), 'targets': selected, 'actions': actions,
                   'automation': automation, 'permissions': 'No merge, release/tag, protected/default branch, workflow change or deployment.',
                   'sideEffects': 'Creates Git objects, campaign ownership/proposal refs and draft PRs; repository automation may run.'}
        return self.ledger.save_preview(tenant, project, campaign_id, payload)

    def _consumer_current(self, campaign, name, proof):
        result = campaign.result
        proposal = result['consumers'][name]
        if 'releasedCandidate' not in proposal:
            raise Conflict('Consumer lacks fresh authenticated-release checks')
        patch = Candidate.model_validate(proposal['releasedCandidate'])
        before = proposal['before']
        if proof['consumerPatchDigests'].get(name) != patch.digest:
            raise Conflict('Consumer patch differs from the private release observation')
        root = next(r for r in campaign.roots if r.id == name)
        source = next(s for s in campaign.snapshots if s.id == root.snapshotId)
        if root_files(source, root.directory) != before:
            raise Conflict('Consumer baseline differs from the graph source')
        after = apply_candidate(before, patch)
        if secret_findings(after):
            raise PermissionError('Sensitive consumer patch denied')
        parsed_before, parsed_after = parse_files(before), parse_files(after)
        if set(parsed_after) - set(parsed_before) - {'.terraform.lock.hcl'}:
            raise PermissionError('Unapproved consumer file creation')
        for path, document in parsed_before.items():
            if path.endswith('.lock.hcl'):
                continue
            expected = _expected_semantics(document['semantic'], control=True)
            for declaration in expected.get('module', []):
                for edge in proposal['edges']:
                    if edge['module'] in declaration:
                        declaration[edge['module']]['source'] = proof['source']
                        declaration[edge['module']].pop('version', None)
            if expected != parsed_after[path]['semantic']:
                raise PermissionError('Consumer changes exceed the independently reviewed semantic scope')
        if any(AUTOMATION.search(c.path) or not c.path.endswith(('.tf', '.lock.hcl')) for c in patch.changes):
            raise PermissionError('Unapproved consumer file changes')
        module_files = apply_candidate(result['moduleBefore'], Candidate.model_validate(result['moduleCandidate']))
        projected, artifact = overlay(after, module_files, proposal['edges'])
        receipts = [r for r in result.get('releaseChecks', []) if r['consumer'] == name]
        if (len(receipts) != 1 or receipts[0]['status'] != 'passed' or not receipts[0].get('cleanupConfirmed')
            or receipts[0]['consumerPatchDigest'] != patch.digest or receipts[0]['moduleArtifactDigest'] != artifact
            or receipts[0]['overlayDigest'] != content_digest(projected) or receipts[0]['graphDigest'] != campaign.graph['digest']
            or receipts[0]['workerIdentity'] != result['workerIdentity'] or receipts[0]['plannerDigest'] != planner_digest()):
            raise Conflict('Exact released-artifact consumer receipt is missing or stale')
        try:
            report = json.loads(receipts[0]['output'])
        except (ValueError, TypeError):
            raise Conflict('Consumer lock receipt is unavailable') from None
        if report.get('lock') != after.get('.terraform.lock.hcl'):
            raise Conflict('Consumer lock differs from independently checked bytes')
        return patch, before

    def _invalidate_remaining(self, tenant, project, campaign_id, merged):
        with self.campaigns.lock:
            current = self.campaigns.get(tenant, campaign_id)
            retained = current.result or next((r for r in reversed(current.history) if r.get('graphDigest') == current.graph['digest']), None)
            if retained is None or not set(merged) <= set(retained.get('consumers', {})):
                raise Conflict('Merged proposal does not match this retained campaign')
            if set(retained.get('observedMergedConsumers', [])) == set(merged):
                return current
            if current.status == 'checking':
                current = self.campaigns.cancel(tenant, campaign_id, current.revision)
            if len(current.history) >= 20:
                raise Conflict('Preserve campaign history before recording another transition')
            original = copy.deepcopy(retained)
            current.history = [*current.history, original]
            result = copy.deepcopy(original)
            remaining = set(result['consumers']) - set(merged)
            result['observedMergedConsumers'] = sorted(merged)
            result['releaseChecks'] = []
            result.pop('releaseObservationId', None)
            for name in remaining:
                result['consumers'][name].pop('releasedCandidate', None)
                for receipt in result.get('checks', []):
                    if receipt['consumer'] == name:receipt['status'] = 'stale'
            result['status'] = 'module_release_pending' if remaining else 'proposals_merged'
            result.pop('digest', None);result['digest'] = digest(result)
            current.result, current.status = result, result['status']
            current.phase = 'remaining_consumer_checks_required' if remaining else 'proposals_merged'
            current.requestKey, current.operationDigest = None, None
            return self.campaigns.store.put(current, current.revision)

    def poll(self, tenant, project, campaign_id, *, force=False):
        campaign = self.campaigns.get(tenant, campaign_id)
        if campaign.projectId != project:
            raise PermissionError('Campaign is outside this project')
        if not force and not self.ledger.poll_due(tenant, project, campaign_id):
            return {'campaignId': campaign_id, 'proposals': self.ledger.pr_observations(tenant, project, campaign_id), 'pollAfterSeconds': 30}
        seen = set()
        for preview in self.ledger.campaign_previews(tenant, project, campaign_id):
            for index, action in enumerate(preview['actions']):
                if action['kind'] != 'pull':continue
                operation = self.ledger.operation(tenant, project, preview['id'], index)
                if operation['state'] != 'confirmed':continue
                target = action['target'];number = operation['result']['number']
                key = (target['repositoryId'], number)
                if key in seen:continue
                seen.add(key)
                item = self._read(tenant, project, target, '/pulls/' + str(number))
                claim = self.ledger.owned(tenant, project, preview['graphDigest'], target['repositoryId'], target['branch'])
                head, base = item.get('head', {}), item.get('base', {})
                if (claim is None or item.get('number') != number or head.get('repo', {}).get('id') != target['repositoryId']
                    or base.get('repo', {}).get('id') != target['repositoryId'] or head.get('ref') != target['branch']
                    or base.get('ref') != target['base'] or head.get('sha') != claim['head']):
                    self.ledger.cancel(tenant, project, preview['id'])
                    raise Conflict('Unknown PR identity or human commit observed; publication stopped')
                if type(item.get('merged')) is not bool or item.get('state') not in {'open', 'closed'}:
                    raise Conflict('Remote PR status is unresolved')
                record = {'repository': target['repository'], 'repositoryId': target['repositoryId'], 'number': number,
                          'root': target['root'], 'head': head['sha'], 'merged': item['merged'], 'state': item['state'],
                          'url': 'https://github.com/' + target['repository'] + '/pull/' + str(number), 'observedAt': int(time.time())}
                self.ledger.retain_pr(tenant, project, campaign_id, preview['graphDigest'], target['root'], record, consumer=preview['wave']=='consumers')
        merged = self.ledger.merged_consumers(tenant, project, campaign_id, campaign.graph['digest'])
        if merged:
            before = campaign.result or {}
            if set(before.get('observedMergedConsumers', [])) != set(merged):
                for preview in self.ledger.campaign_previews(tenant, project, campaign_id):
                    self.ledger.cancel(tenant, project, preview['id'])
                campaign = self._invalidate_remaining(tenant, project, campaign_id, merged)
        return {'campaignId': campaign_id, 'proposals': self.ledger.pr_observations(tenant, project, campaign_id),
                'observedMergedConsumers': sorted(merged), 'status': campaign.status, 'phase': campaign.phase, 'pollAfterSeconds': 30}

    def observe_release(self, tenant, project, campaign_id, *, expected_revision, graph_digest, key,
                        compute_confirmed, connection, repository, tag):
        """Queue authenticated reads and fresh local checks; never creates a tag."""
        campaign = self.campaigns.get(tenant, campaign_id)
        if (campaign.projectId != project or campaign.revision != expected_revision or campaign.graph['digest'] != graph_digest
            or campaign.result is None or campaign.status not in {'module_release_pending', 'local_release_checked'}):
            raise Conflict('Prepare and review the current module campaign first')
        if campaign.result.get('simulatedMergedConsumers'):
            raise Conflict('Prepare fresh source; local merge simulations cannot authorize repository work')
        observed_merges = self.ledger.merged_consumers(tenant, project, campaign_id, graph_digest)
        if set(campaign.result.get('observedMergedConsumers', [])) != set(observed_merges):
            raise Conflict('Refresh actual PR status before checking the remaining wave')
        module = next(r for r in campaign.roots if r.id == campaign.result['module'])
        candidate = Candidate.model_validate(campaign.result['moduleCandidate'])
        expected_files = apply_candidate(campaign.result['moduleBefore'], candidate)
        expected_policy = publication_policy_digest()
        def fetch(event):
            files, observed = self.broker.released_module(tenant, project, connection, repository, tag,
                                                         module.directory, expected_files, cancel_event=event)
            release = {'released_files': files, 'source': observed['source'], 'version': None,
                       'resolved_commit': observed['commit']}
            def retain(checked):
                if event.is_set() or publication_policy_digest() != expected_policy:
                    raise Conflict('Release checks or publication policy changed')
                again = self.broker.resolve_tag(tenant, project, connection, repository, tag)
                if any(again[k] != observed[k] for k in ['tag', 'tagObject', 'commit']):
                    checked['status'] = 'blocked'
                    checked['findings'] = [{'code': 'released_tag_changed'}]
                else:
                    proof = {**observed, 'graphDigest': graph_digest, 'plannerDigest': planner_digest(),
                             'publicationPolicyDigest': expected_policy, 'moduleArtifactDigest': content_digest(files),
                             'mergedObservationDigest': digest(observed_merges),
                             'workerIdentity': checked['workerIdentity'],
                             'consumerPatchDigests': {name: proposal['releasedCandidate']['digest']
                                                     for name, proposal in checked['consumers'].items()}}
                    ident = self.ledger.save_release_observation(tenant, project, campaign_id, proof)
                    checked['release']['observation'] = 'github_authenticated_tag'
                    checked['releaseObservationId'] = ident
                checked.pop('digest', None)
                checked['digest'] = digest(checked)
                return checked
            return release, retain
        descriptor = {'connection': connection, 'repository': repository, 'tag': tag,
                      'moduleCandidateDigest': candidate.digest, 'publicationPolicyDigest': expected_policy}
        return self.campaigns.start(tenant, campaign_id, expected_revision, graph_digest, key, compute_confirmed,
                                    remote_fetch=fetch, remote_request=descriptor)

    def _release_current(self, tenant, project, campaign):
        result = campaign.result
        if result is None or result.get('release', {}).get('observation') != 'github_authenticated_tag' or not result.get('releaseObservationId'):
            raise Conflict('Fetch and check an authenticated actual module release before consumer publication')
        proof = self.ledger.release_observation(tenant, project, campaign.id, result['releaseObservationId'])
        if (proof['graphDigest'] != campaign.graph['digest'] or proof['plannerDigest'] != planner_digest()
            or proof['publicationPolicyDigest'] != publication_policy_digest() or proof['workerIdentity'] != result['workerIdentity']
            or proof['moduleArtifactDigest'] != result['moduleArtifactDigest']
            or proof.get('mergedObservationDigest') != digest(self.ledger.merged_consumers(tenant, project, campaign.id, campaign.graph['digest']))):
            raise Conflict('Authenticated release observation changed; fetch and recheck')
        observed = self.broker.resolve_tag(tenant, project, proof['connection'], proof['repository'], proof['tag'])
        if any(observed[k] != proof[k] for k in ['tag', 'tagObject', 'commit']):
            raise Conflict('Actual module tag moved; prior consumer evidence is stale')
        return proof

    def authorize(self, tenant, project, preview_id, expected_digest, automation_accepted):
        # A fresh preview must still reference the same source/policy at confirmation.
        preview = self.ledger.preview(tenant, project, preview_id)
        self._campaign_current(tenant, project, preview)
        return self.ledger.authorize(tenant, project, preview_id, expected_digest, automation_accepted=automation_accepted)

    def _campaign_current(self, tenant, project, preview):
        campaign = self.campaigns.get(tenant, preview['campaign'])
        if (campaign.projectId != project or campaign.graph['digest'] != preview['graphDigest']
            or preview['plannerDigest'] != planner_digest() or preview.get('publicationPolicyDigest') != publication_policy_digest() or campaign.result is None
            or campaign.result.get('plannerDigest') != planner_digest() or campaign.result.get('digest') != preview['resultDigest'] or
            digest({k: v for k, v in campaign.result.items() if k != 'digest'}) != preview['resultDigest'] or
            campaign.status != ('module_release_pending' if preview['wave']=='module' else 'local_release_checked')):
            raise Conflict('Campaign source, checks or policy changed; review a fresh preview')
        if preview['wave']=='consumers':
            proof = self._release_current(tenant, project, campaign)
            if campaign.result.get('releaseObservationId') != preview['releaseObservationId']:
                raise Conflict('Authenticated module release observation changed')
            for target in preview['targets']:
                patch = campaign.result['consumers'][target['root']].get('releasedCandidate')
                if patch is None or patch['digest'] != target['patchDigest']:
                    raise Conflict('Consumer patch changed after exact confirmation')
        return campaign

    def _proposal_head(self, tenant, project, target):
        if not target.get('appendParent'):
            return target['proposalCommit']
        item = self._read(tenant, project, target, '/git/ref/heads/' + urllib.parse.quote(target['branch'], safe=''))
        head = item.get('object', {}).get('sha')
        if head == target['appendParent']:
            return None
        commit = self._read(tenant, project, target, '/git/commits/' + head)
        parents = commit.get('parents', [])
        if (commit.get('tree', {}).get('sha') != target['expectedTree'] or len(parents) != 1
            or parents[0].get('sha') != target['appendParent']
            or 'AtMem-Operation: ' + target['appendNonce'] not in commit.get('message', '').splitlines()):
            raise Conflict('Unknown proposal commit observed; human changes are never overwritten')
        return head

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
        if kind == 'append':
            head = self._proposal_head(tenant, project, target)
            return {'sha': head, 'tree': target['expectedTree'], 'parent': target['appendParent']} if head else None
        if kind == 'pull':
            expected_head = self._proposal_head(tenant, project, target)
            if expected_head is None:
                raise Conflict('Conditional proposal refresh is not confirmed')
            query = urllib.parse.urlencode({'state': 'all', 'head': target['repository'].split('/')[0] + ':' + target['branch'], 'base': target['base'], 'per_page': 100})
            items = self._read(tenant, project, target, '/pulls?' + query)
            if not isinstance(items, list) or len(items) >= 100:
                raise Conflict('PR reconciliation is incomplete')
            matching = [p for p in items if '<!-- atmem-operation:' + expected + ' -->' in p.get('body', '')]
            if not matching:
                if items:
                    raise Conflict('An unowned or human-created proposal already uses this branch')
                return None
            if len(matching) != 1 or matching[0].get('head', {}).get('sha') != expected_head:
                raise Conflict('Existing proposal contains unknown commits or duplicate identities')
            item = matching[0]
            if (item.get('head', {}).get('repo', {}).get('id') != target['repositoryId'] or
                item.get('base', {}).get('repo', {}).get('id') != target['repositoryId'] or
                item.get('head', {}).get('ref') != target['branch'] or item.get('base', {}).get('ref') != target['base']):
                raise Conflict('PR repository or branch identity differs from the approved proposal')
            if item.get('state') == 'closed' and not item.get('merged'):
                raise Conflict('Maintainer closed this proposal; no replacement was created')
            return {'number': item['number'], 'url': 'https://github.com/' + target['repository'] + '/pull/' + str(item['number']),
                    'head': expected_head, 'state': item['state']}
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
                    if preview['wave']=='consumers':
                        self.poll(tenant, project, preview['campaign'], force=True)
                    self._campaign_current(tenant, project, preview)
                    if target.get('role') != 'campaign_anchor':
                        self._anchor(tenant, project, target, preview['graphDigest'])
                    _, branch = self._current(tenant, project, target)
                    if action['kind'] == 'append':
                        if branch is None or branch.get('commit', {}).get('sha') != target['appendParent']:
                            raise Conflict('Proposal head changed before conditional append')
                    elif action['kind'] == 'pull':
                        if branch is None or branch.get('commit', {}).get('sha') != self._proposal_head(tenant, project, target):
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
        if action['kind'] == 'pull':
            target = action['target']
            # Expose the confirmed write receipt immediately without bypassing
            # the remote status polling budget or inventing a merge observation.
            self.ledger.retain_pr(tenant, project, preview['campaign'], preview['graphDigest'], target['root'], {
                **observed, 'repository': target['repository'], 'repositoryId': target['repositoryId'],
                'root': target['root'], 'merged': None, 'observedAt': None,
            })
        if action['kind'] in {'ref', 'append'}:
            target = action['target']
            manifest = {'tree': target['expectedTree'], 'paths': target['files'], 'baseCommit': target['baseCommit'], 'patchDigest': target['patchDigest']}
            self.ledger.claim(tenant, project, preview['graphDigest'], target['repositoryId'], target['branch'], target['nonce'], observed['sha'],
                              manifest=manifest, expected_head=target.get('appendParent') if action['kind']=='append' else None)
