"""Native Pydantic tool-loop fixture; no paid provider request or cloud claim."""
import os
os.environ['PYDANTIC_AI_NO_BANNER']='1'
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import tempfile
import unittest
from server.atbots_engineering_backend import AtBotsEngineeringBackend,WorkspaceFiles
from server.engineering_sessions import ProjectScope,ModelSelection

class NativeEngineeringTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  from pydantic_ai.models.function import FunctionModel
  from pydantic_ai.messages import ModelResponse,ToolCallPart,TextPart
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'project';self.root.mkdir();self.scope=ProjectScope('tenant-one','project-one');self.selection=ModelSelection('vendor/native-test','medium')
  def step(messages,info):
   if len(messages)==1:return ModelResponse(parts=[ToolCallPart('write_file',{'path':'src/main.py','content':'def main():\n    return "preserved requirements"\n'},tool_call_id='write-one')])
   return ModelResponse(parts=[TextPart('1 file generated. Run registered checks next.')])
  @asynccontextmanager
  async def model(scope,turn,selection):yield FunctionModel(step)
  self.backend=AtBotsEngineeringBackend({(self.scope,'workspace'):self.root},state_path=Path(self.temp.name)/'state.sqlite',model_factory=model,instructions='Preserve requirements; use approved file tools.')
 async def asyncTearDown(self):await self.backend.close();self.temp.cleanup()
 async def test_native_sdk_uses_file_tool_and_emits_real_progress_and_completion(self):
  handle=await self.backend.create(self.scope,'workspace',self.selection)
  turn=await self.backend.start(self.scope,handle,'Implement the saved design',self.selection,request_id='request-one')
  events=[]
  while True:
   event=await asyncio.wait_for(self.backend.next_event(self.scope,handle),10);events.append(event)
   if event.kind in {'completed','failed','interrupted'}:break
  self.assertEqual(events[-1].kind,'completed',repr(getattr(self.backend,'last_error',None)));self.assertIn('Updated src/main.py',[event.text for event in events])
  self.assertIn('preserved requirements',(self.root/'src/main.py').read_text())
  recovered=await self.backend.recover_start(self.scope,handle,'request-one');self.assertEqual(recovered.turn,turn)
  with self.assertRaises(Exception):await self.backend.resume(ProjectScope('tenant-other','project-one'),handle,'workspace',self.selection)
 async def test_immediate_interrupt_does_not_leave_a_permanently_running_turn(self):
  handle=await self.backend.create(self.scope,'workspace',self.selection)
  turn=await self.backend.start(self.scope,handle,'Implement',self.selection,request_id='interrupt')
  await self.backend.interrupt(self.scope,handle,turn)
  terminal=await self.backend.observe(self.scope,handle,turn);self.assertEqual(terminal.kind,'interrupted')
 async def test_explicit_interrupt_reconciles_a_dead_turn_without_model_replay(self):
  handle=await self.backend.create(self.scope,'workspace',self.selection);turn='crashed-native-turn'
  with self.backend.db:self.backend.db.execute('INSERT INTO atbots_turns VALUES (?,?,?,?,?,?,?)',(turn,handle,handle+'\0before-restart','running','Original intent','null','[]'))
  model=self.backend.model_factory;await self.backend.close()
  self.backend=AtBotsEngineeringBackend({(self.scope,'workspace'):self.root},state_path=Path(self.temp.name)/'state.sqlite',model_factory=model)
  with self.assertRaises(Exception):await self.backend.resume(self.scope,handle,'workspace',self.selection)
  with self.assertRaises(Exception):await self.backend.interrupt(ProjectScope('other-tenant','project-one'),handle,turn)
  await self.backend.interrupt(self.scope,handle,turn)
  await self.backend.resume(self.scope,handle,'workspace',self.selection)
  self.assertEqual((await self.backend.observe(self.scope,handle,turn)).kind,'interrupted')
  self.assertEqual((await self.backend.recover_start(self.scope,handle,'before-restart')).status,'interrupted')
  self.assertEqual(self.backend.tasks,{})
  self.assertFalse((self.root/'src/main.py').exists())
 def test_file_tools_reject_escape_links_and_all_spellings_of_pinned_input(self):
  files=WorkspaceFiles(self.root,lambda message:None)
  (self.root/'project-context.json').write_text('accepted original')
  (self.root/'escape').symlink_to(Path(self.temp.name))
  for path in ['../outside','/tmp/outside','escape/outside','project-context.json','./project-context.json','.tools/toolchain.json']:
   with self.assertRaises(ValueError):files.write_file(path,'changed')
  self.assertEqual((self.root/'project-context.json').read_text(),'accepted original')
