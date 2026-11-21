import hashlib,json,tempfile,unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from hosted.sqlite_store import SQLiteTransactions
from hosted.projects import Profiles,Projects,ProjectUnavailable
from hosted.workspace_projects import WorkspaceProjects
from hosted.workspace_jobs import WorkspaceJobs
from hosted.tests.test_storage_projects import BucketFixture
from hosted.x_access import XIdentity
from hosted.credits import Conflict,CreditError

class WorkspaceJobTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.store=SQLiteTransactions(Path(self.temp.name)/'jobs.sqlite');self.profiles=Profiles(self.store)
  for uid in ['1','2']:self.profiles.register(XIdentity(uid,uid,'User'))
  self.projects=Projects(self.store,self.profiles);self.pid=WorkspaceProjects(self.store,self.profiles,self.projects).create('1','new','Project')['id']
  self.bucket=BucketFixture();self.now=1000;self.jobs=WorkspaceJobs(self.store,self.profiles,self.projects,self.bucket,clock=lambda:self.now)
 def tearDown(self):self.temp.cleanup()
 def submit(self):return self.jobs.submit('1','same-request',self.pid,'/api/architect',{'projectId':self.pid,'message':'Preserve the existing application'})
 def test_owner_submission_is_idempotent_and_foreign_or_unregistered_requests_are_denied(self):
  first=self.submit();self.assertEqual(first['id'],self.submit()['id'])
  with self.assertRaises(ProjectUnavailable):self.jobs.submit('2','other',self.pid,'/api/architect',{})
  with self.assertRaises(ProjectUnavailable):self.jobs.read('2',self.pid,first['id'])
  for path in ['/api/login','/api/credentials','/api/engineering/orca/open','http://169.254.169.254/']:
   with self.assertRaises(CreditError):self.jobs.submit('1',path,self.pid,path,{})
  with self.assertRaises(Conflict):self.jobs.submit('1','same-request',self.pid,'/api/architect',{'message':'Different work'})
 def test_only_one_worker_can_claim_and_expiry_does_not_replay_work(self):
  first=self.submit()
  with ThreadPoolExecutor(max_workers=4) as pool:claims=list(pool.map(lambda n:self.jobs.claim('worker-'+str(n)),range(8)))
  self.assertEqual(sum(row is not None for row in claims),1)
  row=next(row for row in claims if row);self.assertEqual(self.jobs.payload(row)['message'],'Preserve the existing application')
  self.now+=121
  self.assertEqual(self.jobs.read('1',self.pid,first['id'])['state'],'recovery_required')
  self.assertIsNone(self.jobs.claim('replacement'))
  self.jobs.finish(row['id'],row['worker'],{'status':200,'body':{'message':'Verified response'}})
  self.assertEqual(self.jobs.read('1',self.pid,first['id'])['response']['body']['message'],'Verified response')
 def test_changed_or_foreign_worker_response_cannot_replace_a_captured_result(self):
  first=self.submit();row=self.jobs.claim('worker')
  with self.assertRaises(Conflict):self.jobs.finish(first['id'],'other-worker',{'status':200,'body':{}})
  result={'status':200,'body':{'ok':True}};self.jobs.finish(first['id'],'worker',result);self.jobs.finish(first['id'],'worker',result)
  with self.assertRaises(Conflict):self.jobs.finish(first['id'],'worker',{'status':200,'body':{'ok':False}})
  self.assertEqual(self.jobs.read('1',self.pid,first['id'])['response'],result)

 def test_large_responses_download_as_integrity_checked_chunks(self):
  import base64
  self.submit();row=self.jobs.claim('worker')
  response={'status':200,'body':{'files':['preserve complete source '*60000]}}
  self.jobs.finish(row['id'],'worker',response)
  receipt=self.jobs.read('1',self.pid,row['id'])['responseTransfer'];parts=[]
  for part in range(receipt['chunks']):
   result=self.jobs.result_chunk('1',self.pid,row['id'],part);raw=base64.b64decode(result['data'])
   self.assertEqual(hashlib.sha256(raw).hexdigest(),result['sha256']);parts.append(raw)
  raw=b''.join(parts);self.assertEqual(len(raw),receipt['size']);self.assertEqual(hashlib.sha256(raw).hexdigest(),receipt['sha256']);self.assertEqual(json.loads(raw),response)
  with self.assertRaises(ProjectUnavailable):self.jobs.result_chunk('2',self.pid,row['id'],0)

 def test_cancelled_queued_work_never_dispatches_and_running_cancel_is_a_request_until_confirmed(self):
  queued=self.submit();self.jobs.cancel('1',self.pid,queued['id']);self.jobs.cancel('1',self.pid,queued['id'])
  self.assertIsNone(self.jobs.claim('worker'));self.assertEqual(self.jobs.read('1',self.pid,queued['id'])['response']['status'],499)
  second=self.jobs.submit('1','running',self.pid,'/api/architect',{});row=self.jobs.claim('worker')
  with self.assertRaises(ProjectUnavailable):self.jobs.cancel('2',self.pid,row['id'])
  self.assertEqual(self.jobs.cancel('1',self.pid,row['id'])['state'],'running');self.assertTrue(self.jobs.cancellation(row['id'],'worker'))
  self.jobs.finish(row['id'],'worker',{'status':499,'body':{'detail':'Stopped'}})
  self.assertEqual(self.jobs.read('1',self.pid,row['id'])['response']['status'],499)
