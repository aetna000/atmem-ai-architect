"""Private, single-tenant process adapter around the existing native application.

No public listener, identity bootstrap, credential route or alternate project
engine. The trusted dispatcher supplies owned snapshots and model factories.
"""
import asyncio,base64,hashlib,json,os,tempfile
from pathlib import Path

class NativeWorkspaceRuntime:
 def __init__(self,*,uid,root,model_factory,architect_factory):
  self.uid,self.root=uid,Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
  configured=os.environ.get('ATMEM_ARCHITECT_HOME')
  if configured and Path(configured).resolve()!=self.root:raise RuntimeError('Each native tenant requires its own process and home')
  os.environ['ATMEM_ARCHITECT_HOME']=str(self.root)
  os.environ['ATMEM_ARCHITECT_ENABLE_ENGINEERING']='1'
  os.environ['ATMEM_ARCHITECT_ENGINEERING_WORKSPACE_ROOT']=str(self.root)
  # Import after binding this private process to its tenant, never from public API.
  from fastapi import FastAPI
  from server import app as native
  from server import engineering_routes
  from server.atbots_engineering_backend import AtBotsEngineeringBackend
  from .workspace_jobs import registered_paths,registered_methods
  self.native,self.architect_factory=native,architect_factory
  if engineering_routes._service is not None:raise RuntimeError('Native engineering must not be shared between tenant runtimes')
  engineering_routes._service=engineering_routes.LocalEngineeringService(backend_factory=lambda registrations,control,instructions:
      AtBotsEngineeringBackend(registrations,state_path=control/'atbots.sqlite',model_factory=model_factory,instructions=instructions))
  self.app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
  self.paths=registered_paths();self.methods=registered_methods()
  # Use public router inventories directly; FastAPI may defer include_router flattening.
  sources=[native.app.router,native.memory_router,native.terraform_router,native.emulation_router,native.engineering_router,native.voice_router,native.openai_voice_router]
  self.app.router.routes=[route for source in sources for route in source.routes if getattr(route,'path',None) in self.paths and set(getattr(route,'methods',{}))&set(self.methods.get(route.path,[]))]
  if {route.path for route in self.app.routes}!=self.paths:raise RuntimeError('Pinned native route inventory no longer matches this runtime')
  self.lock=asyncio.Lock()
 def snapshot(self,pid,row,raw):
  from .projects import project_id
  project_id(pid)
  if row['id']!=pid or len(raw)!=row['size'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('Owned project snapshot failed integrity verification')
  file=json.loads(raw)
  if file.get('format') not in {'atmem.ai-architect.project','atforma.project'}:raise ValueError('Use a complete Architect project document')
  file['meta']['id']=pid
  directory=self.root/'projects';directory.mkdir(mode=0o700,exist_ok=True)
  receipt=directory/(pid+'.cloud-revision');revision=int(receipt.read_text()) if receipt.exists() else 0
  if row['revision']<revision:return
  target=directory/(pid+'.atforma.json')
  fd,temporary=tempfile.mkstemp(prefix='.snapshot-',dir=directory)
  try:
   with os.fdopen(fd,'w') as stream:json.dump(file,stream,ensure_ascii=False,allow_nan=False);stream.flush();os.fsync(stream.fileno())
   os.replace(temporary,target);receipt.write_text(str(row['revision']))
  finally:
   if os.path.exists(temporary):os.unlink(temporary)
 async def dispatch(self,job,body,snapshot,*,model,policy):
  if job['uid']!=self.uid or job['path'] not in self.paths:raise ValueError('Worker identity does not own this operation')
  method=job.get('method','POST')
  if method not in self.methods.get(job['path'],[]):raise ValueError('Worker method is not registered')
  pid=job['projectId']
  if body.get('projectId',pid)!=pid:raise ValueError('Worker operation belongs to another project')
  async with self.lock:
   self.snapshot(pid,job['projectSnapshot'],snapshot)
   if job['path']=='/api/architect':
    body={**body,'projectId':pid,'provider':'openai','model':model,'effort':'medium'}
    self.native.ARCHITECT=self.architect_factory(job,model,policy)
   if job['path']=='/api/engineering/create':body={**body,'model':model,'effort':'medium'}
  import httpx
  async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='http://private-worker',timeout=None) as client:
   if job['path']=='/api/voice/transcribe':
    audio=base64.b64decode(body['__workspaceBinary'],validate=True)
    if len(audio)>1920100:raise ValueError('Voice clip exceeds the existing duration bound')
    response=await client.post(job['path'],content=audio,headers={'Content-Type':'audio/wav'})
   else:response=await client.request(method,job['path'],**({'json':body} if method=='POST' else {}))
  headers={name:value for name,value in response.headers.items() if name.lower() in {'content-type','content-disposition'}}
  if response.headers.get('content-type','').startswith('application/json'):
   return {'status':response.status_code,'headers':headers,'body':response.json()}
  return {'status':response.status_code,'headers':headers,'base64':base64.b64encode(response.content).decode()}
 async def close(self):
  from server.engineering_routes import close
  await close()
  from server.memory_service import service
  memory=service()
  if hasattr(memory,'close'):await asyncio.to_thread(memory.close)
