"""Durable, tenant-bound calls to the existing Architect worker API.

No browser-selected worker, tenant, filesystem path or model credential. A claimed
request is never silently replayed after a lost worker acknowledgement.
"""
import base64,hashlib,json,re,time,uuid
from .credits import CreditError,Conflict,digest,identifier
from .projects import Profiles,ProjectUnavailable,project_id
from .storage_projects import StorageProjects

def registered_methods():
 from pathlib import Path
 return json.loads(Path(__file__).with_name('workspace-routes.json').read_text())['methods']

def registered_paths():
 from pathlib import Path
 return frozenset(json.loads(Path(__file__).with_name('workspace-routes.json').read_text())['paths'])

class CollectionMap:
 def __init__(self,store,mapping):self.store,self.mapping=store,mapping
 def transaction(self,callback):
  mapping=self.mapping
  class Mapped:
   def __init__(self,tx):self.tx=tx
   def get(self,collection,key):return self.tx.get(mapping.get(collection,collection),key)
   def set(self,collection,key,value):return self.tx.set(mapping.get(collection,collection),key,value)
   def create(self,collection,key,value):return self.tx.create(mapping.get(collection,collection),key,value)
   def delete(self,collection,key):return self.tx.delete(mapping.get(collection,collection),key)
  return self.store.transaction(lambda tx:callback(Mapped(tx)))

def transfer_store(store,profiles,bucket,prefix):
 return StorageProjects(CollectionMap(store,{'projects':'workspace_transfer_docs','project_index':'workspace_transfer_index','project_uploads':'workspace_transfer_uploads','project_parts':'workspace_transfer_parts'}),profiles,bucket,object_prefix=prefix)

