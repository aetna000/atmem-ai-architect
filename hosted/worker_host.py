"""Trusted queue consumer. Native tenant processes never receive Google/provider keys."""
import asyncio,base64,hashlib,json,os,secrets,sys,time,uuid
from pathlib import Path

class TenantProcess:
 def __init__(self,process,capability,broker,errors):
  self.process,self.capability,self.broker,self.errors=process,capability,broker,errors
  self.pending={};self.write_lock=asyncio.Lock();self.last_used=time.monotonic()
  self.reader=asyncio.create_task(self.read())
 async def read(self):
  try:
   while raw:=await self.process.stdout.readline():
    message=json.loads(raw);future=self.pending.get(message.get('id'))
    if future and not future.done():future.set_result(message['response'])
  except Exception:pass
  finally:
   for future in self.pending.values():
    if not future.done():future.set_exception(RuntimeError('Worker connection interrupted; no request was replayed'))
 async def request(self,message):
  identity=message.get('id') or message['job']['id'];future=asyncio.get_running_loop().create_future()
  if identity in self.pending:raise RuntimeError('Worker request is already in flight')
  self.pending[identity]=future;self.last_used=time.monotonic()
  try:
   async with self.write_lock:
    self.process.stdin.write(json.dumps(message,ensure_ascii=False,allow_nan=False).encode()+b'\n');await self.process.stdin.drain()
   return await asyncio.wait_for(asyncio.shield(future),600)
  finally:self.pending.pop(identity,None);self.last_used=time.monotonic()
 async def idle(self):
  if self.pending:return False
  state=await self.request({'control':'status','id':'control-'+uuid.uuid4().hex})
  return not state['active']
 async def close(self):
  self.broker.revoke(self.capability);self.process.stdin.close()
  try:await asyncio.wait_for(self.process.wait(),15)
  except TimeoutError:self.process.terminate();await self.process.wait()
  await self.reader;self.errors.close()

class NativeWorkerHost:
 def __init__(self,*,jobs,profiles,settings,broker,bucket,root,broker_socket,worker_id=None,process_limit=4):
  self.jobs,self.profiles,self.settings,self.broker,self.bucket=jobs,profiles,settings,broker,bucket
  self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
  self.socket=broker_socket;self.id=worker_id or 'worker-'+uuid.uuid4().hex
  self.children={};self.process_limit=process_limit;self.child_lock=asyncio.Lock()
 async def child(self,uid):
  async with self.child_lock:
   existing=self.children.get(uid)
   if existing and existing.process.returncode is None:return existing
   if existing:await existing.close();del self.children[uid]
   if len(self.children)>=self.process_limit:
    for owner,child in sorted(self.children.items(),key=lambda pair:pair[1].last_used):
     if await child.idle():await child.close();del self.children[owner];break
    else:raise RuntimeError('Workers are busy. Retry shortly.')
   tenant=self.root/hashlib.sha256(uid.encode()).hexdigest()
   if tenant.is_symlink():raise RuntimeError('Tenant root is not a regular private directory')
   tenant.mkdir(exist_ok=True,mode=0o700)
   capability=await asyncio.to_thread(self.broker.bind,uid)
   environment={key:value for key,value in os.environ.items() if key in {'PATH','LANG','LC_ALL'}}
   # Only reviewed operator registrations are inherited; never provider/Google credentials.
   for name in ['ENGINEERING_TOOL_ROOTS','ENGINEERING_TOOLCHAIN','ENGINEERING_VALIDATORS','ENGINEERING_VALIDATOR_ENDPOINT','ENGINEERING_ISOLATION_PROFILES','ENGINEERING_VALIDATOR_WORKERS','PROVIDER_CACHE','TERRAFORM_BIN','TFLINT_BIN','WHISPER_MODEL']:
    key='ATMEM_ARCHITECT_'+name
    if key in os.environ:environment[key]=os.environ[key]
   errors=(tenant/'runtime.log').open('ab');os.chmod(tenant/'runtime.log',0o600)
   process=await asyncio.create_subprocess_exec(sys.executable,'-m','hosted.native_worker_process',stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=errors,env=environment,limit=150*1024*1024)
   process.stdin.write(json.dumps({'uid':uid,'root':str(tenant),'brokerSocket':self.socket,'capability':capability}).encode()+b'\n');await process.stdin.drain()
   try:
    ready=json.loads(await asyncio.wait_for(process.stdout.readline(),30))
    if ready!={'ready':True}:raise RuntimeError('Native worker could not initialize')
   except BaseException:
    self.broker.revoke(capability);process.kill();await process.wait();errors.close();raise
   child=TenantProcess(process,capability,self.broker,errors);self.children[uid]=child;return child
 async def execute(self,row):
  heartbeat=asyncio.create_task(self.heartbeat(row['id']));monitor=None
  try:
   # Ownership and whitelist are rechecked after queueing, not trusted from browser text.
   await asyncio.to_thread(self.broker.admission,row['uid'])
   self.jobs.store.transaction(lambda tx:self.jobs._project(tx,row['uid'],row['projectId']))
   snapshot=row['projectSnapshot']
   raw=await asyncio.to_thread(self.bucket.blob(snapshot['objectName'],generation=snapshot['generation']).download_as_bytes,if_generation_match=snapshot['generation'],checksum='crc32c')
   body=await asyncio.to_thread(self.jobs.payload,row);policy=await asyncio.to_thread(self.settings.current)
   child=await self.child(row['uid'])
   work=asyncio.create_task(child.request({'job':row,'body':body,'snapshot':base64.b64encode(raw).decode(),'model':policy['model'],'policy':policy}))
   monitor=asyncio.create_task(self.watch_cancellation(row,child,work));response=await work
  except Exception:
   response={'status':503,'body':{'detail':'Worker stopped. Your project is saved; prior model usage may need reconciliation.'}}
  try:await asyncio.to_thread(self.jobs.finish,row['id'],self.id,response)
  finally:
   heartbeat.cancel()
   if monitor:monitor.cancel()
   await asyncio.gather(*([heartbeat,monitor] if monitor else [heartbeat]),return_exceptions=True)
 async def watch_cancellation(self,row,child,work):
  while not work.done():
   if await asyncio.to_thread(self.jobs.cancellation,row['id'],self.id):
    await child.request({'control':'cancel','id':'cancel-'+uuid.uuid4().hex,'jobId':row['id']});return
   await asyncio.sleep(.75)
 async def heartbeat(self,job):
  while True:
   await asyncio.sleep(30);await asyncio.to_thread(self.jobs.heartbeat,job,self.id)
 async def run(self,stop):
  tasks=set()
  try:
   while not stop.is_set():
    if len(tasks)>=4:
     await asyncio.wait(tasks,timeout=1,return_when=asyncio.FIRST_COMPLETED);continue
    from google.api_core.exceptions import Aborted,DeadlineExceeded,ServiceUnavailable
    try:row=await asyncio.to_thread(self.jobs.claim,self.id)
    except (Aborted,DeadlineExceeded,ServiceUnavailable):
     # A queue outage must not terminate unrelated accepted native turns. No
     # model call or accepted job is replayed by retrying queue acquisition.
     await asyncio.sleep(1);continue
    if row:
     task=asyncio.create_task(self.execute(row));tasks.add(task);task.add_done_callback(tasks.discard)
    else:
     try:await asyncio.wait_for(stop.wait(),1)
     except TimeoutError:pass
   if tasks:await asyncio.gather(*tasks)
  finally:
   for child in self.children.values():await child.close()
