"""Saved-context and downloadable-artifact acknowledgements survive transport."""
import asyncio,base64,hashlib,json,tempfile,unittest
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import Response
from hosted.native_runtime import NativeWorkspaceRuntime

class SnapshotProtocolTests(unittest.IsolatedAsyncioTestCase):
 def test_owned_snapshot_keeps_the_exact_acknowledged_bytes(self):
  with tempfile.TemporaryDirectory() as folder:
   runtime=NativeWorkspaceRuntime.__new__(NativeWorkspaceRuntime);runtime.root=Path(folder)
   pid='a'*32;raw=json.dumps({'format':'atmem.ai-architect.project','meta':{'id':pid,'name':'日本語','revision':1}},ensure_ascii=False,indent=3).encode()+b'\r\n'
   row={'id':pid,'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'revision':1}
   runtime.snapshot(pid,row,raw)
   self.assertEqual((Path(folder)/'projects'/(pid+'.atforma.json')).read_bytes(),raw)
 async def test_binary_download_preserves_both_receipt_headers(self):
  raw=b'ZIP fixture';artifact='a'*64;handoff=hashlib.sha256(raw).hexdigest();path='/api/engineering/handoff'
  runtime=NativeWorkspaceRuntime.__new__(NativeWorkspaceRuntime);runtime.uid='owner';runtime.lock=asyncio.Lock();runtime.paths={path};runtime.methods={path:['POST']};runtime.snapshot=lambda *args:None;runtime.app=FastAPI()
  @runtime.app.post(path)
  async def download():return Response(raw,media_type='application/zip',headers={'X-Artifact-Sha256':handoff,'X-Source-Artifact-Sha256':artifact})
  result=await runtime.dispatch({'uid':'owner','path':path,'projectId':'a'*32,'projectSnapshot':{}},{},b'',model='server-policy',policy={})
  self.assertEqual(base64.b64decode(result['base64']),raw)
  self.assertEqual(result['headers']['x-artifact-sha256'],handoff)
  self.assertEqual(result['headers']['x-source-artifact-sha256'],artifact)
