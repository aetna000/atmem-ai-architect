import base64
import hashlib
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from server.app import app, TOKEN
from server.request_uploads import RequestUploads, CHUNK_BYTES, MAX_BYTES
from server.terraform_routes import UPLOADS

class RequestUploadTests(unittest.TestCase):
    def test_large_unicode_request_is_lossless_and_one_use(self):
        raw=('🧠'*100000).encode(); store=RequestUploads(); key=store.start(len(raw),hashlib.sha256(raw).hexdigest())['uploadId']
        for index,offset in enumerate(range(0,len(raw),CHUNK_BYTES)):
            store.append(key,index,raw[offset:offset+CHUNK_BYTES])
        self.assertEqual(store.take(key),raw)
        with self.assertRaises(ValueError): store.take(key)

    def test_order_size_checksum_expiry_cancel_and_quota(self):
        s=RequestUploads();raw=b'hello';digest=hashlib.sha256(raw).hexdigest()
        with self.assertRaises(ValueError):s.start(MAX_BYTES+1,digest)
        key=s.start(5,digest)['uploadId']
        with self.assertRaises(ValueError):s.append(key,1,raw)
        with self.assertRaises(ValueError):s.append(key,0,b'x'*6)
        with self.assertRaises(ValueError):s.take(key)
        key=s.start(5,digest)['uploadId'];s.append(key,0,b'other')
        with self.assertRaises(ValueError):s.take(key)
        key=s.start(5,digest)['uploadId'];s.rows[key]['updated']-=1801
        with self.assertRaises(ValueError):s.append(key,0,raw)
        key=s.start(5,digest)['uploadId'];s.cancel(key)
        with self.assertRaises(ValueError):s.take(key)
        keys=[s.start(MAX_BYTES,digest)['uploadId'] for _ in range(2)]
        with self.assertRaises(ValueError):s.start(1,digest)
        for key in keys:s.cancel(key)

    def test_authenticated_chunk_route_preserves_large_request_and_rejects_executable_files(self):
        import json
        client=TestClient(app);headers={'Authorization':f'Bearer {TOKEN}'}
        self.assertEqual(client.post('/api/terraform/uploads/start',json={'bytes':1,'sha256':'a'*64}).status_code,401)
        def upload(value):
            raw=json.dumps(value).encode();reply=client.post('/api/terraform/uploads/start',headers=headers,json={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()});self.assertEqual(reply.status_code,200);key=reply.json()['uploadId']
            for i,offset in enumerate(range(0,len(raw),CHUNK_BYTES)):
                r=client.post('/api/terraform/uploads/chunk',headers=headers,json={'uploadId':key,'index':i,'data':base64.b64encode(raw[offset:offset+CHUNK_BYTES]).decode()});self.assertEqual(r.status_code,200)
            return key
        project={'requirements':'preserved '*40000}
        key=upload({'project':project,'environment':'staging'})
        with patch('server.terraform_routes.validate',return_value={'status':'unavailable','message':'No CLI test executed','checks':[]}) as validate:
            response=client.post('/api/terraform/validate-upload',headers=headers,json={'uploadId':key});self.assertEqual(response.status_code,200);self.assertEqual(validate.call_args.args[0].project,project)
        key=upload({'project':project,'files':{'main.tf':'not admitted'}})
        with patch('server.terraform_routes.validate') as validate:
            self.assertEqual(client.post('/api/terraform/validate-upload',headers=headers,json={'uploadId':key}).status_code,422);validate.assert_not_called()
