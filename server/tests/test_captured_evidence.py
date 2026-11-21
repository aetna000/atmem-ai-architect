import hashlib
import io
import json
import os
import stat
import unittest
import zipfile
from unittest.mock import patch
from server.tests import test_reviewed_drafts as draft_fixture
from server.captured_evidence import LocalCapturedEvidence,retain_initial_input
from server.engineering_jobs import JobJournal
from server.engineering_sessions import ProjectScope,SessionError

class CapturedEvidenceTests(unittest.TestCase):
    def setUp(self):
        draft_fixture.ReviewedDraftTests.setUp(self)
        self.initial=json.dumps({'format':'atmem.ai-architect.project','meta':{'id':self.scope.project},'requirements':['Original input, different from refinement']}).encode()
        self.pin=hashlib.sha256(self.initial).hexdigest()
        self.journal=JobJournal(self.store)
        self.journal.append(self.scope,self.session,{'kind':'created','contextSha256':self.pin,'inputDigests':{'project-context.json':self.pin}})
        self.store.db.execute('CREATE TABLE engineering_workspaces (id TEXT PRIMARY KEY,tenant TEXT,project TEXT,path TEXT)')
        self.store.db.execute('INSERT INTO engineering_workspaces VALUES (?,?,?,?)',('workspace',self.scope.tenant,self.scope.project,str(self.workspace)))
        self.store.db.commit()
        (self.workspace/'project-context.json').write_bytes(self.initial)
        self.reader=LocalCapturedEvidence(self.path)
    def tearDown(self):draft_fixture.ReviewedDraftTests.tearDown(self)
    def read(self,**changes):
        args={'scope':self.scope,'artifact_id':self.manifest['id'],'draft_sha256':self.sha,'context_sha256':self.context['sha256']};args.update(changes);return self.reader.read(**args)
    def payload(self):
        result=self.read()
        with zipfile.ZipFile(io.BytesIO(result.content)) as z:return result,{name:z.read(name)for name in z.namelist()}
    def recapture(self,files):
        for name,content in files.items():
            target=self.workspace/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
        self.manifest=self.artifacts.capture(self.scope,self.session,self.workspace)
    def test_library_and_sensor_code_transfer_exactly_without_worker_or_execution(self):
        for name in ['library/loans.rb','sensors/worker.go']:
            self.recapture({name:b'Never executed by this reader','AGENTS.md':b'Untrusted captured controls'})
            before=self.path.read_bytes();result,payload=self.payload()
            self.assertEqual(self.path.read_bytes(),before)
            self.assertEqual(payload['initial-context.json'],self.initial)
            self.assertNotEqual(payload['initial-context.json'],payload['submitted-context.json'])
            self.assertEqual(hashlib.sha256(payload['capture.zip']).hexdigest(),self.manifest['sha256'])
            with zipfile.ZipFile(io.BytesIO(payload['capture.zip'])) as z:self.assertEqual(z.read(name),b'Never executed by this reader')
            self.assertEqual(hashlib.sha256(result.content).hexdigest(),result.receipt['bundleSha256'])
            public=str(result.receipt)+payload['initial-context-receipt.json'].decode()
            self.assertNotIn(str(self.workspace),public);self.assertNotIn('private-handle',public)
    def test_retained_initial_input_survives_workspace_deletion_and_cannot_be_replaced(self):
        retain_initial_input(self.store,self.scope,self.session,self.initial)
        retain_initial_input(self.store,self.scope,self.session,self.initial)
        (self.workspace/'project-context.json').unlink()
        _,payload=self.payload();self.assertEqual(payload['initial-context.json'],self.initial)
        self.assertEqual(json.loads(payload['initial-context-receipt.json'])['source'],'retained_control_store')
        with self.assertRaisesRegex(SessionError,'cannot be replaced'):
            retain_initial_input(self.store,self.scope,self.session,b'{"format":"atmem.ai-architect.project","meta":{"id":"project-one"}}')
        with self.store.db:self.store.db.execute('UPDATE engineering_initial_inputs SET content=? WHERE session=?',(b'{}',self.session))
        with self.assertRaisesRegex(SessionError,'initial input digest'):self.read()
    def test_foreign_scope_wrong_pins_failed_run_and_original_event_are_rejected(self):
        for change in [{'scope':ProjectScope('foreign',self.scope.project)},{'scope':ProjectScope(self.scope.tenant,'foreign-project')},{'draft_sha256':'0'*64},{'context_sha256':'0'*64}]:
            with self.subTest(change=change),self.assertRaises(SessionError):self.read(**change)
        with self.store.db:self.store.db.execute("UPDATE engineering_runs SET status='failed' WHERE id=?",(self.run,))
        with self.assertRaises(SessionError):self.read()
        with self.store.db:
            self.store.db.execute("UPDATE engineering_runs SET status='completed' WHERE id=?",(self.run,))
            self.store.db.execute('UPDATE engineering_events SET payload=? WHERE session=?',(json.dumps({'kind':'created','contextSha256':'0'*64,'inputDigests':{'project-context.json':self.pin}}),self.session))
        with self.assertRaisesRegex(SessionError,'pin'):self.read()
    def test_legacy_file_changes_symlink_hardlink_and_wrong_workspace_scope_reject(self):
        target=self.workspace/'project-context.json'
        target.write_bytes(b'{}')
        with self.assertRaisesRegex(SessionError,'digest'):self.read()
        target.unlink();other=self.root/'elsewhere.json';other.write_bytes(self.initial);target.symlink_to(other)
        with self.assertRaises(SessionError):self.read()
        target.unlink();os.link(other,target)
        with self.assertRaisesRegex(SessionError,'unsafe'):self.read()
        target.unlink();target.write_bytes(self.initial)
        with self.store.db:self.store.db.execute("UPDATE engineering_workspaces SET tenant='foreign'")
        with self.assertRaisesRegex(SessionError,'unavailable'):self.read()
    def rewrite_capture(self,transform):
        manifest,raw=self.artifacts.get(self.scope,self.session,self.manifest['id'])
        with zipfile.ZipFile(io.BytesIO(raw)) as z:entries=[(entry,z.read(entry))for entry in z.infolist()]
        entries,manifest=transform(entries,manifest)
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for entry,content in entries:z.writestr(entry,content)
        raw=output.getvalue();manifest.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        with self.store.db:self.store.db.execute('UPDATE engineering_artifacts SET manifest=?,archive=? WHERE id=?',(json.dumps(manifest),raw,self.manifest['id']))
    def test_unsealed_extra_payload_missing_records_and_unsafe_case_collisions_reject(self):
        # Valid draft and review do not authorize arbitrary unlisted or unsafe code.
        variants=['unlisted','wronghash','unsafe','case','symlink']
        original=self.artifacts.get(self.scope,self.session,self.manifest['id'])
        for variant in variants:
            with self.subTest(variant=variant):
                with self.store.db:self.store.db.execute('UPDATE engineering_artifacts SET manifest=?,archive=? WHERE id=?',(json.dumps(original[0]),original[1],self.manifest['id']))
                def transform(entries,manifest):
                    name={'unsafe':'../escape.py','case':'ARCHITECTURE.CANVAS.JSON'}.get(variant,'extra/code.py')
                    entry=zipfile.ZipInfo(name);entry.external_attr=(stat.S_IFLNK|0o777 if variant=='symlink'else stat.S_IFREG|0o644)<<16
                    body=b'unexecuted';entries.append((entry,body))
                    if variant!='unlisted':manifest['files'].append({'path':name,'kind':'file','bytes':len(body),'sha256':'0'*64 if variant=='wronghash'else hashlib.sha256(body).hexdigest()})
                    return entries,manifest
                self.rewrite_capture(transform)
                with self.assertRaises(SessionError):self.read()
    def test_http_authentication_no_model_dependency_and_no_caller_paths(self):
        from fastapi.testclient import TestClient
        from server.app import app,TOKEN
        client=TestClient(app);payload={'projectId':self.scope.project,'artifactId':self.manifest['id'],'draftSha256':self.sha,'contextSha256':self.context['sha256']};headers={'Authorization':'Bearer '+TOKEN}
        self.assertEqual(client.post('/api/design-evidence/capture',json=payload).status_code,401)
        with patch('server.app.product_home',return_value=self.root),patch('server.engineering_routes.local_scope',return_value=(self.scope,self.root/'saved.json')),patch('server.engineering_routes.service',side_effect=AssertionError('No worker initialization')):
            result=client.post('/api/design-evidence/capture',json=payload,headers=headers)
            self.assertEqual(result.status_code,200,result.text[:100]);self.assertEqual(result.headers['content-type'],'application/zip');self.assertEqual(result.headers['cache-control'],'no-store')
            self.assertEqual(hashlib.sha256(result.content).hexdigest(),result.headers['x-evidence-sha256'])
            self.assertEqual(result.headers['x-initial-context-sha256'],self.pin)
            for extra in [{'path':'/private'},{'tenant':'other'},{'sessionId':self.session}]:self.assertEqual(client.post('/api/design-evidence/capture',json={**payload,**extra},headers=headers).status_code,422)
            self.assertEqual(client.post('/api/design-evidence/capture',json={**payload,'contextSha256':'0'*64},headers=headers).status_code,409)
    def test_bounds_reject_without_partial_bundle(self):
        with patch('server.captured_evidence.MAX_FILES',1),self.assertRaises(SessionError):self.read()
        with patch('server.captured_evidence.MAX_ARCHIVE_BYTES',1),self.assertRaises(SessionError):self.read()
        self.recapture({'large/compressible.bin':b'0'*20_000})
        self.assertLess(self.manifest['bytes'],5000)
        with patch('server.captured_evidence.MAX_ARCHIVE_BYTES',5000),self.assertRaisesRegex(SessionError,'expansion bound'):self.read()
    def test_legacy_initial_input_is_preserved_without_inventing_canonical_schema(self):
        initial=b'{"requirements":"Preserve the existing library"}'
        pin=hashlib.sha256(initial).hexdigest()
        retain_initial_input(self.store,self.scope,self.session,initial)
        with self.store.db:
            self.store.db.execute('UPDATE engineering_events SET payload=? WHERE session=?',
                (json.dumps({'kind':'created','contextSha256':pin,'inputDigests':{'project-context.json':pin}}),self.session))
        _,payload=self.payload();self.assertEqual(payload['initial-context.json'],initial)
        with self.assertRaises(SessionError):retain_initial_input(self.store,ProjectScope('foreign',self.scope.project),self.session,initial)
