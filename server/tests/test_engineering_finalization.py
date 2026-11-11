import asyncio
from pathlib import Path
import tempfile
import unittest
from server.engineering_artifacts import EngineeringArtifacts
from server.engineering_finalization import EngineeringFinalization
from server.engineering_jobs import EngineeringJobs
from server.engineering_sessions import BackendEvent,EngineeringSessions,ModelSelection,ProjectScope,SessionError,SqliteSessionStore
from server.local_validation import ValidationSpec
from server.validation_applicability import FileApplicability
from server.validation_jobs import RegisteredValidator,ValidationJobs
from server.tests.test_engineering_sessions import Backend
from server.tests.test_validation_jobs import Worker


class FinalizationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.workspace=self.root/'work';self.workspace.mkdir()
        (self.workspace/'test_river.py').write_text('original river telemetry code')
        self.store=SqliteSessionStore(self.root/'control.sqlite');self.scope=ProjectScope('local-owner','river-monitor')
        self.backend=Backend()
        async def close():pass
        self.backend.close=close
        self.sessions=EngineeringSessions(self.store,self.backend);self.jobs=EngineeringJobs(self.sessions)
        self.session=(await self.sessions.create(self.scope,'work',ModelSelection('exact-model','high')))['id']
        self.artifacts=EngineeringArtifacts(self.store);self.worker=Worker()
        spec=ValidationSpec('python-tests','sha256:'+'a'*64,('/usr/local/bin/python3','-m','unittest','discover','-v'))
        self.checks=ValidationJobs(self.store,self.artifacts,self.worker,{'python-tests':RegisteredValidator('Python',spec,FileApplicability(('**/test_*.py',)))})
        self.captures=[]
        def capture(scope,session):
            manifest=self.artifacts.capture(scope,session,self.workspace);self.captures.append(manifest);return manifest
        self.capture=capture
        self.finalizer=EngineeringFinalization(self.jobs,capture,lambda:self.checks);self.jobs.on_settled=self.finalizer.observe

    async def asyncTearDown(self):
        self.jobs.on_settled=None;self.worker.release.set()
        await self.finalizer.close();await self.checks.close();await self.jobs.close();self.store.close();self.temp.cleanup()

    async def settle_turn(self,kind='completed'):
        state=await self.jobs.start(self.scope,self.session,'Build a river telemetry service; preserve existing devices.')
        await self.backend.events.put(BackendEvent('native-turn-1',kind))
        for _ in range(100):
            if self.jobs.state(self.scope,self.session)['state']=='idle':break
            await asyncio.sleep(.001)
        return state

    async def finish(self):
        await asyncio.gather(*list(self.finalizer.tasks.values()))
        return self.finalizer.list(self.scope,self.session)[-1]

    async def test_completed_turn_captures_before_next_intent_and_checks_exact_bytes_once(self):
        state=await self.settle_turn();result=await self.finish()
        self.assertEqual(result['state'],'local_checks_passed');self.assertEqual(result['runId'],state['run'])
        self.assertEqual(result['artifact']['sha256'],self.captures[0]['sha256'])
        self.assertEqual(self.worker.calls[0][1],result['artifact']['sha256'])
        self.assertEqual(result['acceptance'],'not_established_by_local_checks')
        self.finalizer.observe(self.scope,self.session);await self.jobs.recover(self.scope,self.session)
        self.assertEqual(len(self.captures),1);self.assertEqual(len(self.worker.calls),1)
        self.assertEqual(self.jobs.journal.read(self.scope,self.session)[-2]['kind'],'finalization_local_checks_passed')

    async def test_interrupted_or_failed_turn_does_not_trigger_capture_or_checks(self):
        await self.settle_turn('interrupted');await self.finish_if_any()
        self.assertEqual(self.finalizer.list(self.scope,self.session),[])
        self.assertEqual(self.captures,[]);self.assertEqual(self.worker.calls,[])

    async def finish_if_any(self):await asyncio.gather(*list(self.finalizer.tasks.values()))

    async def test_failed_incomplete_and_empty_selection_are_never_promoted(self):
        self.checks.validators={}
        await self.settle_turn();result=await self.finish()
        self.assertEqual(result['state'],'needs_attention');self.assertEqual(result['checks'],[])
        self.assertEqual(result['plan']['selectionStatus'],'no_available_applicable_checks')

    async def test_failed_check_retains_report_and_needs_attention(self):
        self.worker.receipt_error=True
        await self.settle_turn();result=await self.finish()
        self.assertEqual(result['state'],'needs_attention')
        check=self.checks.get(self.scope,self.session,result['checks'][0])
        self.assertEqual(check['result']['reason'],'validator_unavailable')
        self.assertEqual(len(self.backend.request_ids),1,'No hidden model repair in this supervisor')

    async def test_new_user_turn_supersedes_older_running_check_without_reusing_its_evidence(self):
        self.worker.release.clear();await self.settle_turn()
        await asyncio.to_thread(self.worker.entered.wait,2)
        old=self.finalizer.list(self.scope,self.session)[0]
        original=self.backend.start
        async def next_turn(*args,**kwargs):
            await original(*args,**kwargs);return 'native-turn-2'
        self.backend.start=next_turn
        await self.jobs.start(self.scope,self.session,'Add flood alerts; keep all earlier scope.')
        self.worker.release.set();result=await self.finish()
        self.assertEqual(result['state'],'superseded')
        self.assertEqual(result['artifact'],old['artifact']);self.assertEqual(len(self.captures),1)
        self.assertNotEqual(self.jobs.state(self.scope,self.session)['run'],result['runId'])

    async def test_capture_failure_does_not_hide_completed_turn_or_expose_host_error(self):
        def broken(*args):raise RuntimeError('/private/operator/credentials')
        self.finalizer.capture=broken
        await self.settle_turn();result=await self.finish()
        self.assertEqual(result['state'],'needs_attention');self.assertIsNone(result['artifact'])
        self.assertEqual(self.jobs.state(self.scope,self.session)['last_status'],'completed')
        self.assertNotIn('/private',str(self.jobs.journal.read(self.scope,self.session)))
        self.assertEqual(self.worker.calls,[])

    async def test_restart_retains_original_check_debt_and_does_not_replay_or_recapture(self):
        self.worker.release.clear();await self.settle_turn();await asyncio.to_thread(self.worker.entered.wait,2)
        await self.finalizer.close();self.worker.release.set();await asyncio.gather(*list(self.checks.tasks.values()))
        self.finalizer=EngineeringFinalization(self.jobs,self.capture,lambda:self.checks);self.jobs.on_settled=self.finalizer.observe
        self.finalizer.observe(self.scope,self.session)
        result=self.finalizer.list(self.scope,self.session)[0]
        self.assertEqual(result['state'],'recovery_required')
        self.assertEqual(len(self.captures),1);self.assertEqual(len(self.worker.calls),1)
        with self.assertRaises(SessionError):self.finalizer.list(ProjectScope('other-owner','river-monitor'),self.session)

    async def test_changed_operator_contract_during_check_keeps_pass_historical(self):
        self.worker.release.clear();await self.settle_turn();await asyncio.to_thread(self.worker.entered.wait,2)
        self.worker.policy_digest='changed-reviewed-policy';self.worker.release.set()
        result=await self.finish()
        self.assertEqual(result['state'],'needs_attention')
        check=self.checks.get(self.scope,self.session,result['checks'][0])
        self.assertEqual(check['result']['status'],'passed')
        self.assertNotEqual(check['contractSha256'],self.checks.catalog()[0]['contractSha256'])

    async def test_lost_terminal_event_recovery_captures_verified_existing_run_once(self):
        await self.jobs.start(self.scope,self.session,'Build a local note service.')
        task=self.jobs.tasks[(self.scope,self.session)];task.cancel();await asyncio.gather(task,return_exceptions=True)
        self.backend.observed=BackendEvent('native-turn-1','completed')
        # The test backend's observe method returns this explicitly supplied event.
        async def observe(*args):return self.backend.observed
        self.backend.observe=observe
        await self.jobs.recover(self.scope,self.session);result=await self.finish()
        self.assertEqual(result['state'],'local_checks_passed');self.assertEqual(len(self.backend.request_ids),1)
