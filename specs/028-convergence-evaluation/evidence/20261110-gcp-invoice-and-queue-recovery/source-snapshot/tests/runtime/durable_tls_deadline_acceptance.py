"""Real TLS slow receipt: socket activity must not extend the stage deadline."""
from pathlib import Path
import sys
import time
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(Path(__file__).resolve().parent)]
from durable_postgres_acceptance import DurableFixture
from workflow_tls_destination_fixture import TlsDestinationFixture
from workflow_process_stage import ProcessStage
from workflow_errors import ExternalOutcomeUnknown
from workflow_contract import normalized_contract

class TlsDeadlineTests(DurableFixture,unittest.TestCase):
    def test_external_acceptance_with_continuous_slow_receipt_hits_hard_deadline_and_holds_unknown(self):
        sink=TlsDestinationFixture();sink.mode='slow-receipt'
        try:
            self.store.destination_contract=normalized_contract(sink.url,'synthetic-account');operation=self.approved();row=self.store.claim_dispatch(operation)
            stage=ProcessStage([str(Path(sys.executable).absolute()),'-I',str(Path(__file__).with_name('workflow_stage_child_fixture.py')),'tls'],kind='dispatch',timeout_seconds=1,environment={'DESTINATION_ENDPOINT':sink.url,'DESTINATION_TOKEN':sink.token,'DESTINATION_CA':str(sink.ca_file)})
            start=time.monotonic()
            with self.assertRaises(ExternalOutcomeUnknown):stage(row,idempotency_key=operation,payload_sha256=row['approved_hash'])
            self.assertLess(time.monotonic()-start,2.5);self.assertEqual(len(sink.effects),1);self.assertEqual(len(sink.calls),1)
            self.store.fail(operation,str(row['lease_token']),'destination_unavailable',retryable=True,ambiguous=True)
            self.assertEqual(self.store.get(self.user,operation)['state'],'unknown');self.assertIsNone(self.store.claim_dispatch(operation))
        finally:sink.close()

if __name__=='__main__':unittest.main(verbosity=2)
