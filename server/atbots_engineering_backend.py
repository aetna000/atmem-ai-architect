"""Native AtBots implementation of Architect's existing engineering lifecycle.

Model transport is injected by the authenticated worker. There is no local CLI,
custom agent loop, arbitrary shell tool or browser-selected filesystem root.
"""
import asyncio,json,os,re,sqlite3,stat,uuid
from pathlib import Path
from .engineering_sessions import BackendEvent,RecoveredStart,SessionError
from .engineering_contexts import context_input

class WorkspaceFiles:
 def __init__(self,root,notify):self.root=Path(root).resolve(strict=True);self.notify=notify
 def target(self,path,*,write=False):
  if type(path) is not str or not path or len(path)>500 or '\\' in path or any(ord(c)<32 for c in path) or Path(path).is_absolute() or any(p in {'..',''} for p in Path(path).parts):raise ValueError('Use a relative project file path')
  parts=Path(path).parts
  if write and (parts[0] in {'.tools','.agents','atmem-tools'} or Path(path).as_posix() in {'project-context.json','ATMEM_DELIVERY.md'}):raise ValueError('Pinned input files are read-only')
  target=self.root/path
  if not target.resolve().is_relative_to(self.root):raise ValueError('File is outside the project workspace')
  current=self.root
  for part in parts:
   current=current/part
   if current.is_symlink():raise ValueError('Symbolic links are not project file capabilities')
  return target
 def list_files(self,directory:str='',offset:int=0)->dict:
  """List an explicit page of workspace files. Follow nextOffset until null."""
  if type(offset) is not int or offset<0:raise ValueError('Use a valid file cursor')
  root=self.target(directory) if directory else self.root
  paths=sorted(str(p.relative_to(self.root)) for p in root.rglob('*') if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(self.root))
  return {'files':paths[offset:offset+100],'nextOffset':offset+100 if len(paths)>offset+100 else None}
 def read_file(self,path:str,offset:int=0,limit:int=64000)->dict:
  """Read an explicit UTF-8 byte page. No file content is silently truncated."""
  if type(offset) is not int or offset<0 or type(limit) is not int or not 1<=limit<=64000:raise ValueError('Use bounded byte cursors')
  target=self.target(path)
  with target.open('rb') as f:
   size=os.fstat(f.fileno()).st_size;f.seek(offset);raw=f.read(limit)
   while raw:
    try:text=raw.decode();break
    except UnicodeDecodeError as error:
     if error.start>=len(raw)-4 and offset+len(raw)<size:raw=raw[:error.start]
     else:raise ValueError('Read a UTF-8 text file using the returned nextOffset') from error
   else:text=''
  return {'path':path,'text':text,'nextOffset':offset+len(raw) if offset+len(raw)<size else None,'bytes':size}
 def write_file(self,path:str,content:str)->dict:
  """Create or replace a project implementation file. Pinned inputs stay immutable."""
  from .memory_service import safe
  if type(content) is not str or len(content.encode())>5*1024*1024 or not safe(content):raise ValueError('Use a bounded text artifact without credentials')
  target=self.target(path,write=True);target.parent.mkdir(parents=True,exist_ok=True,mode=0o700);self.target(path,write=True)
  # The model has only these file tools; it cannot create links or choose another root.
  fd,tmp=None,target.parent/('.atmem-write-'+uuid.uuid4().hex)
  try:
   fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
   with os.fdopen(fd,'w',encoding='utf-8') as f:fd=None;f.write(content);f.flush();os.fsync(f.fileno())
   self.target(path,write=True);os.replace(tmp,target)
  finally:
   if fd is not None:os.close(fd)
   if tmp.exists():tmp.unlink()
  self.notify('Updated '+path);return {'path':path,'bytes':target.stat().st_size}

