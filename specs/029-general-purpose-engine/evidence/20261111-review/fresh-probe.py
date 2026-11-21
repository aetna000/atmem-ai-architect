"""Uncoached diagnostic, not held-out qualification; exercises real product adapters."""
import asyncio,json,pathlib,subprocess,sys,time
from unittest.mock import patch
ROOT=pathlib.Path.cwd();sys.path.insert(0,str(ROOT))
from server.architect import AtMemArchitect
from server.agent_runtime import run
from server.contracts import ChatRequest
from server.memory_service import MemoryService
from server.local_providers import signed_in
OUT=ROOT/'specs/029-general-purpose-engine/evidence/20261111-review/fresh-conversation'
OUT.mkdir(exist_ok=True)
def bridge(data):
 r=subprocess.run(['node','scripts/convergence-bridge.mjs'],input=json.dumps(data),capture_output=True,text=True,check=True)
 return json.loads(r.stdout)
async def main():
 if not signed_in('codex'):
  (OUT/'result.json').write_text(json.dumps({'status':'not_run','reason':'Local Codex connector not signed in','cloudOperations':False},indent=2)+'\n');return
 messages=['I run a community equipment library. I need a website where members reserve tools, volunteers check them out and back in, and overdue reminders go by email. We already have a public website and a spreadsheet of members. We are in Australia. Please help me build this on Azure.', 'Some members share an email address. Volunteers must be able to record returns even when the internet drops, and a returned tool needs inspection before anyone can borrow it again. We have about 200 members and a budget around $80 a month.']
 state=bridge({'action':'initial','id':'generality-community-library','scenario':{'name':'Community equipment library'},'provider':'azure','message':messages[0]})
 project=state['project'];history=[];model=AtMemArchitect();memory=MemoryService(ROOT/'.local/generality-review-memory');rows=[]
 for index,message in enumerate(messages,1):
  if index>1:state=bridge({'action':'prepare','project':project,'message':message})
  request=ChatRequest(projectId=project['id'],message=message,provider='codex',model='default',effort='medium',stage='design',origin='chat',project=state['agentProject'],context=state['context'],history=history)
  (OUT/f'turn-{index}-request.json').write_text(json.dumps(request.model_dump(exclude_none=True),indent=2)+'\n');start=time.monotonic()
  try:
   async def disconnected():return False
   with patch('server.agent_runtime.service',return_value=memory):response=await asyncio.wait_for(run(model,request,disconnected),timeout=300)
   (OUT/f'turn-{index}-response.json').write_text(json.dumps(response,indent=2)+'\n')
   applied=bridge({'action':'apply','project':project,'message':message,'response':response});project=applied['project']
   history += [{'role':'user','text':message},{'role':'assistant','text':response['message']}]
   rows.append({'turn':index,'seconds':round(time.monotonic()-start,2),'message':response['message'],'followUp':response.get('followUp'),'nodeCount':len(project['nodes']),'scopePreserved':applied['scopePreserved']})
   print('Fresh turn',index,'completed; nodes',len(project['nodes']),flush=True)
  except Exception as exc:
   rows.append({'turn':index,'status':'failed','errorType':type(exc).__name__,'error':str(exc)[:2000]});break
 (OUT/'project.json').write_text(json.dumps(project,indent=2)+'\n')
 (OUT/'result.json').write_text(json.dumps({'status':'diagnostic','turns':rows,'boundary':'Two-turn uncoached known-to-reviewer probe, not held-out or runtime/deployment proof','cloudOperations':False},indent=2)+'\n')
asyncio.run(main())
