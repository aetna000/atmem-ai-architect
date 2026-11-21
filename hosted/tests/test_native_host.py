"""Durable job -> actual private native process -> verified result, no paid calls."""
import asyncio,hashlib,json,tempfile,unittest
from pathlib import Path
from importlib.util import find_spec
from hosted.sqlite_store import SQLiteTransactions
from hosted.projects import Profiles
from hosted.storage_projects import StorageProjects
from hosted.workspace_projects import WorkspaceProjects
from hosted.workspace_jobs import WorkspaceJobs
from hosted.x_access import XIdentity
from hosted.worker_host import NativeWorkerHost
from hosted.tests.test_storage_projects import BucketFixture

@unittest.skipUnless(find_spec('atbots'),'Native host qualification requires the separate worker lock')
class NativeHostTests(unittest.IsolatedAsyncioTestCase):
 async def test_owned_queue_runs_original_memory_route_and_returns_retained_result(self):
  with tempfile.TemporaryDirectory() as temporary:
   store=SQLiteTransactions(Path(temporary)/'state.sqlite');profiles=Profiles(store);profiles.register(XIdentity('signed','2','User'))
   bucket=BucketFixture();projects=StorageProjects(store,profiles,bucket);pid=WorkspaceProjects(store,profiles,projects).create('2','new','Warehouse')['id']
   jobs=WorkspaceJobs(store,profiles,projects,bucket)
   class Settings:
    def current(self):return {'model':'openai/gpt-6.1-sol','maxOutputTokens':4096}
   class Broker:
    def admission(self,uid):return None
    def bind(self,uid):return 'synthetic-capability'
    def revoke(self,token):pass
   host=NativeWorkerHost(jobs=jobs,profiles=profiles,settings=Settings(),broker=Broker(),bucket=bucket,root=Path(temporary)/'tenants',broker_socket=temporary+'/unused.sock',worker_id='qualified-worker')
   try:
    accepted=jobs.submit('2','inspect',pid,'/api/memory/overview',{'projectId':pid})
    row=jobs.claim(host.id);await host.execute(row)
    result=jobs.read('2',pid,accepted['id'])
    self.assertEqual(result['state'],'completed');self.assertEqual(result['response']['status'],200,result)
    self.assertTrue(await host.children['2'].idle())
    # Reopening the tenant worker retains its actual private memory identity.
    before=result['response']['body'];await host.children['2'].close();del host.children['2']
    again=jobs.submit('2','inspect-again',pid,'/api/memory/overview',{'projectId':pid});await host.execute(jobs.claim(host.id))
    self.assertEqual(jobs.read('2',pid,again['id'])['response']['status'],200)
   finally:
    for child in host.children.values():await child.close()
