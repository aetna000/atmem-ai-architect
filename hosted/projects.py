"""Private profiles and lossless chunked project snapshots on durable storage."""
import base64
import hashlib
import json
import re
import time
import uuid
from datetime import datetime, timezone
from .credits import CreditError, Conflict, AccountUnavailable, digest, identifier, fingerprint

CHUNK_BYTES=256*1024
MAX_PROJECT_BYTES=64*1024*1024
USER_BYTES=256*1024*1024
MAX_PROJECTS=100


class ProjectUnavailable(CreditError): pass


def project_id(value):
    if type(value) is not str or not re.fullmatch('[a-f0-9]{32}',value):raise ProjectUnavailable('Project is unavailable')
    return value


def _now():return datetime.now(timezone.utc).isoformat()


class Profiles:
    def __init__(self,store):self.store=store

    def register(self,identity):
        key=digest(identity.x_id)
        def apply(tx):
            previous=tx.get('profiles',key)
            if previous:
                if previous.get('deleted'):raise AccountUnavailable('Account is unavailable')
                return previous
            record=dict(uid=identity.x_id,xId=identity.x_id,displayName=identity.display_name,revision=1,
                        createdAt=_now(),disabled=False,deleted=False,aiConnection='managed')
            tx.create('profiles',key,record)
            return record
        return self.store.transaction(apply)

    def _account(self,tx,uid):
        key=digest(uid);record=tx.get('profiles',key)
        if not record or record.get('uid')!=uid or record.get('deleted'):raise AccountUnavailable('Account is unavailable')
        return key,record

    def get(self,uid):return self.store.transaction(lambda tx:self._account(tx,uid)[1])

    def update(self,uid,*,revision,display_name=None,ai_connection=None):
        if type(revision) is not int or revision<1:raise CreditError('Use the current profile revision')
        if display_name is not None and (type(display_name) is not str or not 1<=len(display_name.strip())<=120 or any(ord(c)<32 for c in display_name)):
            raise CreditError('Use a display name between 1 and 120 characters')
        if ai_connection is not None and ai_connection not in {'managed','openrouter'}:raise CreditError('Choose the default AI or your OpenRouter key')
        def apply(tx):
            key,record=self._account(tx,uid)
            if record['revision']!=revision:raise Conflict('Profile changed. Reload before saving')
            if display_name is not None:record['displayName']=display_name.strip()
            if ai_connection is not None:record['aiConnection']=ai_connection
            record.update(revision=revision+1,updatedAt=_now());tx.set('profiles',key,record)
            return record
        return self.store.transaction(apply)


