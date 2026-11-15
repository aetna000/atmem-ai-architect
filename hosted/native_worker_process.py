"""One private native runtime per admitted tenant; framed JSON on inherited pipes.

The parent owns Google credentials, billing and provider keys. This child receives
only a revocable model-broker capability and exact owned project snapshots.
"""
import asyncio,base64,json,os,sys
from contextlib import asynccontextmanager
from pathlib import Path

async def main():
 wire=sys.stdout;sys.stdout=sys.stderr
 config=json.loads(await asyncio.to_thread(sys.stdin.readline))
 os.environ['PYDANTIC_AI_NO_BANNER']='1'
 os.environ['ATMEM_ARCHITECT_MEMORY_PYTHON']=sys.executable
 from .native_runtime import NativeWorkspaceRuntime
 from .atbots_architect import AtBotsArchitect
 import httpx
 from openai import AsyncOpenAI
 from pydantic_ai.models.openai import OpenAIChatModel
 from pydantic_ai.providers.openai import OpenAIProvider
 def transport():return httpx.AsyncHTTPTransport(uds=config['brokerSocket'],retries=0)
 @asynccontextmanager
 async def model_factory(scope,turn,selection):
  async with httpx.AsyncClient(transport=transport(),timeout=180,trust_env=False,follow_redirects=False) as client:
   yield OpenAIChatModel(selection.model,provider=OpenAIProvider(openai_client=AsyncOpenAI(
      api_key=config['capability'],base_url='http://architect-broker/v1',http_client=client,max_retries=0,default_headers={'X-Architect-Project':scope.project})))
 def architect_factory(job,model,policy):
  return AtBotsArchitect(store=None,ledger=None,uid=config['uid'],operation=job['id'],model={'id':model},policy=policy,
      api_key=config['capability'],transport_factory=transport,base_url='http://architect-broker/v1',request_headers={'X-Architect-Project':job['projectId']})
 runtime=NativeWorkspaceRuntime(uid=config['uid'],root=config['root'],model_factory=model_factory,architect_factory=architect_factory)
 wire.write(json.dumps({'ready':True})+'\n');wire.flush()
 tasks=set();active_requests={}
 async def respond(request):
  if request.get('control')=='cancel':
   target=active_requests.get(request['jobId'])
   if target:
    target.cancel();await asyncio.gather(target,return_exceptions=True)
    if target.cancelled():
     wire.write(json.dumps({'id':request['jobId'],'response':{'status':499,'body':{'detail':'Request cancelled before execution'}}})+'\n');wire.flush()
   wire.write(json.dumps({'id':request['id'],'response':{'cancelRequested':bool(target)}})+'\n');wire.flush();return
  if request.get('control')=='status':
   from server.engineering_routes import service
   wire.write(json.dumps({'id':request['id'],'response':{'active':bool(service().backend.tasks) or len(tasks)>1}})+'\n');wire.flush();return
  try:
   result=await runtime.dispatch(request['job'],request['body'],base64.b64decode(request['snapshot'],validate=True),model=request['model'],policy=request['policy'])
  except asyncio.CancelledError:
   result={'status':499,'body':{'detail':'Request stopped. Submitted provider usage may still complete.'}}
  except Exception:
   result={'status':503,'body':{'detail':'Worker request stopped. Saved project and evidence remain available.'}}
  wire.write(json.dumps({'id':request['job']['id'],'response':result},ensure_ascii=False,allow_nan=False)+'\n');wire.flush()
 try:
  while line:=await asyncio.to_thread(sys.stdin.readline):
   request=json.loads(line)
   task=asyncio.create_task(respond(request));tasks.add(task);task.add_done_callback(tasks.discard)
   if 'job' in request:
    identity=request['job']['id'];active_requests[identity]=task
    task.add_done_callback(lambda completed,identity=identity:active_requests.pop(identity,None))
   if len(tasks)>=16:await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
  if tasks:await asyncio.gather(*tasks)
 finally:await runtime.close()
if __name__=='__main__':asyncio.run(main())
