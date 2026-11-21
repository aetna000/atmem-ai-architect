"""Real private process, original HTTP routes and installed AtMem; no model spend."""
import base64,hashlib,json,os,subprocess,sys,tempfile,unittest
from importlib.util import find_spec
from pathlib import Path
from server.memory_worker import EXPECTED_ATMEM_VERSION

@unittest.skipUnless(find_spec('atbots'),'Native worker qualification uses hosted/worker-requirements.lock')
class NativeWorkerProcessTests(unittest.TestCase):
 def test_real_atmem_and_existing_engineering_lifecycle_survive_native_process_transport(self):
  with tempfile.TemporaryDirectory() as temporary:
   pid='a'*32;file={'format':'atmem.ai-architect.project','formatVersion':'2.3.0','meta':{'id':pid,'name':'Warehouse','revision':1},'design':{'provider':'tools','nodes':[],'edges':[]},'discovery':{'problem':'Preserve warehouse shipment history'},'requirements':[{'id':'must-one','statement':'Warehouse shipments retain history','source':'user','priority':'must'}],'decisions':[]}
   raw=json.dumps(file).encode();snapshot={'id':pid,'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'revision':1}
   config={'uid':'2','root':temporary,'brokerSocket':temporary+'/not-used.sock','capability':'synthetic-capability'}
   requests=[]
   for path,body in [('/api/memory/sync',{'projectId':pid,'file':file}),('/api/memory/overview',{'projectId':pid}),('/api/engineering/create',{'projectId':pid,'model':'ignored-browser-model','effort':'high'}),('/api/engineering/list',{'projectId':pid})]:
    requests.append({'job':{'id':hashlib.sha256(path.encode()).hexdigest(),'uid':'2','projectId':pid,'path':path,'projectSnapshot':snapshot},'body':body,'snapshot':base64.b64encode(raw).decode(),'model':'openai/gpt-6.1-sol','policy':{'maxOutputTokens':4096}})
   environment={key:value for key,value in os.environ.items() if key in {'PATH','LANG','LC_ALL','SYSTEMROOT'}}
   with tempfile.TemporaryFile(mode='w+') as errors:
    process=subprocess.Popen([sys.executable,'-m','hosted.native_worker_process'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,text=True,env=environment)
    try:
     process.stdin.write(json.dumps(config)+'\n');process.stdin.flush();ready=process.stdout.readline()
     if not ready:
      process.wait(timeout=60);errors.seek(0)
      self.fail('Native fixture process failed during startup:\n'+errors.read())
     responses=[json.loads(ready)]
     for item in requests:
      process.stdin.write(json.dumps(item)+'\n');process.stdin.flush();responses.append(json.loads(process.stdout.readline()))
     process.stdin.close();self.assertEqual(process.wait(timeout=60),0)
    finally:
     if process.poll() is None:process.kill();process.wait()
     if not process.stdin.closed:process.stdin.close()
     process.stdout.close()

   self.assertTrue(responses[0]['ready'])
   for response in responses[1:]:self.assertEqual(response['response']['status'],200,response)
   self.assertEqual(responses[1]['response']['body']['status'],'ready');self.assertIn(EXPECTED_ATMEM_VERSION,responses[1]['response']['body']['engine'])
   self.assertTrue((Path(temporary)/'memory/memories.db').is_file())
   # The original session service pins the administrator-selected model, not browser model/effort.
   created=responses[3]['response']['body'];self.assertEqual(created['model'],'openai/gpt-6.1-sol');self.assertEqual(created['effort'],'medium')
   self.assertNotIn('synthetic-capability',json.dumps(responses))
