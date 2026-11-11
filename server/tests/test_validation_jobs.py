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

    def test_operator_registration_rejects_mutable_images_duplicates_and_extra_policy(self):
        base={'id':'python-tests','label':'Python tests','image':'sha256:'+'a'*64,'command':['/usr/local/bin/python3','-m','unittest']}
        self.assertEqual(registered_validators([base])['python-tests'].label,'Python tests')
        for entries in [[{**base,'image':'python:latest'}],[base,base],[{**base,'privileged':True}],[{**base,'command':'sh -c anything'}]]:
            with self.assertRaises(ValueError):registered_validators(entries)
