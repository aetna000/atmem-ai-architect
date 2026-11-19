"""Source-bound compiler handoffs, retained outside the native writable workspace.

Materialized inputs are checked again at artifact capture. File custody/read
receipts do not establish implementation, interpretation or whole-system quality.
"""
import asyncio
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import shutil
import stat
import subprocess
import tempfile
from .engineering_sessions import SessionError

ROOT=Path(__file__).resolve().parents[1]
MAX_BYTES=8_000_000
MAX_FILES=1000

def digest(raw):return hashlib.sha256(raw).hexdigest()
def encode(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def manifest(value,sha):
    return {'format':'atmem.block-handoff.manifest','version':1,'projectId':value['projectId'],'blockId':value['blockId'],'sourceSha256':value['sourceSha256'],
        'capsuleSha256':sha,'entryPoint':value['entryPoint'],'generatedAt':value['generatedAt'],
        'files':{name:{'sha256':digest(text.encode()),'bytes':len(text.encode())}for name,text in value['files'].items()}}
def safe_name(name):
    if not isinstance(name,str)or len(name)>500 or '\\'in name or ':'in name or any(ord(char)<32 for char in name):raise SessionError('Invalid generated handoff path')
    parts=PurePosixPath(name).parts
    if not parts or name.startswith('/')or any(part in {'','.','..'}for part in name.split('/')):raise SessionError('Invalid generated handoff path')
    return parts

def validate(payload,project,block,source_sha):
    if not isinstance(payload,dict)or set(payload)!={'format','version','projectId','blockId','sourceSha256','generatedAt','blockIds','entryPoint','files'}or payload['format']!='atmem.block-handoff'or type(payload['version'])is not int or payload['version']!=1 or payload['projectId']!=project or payload['blockId']!=block or payload['sourceSha256']!=source_sha:raise SessionError('Generated handoff does not match its owned source/block')
    files=payload['files']
    if not isinstance(files,dict)or not 1<=len(files)<=MAX_FILES or 'CAPSULE.json'in files:raise SessionError('Generated handoff exceeds its file bound or reserved namespace')
    for name,text in files.items():
        safe_name(name)
        if not isinstance(text,str):raise SessionError('Generated handoff files must be UTF-8 text')
    if len(encode(payload))>MAX_BYTES:raise SessionError('Generated handoff exceeds its byte bound; no content was discarded')
    if payload['entryPoint']not in files or 'source-context.json'not in files or digest(files['source-context.json'].encode())!=source_sha:raise SessionError('Generated handoff lacks its entry point or exact source snapshot')
    if payload['entryPoint']!=f'spec-kit/blocks/block-{block.encode().hex()}/WORK_ORDER.md':raise SessionError('Generated handoff entry point differs from the selected block')
    source=json.loads(files['source-context.json']);nodes=source.get('design',{}).get('nodes',[])
    selected={block};changed=True
    while changed:
        changed=False
        for node in nodes:
            if node.get('data',{}).get('parentBlockId')in selected and node['id']not in selected:selected.add(node['id']);changed=True
    if not isinstance(payload['blockIds'],list)or any(not isinstance(id,str)for id in payload['blockIds'])or len(payload['blockIds'])!=len(set(payload['blockIds']))or set(payload['blockIds'])!=selected:raise SessionError('Generated handoff changed its descendant scope')
    return payload

def render(content,project,block):
    node=shutil.which('node')
    if not node:raise SessionError('The server-owned handoff compiler requires Node')
    generated=datetime.now(timezone.utc).isoformat()
    with tempfile.TemporaryDirectory(prefix='atmem-handoff-compiler-')as temporary:
        env={'PATH':os.getenv('PATH',''),'HOME':temporary,'TMPDIR':temporary,'LANG':'en_US.UTF-8'}
        try:result=subprocess.run([node,'--max-old-space-size=384',str(ROOT/'scripts/block-handoff-render.mjs')],input=json.dumps({'sourceContent':content.decode(),'blockId':block,'generatedAt':generated},ensure_ascii=False),text=True,capture_output=True,cwd=ROOT,env=env,timeout=30)
        except (OSError,subprocess.TimeoutExpired):raise SessionError('The server handoff compiler could not finish within its bound; no native work was started')from None
    if result.returncode:raise SessionError('The saved design could not be compiled into a block handoff; no native work was started')
    if len(result.stdout.encode())>MAX_BYTES:raise SessionError('Generated handoff exceeds its byte bound; no content was discarded')
    return validate(json.loads(result.stdout),project,block,digest(content))

class HandoffCapsules:
    def __init__(self,store,workspace,*,renderer=render,max_compilers=1,max_pending=8):
        if type(max_compilers)is not int or not 1<=max_compilers<=4 or type(max_pending)is not int or not max_compilers<=max_pending<=64:raise ValueError('Bound the owned handoff compiler pool')
        self.store=store;self.db=store.db;self.workspace=workspace;self.renderer=renderer
        self.compilers=asyncio.Semaphore(max_compilers);self.max_pending=max_pending;self.render_tasks=set();self.active_renders=set();self.closed=False
        self.db.execute('''CREATE TABLE IF NOT EXISTS engineering_handoff_capsules (
            request TEXT PRIMARY KEY, session TEXT NOT NULL, sha256 TEXT NOT NULL,
            payload BLOB NOT NULL, materialized INTEGER NOT NULL DEFAULT 0)''');self.db.commit()

    async def prepare(self,scope,session,request,content,block):
        self.store.get(scope,session)
        if self.closed or len(self.render_tasks)>=self.max_pending:raise SessionError('The handoff compiler queue is full or closed; retry the same saved request')
        async def compile_owned():
            async with self.compilers:
                task=asyncio.current_task();self.active_renders.add(task)
                try:return await asyncio.to_thread(self.renderer,content,scope.project,block)
                finally:self.active_renders.discard(task)
        task=asyncio.create_task(compile_owned());self.render_tasks.add(task)
        def finished(task):
            self.render_tasks.discard(task)
            if not task.cancelled():task.exception()
        task.add_done_callback(finished)
        value=await asyncio.shield(task)
        if self.closed:raise SessionError('The handoff compiler closed before preparation; no native work was started')
        raw=encode(validate(value,scope.project,block,digest(content)))
        count,size=self.db.execute('SELECT count(*),coalesce(sum(length(payload)),0) FROM engineering_handoff_capsules WHERE session=?',(session,)).fetchone()
        if count>=1000 or size+len(raw)>64_000_000:raise SessionError('Handoff history reached its storage bound; no history was removed')
        sha=digest(raw)
        return {'sha256':sha,'manifestSha256':digest(encode(manifest(value,sha))),'root':f'.atmem-handoffs/{request}','entryPoint':value['entryPoint'],'files':len(value['files'])},raw

    async def close(self):
        self.closed=True
        pending=list(self.render_tasks)
        for task in pending:
            if task not in self.active_renders:task.cancel()
        if pending:await asyncio.gather(*pending,return_exceptions=True)

    def save(self,session,request,prepared):
        descriptor,raw=prepared
        self.db.execute('INSERT INTO engineering_handoff_capsules(request,session,sha256,payload) VALUES (?,?,?,?)',(request,session,descriptor['sha256'],raw))

    def get(self,scope,session,request):
        self.store.get(scope,session)
        row=self.db.execute('SELECT * FROM engineering_handoff_capsules WHERE request=? AND session=?',(request,session)).fetchone()
        if not row:return None
        raw=bytes(row['payload'])
        if digest(raw)!=row['sha256']:raise SessionError('Stored handoff integrity failed')
        value=json.loads(raw);validate(value,scope.project,value['blockId'],value['sourceSha256'])
        order=self.db.execute('SELECT payload FROM engineering_work_orders WHERE request=? AND session=?',(request,session)).fetchone()
        if not order or json.loads(order['payload']).get('handoff',{}).get('sha256')!=row['sha256']:raise SessionError('Handoff does not match its original work-order receipt')
        return row,value

    def materialize(self,scope,session,request,context,intent=None):
        self.store.get(scope,session)
        order=self.db.execute('SELECT session,intent FROM engineering_work_orders WHERE request=?',(request,)).fetchone()
        if order and(order['session']!=session or(intent is not None and order['intent']!=intent)):raise SessionError('A reserved work order cannot change its original session or intent')
        found=self.get(scope,session,request)
        if not found:return
        row,value=found
        if self.store.get(scope,session)['state']!='idle':raise SessionError('Handoff inputs can only be prepared before an idle owned turn')
        if context is None or context['sha256']!=value['sourceSha256']:raise SessionError('Handoff source does not match the submitted context')
        if os.name!='posix'or not hasattr(os,'O_NOFOLLOW'):raise SessionError('This platform has no qualified no-follow handoff materializer')
        root=self.workspace(scope,session)
        prefix=f'.atmem-handoffs/{request}'
        files={**value['files'],'CAPSULE.json':encode(manifest(value,row['sha256'])).decode()}
        recover_partial=not row['materialized']and self.store.get_run(scope,session,request)is None
        recovered_partial=False
        # Directory-relative no-follow traversal; no generated path can select a
        # host destination. Existing bytes are verified, never silently repaired.
        flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
        fd=os.open(root,flags)
        try:
            for part in safe_name(prefix):
                try:os.mkdir(part,mode=0o700,dir_fd=fd)
                except FileExistsError:pass
                next_fd=os.open(part,flags,dir_fd=fd);os.close(fd);fd=next_fd
            for name,text in files.items():
                current=os.dup(fd)
                try:
                    parts=safe_name(name)
                    for part in parts[:-1]:
                        try:os.mkdir(part,mode=0o700,dir_fd=current)
                        except FileExistsError:pass
                        next_fd=os.open(part,flags,dir_fd=current);os.close(current);current=next_fd
                    raw=text.encode()
                    try:target=os.open(parts[-1],os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o400,dir_fd=current)
                    except FileExistsError:
                        target=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=current)
                        try:
                            info=os.fstat(target)
                            if not stat.S_ISREG(info.st_mode)or info.st_nlink!=1 or info.st_size>len(raw):raise SessionError('Existing handoff input changed; no native work was started')
                            observed=b''
                            while len(observed)<info.st_size:
                                part=os.read(target,min(65536,info.st_size-len(observed)))
                                if not part:break
                                observed+=part
                            if observed==raw:pass
                            elif recover_partial and len(observed)<len(raw)and raw.startswith(observed):
                                recovered_partial=True
                                # Only an unaccepted, never-published server copy
                                # may resume a proven prefix from the retained DB.
                                # Accepted/native-edited input is never repaired.
                                os.fchmod(target,0o600)
                                writer=os.open(parts[-1],os.O_WRONLY|os.O_NOFOLLOW,dir_fd=current)
                                try:
                                    actual=os.fstat(writer)
                                    if (actual.st_dev,actual.st_ino,actual.st_nlink)!=(info.st_dev,info.st_ino,1):raise SessionError('Pending handoff changed during recovery')
                                    os.lseek(writer,len(observed),os.SEEK_SET)
                                    with os.fdopen(os.dup(writer),'wb')as output:output.write(raw[len(observed):]);output.flush();os.fsync(output.fileno())
                                    os.fchmod(writer,0o400)
                                finally:os.close(writer)
                            else:raise SessionError('Existing handoff input changed; no native work was started')
                        finally:os.close(target)
                    else:
                        with os.fdopen(target,'wb')as output:output.write(raw);output.flush();os.fsync(output.fileno())
                finally:os.close(current)
        except OSError:raise SessionError('The handoff input path is unavailable or unsafe; no native work was started')from None
        finally:os.close(fd)
        with self.db:self.db.execute('UPDATE engineering_handoff_capsules SET materialized=1 WHERE request=?',(request,))
        return {'handoffSha256':row['sha256'],'sourceSha256':value['sourceSha256'],'blockId':value['blockId'],'files':len(value['files']),'recoveredPartialPreparation':recovered_partial}

    def pins(self,scope,session):
        self.store.get(scope,session);pins={}
        for row in self.db.execute('SELECT request FROM engineering_handoff_capsules WHERE session=? AND materialized=1',(session,)):
            stored,value=self.get(scope,session,row['request']);prefix=f".atmem-handoffs/{row['request']}/"
            pins.update({prefix+name:digest(text.encode())for name,text in value['files'].items()});pins[prefix+'CAPSULE.json']=digest(encode(manifest(value,stored['sha256'])))
        return pins

    def root_request(self,scope,session,run):
        self.store.get(scope,session)
        if self.db.execute('SELECT 1 FROM engineering_handoff_capsules WHERE request=? AND session=?',(run,session)).fetchone():return run
        if self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='engineering_repairs'").fetchone():
            row=self.db.execute('SELECT root_run FROM engineering_repairs WHERE run=? AND session=?',(run,session)).fetchone()
            if row:return row['root_run']
        return None

    def read(self,scope,session,name='READ_ME_FIRST.md',offset=0,sha256=None):
        current=self.store.get(scope,session)
        request=self.root_request(scope,session,current['run'])
        found=self.get(scope,session,request)if request else None
        if not found or not found[0]['materialized']:raise SessionError('No materialized handoff belongs to this active work order')
        row,value=found
        if not isinstance(name,str)or(name not in value['files']and name!='CAPSULE.json')or type(offset)is not int or offset<0:raise ValueError('Choose a file and explicit character offset in this work order')
        text=encode(manifest(value,row['sha256'])).decode()if name=='CAPSULE.json'else value['files'][name];sha=digest(text.encode())
        if offset>len(text)or(offset and sha256!=sha)or(sha256 is not None and sha256!=sha):raise SessionError('Read the same immutable handoff file on every page')
        return {'format':'atmem.block-handoff.read','requestId':request,'blockId':value['blockId'],'handoffSha256':row['sha256'],'sourceSha256':value['sourceSha256'],'path':name,'sha256':sha,
            'page':{'offset':offset,'text':text[offset:offset+4000],'totalCharacters':len(text),'nextOffset':offset+4000 if offset+4000<len(text)else None},
            'entryPoint':value['entryPoint'],'boundary':'Server-retained input delivery only, not interpretation, implementation or acceptance.'}

    def evidence(self,scope,session,run):
        request=self.root_request(scope,session,run);found=self.get(scope,session,request)if request else None
        if not found:return None
        row,value=found;pages={}
        if self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='engineering_tool_calls'").fetchone():
            calls=self.db.execute("SELECT t.result FROM engineering_tool_calls t JOIN engineering_runs r ON r.session=t.session AND r.turn=t.turn WHERE t.session=? AND t.state='finished' AND r.status='completed' AND json_extract(t.request,'$.tool')='atmem_work_order_read'",(session,)).fetchall()
            for call in calls:
                try:
                    result=json.loads(call['result']);metadata=json.loads(result['contentItems'][0]['text'])
                    if not result['success']or metadata.get('format')!='atmem.block-handoff.read'or metadata.get('requestId')!=request or metadata.get('handoffSha256')!=row['sha256']or metadata.get('sourceSha256')!=value['sourceSha256']:continue
                    path=metadata['path'];page=metadata['page'];text=value['files'][path];start=page['offset'];end=start+len(page['text'])
                    if type(start)is not int or start<0 or end>len(text)or page['totalCharacters']!=len(text)or metadata['sha256']!=digest(text.encode())or page['text']!=text[start:end]:continue
                    pages.setdefault(path,[]).append((start,end))
                except (KeyError,TypeError,ValueError):continue
        required={'READ_ME_FIRST.md','spec-kit/interfaces.json'}
        for block in value['blockIds']:
            prefix=f'spec-kit/blocks/block-{block.encode().hex()}/'
            required.update(prefix+name for name in ['WORK_ORDER.md','spec.md','plan.md','tasks.json','testing.md','infrastructure-devops.md'])
        receipts=[]
        for path in sorted(required):
            covered=0
            for start,end in sorted(pages.get(path,[])):
                if start>covered:break
                covered=max(covered,end)
            receipts.append({'path':path,'sha256':digest(value['files'][path].encode()),'complete':bool(pages.get(path))and covered==len(value['files'][path])})
        return {'requestId':request,'blockId':value['blockId'],'handoffSha256':row['sha256'],'sourceSha256':value['sourceSha256'],'materialized':bool(row['materialized']),
            'requiredFiles':receipts,'completeRequiredFiles':sum(receipt['complete']for receipt in receipts),'requiredFileCount':len(receipts),
            'boundary':'Completed-turn server read receipts, not interpretation, code quality or full-system acceptance.'}
