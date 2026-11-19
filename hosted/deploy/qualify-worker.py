"""Operator-only real cloud queue acceptance; never a replacement for X/browser QA.

The Google operator token stays in memory. Model credentials remain on the VM.
--models explicitly permits a managed request using the administrator's wallet;
its first enablement sets a USD20 global daily ceiling, adjustable by the admin.
"""
import argparse,base64,hashlib,json,subprocess,sys,time,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
parser=argparse.ArgumentParser();parser.add_argument('--project',required=True);parser.add_argument('--admin-x-id',required=True);parser.add_argument('--apply',action='store_true');parser.add_argument('--models',action='store_true');parser.add_argument('--generate',action='store_true');args=parser.parse_args()
out=Path('.local/worker-cloud-qualification');out.mkdir(parents=True,exist_ok=True,mode=0o700)
if not args.apply:
 print(json.dumps({'project':args.project,'existingAdminOwnedProject':True,'realCloudQueue':True,'modelRequest':args.models,'providerKeysReadLocally':False}));raise SystemExit(0)
from google.oauth2.credentials import Credentials
from server.memory_worker import EXPECTED_ATMEM_VERSION
from google.cloud import firestore,storage
from hosted.firestore_store import FirestoreTransactions
from hosted.projects import Profiles
from hosted.storage_projects import StorageProjects
from hosted.workspace_projects import WorkspaceProjects
from hosted.workspace_jobs import WorkspaceJobs
from hosted.x_access import XIdentity,XWhitelist
from hosted.pilot_settings import PilotSettings,OpenRouterCatalog
token=subprocess.check_output(['gcloud','auth','print-access-token','--project',args.project],text=True).strip()
credentials=Credentials(token);client=firestore.Client(project=args.project,database='architect',credentials=credentials)
store=FirestoreTransactions(client,namespace='architect_pilot_production');profiles=Profiles(store)
actor=XWhitelist(store,admin_ids=[args.admin_x_id]).authorize(XIdentity('operator-verified-existing-subject',args.admin_x_id,'AtMem AI'))
profiles.get(actor.uid) # Never bootstrap a synthetic account into production.
bucket=storage.Client(project=args.project,credentials=credentials).bucket(args.project+'-architect-projects')
projects=StorageProjects(store,profiles,bucket,object_prefix='architect_pilot_production');workspace=WorkspaceProjects(store,profiles,projects)
record=out/'project.json'
if record.exists():pid=json.loads(record.read_text())['id']
else:
 row=workspace.create(actor.uid,'cloud-qualification-'+uuid.uuid4().hex,'Hosted worker acceptance');pid=row['id'];record.write_text(json.dumps({'id':pid})+'\n')
jobs=WorkspaceJobs(store,profiles,projects,bucket,prefix='architect_pilot_production_jobs')
def run(path,body,timeout=240):
 accepted=jobs.submit(actor.uid,'qualification-'+uuid.uuid4().hex,pid,path,body)
 deadline=time.monotonic()+timeout
 while time.monotonic()<deadline:
  current=jobs.read(actor.uid,pid,accepted['id'])
  if current['state'] in {'completed','cancelled','recovery_required'}:break
  time.sleep(.75)
 else:raise RuntimeError('Cloud worker timed out; retained job '+accepted['id']+' was not replayed')
 if current.get('responseTransfer'):
  transfer=current['responseTransfer'];parts=[]
  for part in range(transfer['chunks']):
   chunk=jobs.result_chunk(actor.uid,pid,accepted['id'],part);raw=base64.b64decode(chunk['data'],validate=True)
   if hashlib.sha256(raw).hexdigest()!=chunk['sha256']:raise RuntimeError('Result chunk failed integrity verification')
   parts.append(raw)
  raw=b''.join(parts)
  if len(raw)!=transfer['size'] or hashlib.sha256(raw).hexdigest()!=transfer['sha256']:raise RuntimeError('Complete worker result failed integrity verification')
  current['response']=json.loads(raw)
 response=current.get('response',{})
 evidence={'jobId':accepted['id'],'path':path,'state':current['state'],'status':response.get('status'),'events':current['events']}
 if response.get('status')!=200:
  evidence['detail']=response.get('body',{}).get('detail','No successful native response')
  (out/'failed-job.json').write_text(json.dumps(evidence,indent=2)+'\n');raise RuntimeError(json.dumps(evidence))
 return evidence,response.get('body',response)
checks=[]
saved,snapshot=projects.download(actor.uid,pid);file=json.loads(snapshot)
if not file['requirements']:
 file['requirements']=[{'id':'operator-acceptance-history','statement':'Retain meeting-room reservation history.','source':'user','priority':'must','sourceText':'Synthetic operator acceptance fixture; not a customer project.'}]
 file['meta']['revision']+=1;snapshot=json.dumps(file,separators=(',',':')).encode();sha=hashlib.sha256(snapshot).hexdigest()
 upload=projects.begin(actor.uid,'fixture-requirement-'+uuid.uuid4().hex,title=saved['title'],size=len(snapshot),sha256=sha,pid=pid,revision=saved['revision'])
 projects.put_chunk(actor.uid,upload['id'],0,base64.b64encode(snapshot).decode(),sha);projects.complete(actor.uid,upload['id'])
evidence,body=run('/api/memory/sync',{'projectId':pid,'file':json.loads(snapshot)});checks.append({**evidence,'engine':body.get('engine'),'nativeMemoryStatus':body.get('status')})
if EXPECTED_ATMEM_VERSION not in body.get('engine',''):
 evidence,body=run('/api/memory/inspect',{'projectId':pid});checks.append({**evidence,'engine':body.get('engine'),'nativeMemoryStatus':body.get('status')})
