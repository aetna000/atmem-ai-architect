"""Actual child deadlines/output caps/process-group cleanup; no cloud claims."""
import os
from pathlib import Path
import sys
import tempfile
import subprocess
import time
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src/runtime'))
from workflow_process_stage import ProcessStage
from workflow_errors import TemporaryWork,ExternalOutcomeUnknown

class ProcessStageTests(unittest.TestCase):
    def stage(self,mode,*,kind='extract',extra=(),deadline=.4):
        return ProcessStage([str(Path(sys.executable).absolute()),'-I',str(Path(__file__).with_name('workflow_stage_child_fixture.py')),mode,*extra],kind=kind,timeout_seconds=deadline)
    def row(self):return {'id':uuid.uuid4(),'account_id':uuid.uuid4(),'kind':'document','source_ref':{'sha256':'a'*64},'result':None,'lease_token':'MUST_STAY_INSIDE_PARENT','dsn':'PRIVATE_DSN'}
    def test_explicit_bounded_json_transport_does_not_inherit_credentials_or_lease_tokens(self):
        os.environ['ATMEM_TEST_PARENT_SECRET']='PRIVATE_PARENT_CREDENTIAL'
        try:result=self.stage('echo')(self.row())
        finally:os.environ.pop('ATMEM_TEST_PARENT_SECRET',None)
        self.assertIsNone(result['inherited_secret']);self.assertNotIn('lease_token',result['operation']);self.assertNotIn('dsn',result['operation']);self.assertEqual(result['operation']['kind'],'document')
    def test_hung_stage_is_killed_by_a_real_wall_clock_deadline(self):
        start=time.monotonic()
        with self.assertRaises(TemporaryWork):self.stage('hang')(self.row())
        self.assertLess(time.monotonic()-start,2)
    def test_output_flood_is_bounded_and_raw_child_errors_are_not_exposed(self):
        for mode in ['flood','invalid','crash']:
            with self.subTest(mode=mode):
                with self.assertRaises(TemporaryWork)as caught:self.stage(mode)(self.row())
                self.assertNotIn('PRIVATE_PROVIDER_RESPONSE',str(caught.exception))
    def test_deadline_kills_descendant_before_it_can_write_after_parent_exit(self):
        with tempfile.TemporaryDirectory()as folder:
            control=Path(folder)/'control'
            subprocess.run([sys.executable,'-I',str(Path(__file__).with_name('workflow_stage_child_fixture.py')),'marker',str(control)],stdin=subprocess.DEVNULL,check=True,timeout=3)
            self.assertEqual(control.read_text(),'escaped')
            marker=Path(folder)/'escaped'
            with self.assertRaises(TemporaryWork):self.stage('descendant',extra=(str(marker),))(self.row())
            time.sleep(1.1);self.assertFalse(marker.exists())
    def test_dispatch_deadline_after_acceptance_is_unknown_even_with_verified_replay(self):
        with tempfile.TemporaryDirectory()as folder:
            marker=Path(folder)/'accepted';stage=self.stage('receipt',kind='dispatch',extra=(str(marker),));stage.idempotency_verified=True
            with self.assertRaises(ExternalOutcomeUnknown):stage(self.row(),idempotency_key=str(uuid.uuid4()),payload_sha256='a'*64)
            self.assertEqual(marker.read_text(),'accepted')
    def test_invalid_configuration_cannot_pass_model_text_to_a_shell_or_unbounded_deadline(self):
        for command,timeout in [(['python','-c','pass'],1),([sys.executable],float('nan')),([sys.executable],float('inf')),([sys.executable],301)]:
            with self.subTest(command=command,timeout=timeout):
                with self.assertRaises(ValueError):ProcessStage(command,kind='extract',timeout_seconds=timeout)

if __name__=='__main__':unittest.main(verbosity=2)
