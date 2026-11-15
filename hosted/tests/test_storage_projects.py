"""Real SQLite metadata plus an explicit object-storage protocol fixture.

This does not establish live Firebase Storage IAM or cloud deployment.
"""
import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from google.api_core.exceptions import PreconditionFailed,NotFound
from hosted.sqlite_store import SQLiteTransactions
from hosted.projects import Profiles,CHUNK_BYTES,ProjectUnavailable
from hosted.storage_projects import StorageProjects
from hosted.x_access import XIdentity
from hosted.credits import Conflict


class BucketFixture:
    def __init__(self):self.rows={};self.serial=0;self.fail_after_upload=False
    def blob(self,name,generation=None):return BlobFixture(self,name,generation)


class BlobFixture:
    def __init__(self,bucket,name,generation):
        self.bucket,self.name,self.generation=bucket,name,generation
        self.metadata={};self.custom_time=None;self.size=None;self.metageneration=None
    def reload(self):
        if self.name not in self.bucket.rows:raise NotFound('Synthetic missing object')
        row=self.bucket.rows[self.name]
        if self.generation is not None and self.generation!=row['generation']:raise NotFound('Synthetic missing generation')
        self.generation=row['generation'];self.metadata=copy.deepcopy(row['metadata']);self.custom_time=row['custom_time']
        self.metageneration=row['metageneration'];self.size=len(row['raw'])
    def upload_from_string(self,raw,**options):
        if options.get('if_generation_match')==0 and self.name in self.bucket.rows:raise PreconditionFailed('Synthetic existing object')
        self.bucket.serial+=1;self.generation=self.bucket.serial
        self.bucket.rows[self.name]=dict(raw=raw,generation=self.generation,metadata=copy.deepcopy(self.metadata),custom_time=None,metageneration=1)
        if self.bucket.fail_after_upload and self.name.endswith('.json'):
            self.bucket.fail_after_upload=False;raise TimeoutError('Synthetic lost successful upload response')
    def download_as_bytes(self,**options):
        self.reload()
        if options.get('if_generation_match')!=self.generation:raise PreconditionFailed('Generation changed')
        raw=self.bucket.rows[self.name]['raw']
        return raw[options.get('start',0):options['end']+1] if 'end' in options else raw
    def patch(self,**options):
        row=self.bucket.rows[self.name]
        if options.get('if_generation_match')!=row['generation'] or options.get('if_metageneration_match')!=row['metageneration']:raise PreconditionFailed('Metadata changed')
        row['custom_time']=self.custom_time;row['metageneration']+=1


class StorageProjectsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=SQLiteTransactions(Path(self.temp.name)/'metadata.sqlite')
        self.profiles=Profiles(self.store)
        for subject in ['1','2']:self.profiles.register(XIdentity('firebase-'+subject,subject,'User'))
        self.bucket=BucketFixture();self.projects=StorageProjects(self.store,self.profiles,self.bucket)
    def tearDown(self):self.temp.cleanup()
    def upload(self,raw,request='save',pid=None,revision=0):
        upload=self.projects.begin('1',request,title='Project',size=len(raw),sha256=hashlib.sha256(raw).hexdigest(),pid=pid,revision=revision)
        for part in range(upload['chunks']):
            data=raw[part*CHUNK_BYTES:(part+1)*CHUNK_BYTES]
            self.projects.put_chunk('1',upload['id'],part,base64.b64encode(data).decode(),hashlib.sha256(data).hexdigest())
        return upload

    def test_large_project_payloads_live_in_storage_and_roundtrip_without_metadata_blob_writes(self):
        raw=json.dumps({'requirements':['preserve text '*(CHUNK_BYTES//2)]}).encode()
        upload=self.upload(raw);saved=self.projects.complete('1',upload['id'])
        self.assertGreater(upload['chunks'],1)
        self.assertEqual(self.projects.download('1',saved['id'])[1],raw)
        with self.store.transaction.__self__.path.open('rb') as f:self.assertNotIn(b'preserve text preserve text',f.read())
        self.assertTrue(all(row['custom_time'] is None for name,row in self.bucket.rows.items() if name.startswith('architect/projects/')))
        with self.assertRaises(ProjectUnavailable):self.projects.download('2',saved['id'])

    def test_successful_blob_upload_with_lost_response_recovers_and_commits_once(self):
        raw=b'{"project":"recovery"}';upload=self.upload(raw)
        self.bucket.fail_after_upload=True
        with self.assertRaises(TimeoutError):self.projects.complete('1',upload['id'])
        self.assertEqual(self.projects.list('1')['projects'],[])
        result=self.projects.complete('1',upload['id']);self.projects.complete('1',upload['id'])
        self.assertEqual(self.projects.list('1')['usedBytes'],len(raw))
        self.assertEqual(self.projects.download('1',result['id'])[1],raw)

    def test_replacing_and_deleting_retire_only_old_generations_and_never_resurrect_old_receipts(self):
        first=self.upload(b'{"revision":1}');old=self.projects.complete('1',first['id'])
        second=self.upload(b'{"revision":2}','replace',old['id'],1);new=self.projects.complete('1',second['id'])
        self.assertIsNotNone(self.bucket.rows[old['objectName']]['custom_time'])
        self.assertIsNone(self.bucket.rows[new['objectName']]['custom_time'])
        self.projects.complete('1',first['id'])
        self.assertEqual(self.projects.download('1',new['id'])[1],b'{"revision":2}')
        self.projects.remove('1',new['id'],2)
        self.assertIsNotNone(self.bucket.rows[new['objectName']]['custom_time'])
        with self.assertRaises(ProjectUnavailable):self.projects.download('1',new['id'])

    def test_corrupt_staged_data_cannot_publish_a_project(self):
        upload=self.upload(b'{"complete":true}')
        name=next(iter(self.bucket.rows));self.bucket.rows[name]['raw']=b'{"corrupt":true}'
        with self.assertRaises(Conflict):self.projects.complete('1',upload['id'])
        self.assertEqual(self.projects.list('1')['projects'],[])
