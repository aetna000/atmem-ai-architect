import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"build/block_7261672d666e"))
import copy
import importlib.util
import json
from pathlib import Path
import sys
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import unittest
from unittest.mock import patch
root=Path(__file__).resolve().parents[1]/'connectors'
for name in ['catalog_admin','connector_sync']:
    spec=importlib.util.spec_from_file_location(name,root/(name+'.py'));module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
sync=sys.modules['connector_sync']

class Checkpoint:
    def __init__(self):self.value=None
    def load(self,source):return copy.deepcopy(self.value)
    def save(self,source,value):self.value=copy.deepcopy(value)
class Store:
    def __init__(self):self.items={};self.fail_after=None;self.writes=0
    def get(self,key):return copy.deepcopy(self.items.get(key))
    def put(self,item,expected):
        if self.fail_after is not None and self.writes>=self.fail_after:raise RuntimeError('Synthetic outage')
        current=self.items.get(item['id']);assert (current.get('revision') if current else None)==expected
        self.writes+=1;result={**item,'revision':str(self.writes)};self.items[item['id']]=result;return result
    def delete(self,key,expected):assert self.items[key]['revision']==expected;del self.items[key]

class ConnectorContractTests(unittest.TestCase):
    def snapshot(self):return {'snapshotId':'snapshot-1','complete':True,'permissionsComplete':True,'documents':[{'sourceId':'source-doc','sourceVersion':'1','title':'Policy','text':'Synthetic policy','allowedSubjects':['alice'],'allowedRegions':['AU']}]}
    def test_local_http_source_contract_requires_complete_permissions(self):
        payload=self.snapshot()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                raw=json.dumps(payload).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(raw)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            endpoint=f'http://127.0.0.1:{server.server_port}/snapshot'
            with self.assertRaises(ValueError):sync.fetch_snapshot(endpoint)
            self.assertEqual(sync.fetch_snapshot(endpoint,allow_local_fixture=True)['snapshotId'],'snapshot-1')
            payload['permissionsComplete']=False
            with self.assertRaises(ValueError):sync.fetch_snapshot(endpoint,allow_local_fixture=True)
        finally:server.shutdown();server.server_close();thread.join()
    def test_updates_deletes_and_acl_revocation_reconcile(self):
        store,checkpoint=Store(),Checkpoint();snapshot=self.snapshot()
        sync.synchronize(snapshot,'sharepoint-test',store,checkpoint)
        snapshot['documents'][0]['sourceVersion']='2';snapshot['documents'][0]['allowedSubjects']=[]
        sync.synchronize(snapshot,'sharepoint-test',store,checkpoint)
        self.assertEqual(next(iter(store.items.values()))['allowedSubjects'],[])
        snapshot['documents']=[];sync.synchronize(snapshot,'sharepoint-test',store,checkpoint)
        self.assertEqual(store.items,{})
    def test_partial_failure_retains_inventory_for_retry_and_delete(self):
        store,checkpoint=Store(),Checkpoint();snapshot=self.snapshot();snapshot['documents'].append({**snapshot['documents'][0],'sourceId':'second'})
        store.fail_after=1
        with self.assertRaises(RuntimeError):sync.synchronize(snapshot,'confluence-test',store,checkpoint)
        self.assertEqual(len(checkpoint.value['pending']),2);self.assertEqual(len(store.items),1)
        store.fail_after=None;snapshot['documents']=[];sync.synchronize(snapshot,'confluence-test',store,checkpoint)
        self.assertEqual(store.items,{});self.assertNotIn('pending',checkpoint.value)
    def test_unknown_permissions_do_not_renew_access_leases(self):
        store,checkpoint=Store(),Checkpoint();snapshot=self.snapshot();sync.synchronize(snapshot,'source',store,checkpoint)
        before=copy.deepcopy(store.items);snapshot['permissionsComplete']=False
        with self.assertRaises(ValueError):sync.synchronize(snapshot,'source',store,checkpoint)
        self.assertEqual(store.items,before)
    def test_duplicate_source_ids_fail_before_any_writes(self):
        snapshot=self.snapshot();snapshot['documents']*=2;store,checkpoint=Store(),Checkpoint()
        with self.assertRaises(ValueError):sync.synchronize(snapshot,'source',store,checkpoint)
        self.assertEqual(store.writes,0)
