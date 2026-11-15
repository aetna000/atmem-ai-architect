"""Firebase Storage payloads with transactional Firestore ownership/metadata.

Blob writes occur outside retryable Firestore callbacks. Names are server-owned;
immutable uploads become visible only after integrity checks and metadata commit.
Configure staging expiry and retired-object lifecycle rules before deployment.
"""
import base64
import hashlib
import json
import re
from datetime import datetime,timezone
from google.api_core.exceptions import PreconditionFailed,NotFound
from .credits import CreditError,Conflict,digest
from .projects import Projects,ProjectUnavailable,CHUNK_BYTES


class StorageProjects(Projects):
    def __init__(self,store,profiles,bucket,*,object_prefix='architect',**kwargs):
        if not re.fullmatch(r'[a-z][a-z0-9_]{2,40}',object_prefix):raise ValueError('Use an explicit bounded storage prefix')
        super().__init__(store,profiles,**kwargs);self.bucket=bucket;self.object_prefix=object_prefix

    def _part_name(self,uid,upload_id,part):return f'{self.object_prefix}/staging/{digest(uid)}/{upload_id}/{part}'

    def put_chunk(self,uid,upload_id,part,encoded,sha256):
        from .credits import fingerprint
        fingerprint(sha256)
        if type(part) is not int or not 0<=part<256 or type(encoded) is not str or len(encoded)>350000:raise CreditError('Invalid project chunk')
        try:raw=base64.b64decode(encoded,validate=True)
        except ValueError as error:raise CreditError('Invalid project chunk encoding') from error
        if hashlib.sha256(raw).hexdigest()!=sha256:raise CreditError('Project chunk failed its integrity check')
        upload=self.store.transaction(lambda tx:self._upload(tx,uid,upload_id))
        if upload['state']!='uploading':raise Conflict('This save no longer accepts chunks')
        if part>=upload['chunks'] or len(raw)!=min(CHUNK_BYTES,upload['size']-part*CHUNK_BYTES):raise CreditError('Project chunk has the wrong size')
        blob=self.bucket.blob(self._part_name(uid,upload_id,part));blob.metadata={'sha256':sha256}
        try:blob.upload_from_string(raw,content_type='application/octet-stream',if_generation_match=0,checksum='crc32c')
        except PreconditionFailed:
            blob.reload()
            if blob.size!=len(raw) or (blob.metadata or {}).get('sha256')!=sha256:raise Conflict('Chunk already contains different content')
        return {'stored':True}

    def complete(self,uid,upload_id):
        upload=self.store.transaction(lambda tx:self._upload(tx,uid,upload_id))
        if upload['state']=='completed':return upload['result']
        if upload['state']!='uploading':raise Conflict('This save was cancelled')
        if self.clock()-upload['createdAt']>24*3600:raise Conflict('This save expired. Cancel it and start a new save')
        parts=[]
        for i in range(upload['chunks']):
            blob=self.bucket.blob(self._part_name(uid,upload_id,i))
            try:
                blob.reload();raw=blob.download_as_bytes(if_generation_match=int(blob.generation),checksum='crc32c')
            except NotFound as error:raise Conflict('Some project chunks are missing. Retry the save') from error
            if hashlib.sha256(raw).hexdigest()!=(blob.metadata or {}).get('sha256'):raise Conflict('Project chunk failed its integrity check')
            parts.append(raw)
        raw=b''.join(parts)
        if len(raw)!=upload['size'] or hashlib.sha256(raw).hexdigest()!=upload['sha256']:raise Conflict('Project integrity check failed')
        try:
            def invalid(value):raise ValueError('Non-finite JSON')
            if not isinstance(json.loads(raw,parse_constant=invalid),dict):raise ValueError('Project must be an object')
        except (ValueError,UnicodeError,RecursionError) as error:raise CreditError('Upload a valid JSON project file') from error
        name=f'{self.object_prefix}/projects/{digest(uid)}/{upload["projectId"]}/{upload_id}.json'
        final=self.bucket.blob(name);final.metadata={'sha256':upload['sha256']}
        try:final.upload_from_string(raw,content_type='application/json',if_generation_match=0,checksum='crc32c')
        except PreconditionFailed:
            final.reload()
            if final.size!=len(raw) or (final.metadata or {}).get('sha256')!=upload['sha256']:raise Conflict('Saved snapshot differs from the admitted project')
        generation=int(final.generation)
        def commit(tx):
            current=self._upload(tx,uid,upload_id)
            if current['state']=='completed':return current['result'],None
            index=self._index(tx,uid);key=self._project_key(uid,current['projectId']);previous=tx.get('projects',key)
            if current['state']!='uploading':raise Conflict('This save was cancelled')
            if (previous['revision'] if previous else 0)!=current['expectedRevision']:raise Conflict('Project changed. Reload before replacing it')
            record=dict(id=current['projectId'],title=current['title'],size=current['size'],sha256=current['sha256'],
                        revision=current['expectedRevision']+1,snapshot=upload_id,chunks=current['chunks'],
                        objectName=name,generation=generation,updatedAt=datetime.now(timezone.utc).isoformat())
            index['bytes']+=current['size']-(previous['size'] if previous else 0);index['reservedBytes']-=current['size'];index['uploads'].remove(upload_id)
            if record['id'] not in index['ids']:index['ids'].append(record['id'])
            current.update(state='completed',result=record)
            tx.set('projects',key,record);tx.set('project_index',digest(uid),index);tx.set('project_uploads',upload_id,current)
            return record,previous
        record,previous=self.store.transaction(commit)
        if previous:self._retire(previous)
        return record

    def download(self,uid,pid):
        def read(tx):
            self.profiles._account(tx,uid);record=tx.get('projects',self._project_key(uid,pid))
            if not record:raise ProjectUnavailable('Project is unavailable')
            return record
        row=self.store.transaction(read)
        try:raw=self.bucket.blob(row['objectName'],generation=row['generation']).download_as_bytes(if_generation_match=row['generation'],checksum='crc32c')
        except NotFound as error:raise Conflict('Saved project is unavailable. Contact the administrator') from error
        if len(raw)!=row['size'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:raise Conflict('Saved project failed its integrity check')
        return row,raw

    def _retire(self,row):
        # Retirement is separate from authorization: deleting metadata immediately
        # denies downloads; blob lifecycle removal follows the configured delay.
        blob=self.bucket.blob(row['objectName'],generation=row['generation'])
        try:
            blob.reload()
            if blob.custom_time is None:
                blob.custom_time=datetime.now(timezone.utc);blob.patch(if_generation_match=row['generation'],if_metageneration_match=blob.metageneration)
        except (NotFound,PreconditionFailed):pass

    def remove(self,uid,pid,revision):
        if type(revision) is not int or revision<1:raise CreditError('Use the current project revision')
        def apply(tx):
            index=self._index(tx,uid);key=self._project_key(uid,pid);row=tx.get('projects',key)
            if not row:raise ProjectUnavailable('Project is unavailable')
            if row['revision']!=revision:raise Conflict('Project changed. Reload before removing it')
            index['bytes']-=row['size'];index['ids'].remove(pid)
            tx.delete('projects',key);tx.set('project_index',digest(uid),index)
            return row
        self._retire(self.store.transaction(apply));return {'removed':True}
