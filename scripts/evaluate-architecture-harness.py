"""Bounded opt-in live-model observations. No cloud plans, apply or automatic grading."""
import argparse,asyncio,hashlib,json,pathlib,sys,time
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
CASES=[
 ('authorization','A public browser lets users chat. The client suggests hiding the download button until Google sign-in. Is that sufficient to protect Terraform generation and downloads? Explain the trust boundaries and what must be implemented and tested. Do not draw a proposal, request tools, ask a question or claim tests ran. Keep the answer under 180 words.'),
 ('retry-and-credit','A service grants paid credit from a payment webhook. Delivery is at least once; two requests can arrive concurrently and a process may crash after updating the balance. Explain how the blocks must interact to prevent double credit and recover safely. Do not invent a payment vendor or currency. Do not draw a proposal, request tools or claim tests ran. Keep the answer under 180 words.'),
 ('durability','An existing local Architect application uses a process-local file/database. The client wants multiple autoscaling containers and private memory per account and project. Explain the state, ownership and authorization boundaries, the changes needed, and how to test them. Do not claim that selecting Firestore automatically provides a working AtMem adapter. Do not draw a proposal, request tools or claim tests ran. Keep the answer under 180 words.')]
async def evaluate(args):
 from server.architect import AtMemArchitect
 from server.agent_runtime import run
 from server.contracts import ChatRequest
 from server.memory_service import MemoryService
 out=pathlib.Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
 memory=MemoryService(out/'isolated-home');model=AtMemArchitect();observations=[]
 for key,prompt in CASES[:args.limit]:
  pid='evaluation-'+key+'-001';request=ChatRequest(projectId=pid,message=prompt,provider=args.provider,model=args.model,stage='review',project={'version':1,'revision':1,'name':'Unseen composition assessment','provider':'aws','nodes':[],'edges':[]})
  start=time.monotonic()
  async def disconnected():return False
  try:
   with patch('server.agent_runtime.service',return_value=memory):response=await asyncio.wait_for(run(model,request,disconnected),timeout=150)
   observation={'case':key,'prompt':prompt,'response':response,'durationSeconds':round(time.monotonic()-start,2),'status':'observed_not_independently_graded'}
  except Exception as exc:observation={'case':key,'status':'failed','errorType':type(exc).__name__,'durationSeconds':round(time.monotonic()-start,2)}
  observations.append(observation);(out/(key+'.json')).write_text(json.dumps(observation,indent=2)+'\n');print(key,observation['status'],flush=True)
  if observation['status']=='failed':break
 report={'provider':args.provider,'model':args.model,'scope':'Live architecture reasoning observations with real AtMem context; no deployment or superiority claim. Independent review still required.','observations':observations,'constitutionSha256':hashlib.sha256((ROOT/'CONSTITUTION.md').read_bytes()).hexdigest()};(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 if any(x['status']=='failed' for x in observations):raise SystemExit(1)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--live',action='store_true',required=True);p.add_argument('--provider',choices=['codex','claude-code'],default='codex');p.add_argument('--model',default='default');p.add_argument('--limit',type=int,choices=[1,2,3],default=1);p.add_argument('--output',required=True);args=p.parse_args();asyncio.run(evaluate(args))
