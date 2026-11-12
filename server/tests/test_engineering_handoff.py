import hashlib
import asyncio
import httpx
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid
import zipfile
from server.app import app, TOKEN
from server import engineering_routes as routes
from server.engineering_artifacts import EngineeringArtifacts
from server.engineering_contexts import EngineeringContexts
from server.engineering_handoff import EngineeringHandoff, digest, design_digest
from server.engineering_jobs import JobJournal
from server.engineering_reconciliation import EngineeringReconciliation
from server.engineering_sessions import SqliteSessionStore, ProjectScope, ModelSelection, SessionError


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = SqliteSessionStore(self.root/'control.sqlite')
        self.scope = ProjectScope('local-owner', 'museum-catalogue')
        self.session = self.store.create(self.scope, 'workspace-museum', 'test', 'private-handle', ModelSelection('exact-model', 'high'))['id']
        self.run = str(uuid.uuid4())
        self.store.reserve(self.scope, self.session, self.run, 'Preserve every requirement.')
        self.store.attach_turn(self.scope, self.session, self.run, 'native-turn')
        self.store.terminal(self.scope, self.session, self.run, 'native-turn', 'completed')
        self.journal = JobJournal(self.store)
        self.journal.append(self.scope, self.session, {'kind': 'accepted', 'runId': self.run, 'text': 'Preserve every requirement.'})
        self.saved = json.dumps({'format': 'atmem.ai-architect.project', 'meta': {'id': self.scope.project, 'revision': 3, 'updatedAt': 'one'},
                                 'design': {'nodes': [], 'edges': []}, 'requirements': [{'statement': 'Preserve café 🍊 and existing ownership.'}]}).encode()
        self.contexts = EngineeringContexts(self.store)
        self.contexts.attach(self.scope, self.session, self.run, self.saved)
        self.artifacts = EngineeringArtifacts(self.store)
        self.checks = []
        self.worker = SimpleNamespace(store=self.store, artifacts=self.artifacts,
            jobs=SimpleNamespace(state=lambda scope, session: {key: self.store.get(scope, session)[key] for key in ('id', 'state', 'run', 'last_status', 'model', 'effort')}),
            reconciliation=EngineeringReconciliation(self.store, self.artifacts, self.contexts),
            checks=SimpleNamespace(list=lambda *args: self.checks))
        self.delivery = EngineeringHandoff(self.worker)
        self.workspace = self.root/'files'
        self.workspace.mkdir()
        (self.workspace/'spec-kit').mkdir()
        (self.workspace/'spec-kit/plan.md').write_text('# Exact implementation plan\n')
        (self.workspace/'run.sh').write_bytes(b'#!/bin/sh\nexit 0\n')
        (self.workspace/'run.sh').chmod(0o755)
        (self.workspace/'project-context.json').write_bytes(self.saved)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def capture(self):
        return self.artifacts.capture(self.scope, self.session, self.workspace)

    def test_lossless_receiving_tree_original_archive_context_and_check_identity(self):
        artifact = self.capture()
        self.checks.append({'id': 'check', 'artifactSha256': artifact['sha256'], 'state': 'finished', 'result': {'status': 'incomplete', 'skipped': 1}})
        report = self.delivery.inspect(self.scope, self.saved)
        self.assertEqual(report['relation'], 'matches_saved_design')
        self.assertEqual(report['session']['model'], 'exact-model')
        data, manifest = self.delivery.package(self.scope, self.saved, self.session, artifact['id'], design_digest(self.saved, self.scope.project))
        with zipfile.ZipFile(io.BytesIO(data)) as receiving:
            original = receiving.read('evidence/original-implementation.zip')
            self.assertEqual(hashlib.sha256(original).hexdigest(), manifest['sha256'])
            with zipfile.ZipFile(io.BytesIO(original)) as source:
                for entry in source.infolist():
                    self.assertEqual(receiving.read('implementation/'+entry.filename), source.read(entry))
                    self.assertEqual(receiving.getinfo('implementation/'+entry.filename).external_attr, entry.external_attr)
            self.assertEqual(receiving.read('design/submitted-project.json'), self.saved)
            self.assertEqual(json.loads(receiving.read('evidence/local-checks.json'))[0]['result']['status'], 'incomplete')
            self.assertIn('not establish full project acceptance', receiving.read('START_HERE.md').decode())

    def test_export_time_only_is_ignored_but_requirements_ownership_and_unicode_changes_are_retained(self):
        artifact = self.capture()
        changed = json.loads(self.saved)
        changed['meta']['updatedAt'] = 'two'
        self.assertEqual(self.delivery.inspect(self.scope, json.dumps(changed).encode())['relation'], 'matches_saved_design')
        changed['requirements'].append({'statement': 'New owner must approve 🍊 export.'})
        current = json.dumps(changed, ensure_ascii=False).encode()
        self.assertEqual(self.delivery.inspect(self.scope, current)['relation'], 'design_changed')
        data, _ = self.delivery.package(self.scope, current, self.session, artifact['id'], design_digest(current, self.scope.project))
        with zipfile.ZipFile(io.BytesIO(data)) as receiving:
            self.assertEqual(receiving.read('design/latest-saved-project.json'), current)
            self.assertEqual(json.loads(receiving.read('evidence/delivery.json'))['relation'], 'design_changed')
        with self.assertRaisesRegex(SessionError, 'saved design changed'):
            self.delivery.package(self.scope, current, self.session, artifact['id'], design_digest(self.saved, self.scope.project))

    def test_empty_and_other_project_do_not_leak_a_package_or_start_work(self):
        self.assertIsNone(self.delivery.inspect(self.scope, self.saved)['artifact'])
        self.capture()
        foreign = ProjectScope('other-tenant', self.scope.project)
        self.assertIsNone(self.delivery.inspect(foreign, self.saved)['artifact'])
        self.assertEqual(self.store.get(self.scope, self.session)['state'], 'idle')

    def test_earlier_turn_and_missing_context_cannot_be_repackaged_as_current_work(self):
        artifact = self.capture()
        with self.store.db:
            self.store.db.execute('DELETE FROM engineering_context_submissions')
        self.assertEqual(self.delivery.inspect(self.scope, self.saved)['relation'], 'unknown')
        with self.assertRaises(SessionError):
            self.delivery.package(self.scope, self.saved, self.session, artifact['id'], design_digest(self.saved, self.scope.project))
        self.store.reserve(self.scope, self.session, str(uuid.uuid4()), 'New work.')
        self.assertEqual(self.delivery.inspect(self.scope, self.saved)['relation'], 'earlier_turn')

    def test_bad_check_or_archive_digest_is_not_exported_as_evidence(self):
        artifact = self.capture()
        self.checks.append({'artifactSha256': 'f'*64})
        with self.assertRaisesRegex(SessionError, 'check receipt'):
            self.delivery.inspect(self.scope, self.saved)
        self.checks.clear()
        with self.store.db:
            self.store.db.execute('UPDATE engineering_artifacts SET archive=? WHERE id=?', (b'broken', artifact['id']))
        with self.assertRaisesRegex(SessionError, 'integrity'):
            self.delivery.package(self.scope, self.saved, self.session, artifact['id'], design_digest(self.saved, self.scope.project))

    def test_actual_http_download_unpacks_exact_captured_source_and_checks(self):
        artifact = self.capture()
        projects = self.root/'projects'
        projects.mkdir()
        (projects/f'{self.scope.project}.atforma.json').write_bytes(self.saved)
        headers = {'Authorization': f'Bearer {TOKEN}'}
        with patch.object(routes, 'home', return_value=self.root), patch.object(routes, 'setting', side_effect=lambda key: '1' if key == 'ENABLE_ENGINEERING' else None), patch.object(routes, 'service', return_value=self.worker):
            async def exercise():
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://testserver') as client:
                    response = await client.post('/api/engineering/delivery', json={'projectId': self.scope.project}, headers=headers)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertNotIn('content', response.json()['context'])
                    body = {'projectId': self.scope.project, 'sessionId': self.session, 'artifactId': artifact['id'],
                            'savedDesignSha256': response.json()['savedDesignSha256']}
                    denied = await client.post('/api/engineering/handoff', json=body)
                    self.assertEqual(denied.status_code, 401)
                    download = await client.post('/api/engineering/handoff', json=body, headers=headers)
                    self.assertEqual(download.status_code, 200, download.text[:100] if download.status_code != 200 else '')
                    self.assertEqual(download.headers['X-Artifact-Sha256'], digest(download.content))
                    self.assertEqual(download.headers['X-Source-Artifact-Sha256'], artifact['sha256'])
                    with zipfile.ZipFile(io.BytesIO(download.content)) as receiving:
                        self.assertEqual(receiving.read('implementation/run.sh'), (self.workspace/'run.sh').read_bytes())
                        self.assertEqual(receiving.read('implementation/spec-kit/plan.md'), (self.workspace/'spec-kit/plan.md').read_bytes())
                        self.assertEqual(receiving.read('design/submitted-project.json'), self.saved)
                        self.assertEqual(digest(receiving.read('evidence/original-implementation.zip')), artifact['sha256'])
            asyncio.run(exercise())
