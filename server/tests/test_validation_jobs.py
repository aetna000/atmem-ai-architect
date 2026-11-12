import asyncio
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
import zipfile
from server.engineering_artifacts import EngineeringArtifacts
from server.engineering_sessions import ModelSelection,ProjectScope,SessionError,SqliteSessionStore
from server.local_validation import ValidationSpec
from server.validation_jobs import RegisteredValidator,ValidationJobs,registered_validators
from server.validation_applicability import FileApplicability
from server.runtime_evidence import RuntimeEvidence
from server.tests.test_runtime_evidence import observation


class Worker:
    policy_digest='policy-one'
    identity_digest='local-worker-one'
    def __init__(self):
        self.calls=[];self.entered=threading.Event();self.release=threading.Event();self.release.set()
        self.recovered=[];self.recovery_error=False;self.receipt_error=False
    def run(self,content,digest,spec,*,execution_id,cancel_event):
        self.calls.append((content,digest,spec,execution_id));self.entered.set()
        while not self.release.wait(.01):
            if cancel_event.is_set():return {'artifactSha256':digest,'status':'failed','reason':'cancelled'}
        return {'artifactSha256':'different' if self.receipt_error else digest,'status':'passed','testsReported':9}
    def recover(self,job):
        self.recovered.append(job)
        if self.recovery_error:raise RuntimeError('private daemon error')
        return {'cleanupConfirmed':True,'workReplayed':False}


class ValidationJobTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.store=SqliteSessionStore(self.root/'control.sqlite')
        self.artifacts=EngineeringArtifacts(self.store)
        self.scope=ProjectScope('local-owner','project-one')
        self.session=self.store.create(self.scope,'workspace-one','backend','private-thread',ModelSelection('exact-model','high'))['id']
        self.store.reserve(self.scope,self.session,'run-one','Keep source immutable')
        self.store.attach_turn(self.scope,self.session,'run-one','turn-one')
        self.store.terminal(self.scope,self.session,'run-one','turn-one','completed')
        workspace=self.root/'source';workspace.mkdir();(workspace/'test_unit.py').write_text('original code')
        self.manifest=self.artifacts.capture(self.scope,self.session,workspace)
        self.artifact=self.manifest['id'];self.worker=Worker()
        self.spec=ValidationSpec('python-tests','sha256:'+'a'*64,('/usr/local/bin/python3','-m','unittest','discover','-v'))
        self.catalog={self.spec.name:RegisteredValidator('Local Python tests',self.spec)}
        self.jobs=ValidationJobs(self.store,self.artifacts,self.worker,self.catalog)

    async def asyncTearDown(self):
        self.worker.release.set();await self.jobs.close();self.store.close();self.temp.cleanup()

    async def finish(self):
        await asyncio.gather(*list(self.jobs.tasks.values()))

    async def test_digest_bound_job_survives_http_reader_loss_and_replays_receipt(self):
        state=await self.jobs.start(self.scope,self.session,self.artifact,'python-tests')
        await self.finish()
        result=self.jobs.get(self.scope,self.session,state['id'])
        self.assertEqual(result['state'],'finished');self.assertEqual(result['result']['status'],'passed')
        self.assertEqual(result['acceptance'],'not_established_by_local_check')
        self.assertEqual(self.worker.calls[0][1],self.manifest['sha256'])
        with zipfile.ZipFile(io.BytesIO(self.worker.calls[0][0])) as archive:self.assertEqual(archive.read('test_unit.py'),b'original code')
        await self.jobs.close()
        self.jobs=ValidationJobs(self.store,self.artifacts,self.worker,self.catalog)
        self.assertEqual(self.jobs.get(self.scope,self.session,state['id'])['result'],result['result'])
        self.assertEqual(len(self.worker.calls),1)

    async def test_dependency_lock_pins_select_matching_runtime_from_actual_captured_bytes(self):
        import hashlib
        workspace=self.root/'source';(workspace/'nested').mkdir();lock=workspace/'nested/requirements.lock';lock.write_bytes(b'client_sdk==1.0\n')
        artifact=self.artifacts.capture(self.scope,self.session,workspace)
        first_pin=hashlib.sha256(lock.read_bytes()).hexdigest();other_pin=hashlib.sha256(b'other_sdk==2.0\n').hexdigest()
        def rule(pin):return FileApplicability.parse({'anyOf':['**/test_*.py'],'anyFileSha256':[{'pattern':'**/requirements.lock','sha256':pin}]})
        self.jobs.validators={'matching-runtime':RegisteredValidator('Matching runtime',ValidationSpec('matching-runtime',self.spec.image,self.spec.command),rule(first_pin)),
                              'other-runtime':RegisteredValidator('Other runtime',ValidationSpec('other-runtime',self.spec.image,self.spec.command),rule(other_pin))}
        plan=self.jobs.plan(self.scope,self.session,artifact['id'])
        self.assertEqual([d['state']for d in plan['decisions']],['selected','not_applicable']);self.assertEqual(self.worker.calls,[])
        first_contract=plan['decisions'][0]['contractSha256']
        lock.write_bytes(b'client_sdk==1.1\n');changed=self.artifacts.capture(self.scope,self.session,workspace)
        stale=self.jobs.plan(self.scope,self.session,changed['id']);self.assertEqual(stale['selectionStatus'],'no_available_applicable_checks')
        self.assertEqual(self.jobs.plan(self.scope,self.session,artifact['id']),plan)
        self.jobs.validators['matching-runtime']=RegisteredValidator('Matching runtime',ValidationSpec('matching-runtime',self.spec.image,self.spec.command),rule(hashlib.sha256(lock.read_bytes()).hexdigest()))
        updated=self.jobs.plan(self.scope,self.session,changed['id']);self.assertEqual(updated['decisions'][0]['state'],'selected');self.assertNotEqual(updated['decisions'][0]['contractSha256'],first_contract)

    async def test_executable_scratch_changes_contract_and_is_disclosed_without_reusing_old_check(self):
        from dataclasses import replace
        first=await self.jobs.start(self.scope,self.session,self.artifact,'python-tests');await self.finish()
        legacy=self.jobs._contract(self.jobs.validators['python-tests'])[1]
        self.assertNotIn('executable_scratch',legacy['spec'])
        self.assertEqual(self.jobs.catalog()[0]['runtime']['executableScratchDirectories'],[])
        self.jobs.validators['python-tests']=RegisteredValidator('Native dependency checks',replace(self.spec,executable_scratch=True))
        second=await self.jobs.start(self.scope,self.session,self.artifact,'python-tests');await self.finish()
        self.assertNotEqual(first['contractSha256'],second['contractSha256']);self.assertEqual(len(self.worker.calls),2)
        self.assertEqual(self.jobs.catalog()[0]['runtime']['executableScratchDirectories'],['/dependencies'])
        self.assertEqual(self.jobs.get(self.scope,self.session,first['id'])['contractSha256'],first['contractSha256'])

    async def test_manual_recapture_keeps_automatic_package_checks_visible_without_replay(self):
        check=await self.jobs.start(self.scope,self.session,self.artifact,'python-tests');await self.finish()
        captured=self.artifacts.capture(self.scope,self.session,self.root/'source')
        self.assertEqual(captured['id'],self.artifact)
        restored=self.jobs.list(self.scope,self.session,captured['id'])
        self.assertEqual(len(restored),1);self.assertEqual(restored[0]['id'],check['id'])
        self.assertEqual(restored[0]['result']['status'],'passed');self.assertEqual(len(self.worker.calls),1)

    async def test_pinned_observed_runtime_changes_contract_but_does_not_rewrite_prior_check(self):
        import hashlib
        first=await self.jobs.start(self.scope,self.session,self.artifact,'python-tests');await self.finish()
        path=self.root/'runtime.json';path.write_text(json.dumps(observation(self.spec)))
        reference={'path':str(path.resolve()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        self.jobs.validators['python-tests']=RegisteredValidator('Python',self.spec,runtime_evidence=RuntimeEvidence.load(reference,self.spec))
        catalog=self.jobs.catalog()[0]
        self.assertEqual(catalog['runtimeEvidence']['observed']['executableVersion'],'3.13.18')
        self.assertNotEqual(first['contractSha256'],catalog['contractSha256']);self.assertNotIn(str(path),str(catalog))
        catalog['runtimeEvidence']['observed']['executableVersion']='invented'
        self.assertEqual(self.jobs.catalog()[0]['runtimeEvidence']['observed']['executableVersion'],'3.13.18')
        second=await self.jobs.start(self.scope,self.session,self.artifact,'python-tests');await self.finish()
        self.assertNotEqual(first['id'],second['id']);self.assertEqual(self.jobs.get(self.scope,self.session,first['id'])['contractSha256'],first['contractSha256'])

    def test_operator_runtime_receipt_is_loaded_during_registration_and_cannot_override_image(self):
        import hashlib
        path=self.root/'runtime.json';path.write_text(json.dumps(observation(self.spec)))
        reference={'path':str(path.resolve()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        entry={'id':self.spec.name,'label':'Python','image':self.spec.image,'command':list(self.spec.command),'runtimeReceipt':reference}
        registered=registered_validators([entry])[self.spec.name]
        self.assertEqual(registered.runtime_evidence.public()['receiptSha256'],reference['sha256'])
        with self.assertRaises(ValueError):registered_validators([{**entry,'image':'sha256:'+'f'*64}])

    async def test_other_scope_session_or_artifact_cannot_start_or_observe(self):
        state=await self.jobs.start(self.scope,self.session,self.artifact,'python-tests');await self.finish()
        for scope in [ProjectScope('other-owner','project-one'),ProjectScope('local-owner','project-two')]:
            with self.assertRaises(SessionError):await self.jobs.start(scope,self.session,self.artifact,'python-tests')
            with self.assertRaises(SessionError):self.jobs.get(scope,self.session,state['id'])
            with self.assertRaises(SessionError):self.jobs.list(scope,self.session,self.artifact)
            with self.assertRaises(SessionError):await self.jobs.recover(scope,self.session,state['id'])
        with self.assertRaises(SessionError):await self.jobs.start(self.scope,self.session,'other-artifact','python-tests')
        self.assertEqual(len(self.worker.calls),1)

    async def test_duplicate_requests_share_job_and_retry_is_explicit(self):
        first,second=await asyncio.gather(*[self.jobs.start(self.scope,self.session,self.artifact,'python-tests') for _ in range(2)])
        self.assertEqual(first['id'],second['id']);await self.finish()
        again=await self.jobs.start(self.scope,self.session,self.artifact,'python-tests')
        self.assertEqual(again['id'],first['id']);self.assertEqual(len(self.worker.calls),1)
        retried=await self.jobs.start(self.scope,self.session,self.artifact,'python-tests',retry=True)
        self.assertNotEqual(retried['id'],first['id']);await self.finish();self.assertEqual(len(self.worker.calls),2)

    async def test_changed_policy_is_a_distinct_contract_and_old_evidence_remains(self):
        first=await self.jobs.start(self.scope,self.session,self.artifact,'python-tests');await self.finish()
        self.worker.policy_digest='policy-two'
        second=await self.jobs.start(self.scope,self.session,self.artifact,'python-tests');await self.finish()
        self.assertNotEqual(first['contractSha256'],second['contractSha256'])
        self.assertEqual(len(self.jobs.list(self.scope,self.session,self.artifact)),2)

    async def test_restart_requires_confirmed_same_worker_cleanup_without_replay(self):
        state=await self.jobs.start(self.scope,self.session,self.artifact,'python-tests');await self.finish()
        # Simulate an interrupted supervisor's durable record, not a live thread.
        with self.store.db:self.store.db.execute("UPDATE artifact_validation_jobs SET state='running',result=NULL WHERE id=?",(state['id'],))
        self.jobs=ValidationJobs(self.store,self.artifacts,self.worker,self.catalog)
        self.assertEqual(self.jobs.get(self.scope,self.session,state['id'])['state'],'recovery_required')
        self.worker.identity_digest='different-worker'
        with self.assertRaises(SessionError):await self.jobs.recover(self.scope,self.session,state['id'])
        self.assertEqual(self.worker.recovered,[])
        self.worker.identity_digest='local-worker-one';self.worker.recovery_error=True
        with self.assertRaises(SessionError):await self.jobs.recover(self.scope,self.session,state['id'])
        self.assertEqual(self.jobs.get(self.scope,self.session,state['id'])['state'],'recovery_required')
        self.worker.recovery_error=False
        result=await self.jobs.recover(self.scope,self.session,state['id'])
        self.assertEqual(result['result']['reason'],'supervisor_restart');self.assertEqual(len(self.worker.calls),1)

    async def test_shutdown_cancels_active_checks_and_records_failure(self):
        self.worker.release.clear()
        state=await self.jobs.start(self.scope,self.session,self.artifact,'python-tests')
        await asyncio.to_thread(self.worker.entered.wait,2)
        await self.jobs.close()
        result=self.jobs.get(self.scope,self.session,state['id'])
        self.assertEqual(result['result']['reason'],'cancelled')
        with self.assertRaises(SessionError):await self.jobs.start(self.scope,self.session,self.artifact,'python-tests')

    async def test_wrong_artifact_receipt_fails_without_exposing_diagnostics(self):
        self.worker.receipt_error=True
        state=await self.jobs.start(self.scope,self.session,self.artifact,'python-tests');await self.finish()
        result=self.jobs.get(self.scope,self.session,state['id'])
        self.assertEqual(result['result']['status'],'failed');self.assertEqual(result['result']['reason'],'validator_unavailable')

    async def test_unknown_validator_does_not_run_model_supplied_commands(self):
        with self.assertRaises(SessionError):await self.jobs.start(self.scope,self.session,self.artifact,'not-registered')
        self.assertEqual(self.worker.calls,[])

    async def test_plan_binds_exact_bytes_without_execution_and_retains_every_decision(self):
        python=FileApplicability(('**/test_*.py',))
        node=FileApplicability(('**/*.test.mjs',))
        self.jobs.validators={
            'python-tests':RegisteredValidator('Python',self.spec,python),
            'node-tests':RegisteredValidator('Node',ValidationSpec('node-tests',self.spec.image,('/usr/bin/node','--test')),node),
            'manual-test':RegisteredValidator('Manual',ValidationSpec('manual-test',self.spec.image,('/usr/bin/true',)))}
        plan=self.jobs.plan(self.scope,self.session,self.artifact)
        self.assertEqual(plan['artifactSha256'],self.manifest['sha256'])
        self.assertEqual([d['state'] for d in plan['decisions']],['selected','not_applicable','manual_only'])
        self.assertEqual(plan['acceptance'],'not_established_by_file_applicability')
        self.assertEqual(self.worker.calls,[])
        self.assertEqual(self.store.db.execute('select count(*) from artifact_validation_jobs').fetchone()[0],0)
        self.jobs.worker=None
        unavailable=self.jobs.plan(self.scope,self.session,self.artifact)
        self.assertEqual(unavailable['decisions'][0]['state'],'unavailable')
        self.assertEqual(unavailable['selectionStatus'],'no_available_applicable_checks')
        self.assertIsNone(unavailable['decisions'][0]['contractSha256'])
        with self.assertRaises(SessionError):self.jobs.plan(ProjectScope('other-owner','project-one'),self.session,self.artifact)

    async def test_applicability_change_invalidates_contract_without_erasing_old_check(self):
        first=await self.jobs.start(self.scope,self.session,self.artifact,'python-tests');await self.finish()
        self.jobs.validators['python-tests']=RegisteredValidator('Python',self.spec,FileApplicability(('**/test_*.py',)))
        plan=self.jobs.plan(self.scope,self.session,self.artifact)
        self.assertNotEqual(first['contractSha256'],plan['decisions'][0]['contractSha256'])
        second=await self.jobs.start(self.scope,self.session,self.artifact,'python-tests');await self.finish()
        self.assertEqual(second['contractSha256'],plan['decisions'][0]['contractSha256'])
        self.assertEqual(len(self.jobs.list(self.scope,self.session,self.artifact)),2)

    def test_operator_registration_rejects_mutable_images_duplicates_and_extra_policy(self):
        base={'id':'python-tests','label':'Python tests','image':'sha256:'+'a'*64,'command':['/usr/local/bin/python3','-m','unittest']}
        self.assertEqual(registered_validators([base])['python-tests'].label,'Python tests')
        for entries in [[{**base,'image':'python:latest'}],[base,base],[{**base,'privileged':True}],[{**base,'command':'sh -c anything'}]]:
            with self.assertRaises(ValueError):registered_validators(entries)

    async def test_named_placement_runs_only_selected_worker_and_preserves_legacy_contract(self):
        import hashlib
        from dataclasses import asdict,replace
        peer=Worker();peer.identity_digest='amd-worker';peer.policy_digest='amd-policy'
        original=self.jobs._contract(self.catalog[self.spec.name])[0]
        expected={'spec':asdict(self.spec),'workerIdentity':self.worker.identity_digest}
        expected['spec'].pop('executable_scratch')
        self.assertEqual(original,hashlib.sha256(json.dumps({**expected,'policy':self.worker.policy_digest},sort_keys=True).encode()).hexdigest())
        self.jobs.workers={'arm-executor':self.worker,'amd-executor':peer}
        self.assertEqual(self.jobs._contract(self.catalog[self.spec.name])[0],original)
        spec=replace(self.spec,name='named-tests')
        self.jobs.validators['named-tests']=RegisteredValidator('Named AMD checks',spec,worker_id='amd-executor')
        state=await self.jobs.start(self.scope,self.session,self.artifact,'named-tests');await self.finish()
        self.assertEqual(len(peer.calls),1);self.assertEqual(self.worker.calls,[])
        self.assertEqual(state['placement'],{'workerId':'amd-executor'})
        stored=json.loads(self.store.db.execute('SELECT spec FROM artifact_validation_jobs WHERE id=?',(state['id'],)).fetchone()[0])
        self.assertEqual(stored['workerIdentity'],peer.identity_digest);self.assertEqual(stored['workerId'],'amd-executor')
        self.jobs.worker=None
        self.assertTrue(self.jobs.available());self.assertTrue(self.jobs.validator_available('named-tests'))
        self.assertFalse(self.jobs.validator_available('python-tests'))

    async def test_missing_named_worker_never_falls_back_to_configured_default(self):
        self.jobs.validators['python-tests']=RegisteredValidator('Unavailable named check',self.spec,FileApplicability(('**/test_*.py',)),worker_id='missing-executor')
        row=self.jobs.catalog()[0];self.assertFalse(row['available']);self.assertIsNone(row['contractSha256'])
        self.assertEqual(row['placement']['status'],'worker_unavailable')
        self.assertEqual(self.jobs.plan(self.scope,self.session,self.artifact)['decisions'][0]['state'],'unavailable')
        with self.assertRaises(SessionError):await self.jobs.start(self.scope,self.session,self.artifact,'python-tests')
        self.assertEqual(self.worker.calls,[]);self.assertEqual(self.store.db.execute('SELECT count(*) FROM artifact_validation_jobs').fetchone()[0],0)

    async def test_named_observations_must_match_selected_identity_and_policy(self):
        import hashlib
        peer=Worker();peer.identity_digest='d'*64;peer.policy_digest='e'*64
        self.jobs.workers={'observed-executor':peer}
        def register(identity,policy):
            receipt=observation(self.spec);receipt.update(workerIdentitySha256=identity,workerPolicySha256=policy)
            path=self.root/'observed.json';path.write_text(json.dumps(receipt))
            evidence=RuntimeEvidence.load({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()},self.spec)
            self.jobs.validators['python-tests']=RegisteredValidator('Observed named runtime',self.spec,runtime_evidence=evidence,worker_id='observed-executor')
        for identity,policy in [('f'*64,peer.policy_digest),(peer.identity_digest,'f'*64)]:
            register(identity,policy);row=self.jobs.catalog()[0]
            self.assertFalse(row['available']);self.assertIsNone(row['contractSha256']);self.assertNotIn('runtimeEvidence',row)
            self.assertEqual(row['placement']['status'],'runtime_observation_mismatch')
            with self.assertRaises(SessionError):await self.jobs.start(self.scope,self.session,self.artifact,'python-tests')
        self.assertEqual(peer.calls,[]);self.assertEqual(self.worker.calls,[])
        register(peer.identity_digest,peer.policy_digest)
        self.assertTrue(self.jobs.catalog()[0]['available']);self.assertIn('runtimeEvidence',self.jobs.catalog()[0])
        await self.jobs.start(self.scope,self.session,self.artifact,'python-tests');await self.finish()
        self.assertEqual(len(peer.calls),1)

    async def test_named_profile_unavailable_cannot_run_or_use_peer_profile(self):
        peer=Worker();peer.identity_digest='no-browser-worker';peer.supports=lambda spec:False
        self.jobs.workers={'limited-executor':peer}
        self.jobs.validators['python-tests']=RegisteredValidator('No profile fallback',self.spec,worker_id='limited-executor')
        self.assertEqual(self.jobs.catalog()[0]['placement']['status'],'isolation_profile_unavailable')
        with self.assertRaises(SessionError):await self.jobs.start(self.scope,self.session,self.artifact,'python-tests')
        self.assertEqual(peer.calls,[]);self.assertEqual(self.worker.calls,[])

    async def test_legacy_context_bound_receipt_cannot_follow_changed_default_worker(self):
        import hashlib
        from server.tests.test_runtime_evidence import process_observation
        value=process_observation(self.spec);value.update(workerIdentitySha256='a'*64,workerPolicySha256='b'*64)
        path=self.root/'context.json';path.write_text(json.dumps(value))
        evidence=RuntimeEvidence.load({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()},self.spec)
        self.worker.identity_digest='a'*64;self.worker.policy_digest='b'*64
        self.jobs.validators['python-tests']=RegisteredValidator('Observed legacy context',self.spec,runtime_evidence=evidence)
        original=self.jobs.catalog()[0];self.assertTrue(original['available']);self.assertNotIn('placement',original)
        self.worker.identity_digest='c'*64
        changed=self.jobs.catalog()[0];self.assertFalse(changed['available']);self.assertNotIn('runtimeEvidence',changed)
        self.assertEqual(changed['placement']['status'],'runtime_observation_mismatch');self.assertIsNone(changed['contractSha256'])
        with self.assertRaises(SessionError):await self.jobs.start(self.scope,self.session,self.artifact,'python-tests')
        self.assertEqual(self.worker.calls,[])

    async def test_queued_execution_retains_admitted_worker_when_placement_changes(self):
        peer=Worker();peer.identity_digest='replacement-worker'
        self.jobs.workers={'selected-executor':self.worker}
        self.jobs.validators['python-tests']=RegisteredValidator('Queued named runtime',self.spec,worker_id='selected-executor')
        self.jobs.semaphore=asyncio.Semaphore(0)
        state=await self.jobs.start(self.scope,self.session,self.artifact,'python-tests')
        self.jobs.workers['selected-executor']=peer
        self.jobs.semaphore.release();await self.finish()
        self.assertEqual(len(self.worker.calls),1);self.assertEqual(peer.calls,[])
        second=await self.jobs.start(self.scope,self.session,self.artifact,'python-tests');await self.finish()
        self.assertNotEqual(state['contractSha256'],second['contractSha256']);self.assertEqual(len(peer.calls),1)

    async def test_mutated_admitted_worker_fails_closed_before_execution(self):
        self.jobs.semaphore=asyncio.Semaphore(0)
        state=await self.jobs.start(self.scope,self.session,self.artifact,'python-tests')
        self.worker.policy_digest='changed-after-admission'
        self.jobs.semaphore.release();await self.finish()
        self.assertEqual(self.worker.calls,[])
        self.assertEqual(self.jobs.get(self.scope,self.session,state['id'])['result']['reason'],'validator_unavailable')

    async def test_restart_cleanup_follows_saved_worker_even_after_validator_removed_and_default_changed(self):
        peer=Worker();peer.identity_digest='peer-worker'
        self.jobs.workers={'original-executor':self.worker}
        self.jobs.validators['python-tests']=RegisteredValidator('Original placed check',self.spec,worker_id='original-executor')
        state=await self.jobs.start(self.scope,self.session,self.artifact,'python-tests');await self.finish()
        with self.store.db:self.store.db.execute("UPDATE artifact_validation_jobs SET state='running',result=NULL WHERE id=?",(state['id'],))
        self.jobs=ValidationJobs(self.store,self.artifacts,peer,{},workers={'approved-original':self.worker})
        result=await self.jobs.recover(self.scope,self.session,state['id'])
        self.assertEqual(result['result']['reason'],'supervisor_restart');self.assertEqual(self.worker.recovered,[state['id']])
        self.assertEqual(peer.recovered,[]);self.assertEqual(peer.calls,[]);self.assertEqual(len(self.worker.calls),1)

    async def test_legacy_cleanup_can_use_exact_original_identity_after_default_reassignment(self):
        peer=Worker();peer.identity_digest='new-default-worker'
        state=await self.jobs.start(self.scope,self.session,self.artifact,'python-tests');await self.finish()
        with self.store.db:self.store.db.execute("UPDATE artifact_validation_jobs SET state='running',result=NULL WHERE id=?",(state['id'],))
        self.jobs=ValidationJobs(self.store,self.artifacts,peer,self.catalog)
        with self.assertRaises(SessionError):await self.jobs.recover(self.scope,self.session,state['id'])
        self.assertEqual(peer.recovered,[])
        self.jobs.workers['approved-original']=self.worker
        await self.jobs.recover(self.scope,self.session,state['id'])
        self.assertEqual(self.worker.recovered,[state['id']]);self.assertEqual(peer.recovered,[])

    def test_worker_assignment_is_operator_only_and_requires_exact_ids(self):
        base={'id':'python-tests','label':'Placed tests','image':self.spec.image,'command':list(self.spec.command),'workerId':'approved-executor'}
        self.assertEqual(registered_validators([base])['python-tests'].worker_id,'approved-executor')
        for worker in [None,'','../worker','default:any',True]:
            with self.subTest(worker=worker),self.assertRaises(ValueError):registered_validators([{**base,'workerId':worker}])
