"""Capability/ownership/replay tests; fake executor is not runtime acceptance."""
import asyncio,copy,json
from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
from server.engineering_tools import EngineeringTools
from server.engineering_artifacts import EngineeringArtifacts
from server.engineering_sessions import ModelSelection,ProjectScope,SessionError,SqliteSessionStore
from server.validation_jobs import ValidationJobs,RegisteredValidator
from server.local_validation import ValidationSpec
from server.tests.test_validation_jobs import Worker

class EngineeringToolTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.store=SqliteSessionStore(self.root/'control.sqlite');self.scope=ProjectScope('local-owner','project-one');self.workspace='workspace-one';self.session=self.store.create(self.scope,self.workspace,'backend','private-native-handle',ModelSelection('selected-model','high'))['id'];self.artifacts=EngineeringArtifacts(self.store);self.worker=Worker()
  self.checks=ValidationJobs(self.store,self.artifacts,self.worker,{'local-tests':RegisteredValidator('Synthetic local tests',ValidationSpec('local-tests','sha256:'+'a'*64,('/usr/local/bin/python3','-m','unittest','discover','-v')))})
  self.tools=EngineeringTools(self.store,self.artifacts,lambda:self.checks);self.receipt=self.tools.register(self.scope,self.workspace)
  self.store.reserve(self.scope,self.session,'run-one','Initial work');self.store.attach_turn(self.scope,self.session,'run-one','turn-one');self.counter=0
 async def asyncTearDown(self):
  await self.checks.close();self.store.close();self.temp.cleanup()
 async def call(self,tool,args,identity=None):
  self.counter+=1
  return await self.tools.invoke(self.scope,self.workspace,'turn-one',identity or 'call-'+str(self.counter),tool,args)
 def value(self,result):return json.loads(result['contentItems'][0]['text'])
 async def test_complete_pinned_knowledge_transfer_and_provider_filters(self):
  for provider in ['aws','azure','gcp','ibm']:
   found=self.value(await self.call('atmem_knowledge_search',{'query':'identity authorization container','providers':[provider]}))
   self.assertTrue(found['results']);self.assertEqual(found['snapshotSha256'],self.receipt['knowledgeSnapshotSha256'])
   for row in found['results']:self.assertIn(row['provider'],[provider,'portable'])
   selected=self.value(await self.call('atmem_knowledge_read',{'id':found['results'][0]['id']}))
   self.assertTrue(selected['complete']);self.assertEqual(selected['sha256'],found['results'][0]['sha256']);self.assertIn('source',selected['record']);self.assertIn('practice',selected['record'])
  self.assertFalse((await self.call('atmem_knowledge_search',{'query':'x','providers':['unapproved']}))['success'])
 async def test_no_truncation_and_changed_or_revoked_records_are_not_substituted(self):
  import server.engineering_tools as module
  rows=module.records();long=copy.deepcopy(rows[0]);long['practice']='Complete reviewed evidence. '*300
  with patch.object(module,'records',return_value=[long]):
   # A separate registered workspace avoids changing the existing pinned input.
   self.store.db.execute("UPDATE engineering_sessions SET workspace='workspace-long' WHERE id=?",(self.session,));self.store.db.commit();self.workspace='workspace-long';self.tools.register(self.scope,self.workspace)
   value=self.value(await self.call('atmem_knowledge_read',{'id':long['id']}));self.assertEqual(value['record']['practice'],long['practice']);self.assertGreater(len(value['record']['practice']),3000)
  with patch.object(module,'records',return_value=rows):self.assertFalse((await self.call('atmem_knowledge_read',{'id':long['id']}))['success'])
 async def test_foreign_turn_scope_workspace_and_raw_execution_inputs_fail_closed(self):
  for scope,workspace,turn in [(ProjectScope('other-owner','project-one'),self.workspace,'turn-one'),(self.scope,'foreign-workspace','turn-one'),(self.scope,self.workspace,'old-turn')]:
   with self.assertRaises(SessionError):await self.tools.invoke(scope,workspace,turn,'call','atmem_check_catalog',{})
  for tool,args in [('atmem_check_catalog',{'command':['rm','-rf','/']}),('atmem_check_start',{'artifactId':'x','validatorId':'local-tests','image':'evil'}),('atmem_knowledge_read',{'id':'../private-file'})]:self.assertFalse((await self.call(tool,args))['success'])
  self.assertEqual(self.worker.calls,[])
 async def test_durable_check_identity_exact_artifact_and_paged_output(self):
  # Keep control storage outside the captured source.
  source=self.root/'source';source.mkdir();(source/'test_example.py').write_text('pass')
  self.store.terminal(self.scope,self.session,'run-one','turn-one','completed');manifest=self.artifacts.capture(self.scope,self.session,source)
  self.store.reserve(self.scope,self.session,'run-two','Repair');self.store.attach_turn(self.scope,self.session,'run-two','turn-two')
  args={'artifactId':manifest['id'],'validatorId':'local-tests'}
  async def call(identity,tool,arguments):return await self.tools.invoke(self.scope,self.workspace,'turn-two',identity,tool,arguments)
  first=await call('native-call','atmem_check_start',args);again=await call('native-call','atmem_check_start',args);self.assertEqual(first,again)
  job=self.value(first);await asyncio.gather(*list(self.checks.tasks.values()));self.assertEqual(len(self.worker.calls),1)
  data=self.checks.get(self.scope,self.session,job['id'])['result'];data['output']='é'*17000;self.checks._settle(job['id'],data)
  text='';offset=0
  for index in range(3):
   value=self.value(await call('page-'+str(index),'atmem_check_read',{'checkId':job['id'],'offset':offset}));self.assertEqual(value['artifactSha256'],manifest['sha256']);page=value['result']['outputPage'];text+=page['text'];offset=page['nextOffset']
  self.assertEqual(text,data['output']);self.assertIsNone(offset)
  with self.assertRaises(SessionError):await call('native-call','atmem_check_start',{**args,'validatorId':'different'})
  self.store.db.execute("UPDATE engineering_tool_calls SET state='reserved',result=NULL WHERE call='native-call'");self.store.db.commit()
  uncertain=await call('native-call','atmem_check_start',args);self.assertFalse(uncertain['success']);self.assertEqual(len(self.worker.calls),1)
  restarted=EngineeringTools(self.store,self.artifacts,lambda:self.checks);self.assertFalse((await restarted.invoke(self.scope,self.workspace,'turn-two','native-call','atmem_check_start',args))['success']);self.assertEqual(len(self.worker.calls),1)
 async def test_working_files_are_not_implicitly_captured_and_foreign_artifacts_denied(self):
  self.assertEqual(self.value(await self.call('atmem_check_artifacts',{}))['artifacts'],[])
  for args in [{'artifactId':'foreign-artifact','validatorId':'local-tests'},{'artifactId':'x','validatorId':'unknown'}]:self.assertFalse((await self.call('atmem_check_start',args))['success'])
  self.assertFalse((await self.call('atmem_check_read',{'checkId':'foreign-check'}))['success']);self.assertEqual(self.worker.calls,[])