if body.get('status')!='ready' or EXPECTED_ATMEM_VERSION not in body.get('engine',''):raise RuntimeError('The actual AtMem SDK did not confirm the persisted fixture requirement')
evidence,body=run('/api/memory/overview',{'projectId':pid});checks.append({**evidence,'engine':body.get('engine'),'nativeMemoryStatus':body.get('status')})
if args.models:
 access=XWhitelist(store,admin_ids=[actor.uid]);settings=PilotSettings(store,access,OpenRouterCatalog());policy=settings.current()
 if not policy['platformSpendingEnabled']:
  policy=settings.update(actor,policy['revision'],{'platformSpendingEnabled':True,'dailyPlatformBudgetMicros':policy['dailyPlatformBudgetMicros'] or 20_000_000})
 evidence,body=run('/api/architect',{'provider':'openai','model':policy['model'],'effort':'medium','projectId':pid,
  'message':'We need a meeting-room booking application for a community centre. Ask the most important business question first; preserve open decisions.',
  'project':{'version':1,'revision':1,'name':'Community meeting rooms','provider':'tools','requirements':'','nodes':[],'edges':[]}})
 checks.append({**evidence,'model':policy['model'],'hasMessage':bool(body.get('message')),'phase':body.get('phase')})
if args.generate:
 generation=out/'generation.json'
 if generation.exists():session=json.loads(generation.read_text())['sessionId']
 else:
  saved,raw=projects.download(actor.uid,pid);file=json.loads(raw)
  statements=['Provide a dependency-free Node HTTP service and browser UI for community-centre meeting-room reservations.',
   'Rooms are A and B. Accept a visitor name and UTC start/end times. Reject invalid ranges and overlapping reservations per room, including simultaneous requests.',
   'Persist reservations through service restarts in an atomic local JSON file. A reservation for room A must not block room B.',
   'Run as a single local process. No cloud resources, login, payments or AI are required inside this generated application.',
   'Deliver complete implementation, dependent Spec Kit tasks, run instructions and real HTTP/restart/concurrency and browser tests.']
  file['requirements']=[{'id':'operator-room-'+str(i),'statement':text,'source':'user','priority':'must','sourceText':'Synthetic operator acceptance fixture.'} for i,text in enumerate(statements)]
  file['meta']['revision']+=1;raw=json.dumps(file,separators=(',',':')).encode();sha=hashlib.sha256(raw).hexdigest()
  upload=projects.begin(actor.uid,'generation-fixture-'+uuid.uuid4().hex,title=saved['title'],size=len(raw),sha256=sha,pid=pid,revision=saved['revision'])
  projects.put_chunk(actor.uid,upload['id'],0,base64.b64encode(raw).decode(),sha);projects.complete(actor.uid,upload['id'])
  _,created=run('/api/engineering/create',{'projectId':pid,'model':'server-selected','effort':'medium'});session=created['id']
  generation.write_text(json.dumps({'sessionId':session,'projectId':pid,'started':False})+'\n')
 state=json.loads(generation.read_text())
 if not state['started']:
  # Persist the intention first: an uncertain acknowledgement requires explicit
  # recovery, never another paid generation attempt from rerunning this script.
  state['started']=True;state['startAcknowledged']=False;generation.write_text(json.dumps(state)+'\n')
  _,started=run('/api/engineering/start',{'projectId':pid,'sessionId':session,'text':'Implement every saved accepted requirement in project-context.json. Deliver the complete application and Spec Kit. Use registered checks, repair failures and retain evidence. Name the browser test browser.test.mjs and use the provided image-local Playwright module with Chromium sandbox enabled. Put detailed explanations in the specification; progress stays concise.'})
  state['startAcknowledged']=True;state['runId']=started.get('run');generation.write_text(json.dumps(state)+'\n')
 if not state.get('startAcknowledged'):raise RuntimeError('Prior generation acknowledgement is uncertain. Recover its existing session; do not replay it.')
 deadline=time.monotonic()+1200
 while time.monotonic()<deadline:
  _,current=run('/api/engineering/state',{'projectId':pid,'sessionId':session})
  if current['state']=='idle':break
  time.sleep(3)
 else:raise RuntimeError('Generation remains active; retained session was not replayed')
 if current.get('lastStatus',current.get('last_status'))!='completed':
  (out/'generation-state.json').write_text(json.dumps(current,indent=2)+'\n');raise RuntimeError('Generation did not complete; inspect retained native state')
 for _ in range(90):
  _,finished=run('/api/engineering/finalizations',{'projectId':pid,'sessionId':session})
  if finished['finalizations'] and all(row['state'] not in {'checking','repair_requested'} for row in finished['finalizations']):break
  time.sleep(2)
 _,delivery=run('/api/engineering/delivery',{'projectId':pid})
 (out/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n')
 artifact=delivery.get('artifact')
 if not artifact or not delivery.get('canPackage'):raise RuntimeError('The completed package cannot be downloaded with its saved design')
 _,handoff=run('/api/engineering/handoff',{'projectId':pid,'sessionId':session,'artifactId':artifact['id'],'savedDesignSha256':delivery['savedDesignSha256']})
 (out/'handoff.zip').write_bytes(base64.b64decode(handoff['base64'],validate=True))
 checks.append({'path':'/api/engineering/handoff','status':200,'sessionId':session,'artifactSha256':artifact['sha256'],'downloadBytes':(out/'handoff.zip').stat().st_size,'finalizations':finished['finalizations'],'checks':delivery['checks']})
receipt={'kind':'Actual Google Firestore/GCS queue and private Google VM native runtime','projectId':pid,'checks':checks,'realModelRequested':args.models,'browserOAuthAcceptance':False,'fullHostedExperienceComplete':False}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
