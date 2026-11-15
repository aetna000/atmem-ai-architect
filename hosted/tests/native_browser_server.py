"""Loopback-only integration harness: native UI, actual AtBots and AtMem, fixture identity/storage.

No production data/identity and no provider spend. Model replies are explicit
fixtures. Run with the separate worker lock; never mount this in a public service.
"""
import asyncio,json,os,re,tempfile,uuid
from contextlib import asynccontextmanager
from pathlib import Path
import httpx
from fastapi import HTTPException
from fastapi.responses import FileResponse,HTMLResponse,Response
from hosted.sqlite_store import SQLiteTransactions
from hosted.projects import Profiles
from hosted.storage_projects import StorageProjects
from hosted.workspace_jobs import WorkspaceJobs,transfer_store
from hosted.model_broker import NativeModelBroker
from hosted.worker_host import NativeWorkerHost
from hosted.credits import CreditLedger
from hosted.credentials import CredentialVault
from hosted.pilot_settings import PilotSettings,OpenRouterCatalog
from hosted.x_access import XWhitelist,XIdentity
from hosted.pilot_api import create_pilot_app,PilotServices
from hosted.tests.test_pilot import XIdentityFixture,catalog_fixture
from hosted.tests.test_storage_projects import BucketFixture

root=Path('.local/native-browser')/uuid.uuid4().hex;root.mkdir(parents=True,exist_ok=True,mode=0o700)
site=Path(os.environ['ARCHITECT_QUALIFICATION_SITE']).resolve();dist=site/'site/dist'
store=SQLiteTransactions(root/'control.sqlite');profiles=Profiles(store);bucket=BucketFixture()
access=XWhitelist(store,admin_ids=['1'],initial_ids=['2','3'])
catalog=OpenRouterCatalog(fetch=lambda:{'data':[{**row,'context_length':1000000} for row in catalog_fixture()['data']]})
settings=PilotSettings(store,access,catalog);policy=settings.current()
if not policy['platformSpendingEnabled']:settings.update(XIdentity('signed','1','Fixture owner'),policy['revision'],{'platformSpendingEnabled':True,'dailyPlatformBudgetMicros':2000000})
vault=CredentialVault(store,profiles,keyring={'test':b't'*32},active_key='test')
def reply(request):
 return httpx.Response(200,json={'id':'fixture-native-'+uuid.uuid4().hex,'object':'chat.completion','created':1,'model':'openai/gpt-6.1-sol',
   'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':json.dumps({'message':'Who will use this system?','phase':'Discovery'})}}],
   'usage':{'prompt_tokens':10,'completion_tokens':10,'total_tokens':20,'cost':'0'}})
projects=StorageProjects(store,profiles,bucket)
broker=NativeModelBroker(store=store,profiles=profiles,access=access,settings=settings,vault=vault,platform_key=lambda:'fixture-only-no-provider-key',transport_factory=lambda:httpx.MockTransport(reply),projects=projects)
jobs=WorkspaceJobs(store,profiles,projects,bucket)
app=create_pilot_app(PilotServices(store,XIdentityFixture(),access,vault,catalog,True,projects,jobs,transfer_store(store,profiles,bucket,'qualification_transfers')))

@asynccontextmanager
async def lifespan(application):
 import uvicorn
 with tempfile.TemporaryDirectory(prefix='ar-native-',dir='/tmp') as sockets:
  socket=str(Path(sockets)/'broker.sock')
  server=uvicorn.Server(uvicorn.Config(broker.app,uds=socket,access_log=False,log_level='warning'))
  serving=asyncio.create_task(server.serve())
  while not server.started:await asyncio.sleep(.05)
  stop=asyncio.Event();host=NativeWorkerHost(jobs=jobs,profiles=profiles,settings=settings,broker=broker,bucket=bucket,root=root/'tenants',broker_socket=socket)
  work=asyncio.create_task(host.run(stop))
  try:yield
  finally:stop.set();await work;server.should_exit=True;await serving
app.router.lifespan_context=lifespan

@app.middleware('http')
async def published_header_contract(request,call_next):
 response=await call_next(request);headers={};path=request.url.path
 for rule in json.loads((site/'firebase.json').read_text())['hosting']['headers']:
  source=rule['source'];matched=source=='**' or source=='/architect{,/}' and path in {'/architect','/architect/'} or source=='/architect/workspace{,/**}' and (path=='/architect/workspace' or path.startswith('/architect/workspace/')) or source=='/docs{,/**}' and (path=='/docs' or path.startswith('/docs/'))
  if matched:headers.update({header['key']:header['value'] for header in rule['headers']})
 response.headers.update(headers);return response

@app.get('/fixture/{name}')
async def module(name:str):
 if name not in {'account-controller.mjs','workspace-controller.mjs'}:raise HTTPException(404)
 return FileResponse(site/'site/src/components/architect'/name,media_type='text/javascript')

@app.get('/architect/')
async def page():
 html=(dist/'architect.html').read_text()
 html=re.sub(r'<script\b[^>]*>.*?</script>','',html,flags=re.S)
 script="""<script type="module">
import {mountAccount} from '/fixture/account-controller.mjs';
mountAccount(document.getElementById('architect-account'),{apiPrefix:'/api/ai-architect',loadIdentity:async()=>({signIn:async()=>({getIdToken:async()=>'owner'}),signOut:async()=>{}})});
</script><style>body::after{content:'Local qualification · fixture identity/storage/model';position:fixed;bottom:4px;right:8px;z-index:20000;background:white;color:#172033;font:11px sans-serif;padding:3px;border:1px solid #aaa}</style>"""
 return HTMLResponse(html.replace('</body>',script+'</body>'))

@app.get('/{path:path}')
async def asset(path:str):
 target=(dist/path).resolve()
 if not target.is_relative_to(dist) or not target.is_file():raise HTTPException(404)
 return FileResponse(target)

if __name__=='__main__':
 import uvicorn
 uvicorn.run(app,host='127.0.0.1',port=4333,access_log=False,log_level='warning')