class AtBotsEngineeringBackend:
 name='atbots'
 @property
 def session_count(self):return self.db.execute('SELECT COUNT(*) FROM atbots_sessions').fetchone()[0]
 def __init__(self,workspaces,*,state_path,model_factory,instructions='',tools=None):
  self.workspaces=workspaces;self.model_factory=model_factory;self.instructions=instructions;self.tools=tools
  self.db=sqlite3.connect(state_path);self.db.row_factory=sqlite3.Row
  self.db.executescript('''CREATE TABLE IF NOT EXISTS atbots_sessions(id TEXT PRIMARY KEY,tenant TEXT,project TEXT,workspace TEXT,model TEXT,effort TEXT);
    CREATE TABLE IF NOT EXISTS atbots_turns(id TEXT PRIMARY KEY,handle TEXT,request TEXT UNIQUE,state TEXT,text TEXT,context TEXT,steering TEXT);
    CREATE TABLE IF NOT EXISTS atbots_history(handle TEXT PRIMARY KEY,messages BLOB NOT NULL);
    CREATE TABLE IF NOT EXISTS atbots_steering(request TEXT PRIMARY KEY,turn TEXT NOT NULL,payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS atbots_events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,handle TEXT,turn TEXT,kind TEXT,text TEXT,delivered INTEGER DEFAULT 0);''')
  with self.db:self.db.execute("UPDATE atbots_turns SET state='recovery_required' WHERE state IN ('starting','running')")
  self.tasks={};self.wake={}
 def _workspace(self,scope,workspace):
  root=self.workspaces.get((scope,workspace))
  if root is None or not Path(root).is_dir() or Path(root).is_symlink():raise SessionError('Workspace is unavailable for this project')
  return Path(root).resolve(strict=True)
 def _owned(self,scope,handle,selection=None):
  row=self.db.execute('SELECT * FROM atbots_sessions WHERE id=? AND tenant=? AND project=?',(handle,scope.tenant,scope.project)).fetchone()
  if not row or selection and (row['model'],row['effort'])!=(selection.model,selection.effort):raise SessionError('Session does not match its project and model selection')
  return row,self._workspace(scope,row['workspace'])
 def _emit(self,handle,turn,kind,text=''):
  # Public progress contains actual file/tool events, never private model reasoning.
  with self.db:self.db.execute('INSERT INTO atbots_events(handle,turn,kind,text) VALUES (?,?,?,?)',(handle,turn,kind,text))
  self.wake.setdefault(handle,asyncio.Event()).set()
 async def create(self,scope,workspace,selection):
  self._workspace(scope,workspace);handle=str(uuid.uuid4())
  with self.db:self.db.execute('INSERT INTO atbots_sessions VALUES (?,?,?,?,?,?)',(handle,scope.tenant,scope.project,workspace,selection.model,selection.effort))
  return handle
 async def resume(self,scope,handle,workspace,selection):
  row,_=self._owned(scope,handle,selection)
  if row['workspace']!=workspace:raise SessionError('Session workspace changed')
  if self.db.execute("SELECT 1 FROM atbots_turns WHERE handle=? AND state='recovery_required'",(handle,)).fetchone():raise SessionError('Prior native work requires recovery; no model request was replayed')
 async def start(self,scope,handle,text,selection,*,request_id,context=None):
  row,root=self._owned(scope,handle,selection)
  if context is not None and context.get('projectId')!=scope.project:raise SessionError('Context belongs to a different project')
  if not request_id:raise SessionError('Use an idempotent native request identity')
  key=handle+'\0'+request_id;existing=self.db.execute('SELECT * FROM atbots_turns WHERE request=?',(key,)).fetchone()
  if existing:raise SessionError('This native request was already accepted; recover its acknowledgement')
  if self.db.execute("SELECT 1 FROM atbots_turns WHERE handle=? AND state IN ('starting','running','recovery_required')",(handle,)).fetchone():raise SessionError('A native turn is active or requires recovery')
  turn=str(uuid.uuid4());self.last_error=None
  with self.db:self.db.execute('INSERT INTO atbots_turns VALUES (?,?,?,?,?,?,?)',(turn,handle,key,'starting',text,json.dumps(context), '[]'))
  self.tasks[turn]=asyncio.create_task(self._run(scope,handle,turn,root,selection,text,context));return turn
 async def _run(self,scope,handle,turn,root,selection,text,context):
  from atbots.providers.pydantic_ai import PydanticAIProvider
  from pydantic_ai.usage import UsageLimits
  # Yield until EngineeringSessions has durably attached this acknowledged turn.
  await asyncio.sleep(0)
  with self.db:self.db.execute("UPDATE atbots_turns SET state='running' WHERE id=?",(turn,))
  self._emit(handle,turn,'progress','Generating project files.')
  try:
   async with self.model_factory(scope,turn,selection) as model:
    provider=PydanticAIProvider(name='AtMem AI Architect engineering',model=selection.model,endpoint='https://openrouter.ai/api/v1',kind='openai-compatible',egress_class='remote',retries=0)
    agent=provider._build_agent(model,self.instructions,None)
    agent.model_settings={'max_tokens':4096,'openai_reasoning_effort':'medium','extra_body':{'reasoning':{'effort':'medium'}},'max_retries':0}
    files=WorkspaceFiles(root,lambda text:None)
    async def list_files(directory:str='',offset:int=0)->dict:
     """List a page of project files; follow nextOffset until null."""
     return await asyncio.to_thread(files.list_files,directory,offset)
    async def read_file(path:str,offset:int=0,limit:int=64000)->dict:
     """Read a UTF-8 byte page; follow nextOffset without dropping content."""
     return await asyncio.to_thread(files.read_file,path,offset,limit)
    async def write_file(path:str,content:str)->dict:
     """Create or replace an implementation file; frozen inputs are read-only."""
     result=await asyncio.to_thread(files.write_file,path,content)
     self._emit(handle,turn,'progress','Updated '+path)
     return result
    for function in [list_files,read_file,write_file]:agent.tool_plain(function,sequential=True)
    if self.tools:
     async def engineering_tool(name:str,arguments:dict)->dict:
      """Use an operator-registered engineering evidence/check tool. Available schemas are provided in the request context."""
      result=await self.tools.invoke(scope,self._owned(scope,handle)[0]['workspace'],turn,str(uuid.uuid4()),name,arguments)
      self._emit(handle,turn,'progress','Checked '+name);return result
     agent.tool_plain(engineering_tool,sequential=True)
    prompt=text
    if context is not None:prompt+='\n\n'+context_input(context)['text']
    if self.tools:prompt+='\n\nRegistered engineering tools (server-owned schemas):\n'+json.dumps(self.tools.specs)
    from pydantic_ai.messages import ModelMessagesTypeAdapter
    saved_history=self.db.execute('SELECT messages FROM atbots_history WHERE handle=?',(handle,)).fetchone()
    history=ModelMessagesTypeAdapter.validate_json(saved_history['messages']) if saved_history else None
    while True:
     result=await agent.run(prompt,message_history=history,usage_limits=UsageLimits(request_limit=64))
     history=result.all_messages()
     with self.db:self.db.execute('INSERT OR REPLACE INTO atbots_history VALUES (?,?)',(handle,ModelMessagesTypeAdapter.dump_json(history)))
     self._emit(handle,turn,'message',str(result.output))
     row=self.db.execute('SELECT steering FROM atbots_turns WHERE id=?',(turn,)).fetchone();steering=json.loads(row['steering'])
     if not steering:break
     # Explicitly queued user steering becomes another native SDK turn, not a custom model loop.
     with self.db:self.db.execute("UPDATE atbots_turns SET steering='[]' WHERE id=?",(turn,))
     prompt='\n\n'.join(steering)
    with self.db:self.db.execute("UPDATE atbots_turns SET state='completed' WHERE id=?",(turn,))
    self._emit(handle,turn,'completed')
  except asyncio.CancelledError:
   with self.db:self.db.execute("UPDATE atbots_turns SET state='interrupted' WHERE id=?",(turn,))
   self._emit(handle,turn,'interrupted')
  except Exception as error:
   self.last_error=error
   with self.db:self.db.execute("UPDATE atbots_turns SET state='failed' WHERE id=?",(turn,))
   self._emit(handle,turn,'failed','Native generation stopped. Inspect the retained files and check evidence.')
  finally:self.tasks.pop(turn,None)
 async def recover_start(self,scope,handle,request_id):
  self._owned(scope,handle);row=self.db.execute('SELECT * FROM atbots_turns WHERE request=?',(handle+'\0'+request_id,)).fetchone()
  if not row:return None
  if row['state'] not in {'running','completed','failed','interrupted'}:raise SessionError('Native request acceptance requires reconciliation')
  return RecoveredStart(request_id,row['id'],row['state'])
 async def observe(self,scope,handle,turn):
  self._owned(scope,handle);row=self.db.execute('SELECT state FROM atbots_turns WHERE id=? AND handle=?',(turn,handle)).fetchone()
  if not row:raise SessionError('Turn does not belong to this session')
  if row['state']=='recovery_required':raise SessionError('Native work requires reconciliation; it was not replayed')
  return BackendEvent(turn,row['state']) if row['state'] in {'completed','failed','interrupted'} else None
 async def steer(self,scope,handle,turn,text,*,request_id=None,context=None):
  self._owned(scope,handle)
  if context is not None and context.get('projectId')!=scope.project:raise SessionError('Context belongs to another project')
  if not request_id:raise SessionError('Use an idempotent steering identity')
  payload=text+('\n'+context_input(context)['text'] if context else '')
  key=handle+'\0'+request_id
  previous=self.db.execute('SELECT * FROM atbots_steering WHERE request=?',(key,)).fetchone()
  if previous:
   if previous['turn']!=turn or previous['payload']!=payload:raise SessionError('Steering identity belongs to different work')
   return
  row=self.db.execute('SELECT * FROM atbots_turns WHERE id=? AND handle=?',(turn,handle)).fetchone()
  if not row or row['state']!='running':raise SessionError('The native turn is not running')
  steering=json.loads(row['steering']);steering.append(payload)
  with self.db:
   self.db.execute('INSERT INTO atbots_steering VALUES (?,?,?)',(key,turn,payload))
   self.db.execute('UPDATE atbots_turns SET steering=? WHERE id=?',(json.dumps(steering),turn))
 async def interrupt(self,scope,handle,turn):
  self._owned(scope,handle)
  owned=self.db.execute('SELECT state FROM atbots_turns WHERE id=? AND handle=?',(turn,handle)).fetchone()
  if not owned:raise SessionError('Turn does not belong to this session')
  task=self.tasks.get(turn)
  if task:
   task.cancel();await asyncio.gather(task,return_exceptions=True)
   row=self.db.execute('SELECT state FROM atbots_turns WHERE id=? AND handle=?',(turn,handle)).fetchone()
   if row and row['state'] in {'starting','running'}:
    with self.db:self.db.execute("UPDATE atbots_turns SET state='interrupted' WHERE id=?",(turn,))
    self._emit(handle,turn,'interrupted')
  elif owned['state']=='recovery_required':
   # This process has no task to stop after a restart. Explicit user interruption
   # settles execution only: unknown provider charges remain reserved separately.
   with self.db:self.db.execute("UPDATE atbots_turns SET state='interrupted' WHERE id=? AND handle=?",(turn,handle))
   self._emit(handle,turn,'interrupted','Prior worker stopped. Saved files remain; submitted provider usage may still be billable.')
 async def next_event(self,scope,handle):
  self._owned(scope,handle);wake=self.wake.setdefault(handle,asyncio.Event())
  while True:
   wake.clear();row=self.db.execute('SELECT * FROM atbots_events WHERE handle=? AND delivered=0 ORDER BY sequence LIMIT 1',(handle,)).fetchone()
   if row:
    with self.db:self.db.execute('UPDATE atbots_events SET delivered=1 WHERE sequence=?',(row['sequence'],))
    return BackendEvent(row['turn'],row['kind'],row['text'])
   await wake.wait()
 async def close(self):
  tasks=list(self.tasks.values())
  for task in tasks:task.cancel()
  if tasks:await asyncio.gather(*tasks,return_exceptions=True)
  self.db.close()
