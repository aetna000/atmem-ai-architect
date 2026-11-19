import hashlib
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from server.engineering_artifacts import EngineeringArtifacts
from server.engineering_contexts import EngineeringContexts
from server.engineering_sessions import SqliteSessionStore,ProjectScope,ModelSelection,SessionError
from server.reviewed_drafts import LocalReviewedDrafts

class ReviewedDraftTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'engineering').mkdir();self.path=self.root/'engineering'/'control.sqlite'
        self.store=SqliteSessionStore(self.path);self.scope=ProjectScope('local-owner','project-one')
        self.session=self.store.create(self.scope,'workspace','backend','private-handle',ModelSelection('selected','medium'))['id']
        self.run=str(uuid.uuid4());self.store.reserve(self.scope,self.session,self.run,'Design only');self.store.attach_turn(self.scope,self.session,self.run,'native-turn')
        self.contexts=EngineeringContexts(self.store)
        self.context=self.contexts.attach(self.scope,self.session,self.run,json.dumps({'format':'atmem.ai-architect.project','meta':{'id':self.scope.project}}).encode())
        self.store.terminal(self.scope,self.session,self.run,'native-turn','completed')
        self.workspace=self.root/'workspace';self.workspace.mkdir()
        self.content=' {\n "version": 1, "title": "Archive — café", "sourceSlots": [1]\n}\n'.encode()
        self.sha=hashlib.sha256(self.content).hexdigest()
        (self.workspace/'architecture.canvas.json').write_bytes(self.content)
        (self.workspace/'architecture.review.md').write_bytes(('Reviewed source.\r\nDraft SHA-256: '+self.sha+'\r\n').encode())
        self.artifacts=EngineeringArtifacts(self.store);self.manifest=self.artifacts.capture(self.scope,self.session,self.workspace)
        self.reader=LocalReviewedDrafts(self.path)
    def tearDown(self):self.store.close();self.temp.cleanup()
    def read(self,**changes):
        args={'scope':self.scope,'artifact_id':self.manifest['id'],'draft_sha256':self.sha,'context_sha256':self.context['sha256']};args.update(changes);return self.reader.read(**args)
    def test_exact_bytes_owner_context_review_and_restart_without_worker(self):
        before=self.path.read_bytes();result=self.read()
        self.assertEqual(result.content,self.content);self.assertEqual(result.receipt['draftSha256'],self.sha)
        self.assertEqual(result.receipt['artifactSha256'],self.manifest['sha256'])
        self.assertEqual(LocalReviewedDrafts(self.path).read(self.scope,self.manifest['id'],self.sha,self.context['sha256']).content,self.content)
        self.assertEqual(self.path.read_bytes(),before)
        self.assertNotIn('private-handle',str(result.receipt));self.assertNotIn(str(self.workspace),str(result.receipt))
    def test_wrong_project_tenant_context_and_draft_are_not_substituted(self):
        for changes in [{'scope':ProjectScope('other-owner','project-one')},{'scope':ProjectScope('local-owner','project-two')},{'artifact_id':str(uuid.uuid4())},{'draft_sha256':'0'*64},{'context_sha256':'0'*64}]:
            with self.subTest(changes=changes),self.assertRaises(SessionError):self.read(**changes)
    def test_corrupt_archive_and_submitted_context_fail(self):
        original=self.artifacts.get(self.scope,self.session,self.manifest['id'])[1]
        corrupted=bytearray(original);corrupted[16]^=1
        with self.store.db:self.store.db.execute('UPDATE engineering_artifacts SET archive=? WHERE id=?',(bytes(corrupted),self.manifest['id']))
        with self.assertRaisesRegex(SessionError,'archive integrity'):self.read()
        with self.store.db:
            self.store.db.execute('UPDATE engineering_artifacts SET archive=? WHERE id=?',(original,self.manifest['id']))
            self.store.db.execute('UPDATE engineering_contexts SET content=? WHERE id=?',(b'{}',self.context['id']))
        with self.assertRaisesRegex(SessionError,'context digest'):self.read()
    def test_missing_seal_oversize_and_failed_run_are_not_reviewed_evidence(self):
        (self.workspace/'architecture.review.md').write_text('Unsealed draft')
        self.manifest=self.artifacts.capture(self.scope,self.session,self.workspace)
        with self.assertRaisesRegex(SessionError,'review seal'):self.read()
        (self.workspace/'architecture.review.md').write_text('Draft SHA-256: '+self.sha)
        self.manifest=self.artifacts.capture(self.scope,self.session,self.workspace)
        with patch('server.reviewed_drafts.MAX_CONTEXT_BYTES',20),self.assertRaises(SessionError):self.read()
        with self.store.db:self.store.db.execute("UPDATE engineering_runs SET status='failed' WHERE id=?",(self.run,))
        with self.assertRaises(SessionError):self.read()
    def test_selected_oversize_member_rejects_before_expansion(self):
        content=json.dumps({'version':1,'padding':'x'*2_000_000}).encode();self.sha=hashlib.sha256(content).hexdigest()
        (self.workspace/'architecture.canvas.json').write_bytes(content)
        (self.workspace/'architecture.review.md').write_text('Draft SHA-256: '+self.sha)
        self.manifest=self.artifacts.capture(self.scope,self.session,self.workspace)
        with self.assertRaisesRegex(SessionError,'file exceeds its bound'):self.read()
    def test_invalid_manifest_and_boolean_version_are_not_supported_proposals(self):
        with self.store.db:self.store.db.execute('UPDATE engineering_artifacts SET manifest=? WHERE id=?',('[]',self.manifest['id']))
        with self.assertRaisesRegex(SessionError,'capture receipt is invalid'):self.read()
        with self.store.db:self.store.db.execute('UPDATE engineering_artifacts SET manifest=? WHERE id=?',(json.dumps(self.manifest),self.manifest['id']))
        content=b'{"version":true}';self.sha=hashlib.sha256(content).hexdigest()
        (self.workspace/'architecture.canvas.json').write_bytes(content)
        (self.workspace/'architecture.review.md').write_text('Draft SHA-256: '+self.sha)
        self.manifest=self.artifacts.capture(self.scope,self.session,self.workspace)
        with self.assertRaisesRegex(SessionError,'supported JSON proposal'):self.read()
    def test_authenticated_http_no_model_service_and_extra_claims_rejected(self):
        from fastapi.testclient import TestClient
        from server.app import app,TOKEN
        client=TestClient(app);payload={'projectId':self.scope.project,'artifactId':self.manifest['id'],'draftSha256':self.sha,'contextSha256':self.context['sha256']};headers={'Authorization':'Bearer '+TOKEN}
        self.assertEqual(client.post('/api/design-evidence/draft',json=payload).status_code,401)
        with patch('server.app.product_home',return_value=self.root),patch('server.engineering_routes.local_scope',return_value=(self.scope,self.root/'saved.json')),patch('server.engineering_routes.service',side_effect=AssertionError('Must not initialize a worker')):
            response=client.post('/api/design-evidence/draft',json=payload,headers=headers)
            self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.content,self.content)
            self.assertEqual(response.headers['x-draft-sha256'],self.sha);self.assertEqual(response.headers['x-context-sha256'],self.context['sha256']);self.assertEqual(response.headers['cache-control'],'no-store')
            self.assertEqual(client.post('/api/design-evidence/draft',json={**payload,'tenant':'other'},headers=headers).status_code,422)
            self.assertEqual(client.post('/api/design-evidence/draft',json={**payload,'path':'/private'},headers=headers).status_code,422)
            self.assertEqual(client.post('/api/design-evidence/draft',json={**payload,'draftSha256':'0'*64},headers=headers).status_code,409)
