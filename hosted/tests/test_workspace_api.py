"""Actual ASGI API plus durable fixtures; not a deployed-system claim."""
import base64,hashlib,json,tempfile,unittest
from pathlib import Path
import httpx
from hosted.sqlite_store import SQLiteTransactions
from hosted.projects import Profiles,Projects,CHUNK_BYTES
from hosted.workspace_jobs import WorkspaceJobs,transfer_store
from hosted.pilot_api import PilotServices,create_pilot_app
from hosted.x_access import XWhitelist
from hosted.tests.test_pilot import XIdentityFixture,catalog_fixture
from hosted.pilot_settings import OpenRouterCatalog
from hosted.tests.test_storage_projects import BucketFixture

class WorkspaceApiTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.temp=tempfile.TemporaryDirectory();store=SQLiteTransactions(Path(self.temp.name)/'api.sqlite');profiles=Profiles(store)
  self.jobs=WorkspaceJobs(store,profiles,Projects(store,profiles),BucketFixture())
  transfers=transfer_store(store,profiles,BucketFixture(),'workspace_transfers')
  services=PilotServices(store,XIdentityFixture(),XWhitelist(store,admin_ids=['1'],initial_ids=['2','3']),catalog=OpenRouterCatalog(fetch=catalog_fixture),projects=self.jobs.projects,workspace_jobs=self.jobs,workspace_transfers=transfers)
  self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=create_pilot_app(services)),base_url='https://example.test')
  await self.call('POST','/profile');await self.call('POST','/profile',user='bob')
  self.pid=(await self.call('POST','/workspace/projects/new',json={'requestId':'new'})).json()['id']
 async def asyncTearDown(self):await self.client.aclose();self.temp.cleanup()
 async def call(self,method,path,user='alice',**kwargs):return await self.client.request(method,'/api/ai-architect'+path,headers={'Authorization':'Bearer '+user},**kwargs)
 async def test_owned_native_job_roundtrips_and_revoked_access_cannot_poll(self):
  request={'requestId':'design','projectId':self.pid,'path':'/api/architect','body':{'projectId':self.pid,'message':'Keep the full application'}}
  submitted=await self.call('POST','/workspace/jobs',json=request);self.assertEqual(submitted.status_code,200,submitted.text);job=submitted.json()
  claimed=self.jobs.claim('native-worker');self.assertEqual(self.jobs.payload(claimed)['message'],request['body']['message'])
  self.jobs.finish(job['id'],'native-worker',{'status':200,'body':{'message':'actual fixture output'}})
  path=f'/workspace/projects/{self.pid}/jobs/{job["id"]}'
  self.assertEqual((await self.call('GET',path)).json()['response']['body']['message'],'actual fixture output')
  self.assertEqual((await self.call('GET',path,user='bob')).status_code,404)
  self.assertEqual((await self.call('POST','/workspace/jobs',json={**request,'path':'/api/credentials'})).status_code,400)
  revoked=await self.call('PUT','/admin/whitelist/2',user='owner',json={'revision':0,'allowed':False,'role':'user'})
  self.assertEqual(revoked.status_code,200);self.assertEqual((await self.call('GET',path)).status_code,403)
 async def test_large_request_uses_verified_chunks_without_truncation(self):
  content={'projectId':self.pid,'files':[{'name':'main.tf','content':'# preserve complete source\n'*80000}]};raw=json.dumps(content).encode()
  upload=(await self.call('POST','/workspace/transfers',json={'requestId':'large','size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})).json()
  for part,start in enumerate(range(0,len(raw),CHUNK_BYTES)):
   chunk=raw[start:start+CHUNK_BYTES];response=await self.call('PUT',f'/workspace/transfers/{upload["id"]}/parts/{part}',json={'data':base64.b64encode(chunk).decode(),'sha256':hashlib.sha256(chunk).hexdigest()});self.assertEqual(response.status_code,200,response.text)
  transfer=(await self.call('POST',f'/workspace/transfers/{upload["id"]}/complete')).json()
  response=await self.call('POST','/workspace/jobs',json={'requestId':'validate','projectId':self.pid,'path':'/api/terraform/validate','transferId':transfer['id']});self.assertEqual(response.status_code,200,response.text)
  job=self.jobs.claim('native-worker');self.assertEqual(self.jobs.payload(job),content)
  self.assertEqual((await self.call('POST','/workspace/jobs',user='bob',json={'requestId':'stolen','projectId':self.pid,'path':'/api/terraform/validate','transferId':transfer['id']})).status_code,404)

 async def test_native_session_refreshes_do_not_consume_signup_admission_or_repeat_credit_grants(self):
  for _ in range(15):
   response=await self.call('GET','/workspace/session');self.assertEqual(response.status_code,200,response.text)
  data=response.json();self.assertEqual(data['ai']['model'],'openai/gpt-6.1-sol');self.assertTrue(data['ai']['workspaceAvailable'])
  profile=await self.call('POST','/profile');self.assertEqual(profile.status_code,200);self.assertEqual(profile.json()['balanceMicros'],20000000)
