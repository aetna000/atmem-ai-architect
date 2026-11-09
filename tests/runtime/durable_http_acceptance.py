"""Actual TLS/HTTP normalized action adapter, scoped to a synthetic destination."""
from pathlib import Path
import ssl
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(Path(__file__).resolve().parent)]
from approved_http_destination import ApprovedHttpDestination
from workflow_errors import ExternalOutcomeUnknown,DestinationNotAttempted,InvalidDispatch
from durable_postgres_acceptance import DurableFixture
from workflow_tls_destination_fixture import TlsDestinationFixture

class ApprovedHttpTests(DurableFixture,unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass();cls.destination=TlsDestinationFixture()
    @classmethod
    def tearDownClass(cls):cls.destination.close()
    def setUp(self):
        super().setUp();self.store.destination_contract=self.client().contract
        with self.destination.lock:self.destination.calls.clear();self.destination.effects.clear();self.destination.mode='completed'
    def client(self,credential=None):return ApprovedHttpDestination(self.destination.url,credential or(lambda:self.destination.token),destination_scope='synthetic-account',idempotency_verified=True,tls_context=self.destination.context)
    def lease(self):
        operation=self.approved();return self.store.claim_dispatch(operation)
    def call(self,client,row):return client(row,idempotency_key=str(row['id']),payload_sha256=row['approved_hash'])
    def test_actual_tls_receipt_and_repeated_http_request_create_one_external_effect(self):
        row=self.lease();client=self.client();first=self.call(client,row);second=self.call(client,row)
        self.assertEqual(first,second);self.assertEqual(len(self.destination.calls),2);self.assertEqual(len(self.destination.effects),1);self.assertEqual(first['operationId'],str(row['id']))
        sent=self.store.record_sent(str(row['id']),str(row['lease_token']),first);self.assertEqual(sent['state'],'sent')
    def test_unapproved_changed_or_disallowed_payload_never_reaches_the_tls_destination(self):
        row=self.lease();client=self.client()
        for changed in [{**row,'state':'review'},{**row,'kind':'account_change'},{**row,'result':{'supplier':'tampered after approval'}}]:
            with self.assertRaises(InvalidDispatch):self.call(client,changed)
        self.assertEqual(self.destination.calls,[])
    def test_changed_destination_account_or_endpoint_cannot_receive_an_old_approval(self):
        row=self.lease()
        for endpoint,scope in [(self.destination.url,'different-account'),(self.destination.url+'/changed','synthetic-account')]:
            client=ApprovedHttpDestination(endpoint,lambda:self.destination.token,destination_scope=scope,tls_context=self.destination.context)
            with self.assertRaises(InvalidDispatch):self.call(client,row)
        self.assertEqual(self.destination.calls,[])
    def test_202_or_wrong_receipt_cannot_be_reported_as_a_completed_action(self):
        row=self.lease()
        for mode in ['pending','wrong-receipt']:
            self.destination.mode=mode
            with self.assertRaises(ExternalOutcomeUnknown):self.call(self.client(),row)
    def test_tls_verification_cannot_be_disabled_and_untrusted_certificates_fail_closed(self):
        context=ssl._create_unverified_context()
        with self.assertRaises(ValueError):ApprovedHttpDestination(self.destination.url,lambda:self.destination.token,destination_scope='synthetic-account',tls_context=context)
        with self.assertRaises(ExternalOutcomeUnknown):self.call(ApprovedHttpDestination(self.destination.url,lambda:self.destination.token,destination_scope='synthetic-account'),self.lease())
        self.assertEqual(self.destination.calls,[])
    def test_missing_credentials_are_distinguished_from_an_attempt_with_lost_acknowledgement(self):
        row=self.lease()
        def unavailable():raise RuntimeError('PRIVATE_SECRET_BACKEND_ERROR')
        with self.assertRaises(DestinationNotAttempted):self.call(self.client(unavailable),row)
        self.assertEqual(self.destination.calls,[])
    def test_invalid_bearer_credential_cannot_authorize_a_normalized_action(self):
        with self.assertRaises(ExternalOutcomeUnknown):self.call(self.client(lambda:'wrong-token'),self.lease())
        self.assertEqual(self.destination.effects,{})

if __name__=='__main__':unittest.main(verbosity=2)