class Projects:
    def __init__(self,store,profiles,*,clock=time.time):self.store,self.profiles,self.clock=store,profiles,clock

    @staticmethod
    def _project_key(uid,pid):return digest(uid)+'-'+project_id(pid)

    def _index(self,tx,uid):
        self.profiles._account(tx,uid)
        return tx.get('project_index',digest(uid)) or dict(ids=[],bytes=0,reservedBytes=0,uploads=[])

    def list(self,uid):
        def apply(tx):
            index=self._index(tx,uid)
            return {'projects':[tx.get('projects',self._project_key(uid,pid)) for pid in index['ids']],
                    'usedBytes':index['bytes'],'reservedBytes':index['reservedBytes'],'limitBytes':USER_BYTES,
                    'maxProjectBytes':MAX_PROJECT_BYTES,'chunkBytes':CHUNK_BYTES}
        return self.store.transaction(apply)

    def begin(self,uid,request_id,*,title,size,sha256,pid=None,revision=0):
        identifier(request_id);fingerprint(sha256)
        if type(title) is not str or not 1<=len(title.strip())<=120 or any(ord(c)<32 for c in title):raise CreditError('Use a project name between 1 and 120 characters')
        if type(size) is not int or not 1<=size<=MAX_PROJECT_BYTES:raise CreditError('Project files must be between 1 byte and 64 MiB')
        if type(revision) is not int or revision<0:raise CreditError('Use the current project revision')
        requested_pid=project_id(pid) if pid else None
        proposed_pid=requested_pid or uuid.uuid4().hex
        upload_id=hashlib.sha256((identifier(uid)+'\0'+request_id).encode()).hexdigest()
        fp=hashlib.sha256(json.dumps([title.strip(),size,sha256,requested_pid,revision],separators=(',',':')).encode()).hexdigest()
        def apply(tx):
            index=self._index(tx,uid)
            previous=tx.get('project_uploads',upload_id)
            current=tx.get('projects',self._project_key(uid,proposed_pid))
            if previous:
                if previous['uid']!=uid or previous['fingerprint']!=fp:raise Conflict('Save request already belongs to different content')
                return previous
            if requested_pid and not current:raise ProjectUnavailable('Project is unavailable')
            if (current['revision'] if current else 0)!=revision:raise Conflict('Project changed. Reload before replacing it')
            if len(index['uploads'])>=4:raise CreditError('Finish or cancel an existing save before starting another')
            if not current and len(index['ids'])+len(index['uploads'])>=MAX_PROJECTS:raise CreditError('Project limit reached')
            if index['bytes']+index['reservedBytes']+size>USER_BYTES:raise CreditError('Project storage is full. Download and remove unused projects')
            record=dict(uid=uid,id=upload_id,projectId=proposed_pid,title=title.strip(),size=size,sha256=sha256,
                        expectedRevision=revision,chunks=(size+CHUNK_BYTES-1)//CHUNK_BYTES,
                        state='uploading',fingerprint=fp,createdAt=self.clock())
            index['uploads'].append(upload_id);index['reservedBytes']+=size
            tx.set('project_index',digest(uid),index);tx.create('project_uploads',upload_id,record)
            return record
        return self.store.transaction(apply)

    def _upload(self,tx,uid,upload_id):
        fingerprint(upload_id);self.profiles._account(tx,uid)
        upload=tx.get('project_uploads',upload_id)
        if not upload or upload['uid']!=uid:raise ProjectUnavailable('Save is unavailable')
        return upload

    def put_chunk(self,uid,upload_id,part,encoded,sha256):
        fingerprint(sha256)
        if type(part) is not int or not 0<=part<MAX_PROJECT_BYTES//CHUNK_BYTES:raise CreditError('Invalid project chunk')
        if type(encoded) is not str or len(encoded)>((CHUNK_BYTES+2)//3)*4:raise CreditError('Project chunk is too large')
        try:raw=base64.b64decode(encoded,validate=True)
        except ValueError as error:raise CreditError('Invalid project chunk encoding') from error
        if hashlib.sha256(raw).hexdigest()!=sha256:raise CreditError('Project chunk failed its integrity check')
        def apply(tx):
            upload=self._upload(tx,uid,upload_id)
            key=upload_id+'-'+str(part)
            previous=tx.get('project_parts',key)
            if upload['state']!='uploading':raise Conflict('This save no longer accepts chunks')
            expected=min(CHUNK_BYTES,upload['size']-part*CHUNK_BYTES)
            if part>=upload['chunks'] or len(raw)!=expected:raise CreditError('Project chunk has the wrong size')
            if previous:
                if previous['sha256']!=sha256:raise Conflict('Chunk already contains different content')
                return {'stored':True}
            tx.create('project_parts',key,dict(data=encoded,sha256=sha256));return {'stored':True}
        return self.store.transaction(apply)

    def complete(self,uid,upload_id):
        def apply(tx):
            upload=self._upload(tx,uid,upload_id)
            if upload['state']=='completed':return upload['result']
            if upload['state']!='uploading':raise Conflict('This save was cancelled')
            index=self._index(tx,uid)
            key=self._project_key(uid,upload['projectId']);previous=tx.get('projects',key)
            parts=[tx.get('project_parts',upload_id+'-'+str(i)) for i in range(upload['chunks'])]
            if any(row is None for row in parts):raise Conflict('Some project chunks are missing. Retry the save')
            if (previous['revision'] if previous else 0)!=upload['expectedRevision']:raise Conflict('Project changed. Reload before replacing it')
            raw=b''.join(base64.b64decode(part['data'],validate=True) for part in parts)
            if len(raw)!=upload['size'] or hashlib.sha256(raw).hexdigest()!=upload['sha256']:raise Conflict('Project integrity check failed')
            try:
                def invalid(value):raise ValueError('Non-finite JSON')
                parsed=json.loads(raw,parse_constant=invalid)
                if not isinstance(parsed,dict):raise ValueError('Project must be an object')
            except (ValueError,UnicodeError,RecursionError) as error:raise CreditError('Upload a valid JSON project file') from error
            record=dict(id=upload['projectId'],title=upload['title'],size=upload['size'],sha256=upload['sha256'],
                        revision=upload['expectedRevision']+1,snapshot=upload_id,chunks=upload['chunks'],updatedAt=_now())
            index['bytes']+=upload['size']-(previous['size'] if previous else 0)
            index['reservedBytes']-=upload['size'];index['uploads'].remove(upload_id)
            if record['id'] not in index['ids']:index['ids'].append(record['id'])
            upload.update(state='completed',result=record)
            # Superseded bytes are removed atomically; the prior idempotency
            # receipt remains, so retrying an old completion cannot overwrite newer work.
            if previous:
                for i in range(previous['chunks']):tx.delete('project_parts',previous['snapshot']+'-'+str(i))
            tx.set('projects',key,record);tx.set('project_index',digest(uid),index);tx.set('project_uploads',upload_id,upload)
            return record
        return self.store.transaction(apply)

    def download(self,uid,pid):
        def apply(tx):
            self.profiles._account(tx,uid)
            row=tx.get('projects',self._project_key(uid,pid))
            if not row:raise ProjectUnavailable('Project is unavailable')
            parts=[tx.get('project_parts',row['snapshot']+'-'+str(i)) for i in range(row['chunks'])]
            if any(part is None for part in parts):raise Conflict('Saved project is incomplete. Contact the administrator')
            raw=b''.join(base64.b64decode(part['data'],validate=True) for part in parts)
            if len(raw)!=row['size'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:raise Conflict('Saved project failed its integrity check')
            return row,raw
        return self.store.transaction(apply)

    def cancel(self,uid,upload_id):
        def apply(tx):
            row=self._upload(tx,uid,upload_id);index=self._index(tx,uid)
            if row['state']=='cancelled':return {'cancelled':True}
            if row['state']!='uploading':raise Conflict('Completed projects cannot be cancelled')
            for i in range(row['chunks']):tx.delete('project_parts',upload_id+'-'+str(i))
            index['reservedBytes']-=row['size'];index['uploads'].remove(upload_id);row['state']='cancelled'
            tx.set('project_index',digest(uid),index);tx.set('project_uploads',upload_id,row)
            return {'cancelled':True}
        return self.store.transaction(apply)

    def remove(self,uid,pid,revision):
        if type(revision) is not int or revision<1:raise CreditError('Use the current project revision')
        def apply(tx):
            index=self._index(tx,uid);key=self._project_key(uid,pid);row=tx.get('projects',key)
            if not row:raise ProjectUnavailable('Project is unavailable')
            if row['revision']!=revision:raise Conflict('Project changed. Reload before removing it')
            index['bytes']-=row['size'];index['ids'].remove(pid)
            for i in range(row['chunks']):tx.delete('project_parts',row['snapshot']+'-'+str(i))
            tx.delete('projects',key);tx.set('project_index',digest(uid),index)
            return {'removed':True}
        return self.store.transaction(apply)
