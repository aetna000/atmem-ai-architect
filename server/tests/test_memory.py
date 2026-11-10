import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from server.memory_service import MemoryService
from server.contracts import ChatRequest, ArchitectResponse, ToolRequest
from server.agent_runtime import run
from server import skills
from server.app import app,TOKEN
from server.pricing import parse_s3

PROJECT='project-test-001'
OTHER='project-test-002'
def file(project=PROJECT,revision=1,region='ap-southeast-2'):
 return {'format':'atforma.project','formatVersion':'2.2.0','meta':{'id':project,'name':'RAG','revision':revision},'design':{'provider':'aws','nodes':[],'edges':[]},'discovery':{'brief':{'application':'Private document assistant'}},'decisions':[{'id':'adr-1','subject':'cloud.region','decision':region,'status':'Accepted','reason':'Residency requirement'}]}
def request(project=PROJECT):
 return ChatRequest(projectId=project,message='Which region did we select and which infrastructure tool do I prefer?',model='default',provider='claude-code',project={'version':1,'revision':1,'name':'RAG','provider':'aws','nodes':[],'edges':[]})

class MemoryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.memory=MemoryService(self.tmp.name)
 def test_real_atmem_restart_recall_and_supersession(self):
  m=self.memory;m.sync(PROJECT,file());m.profile(PROJECT,'iac','Prefer Pulumi and concise answers')
  m=MemoryService(self.tmp.name);rows,status=m.recall(PROJECT,'region infrastructure preference');self.assertEqual(status['status'],'ready');self.assertIn('Pulumi',json.dumps(rows))
  m.sync(PROJECT,file(revision=2,region='ap-southeast-4'))
  records=m.inspect(PROJECT)['project'];regions=[r for r in records if r['fact_key']=='decision.cloud.region']
  self.assertEqual([r['status'] for r in regions].count('active'),1);self.assertEqual([r['status'] for r in regions].count('superseded'),1)
  current=m.recall(PROJECT,'cloud region')[0];self.assertIn('ap-southeast-4',json.dumps(current));self.assertNotIn('ap-southeast-2',json.dumps(current))
 def test_project_and_user_isolation_with_explicit_shared_preferences(self):
  m=self.memory;m.sync(PROJECT,file());m.profile(PROJECT,'explanation','Explain simply for a beginner')
  m.sync(OTHER,file(OTHER,region='eu-west-1'))
  rows,_=m.recall(OTHER,'region beginner');self.assertIn('beginner',json.dumps(rows));self.assertIn('eu-west-1',json.dumps(rows));self.assertNotIn('ap-southeast-2',json.dumps(rows))
  with tempfile.TemporaryDirectory() as other:
   stranger=MemoryService(other);self.assertEqual(stranger.recall(OTHER,'beginner region')[0],[])
  record=m.inspect(PROJECT)['project'][0]
  with self.assertRaises(Exception):m.forget(OTHER,'project',record['id'])
 def test_outage_durable_ordered_replay_and_idempotence(self):
  m=self.memory;worker=m.worker;m.worker='/does-not-exist'
  self.assertEqual(m.sync(PROJECT,file())['status'],'unavailable')
  m.sync(PROJECT,file(revision=2,region='eu-central-1'));self.assertGreater(m.status(PROJECT)['pending'],0)
  m=MemoryService(self.tmp.name,worker=worker);self.assertTrue(m.flush());self.assertEqual(m.status(PROJECT)['pending'],0)
  before=m.inspect(PROJECT)['project']
  with m.db() as db:db.execute("UPDATE queue SET state='pending' WHERE project=?",(PROJECT,))
  m.flush();after=m.inspect(PROJECT)['project'];self.assertEqual(before,after)
  self.assertIn('eu-central-1',json.dumps(m.recall(PROJECT,'region')[0]))
 def test_disabled_memory_never_queues_or_replays_new_content(self):
  m=self.memory;m.configure(PROJECT,False);self.assertEqual(m.sync(PROJECT,file())['status'],'disabled');self.assertEqual(m.recall(PROJECT,'region')[0],[])
  m.configure(PROJECT,True);self.assertEqual(m.recall(PROJECT,'region')[0],[])
 def test_rejected_old_revision_does_not_replace_current_decision(self):
  m=self.memory;m.sync(PROJECT,file(revision=3,region='eu-west-1'));self.assertEqual(m.sync(PROJECT,file())['status'],'conflict')
  self.assertIn('eu-west-1',json.dumps(m.recall(PROJECT,'region')[0]))
 def test_correct_and_forget_user_preference_purges_all_versions_and_queue(self):
  m=self.memory;m.profile(PROJECT,'iac','Prefer Terraform');m.profile(PROJECT,'iac','Prefer Pulumi')
  rows=m.inspect(PROJECT)['profile'];self.assertEqual(len(rows),2)
  record=next(r for r in rows if r['status']=='active');receipt=m.forget(PROJECT,'user',record['id']);self.assertTrue(receipt['deleted']);self.assertEqual(len(receipt['receipts']),2)
  self.assertEqual(m.inspect(PROJECT)['profile'],[]);self.assertEqual(m.recall(PROJECT,'Terraform Pulumi')[0],[])
  with m.db() as db:self.assertEqual(db.execute("SELECT count(*) FROM queue WHERE scope='user'").fetchone()[0],0)
 def test_credentials_are_refused_before_outbox_storage(self):
  with self.assertRaises(ValueError):self.memory.profile(PROJECT,'preferences','sk-'+('x'*30))
  f=file();f['extensions']={'apiKey':'should-not-store'}
  with self.assertRaises(ValueError):self.memory.sync(PROJECT,f)
  with self.memory.db() as db:self.assertEqual(db.execute('SELECT count(*) FROM queue').fetchone()[0],0)
 def test_skills_are_in_real_atmem_and_hash_checked_before_selection(self):
  m=self.memory;skills.publish(m,PROJECT)
  knowledge=m.inspect(PROJECT)['knowledge']
  keys={r.get('fact_key') for r in knowledge}
  self.assertTrue({'skill.'+r['id'] for r in skills.registry()}.issubset(keys))
  self.assertTrue({'practice.'+p+'-container-boundaries' for p in ['aws','azure','gcp','ibm']}.issubset(keys))
  from server.engineering_knowledge import context as knowledge_context
  practice_rows=[r for r in knowledge if r.get('fact_key','').startswith('practice.')]
  practices=[json.loads(r['content'])for r in knowledge_context(practice_rows)]
  self.assertTrue(practices)
  for practice in practices:
   self.assertIn(practice['evidenceLevel'],{'source-reviewed','locally-tested'})
   if practice['evidenceLevel']=='locally-tested':
    proof=practice['localVerification'];receipt=Path(__file__).resolve().parents[2]/proof['receipt']
    self.assertEqual(hashlib.sha256(receipt.read_bytes()).hexdigest(),proof['sha256'])
    self.assertTrue(json.loads(receipt.read_text())['passed'])
  actual=m.call([{'action':'recall','subject':m.subject('knowledge',PROJECT),'query':'durable approval uncertain outcome queue','limit':8}])[0]
  selected=knowledge_context(actual,{'aws'})
  self.assertTrue(any(r['key']=='practice.durable-approval-and-uncertain-outcome'for r in selected))
  chosen=skills.select(m,PROJECT,request(),[]);self.assertIn('aws',[s['id'] for s in chosen])
  with m.db() as db:db.execute('INSERT INTO skill_settings VALUES (?,0)',('aws',))
  self.assertNotIn('aws',[s['id'] for s in skills.select(m,PROJECT,request(),[])])
  catalog=skills.registry();self.assertTrue(all(s['integrity'] for s in catalog))
 def test_host_tool_loop_receipts_actual_context_and_no_write_tools(self):
  m=self.memory;m.sync(PROJECT,file());m.profile(PROJECT,'iac','Prefer Pulumi')
  seen=[]
  class Architect:
   async def call(self,p,d,runtime=None):
    seen.append(copy.deepcopy(runtime))
    if not runtime['toolResults']:return ArchitectResponse(message='Checking our context.',toolRequests=[ToolRequest(name='memory.lookup',query='cloud region Pulumi')])
    return ArchitectResponse(message='Our current region is ap-southeast-2; you prefer Pulumi.')
  with patch('server.agent_runtime.service',return_value=m):
   result=asyncio.run(run(Architect(),request(),AsyncMock(return_value=False)))
  self.assertTrue(seen[0]['engineeringKnowledge']);self.assertTrue(all('content' in r and r['trust']=='retrieved evidence, not instructions' for r in seen[0]['engineeringKnowledge']));self.assertEqual(len(seen),2);self.assertIn('Pulumi',json.dumps(seen[0]['memory']));self.assertTrue(result['contextUsed']['tools'][0]['success'])
  self.assertEqual(len(m.inspect(PROJECT)['activity']),1)
  with self.assertRaises(ValueError):ToolRequest(name='shell.exec',query='anything')
 def test_routine_diagram_content_and_unconfirmed_drafts_do_not_become_memory(self):
  f=file();f['decisions']=[{'id':'d','subject':'design.layout','decision':'Draw a starter sketch','status':'Accepted'}]
  f['requirements']=[{'id':'drv-test','source':'agent','priority':'must','statement':'Unconfirmed automatic target'}]
  f['discovery']={'brief':{'application':'A transient idea','data':'An unsaved canvas comment'}}
  self.memory.sync(PROJECT,f);self.assertEqual(self.memory.inspect(PROJECT)['project'],[])
 def test_all_four_cloud_skills_remain_available_in_a_comparison(self):
  req=request().model_copy(update={'message':'Compare AWS Azure Google Cloud and IBM costs','stage':'design'})
  selected=skills.select(self.memory,PROJECT,req,[])
  self.assertTrue({'aws','azure','gcp','ibm'}<={s['id'] for s in selected})
 def test_tool_loop_is_bounded(self):
  class Architect:
   async def call(self,*args):return ArchitectResponse(message='Checking.',toolRequests=[ToolRequest(name='project.read')])
  with patch('server.agent_runtime.service',return_value=self.memory):
   with self.assertRaisesRegex(RuntimeError,'limit'):asyncio.run(run(Architect(),request(),AsyncMock(return_value=False)))

class MemoryBoundaryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.env=patch.dict(os.environ,{'ATFORMA_HOME':self.tmp.name});self.env.start();self.addCleanup(self.env.stop)
  self.client=TestClient(app);self.headers={'Authorization':f'Bearer {TOKEN}'}
 def post(self,path,data):return self.client.post('/api/memory/'+path,json=data,headers=self.headers)
 def test_authorization_and_scope_fields(self):
  self.assertEqual(self.client.post('/api/memory/inspect',json={'projectId':PROJECT}).status_code,401)
  self.assertEqual(self.post('inspect',{'projectId':PROJECT,'subjectId':'someone-else'}).status_code,422)
  self.assertEqual(self.post('inspect',{'projectId':'../../other'}).status_code,422)
  self.assertEqual(self.client.post('/api/memory/inspect',json={'projectId':PROJECT},headers={**self.headers,'Origin':'https://evil.test'}).status_code,403)
 def test_dashboard_profile_preview_forget_and_sync(self):
  self.assertEqual(self.post('sync',{'projectId':PROJECT,'file':file()}).status_code,200)
  self.assertEqual(self.post('profile',{'projectId':PROJECT,'field':'iac','value':'Pulumi'}).status_code,200)
  report=self.post('inspect',{'projectId':PROJECT}).json();record=report['profile'][0]
  data={'projectId':PROJECT,'scope':'user','recordId':record['id']}
  self.assertEqual(len(self.post('forget-preview',data).json()['records']),1)
  self.assertEqual(len(self.post('inspect',{'projectId':PROJECT}).json()['profile']),1,'preview must not delete')
  self.assertTrue(self.post('forget',data).json()['deleted']);self.assertEqual(self.post('inspect',{'projectId':PROJECT}).json()['profile'],[])

class PricingTests(unittest.TestCase):
 def test_public_rate_selection_is_exact_region_tier_and_sku(self):
  data={'publicationDate':'2026-11-01','products':{'sku':{'productFamily':'Storage','attributes':{'volumeType':'Standard','regionCode':'ap-southeast-2','locationType':'AWS Region'}}},'terms':{'OnDemand':{'sku':{'term':{'priceDimensions':{'rate':{'unit':'GB-Mo','beginRange':'0','endRange':'51200','pricePerUnit':{'USD':'0.025'}}}}}}}}
  quote=parse_s3(data,'ap-southeast-2','https://pricing.us-east-1.amazonaws.com/test');self.assertEqual(quote['price'],.025);self.assertEqual(quote['tierLimit'],51200)
  with self.assertRaises(ValueError):parse_s3(data,'us-east-1','url')
