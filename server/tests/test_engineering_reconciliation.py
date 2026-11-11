import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import uuid
from server.engineering_artifacts import EngineeringArtifacts
from server.engineering_contexts import EngineeringContexts
from server.engineering_jobs import JobJournal
from server.engineering_reconciliation import EngineeringReconciliation
from server.engineering_sessions import SqliteSessionStore,ProjectScope,ModelSelection,SessionError


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.workspace=self.root/'files';self.workspace.mkdir()
        self.store=SqliteSessionStore(self.root/'control.sqlite');self.scope=ProjectScope('tenant-local','museum-catalogue')
        self.session=self.store.create(self.scope,'workspace-museum','test-backend','private-handle',ModelSelection('exact-model','high'))['id']
        self.run=str(uuid.uuid4());self.store.reserve(self.scope,self.session,self.run,'Preserve the museum catalogue; build the read-only adapter.')
        self.store.attach_turn(self.scope,self.session,self.run,'native-turn-one');self.store.terminal(self.scope,self.session,self.run,'native-turn-one','completed')
        self.journal=JobJournal(self.store);self.journal.append(self.scope,self.session,{'kind':'accepted','runId':self.run,'text':'Preserve the museum catalogue; build the read-only adapter.'})
        self.contexts=EngineeringContexts(self.store)
        content=json.dumps({'format':'atmem.ai-architect.project','meta':{'id':self.scope.project},'design':{'provider':'tools','nodes':[]},'requirements':[{'id':'read-only','statement':'Read-only catalogue access.'}]}).encode()
        self.context=self.contexts.attach(self.scope,self.session,self.run,content)
        (self.workspace/'project-context.json').write_bytes(content);(self.workspace/'adapter.cjs').write_text('exports.read = value => value;\n');(self.workspace/'adapter.test.cjs').write_text('// Generated test source, not executed by reconciliation.\n')
        self.records=[{'id':'catalogue-adapter','kind':'implementation','title':'Catalogue adapter','description':'Reference the existing museum catalogue.','dependsOn':['requirement:read-only'],'data':{'files':['adapter.cjs']}},
            {'id':'adapter-test','kind':'evidence','title':'Adapter test reference','description':'A proposed test mapping, not a pass.','dependsOn':['work:catalogue-adapter'],'data':{'files':['adapter.test.cjs'],'reportedStatus':'passed'}}]
        self.artifacts=EngineeringArtifacts(self.store);self.engine=EngineeringReconciliation(self.store,self.artifacts,self.contexts)

    def tearDown(self):
        self.store.close();self.temp.cleanup()

    def capture(self,records=None,raw=None):
        value={'version':1,'records':self.records if records is None else records}
        (self.workspace/'architecture-work-proposal.json').write_bytes(raw if raw is not None else json.dumps(value,ensure_ascii=False).encode())
        return self.artifacts.capture(self.scope,self.session,self.workspace,expected_inputs={'project-context.json':self.context['sha256']})

    def prepare(self,artifact):
        return self.engine.prepare(self.scope,self.session,artifact['id'])

    def test_actual_archive_files_context_intent_and_receipt_are_bound_without_execution(self):
        artifact=self.capture();receipt=self.prepare(artifact);payload=json.loads(receipt['content'])
        self.assertEqual(receipt['sha256'],hashlib.sha256(receipt['content'].encode()).hexdigest())
        self.assertEqual(payload['artifactSha256'],artifact['sha256']);self.assertEqual(payload['context'],self.context)
        self.assertEqual(payload['proposal']['records'][1]['data']['reportedStatus'],'passed')
        self.assertEqual(payload['boundary'],'artifact_file_binding_only')
        self.assertEqual([r['path'] for r in payload['files']],['adapter.cjs','adapter.test.cjs'])
        self.assertEqual(payload['events'][0]['runId'],self.run)
        self.assertEqual(self.prepare(artifact),receipt)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM engineering_reconciliations').fetchone()[0],1)
        self.assertEqual((self.workspace/'project-context.json').read_bytes(),self.context['content'].encode())

    def test_changed_working_file_cannot_change_immutable_file_binding(self):
        artifact=self.capture();first=self.prepare(artifact)
        (self.workspace/'adapter.cjs').write_text('different working bytes')
        self.assertEqual(self.prepare(artifact),first)
        second=self.artifacts.capture(self.scope,self.session,self.workspace,expected_inputs={'project-context.json':self.context['sha256']})
        self.assertNotEqual(second['sha256'],artifact['sha256'])
        self.assertNotEqual(json.loads(self.prepare(second)['content'])['files'],json.loads(first['content'])['files'])

    def test_missing_proposal_is_explicit_and_does_not_synthesize_mapping(self):
        artifact=self.artifacts.capture(self.scope,self.session,self.workspace)
        self.assertEqual(self.prepare(artifact)['status'],'proposal_missing')
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM engineering_reconciliations').fetchone()[0],0)

    def test_unknown_stale_active_failed_and_foreign_artifacts_reject(self):
        artifact=self.capture()
        with self.assertRaises(SessionError):self.engine.prepare(ProjectScope('tenant-other',self.scope.project),self.session,artifact['id'])
        with self.assertRaises(SessionError):self.engine.prepare(self.scope,self.session,str(uuid.uuid4()))
        self.store.reserve(self.scope,self.session,str(uuid.uuid4()),'Newer museum requirement.')
        with self.assertRaises(SessionError):self.prepare(artifact)
        self.store.db.execute("UPDATE engineering_sessions SET state='idle',last_status='failed'");self.store.db.commit()
        with self.assertRaises(SessionError):self.prepare(artifact)

    def test_missing_input_paths_traversal_repeated_and_nonfile_claims_reject_atomically(self):
        for files in [[],['missing.cjs'],['../adapter.cjs'],['/adapter.cjs'],['C:/adapter.cjs'],['adapter.cjs','adapter.cjs'],['project-context.json'],['architecture-work-proposal.json'],[{}]]:
            records=json.loads(json.dumps(self.records));records[0]['data']['files']=files
            with self.subTest(files=files):
                with self.assertRaises(SessionError):self.prepare(self.capture(records))
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM engineering_reconciliations').fetchone()[0],0)

    def test_duplicate_record_ids_and_unsupported_json_are_not_normalized(self):
        with self.assertRaises(SessionError):self.prepare(self.capture(self.records*2))
        for raw in [b'{"version":1,"version":1,"records":[]}',b'{"version":3,"records":[]}',b'{"value":NaN}',b'\xff',b'{"version":1,"records":[]}',b'{"version":1,"records":[],"unexpected":true}']:
            with self.assertRaises(SessionError):self.prepare(self.capture(raw=raw))

    def test_corrupt_archive_or_manifest_cannot_create_receipt(self):
        artifact=self.capture()
        self.store.db.execute('UPDATE engineering_artifacts SET archive=? WHERE id=?',(b'corrupt archive',artifact['id']));self.store.db.commit()
        with self.assertRaises(SessionError):self.prepare(artifact)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM engineering_reconciliations').fetchone()[0],0)

    def test_latest_accepted_steering_context_is_used_and_uncertain_delivery_is_retained(self):
        request=str(uuid.uuid4());updated=self.context['content'].replace('Read-only catalogue access.','Keep Unicode labels 🛰️ while reading the catalogue.')
        second=self.contexts.attach(self.scope,self.session,request,updated.encode())
        self.journal.append(self.scope,self.session,{'kind':'steering_submitted','requestId':request,'text':'Preserve Unicode labels 🛰️.'})
        artifact=self.capture()
        with self.assertRaises(SessionError):self.prepare(artifact)
        self.journal.append(self.scope,self.session,{'kind':'steering_delivery_uncertain','requestId':request})
        with self.assertRaises(SessionError):self.prepare(artifact)
        self.journal.append(self.scope,self.session,{'kind':'steering_accepted','requestId':request})
        payload=json.loads(self.prepare(artifact)['content']);self.assertEqual(payload['context'],second)
        self.assertEqual(payload['events'][1]['text'],'Preserve Unicode labels 🛰️.')

    def test_legacy_missing_context_requires_regeneration_instead_of_guessing(self):
        self.store.db.execute('DELETE FROM engineering_context_submissions');self.store.db.commit()
        with self.assertRaises(SessionError):self.prepare(self.capture())

    def test_automatic_repair_retains_client_context_and_excludes_control_prompt(self):
        repair=str(uuid.uuid4());self.store.reserve(self.scope,self.session,repair,'INTERNAL repair prompt')
        self.store.attach_turn(self.scope,self.session,repair,'repair-turn');self.store.terminal(self.scope,self.session,repair,'repair-turn','completed')
        self.journal.append(self.scope,self.session,{'kind':'accepted','runId':repair,'text':'INTERNAL repair prompt','origin':'automatic_repair'})
        payload=json.loads(self.prepare(self.capture())['content'])
        self.assertEqual(payload['context'],self.context);self.assertNotIn('INTERNAL',json.dumps(payload))

    def test_receipt_and_previous_bytes_survive_control_store_restart(self):
        artifact=self.capture();receipt=self.prepare(artifact)
        self.store.close();self.store=SqliteSessionStore(self.root/'control.sqlite');self.contexts=EngineeringContexts(self.store)
        self.artifacts=EngineeringArtifacts(self.store);self.engine=EngineeringReconciliation(self.store,self.artifacts,self.contexts)
        self.assertEqual(self.prepare(artifact),receipt)