class WorkspaceJobs:
 def __init__(self,store,profiles,projects,bucket,*,prefix='architect_workspace_jobs',clock=time.time,paths=None):
  if not re.fullmatch(r'[a-z][a-z0-9_]{2,40}',prefix):raise ValueError('Use a bounded job storage prefix')
  self.store,self.profiles,self.projects,self.bucket=store,profiles,projects,bucket
  self.prefix,self.clock,self.paths=prefix,clock,paths or registered_paths()
 def _project(self,tx,uid,pid):
  self.profiles._account(tx,uid);row=tx.get('projects',self.projects._project_key(uid,pid))
  if not row or row.get('trashed'):raise ProjectUnavailable('Project is unavailable')
  return row
 def submit(self,uid,request_id,pid,path,body,method='POST'):
  identifier(uid);identifier(request_id);project_id(pid)
  if path not in self.paths or method not in registered_methods().get(path,[]):raise CreditError('This worker operation is not registered')
  if type(body) is not dict or body.get('projectId',pid)!=pid:raise CreditError('Use this project’s own workspace')
  content=json.dumps(body,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
  if len(content)>64*1024*1024:raise CreditError('Workspace request exceeds 64 MiB; nothing was truncated')
  request_sha=hashlib.sha256(method.encode()+b'\0'+path.encode()+b'\0'+content).hexdigest();job_id=hashlib.sha256((uid+'\0'+request_id).encode()).hexdigest()
  def admit(tx):
   project=self._project(tx,uid,pid);previous=tx.get('workspace_jobs',job_id)
   queue=tx.get('workspace_queue','pending') or {'ids':[]}
   if previous:
    if previous['uid']!=uid or previous['requestSha256']!=request_sha or previous['projectId']!=pid:raise Conflict('Request identifier belongs to different work')
    return previous
   if sum(tx.get('workspace_jobs',key).get('uid')==uid for key in queue['ids'])>=8:raise CreditError('Finish existing workspace operations before starting more.')
   if len(queue['ids'])>=100:raise CreditError('Workspace queue is full. Retry shortly.')
   row={'id':job_id,'uid':uid,'projectId':pid,'path':path,'method':method,'requestSha256':request_sha,'payloadSha256':hashlib.sha256(content).hexdigest(),
        'projectSnapshot':project,'state':'uploading','createdAt':self.clock(),'events':[{'kind':'queued','at':self.clock()}]}
   tx.create('workspace_jobs',job_id,row);queue['ids'].append(job_id);tx.set('workspace_queue','pending',queue);return row
  row=self.store.transaction(admit)
  if row['state']=='uploading':
   name=f'{self.prefix}/requests/{digest(uid)}/{job_id}.json';blob=self.bucket.blob(name);blob.metadata={'sha256':row['payloadSha256']}
   from google.api_core.exceptions import PreconditionFailed
   try:blob.upload_from_string(content,content_type='application/json',if_generation_match=0,checksum='crc32c')
   except PreconditionFailed:
    blob.reload()
    if blob.size!=len(content) or blob.metadata.get('sha256')!=row['payloadSha256']:raise Conflict('Request payload differs from the admitted work')
   def ready(tx):
    current=tx.get('workspace_jobs',job_id)
    if current['state']=='uploading':current.update(state='queued',payloadObject=name,payloadGeneration=int(blob.generation));tx.set('workspace_jobs',job_id,current)
    return current
   row=self.store.transaction(ready)
  return self.public(row)
 @staticmethod
 def public(row):
  return {key:row[key] for key in ['id','projectId','state','createdAt','events']}
 def read(self,uid,pid,job_id):
  if not re.fullmatch('[a-f0-9]{64}',job_id):raise ProjectUnavailable('Workspace request is unavailable')
  def read(tx):
   self._project(tx,uid,pid);row=tx.get('workspace_jobs',job_id)
   if not row or row['uid']!=uid or row['projectId']!=pid:raise ProjectUnavailable('Workspace request is unavailable')
   if row['state']=='running' and row['leaseUntil']<self.clock():
    row.update(state='recovery_required');tx.set('workspace_jobs',job_id,row)
   return row
  row=self.store.transaction(read);result=self.public(row)
  if row['state']=='cancelled':
   result['response']={'status':499,'body':{'detail':'Request cancelled before execution'}};return result
  if row['state']=='completed' and row.get('resultBytes',0)>512*1024:
   result['responseTransfer']={'size':row['resultBytes'],'sha256':row['resultSha256'],'chunkBytes':256*1024,'chunks':(row['resultBytes']+256*1024-1)//(256*1024)}
   return result
  if row['state']=='completed':
   blob=self.bucket.blob(row['resultObject'],generation=row['resultGeneration']);raw=blob.download_as_bytes(if_generation_match=row['resultGeneration'],checksum='crc32c')
   if hashlib.sha256(raw).hexdigest()!=row['resultSha256']:raise Conflict('Workspace response failed its integrity check')
   result['response']=json.loads(raw)
  return result
 def cancel(self,uid,pid,job_id):
  if not re.fullmatch('[a-f0-9]{64}',job_id):raise ProjectUnavailable('Workspace request is unavailable')
  def cancel(tx):
   self._project(tx,uid,pid);row=tx.get('workspace_jobs',job_id);queue=tx.get('workspace_queue','pending')
   if not row or row['uid']!=uid or row['projectId']!=pid:raise ProjectUnavailable('Workspace request is unavailable')
   if row['state'] in {'uploading','queued'}:
    row['state']='cancelled';row['events'].append({'kind':'cancelled','at':self.clock()});queue['ids']=[key for key in queue['ids'] if key!=job_id]
    tx.set('workspace_jobs',job_id,row);tx.set('workspace_queue','pending',queue)
   elif row['state'] in {'running','recovery_required'} and not row.get('cancelRequested'):
    row['cancelRequested']=True;row['events'].append({'kind':'cancel_requested','at':self.clock()});tx.set('workspace_jobs',job_id,row)
   return self.public(row)
  return self.store.transaction(cancel)
 def cancellation(self,job_id,worker):
  row=self.store.transaction(lambda tx:tx.get('workspace_jobs',job_id))
  if not row or row.get('worker')!=worker:raise Conflict('Worker no longer owns this operation')
  return bool(row.get('cancelRequested'))
 def result_chunk(self,uid,pid,job_id,part):
  state=self.read(uid,pid,job_id)
  transfer=state.get('responseTransfer')
  if not transfer or type(part) is not int or not 0<=part<transfer['chunks']:raise CreditError('Use a valid result chunk')
  row=self.store.transaction(lambda tx:tx.get('workspace_jobs',job_id))
  first=part*transfer['chunkBytes'];last=min(row['resultBytes'],first+transfer['chunkBytes'])-1
  raw=self.bucket.blob(row['resultObject'],generation=row['resultGeneration']).download_as_bytes(
      if_generation_match=row['resultGeneration'],start=first,end=last,checksum=None)
  if len(raw)!=last-first+1:raise Conflict('Worker result chunk is incomplete')
  return {'data':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
 def claim(self,worker):
  identifier(worker)
  def claim(tx):
   queue=tx.get('workspace_queue','pending') or {'ids':[]}
   rows=[tx.get('workspace_jobs',job_id) for job_id in queue['ids']]
   selected=next((row for row in rows if row and row['state']=='queued'),None)
   if not selected:return None
   selected.update(state='running',worker=worker,leaseUntil=self.clock()+120,startedAt=self.clock())
   selected['events'].append({'kind':'started','at':self.clock()});tx.set('workspace_jobs',selected['id'],selected);return selected
  return self.store.transaction(claim)
 def heartbeat(self,job_id,worker):
  def beat(tx):
   row=tx.get('workspace_jobs',job_id)
   if not row or row.get('worker')!=worker or row['state']!='running':raise Conflict('Worker no longer owns this request')
   row['leaseUntil']=self.clock()+120;tx.set('workspace_jobs',job_id,row)
  return self.store.transaction(beat)
 def payload(self,row):
  blob=self.bucket.blob(row['payloadObject'],generation=row['payloadGeneration']);raw=blob.download_as_bytes(if_generation_match=row['payloadGeneration'],checksum='crc32c')
  if hashlib.sha256(raw).hexdigest()!=row['payloadSha256']:raise Conflict('Workspace payload failed its integrity check')
  return json.loads(raw)
 def finish(self,job_id,worker,response):
  raw=json.dumps(response,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
  if len(raw)>100*1024*1024:raise CreditError('Worker response exceeds its explicit bound')
  row=self.store.transaction(lambda tx:tx.get('workspace_jobs',job_id))
  if not row or row.get('worker')!=worker:raise Conflict('Worker does not own this request')
  name=f'{self.prefix}/responses/{digest(row["uid"])}/{job_id}.json';blob=self.bucket.blob(name);sha=hashlib.sha256(raw).hexdigest();blob.metadata={'sha256':sha}
  from google.api_core.exceptions import PreconditionFailed
  try:blob.upload_from_string(raw,content_type='application/json',if_generation_match=0,checksum='crc32c')
  except PreconditionFailed:
   blob.reload()
   if blob.metadata.get('sha256')!=sha:raise Conflict('A different worker response was already captured')
  def finish(tx):
   current=tx.get('workspace_jobs',job_id);queue=tx.get('workspace_queue','pending')
   if current.get('worker')!=worker:raise Conflict('Worker does not own this request')
   if current['state']=='completed':return
   if current['state'] not in {'running','recovery_required'}:raise Conflict('Workspace request is already settled')
   current.update(state='completed',resultBytes=len(raw),resultObject=name,resultGeneration=int(blob.generation),resultSha256=sha)
   current['events'].append({'kind':'finished','at':self.clock()});queue['ids']=[i for i in queue['ids'] if i!=job_id]
   tx.set('workspace_jobs',job_id,current);tx.set('workspace_queue','pending',queue)
  self.store.transaction(finish)
