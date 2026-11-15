"""Pilot transactions against the real local Firestore emulator.

Object data uses the explicitly named fixture; cloud IAM and X OAuth are separate.
"""
import base64
import hashlib
import os
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from hosted.credits import CreditLedger, Conflict
from hosted.firestore_store import FirestoreTransactions
from hosted.projects import Profiles, ProjectUnavailable
from hosted.storage_projects import StorageProjects
from hosted.x_access import XIdentity, XWhitelist
from hosted.auth import Forbidden
from hosted.tests.test_storage_projects import BucketFixture


class PilotConfigurationTests(unittest.TestCase):
    def test_production_rejects_each_emulator_before_opening_cloud_clients(self):
        from hosted.pilot_api import configured_pilot_app
        for variable in ['FIRESTORE_EMULATOR_HOST', 'FIREBASE_AUTH_EMULATOR_HOST', 'STORAGE_EMULATOR_HOST']:
            with self.subTest(variable=variable), patch.dict(os.environ, {
                'ARCHITECT_DATA_ENVIRONMENT':'production', variable:'127.0.0.1:9999',
            }, clear=True), patch.object(FirestoreTransactions, 'configured') as client:
                with self.assertRaisesRegex(ValueError, 'Production cannot use Firebase emulators'):
                    configured_pilot_app()
                client.assert_not_called()

    def test_sandbox_and_production_use_distinct_metadata_and_blob_namespaces(self):
        from hosted.pilot_api import configured_pilot_app
        from types import SimpleNamespace
        from google.cloud import storage
        seen=[]
        for environment in ['sandbox', 'production']:
            with patch.dict(os.environ, {
                'ARCHITECT_DATA_ENVIRONMENT':environment, 'ARCHITECT_GOOGLE_PROJECT':'demo-architect-hosted',
                'ARCHITECT_FIRESTORE_DATABASE':'(default)', 'ARCHITECT_ADMIN_X_IDS':'1',
                'ARCHITECT_FIREBASE_STORAGE_BUCKET':'synthetic-bucket',
            }, clear=True), patch.object(FirestoreTransactions, 'configured', return_value=SimpleNamespace(client=object())), \
                patch('hosted.pilot_api.FirebaseXIdentity'), patch.object(storage, 'Client'), \
                patch('hosted.pilot_api.create_pilot_app', side_effect=lambda services:services):
                services=configured_pilot_app()
                self.assertIsInstance(services.store, FirestoreTransactions)
                self.assertIsInstance(services.projects, StorageProjects)
                self.assertEqual(services.store.namespace, services.projects.object_prefix)
                self.assertFalse(services.managed_ai_ready)
                seen.append(services.store.namespace)
        self.assertEqual(seen, ['architect_pilot_sandbox','architect_pilot_production'])


@unittest.skipUnless(os.environ.get('FIRESTORE_EMULATOR_HOST'), 'Explicit local Firestore emulator required')
class FirebasePilotTests(unittest.TestCase):
    def setUp(self):
        from google.cloud import firestore
        self.client=firestore.Client(project='demo-architect-hosted')
        self.namespace='pilot_test_'+uuid.uuid4().hex[:16]
        self.store=FirestoreTransactions(self.client,namespace=self.namespace)
        self.profiles=Profiles(self.store)
        self.owner=XIdentity('firebase-owner','1','AtMem')
        self.alice=XIdentity('firebase-alice','2','Alice')
        self.bob=XIdentity('firebase-bob','3','Bob')
        for actor in [self.owner,self.alice,self.bob]:self.profiles.register(actor)

    def tearDown(self):
        for collection in self.client.collections():
            if collection.id.startswith(self.namespace+'_'):
                for snapshot in collection.stream():snapshot.reference.delete()
        self.client.close()

    def test_concurrent_signup_is_one_grant_per_x_id_after_firebase_uid_recreation(self):
        def register(index):
            actor=XIdentity('recreated-firebase-'+str(index),'2','Alice')
            self.profiles.register(actor)
            return CreditLedger(self.store,welcome_units=20_000_000,policy_version='pilot').register(actor.uid)
        with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(register,range(8)))
        self.assertTrue(all(result['available']==20_000_000 for result in results))
        recovered=FirestoreTransactions(self.client,namespace=self.namespace)
        self.assertEqual(Profiles(recovered).get('2')['xId'],'2')
        self.assertEqual(CreditLedger(recovered,welcome_units=99,policy_version='changed').register('2')['available'],20_000_000)

    def test_whitelist_revocation_survives_service_reconstruction(self):
        access=XWhitelist(self.store,admin_ids=['1'],initial_ids=['2'])
        self.assertFalse(access.authorize(self.alice).admin)
        access.update(self.owner,'2',allowed=False,role='user',revision=0)
        recovered=XWhitelist(FirestoreTransactions(self.client,namespace=self.namespace),admin_ids=['1'],initial_ids=['2'])
        with self.assertRaises(Forbidden):recovered.authorize(self.alice)
        with self.assertRaises(Forbidden):recovered.authorize(XIdentity('spoof','3','AtMem',admin=True))

    def test_storage_metadata_commit_cancel_and_delete_use_real_firestore_transactions(self):
        bucket=BucketFixture()
        projects=StorageProjects(self.store,self.profiles,bucket,object_prefix='synthetic_pilot')
        raw=b'{"domain":"legal","requirements":["Preserve signed obligations"]}'
        sha=hashlib.sha256(raw).hexdigest()
        def begin(request):return projects.begin('2',request,title='Legal',size=len(raw),sha256=sha)
        upload=begin('save')
        projects.put_chunk('2',upload['id'],0,base64.b64encode(raw).decode(),sha)
        saved=projects.complete('2',upload['id'])
        recovered=StorageProjects(FirestoreTransactions(self.client,namespace=self.namespace),self.profiles,bucket,object_prefix='synthetic_pilot')
        self.assertEqual(recovered.download('2',saved['id'])[1],raw)
        with self.assertRaises(ProjectUnavailable):recovered.download('3',saved['id'])
        pending=begin('cancel');recovered.cancel('2',pending['id'])
        self.assertEqual(recovered.list('2')['reservedBytes'],0)
        with self.assertRaises(Conflict):recovered.remove('2',saved['id'],99)
        recovered.remove('2',saved['id'],1)
        self.assertEqual(recovered.list('2')['usedBytes'],0)

    def test_native_job_claim_and_large_receipt_use_real_firestore_transactions(self):
        from hosted.workspace_jobs import WorkspaceJobs
        from hosted.workspace_projects import WorkspaceProjects
        bucket=BucketFixture();projects=StorageProjects(self.store,self.profiles,bucket,object_prefix='synthetic_workspace')
        pid=WorkspaceProjects(self.store,self.profiles,projects).create('2','native-new','Warehouse')['id']
        jobs=WorkspaceJobs(self.store,self.profiles,projects,bucket)
        accepted=jobs.submit('2','native-chat',pid,'/api/architect',{'projectId':pid,'message':'Preserve existing warehouse systems'})
        row=jobs.claim('native-worker');self.assertEqual(row['id'],accepted['id']);self.assertIsNone(jobs.claim('other-worker'))
        response={'status':200,'body':{'message':'Complete response '*50000}}
        jobs.finish(row['id'],'native-worker',response)
        received=jobs.read('2',pid,row['id']);self.assertIn('responseTransfer',received)
        with self.assertRaises(ProjectUnavailable):jobs.read('3',pid,row['id'])
