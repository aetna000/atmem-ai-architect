// Build exact emitted source and execute it in Linux/amd64. Never push an image.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
const target=path.resolve(process.argv[2]||''),provider=process.argv[3];
if(!process.argv[2]||!['aws','azure','gcp','ibm'].includes(provider))throw Error('Supply an emitted Terraform directory and aws, azure, gcp or ibm');
const tf=JSON.parse(fs.readFileSync(path.join(target,'main.tf.json'))),files=fs.readdirSync(path.join(target,'applications'));
const faq=!!JSON.parse(fs.readFileSync(path.join(target,'resource-schedule.json'))).publicFaqPlan?.entries?.length;
if(provider==='aws'&&!faq)throw Error('AWS container qualification currently applies only to the emitted public FAQ composition');
const host=process.env.ATMEM_QUALIFICATION_DOCKER_HOST||'unix://'+path.join(os.homedir(),'.colima/architect-qualification/docker.sock');
const tools=path.resolve(process.env.ATMEM_STRUCTURED_QUALIFICATION_SDK||'.local/azure-runtime-sdk');
const scratch=fs.mkdtempSync('/tmp/atmem-image-'),config=path.join(scratch,'docker-config');fs.mkdirSync(config);
const logs=path.join(target,'container-attempts',new Date().toISOString().replaceAll(':','-'));fs.mkdirSync(logs,{recursive:true});
// Locate trusted local CLI tooling without reading the user's registry credentials.
const plugins='/opt/homebrew/lib/docker/cli-plugins';
fs.writeFileSync(path.join(config,'config.json'),JSON.stringify({cliPluginsExtraDirs:fs.existsSync(plugins)?[plugins]:[]}));
const env={PATH:process.env.PATH,HOME:scratch,DOCKER_HOST:host,DOCKER_CONFIG:config},checks=[],images=[];
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
function run(name,args,{cwd=target,timeout=300000,input}={}){
 const r=spawnSync('docker',args,{cwd,env,input,encoding:'utf8',timeout,maxBuffer:8*1024*1024});
 const text=(r.stdout||'')+'\n'+(r.stderr||'');fs.writeFileSync(path.join(logs,name+'.log'),text);
 checks.push({name,passed:r.status===0&&!r.error,exitCode:r.status,error:r.error?.message||null,logSha256:sha(text)});
 if(r.status!==0||r.error)throw Error(name+' failed: '+text.slice(-2000));return r.stdout;
}
try{
 for(const address of files){
  if(!/^block_[0-9a-f]+$/.test(address))throw Error('Invalid compiler application path');
  const app=path.join(target,'applications',address),image='atmem-qualification/'+provider+'-'+address+':local',name='atmem-qa-'+provider+'-'+process.pid;
  const hashes=Object.fromEntries(fs.readdirSync(app,{recursive:true}).filter(n=>fs.statSync(path.join(app,n)).isFile()).map(n=>[n,sha(fs.readFileSync(path.join(app,n)))]));
  run(address+'-image-build',['build','--platform','linux/amd64','--pull','--progress','plain','-t',image,'.'],{cwd:app});
  const inspection=JSON.parse(run(address+'-image-inspect',['image','inspect',image]))[0];
  if(inspection.Os!=='linux'||inspection.Architecture!=='amd64'||inspection.Config.User!=='10001:10001')throw Error('Image platform or runtime user mismatch');
  const appSettings=provider==='aws'?tf.resource.aws_lambda_function[address].environment.variables:provider==='azure'?tf.resource.azurerm_linux_web_app[address].app_settings:provider==='ibm'?Object.fromEntries(tf.resource.ibm_code_engine_app[address].run_env_variables.map(e=>[e.name,e.value])):Object.fromEntries(tf.resource.google_cloud_run_v2_service[address].template.containers.env.map(e=>[e.name,e.value]));
  const fields=faq?[]:JSON.parse(Buffer.from(appSettings.OUTPUT_CONTRACT_BASE64,'base64').toString()).fields;
  const fixture={OUTPUT_CONTRACT_BASE64:appSettings.OUTPUT_CONTRACT_BASE64,MAX_INPUT_BYTES:appSettings.MAX_INPUT_BYTES,MAX_OUTPUT_TOKENS:appSettings.MAX_OUTPUT_TOKENS};
  Object.assign(fixture,provider==='aws'?{REGION:'ap-southeast-2',ACCOUNT_ID:'123456789012',MODEL_ID:'anthropic.reviewed-model-v1:0',CATALOG_BUCKET:'reviewed-public-catalog',PUBLIC_ORIGIN:'https://fixture.execute-api.ap-southeast-2.amazonaws.com',AWS_EC2_METADATA_DISABLED:'true'}:provider==='azure'?{TENANT_ID:'11111111-1111-1111-1111-111111111111',API_CLIENT_ID:'22222222-2222-2222-2222-222222222222',SPA_CLIENT_ID:'33333333-3333-3333-3333-333333333333',MANAGED_IDENTITY_CLIENT_ID:'44444444-4444-4444-4444-444444444444',MODEL_RESOURCE_ID:'/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/reviewed/providers/Microsoft.CognitiveServices/accounts/reviewed-ai',MODEL_ENDPOINT:'https://reviewed-ai.openai.azure.com',MODEL_DEPLOYMENT:'reviewed-model',PUBLIC_ORIGIN:'https://reviewed-app.azurewebsites.net'}:provider==='ibm'?{ACCOUNT_ID:'a'.repeat(32),WATSONX_PROJECT_ID:'33333333-3333-3333-3333-333333333333',RUNTIME_INSTANCE_ID:'44444444-4444-4444-4444-444444444444',MODEL_REGION:'au-syd',MODEL_ID:'ibm/reviewed-model',IAM_PROFILE_ID:'Profile-fixture',APPID_TENANT_ID:'11111111-1111-1111-1111-111111111111',APPID_CLIENT_ID:'22222222-2222-2222-2222-222222222222',APPID_ISSUER:'https://au-syd.appid.cloud.ibm.com/oauth/v4/11111111-1111-1111-1111-111111111111',AUTH_SCOPE:'reviewed-app/process',PUBLIC_ORIGIN:'https://reviewed-app.fixture123.au-syd.codeengine.appdomain.cloud'}:{PROJECT_ID:'reviewed-project',PROJECT_NUMBER:'123456789012',REGION:'australia-southeast1',SERVICE_NAME:'reviewed-app',MODEL_ID:'gemini-reviewed-version',PUBLIC_ORIGIN:'https://reviewed-app-123456789012.australia-southeast1.run.app'});
  if(faq){delete fixture.OUTPUT_CONTRACT_BASE64;delete fixture.MAX_INPUT_BYTES;Object.assign(fixture,provider==='azure'?{CATALOG_ACCOUNT:'reviewedstorage',CATALOG_CONTAINER:'public-catalog'}:{CATALOG_BUCKET:'reviewed-public-catalog'});}
  const envFile=path.join(scratch,'fixture.env');fs.writeFileSync(envFile,Object.entries(fixture).map(([k,v])=>k+'='+v).join('\n')+'\n',{mode:0o600});
  try{
   run(address+'-image-start',['run','-d','--platform','linux/amd64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--memory','512m','--cpus','1','--tmpfs','/tmp:rw,noexec,nosuid,size=32m','--env-file',envFile,'--name',name,image]);
   const privateProbe=`import http.client,time,json,os,sys\nsys.path.insert(0,'/app')\nfrom structured_output import decode_output,InvalidModelOutput\nfields=json.loads(__import__('base64').b64decode(os.environ['OUTPUT_CONTRACT_BASE64']))['fields']\nresult={f['name']:(f.get('values',['fixture'])[0] if f['type']=='string' else True if f['type']=='boolean' else 0) for f in fields}\nassert decode_output(json.dumps(result),fields)==result\nfor attempt in range(100):\n try:\n  c=http.client.HTTPConnection('127.0.0.1',8080,timeout=2);c.request('GET','/healthz');r=c.getresponse();assert r.status==200;assert json.loads(r.read())['status']=='running';c.close();break\n except (OSError,AssertionError):time.sleep(.1)\nelse:raise RuntimeError('Container never became live')\nc=http.client.HTTPConnection('127.0.0.1',8080,timeout=3);c.request('POST','/api/ask',body=json.dumps({'text':'Synthetic denied request'}),headers={'Content-Type':'application/json','Origin':os.environ['PUBLIC_ORIGIN']});r=c.getresponse();assert r.status==401;assert 'result' not in json.loads(r.read());assert r.getheader('Cache-Control')=='no-store';c.close()\nprint(json.dumps({'linuxStartup':'passed','unsignedRequest':'denied','actualOutputSchemaFields':len(fields),'cloudNetwork':'disabled'}))\n`;
   const publicProbe=`import http.client,time,json,os
for attempt in range(100):
 try:
  c=http.client.HTTPConnection('127.0.0.1',8080,timeout=2);c.request('GET','/healthz');r=c.getresponse();assert r.status==200;assert json.loads(r.read())['status']=='running';c.close();break
 except (OSError,AssertionError):time.sleep(.1)
else:raise RuntimeError('Container never became live')
for path in ['/','/app.js','/app.css','/config.json']:
 c=http.client.HTTPConnection('127.0.0.1',8080,timeout=2);c.request('GET',path);r=c.getresponse();assert r.status==200,(path,r.status);assert r.getheader('Cache-Control')=='no-store';r.read();c.close()
for origin in [None,'https://attacker.example']:
 c=http.client.HTTPConnection('127.0.0.1',8080,timeout=2);h={'Content-Type':'application/json'}
 if origin:h['Origin']=origin
 c.request('POST','/api/ask',body=json.dumps({'text':'Synthetic denied request'}),headers=h);r=c.getresponse();assert r.status==403;assert 'result' not in json.loads(r.read());c.close()
# Test the deployed factory on the actual image: a public visitor is admitted,
# then unavailable cloud catalog fails closed rather than inventing an answer.
c=http.client.HTTPConnection('127.0.0.1',8080,timeout=20);origin=os.environ['PUBLIC_ORIGIN'];c.request('POST','/api/ask',body=json.dumps({'text':'Synthetic unknown request'}),headers={'Content-Type':'application/json','Origin':origin,'Host':__import__('urllib.parse',fromlist=['urlsplit']).urlsplit(origin).netloc});r=c.getresponse();assert r.status==503,r.status;assert 'result' not in json.loads(r.read());c.close()
print(json.dumps({'linuxStartup':'passed','publicAssets':'passed','wrongOrigin':'denied','cloudUnavailable':'fails_closed','cloudNetwork':'disabled'}))
`;
   const probe=faq?publicProbe:privateProbe;
   run(address+'-image-health',['exec',name,'python','-I','-c',probe]);
   const tooling=path.join(scratch,'tooling');fs.mkdirSync(tooling,{recursive:true});
   for(const module of ['httpx','httpcore'])fs.cpSync(path.join(tools,module),path.join(tooling,module),{recursive:true});
   for(const test of fs.readdirSync(app).filter(n=>n.endsWith('_acceptance.py')||(faq&&n==='public_catalog_admin.py')))fs.copyFileSync(path.join(app,test),path.join(tooling,test));
   const assets=Object.fromEntries(fs.readdirSync(tooling,{recursive:true}).filter(file=>!file.split(path.sep).includes('__pycache__')&&!file.endsWith('.pyc')&&fs.statSync(path.join(tooling,file)).isFile()).map(file=>[file.split(path.sep).join('/'),fs.readFileSync(path.join(tooling,file)).toString('base64')]));
   const install=`import json,sys,base64\nfrom pathlib import Path,PurePosixPath\nroot=Path('/tmp/qualification');root.mkdir(exist_ok=True)\nfor name,value in json.load(sys.stdin).items():\n path=PurePosixPath(name)\n if path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe test tool path')\n file=root.joinpath(*path.parts);file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(base64.b64decode(value,validate=True))\n`;
   run(address+'-copy-test-tooling',['exec','-i',name,'python','-I','-c',install],{input:JSON.stringify(assets)});
   const wrapper=`import sys,socket,runpy\nsys.path[:0]=['/tmp/qualification','/app']\ndef denied(*args,**kwargs):raise RuntimeError('Qualification forbids external sockets')\nsocket.socket.connect=denied;socket.socket.connect_ex=denied;socket.getaddrinfo=denied\nsys.argv=['${faq?'faq':provider}_acceptance.py','-v']\nrunpy.run_path('/tmp/qualification/${faq?'faq':provider}_acceptance.py',run_name='__main__')\n`;
   run(address+'-image-runtime-tests',['exec',name,'python','-I','-c',wrapper]);
   images.push({component:address,imageId:inspection.Id,os:inspection.Os,architecture:inspection.Architecture,runtimeUser:inspection.Config.User,sourceFileHashes:hashes,actualContractFields:faq?['answer','citations','abstained']:fields.map(f=>f.name),testTooling:'Pinned pure-Python httpx/httpcore copied as local test tools; delivery image and application source unchanged.'});
  }finally{const log=spawnSync('docker',['logs',name],{env,encoding:'utf8'});fs.writeFileSync(path.join(logs,address+'-container.log'),(log.stdout||'')+'\n'+(log.stderr||''));spawnSync('docker',['rm','-f',name],{env,encoding:'utf8'});}
 }
}catch(error){checks.push({name:'container-qualification',passed:false,error:error.message});process.exitCode=1;}
finally{
 const receipt={kind:'emitted-linux-container-qualification',provider,application:faq?'public-faq':'private-structured',checks,images,logDirectory:path.relative(target,logs),passed:images.length>0&&checks.every(c=>c.passed),cloudOperations:false,imagePublished:false,vulnerabilityScan:'not_run',boundary:'Exact emitted Dockerfile/source and hash-locked dependencies built as Linux/amd64, nonroot read-only runtime with network disabled, actual schema/startup/origin or unsigned-request checks and emitted ASGI/lifecycle/scripted transport tests against delivery-image application modules. No real provider identity/model, account plan or deployment; image vulnerability scanning is separate.'};
 fs.writeFileSync(path.join(logs,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');fs.writeFileSync(path.join(target,'container-qualification.json'),JSON.stringify(receipt,null,2)+'\n');fs.rmSync(scratch,{recursive:true,force:true});console.log(JSON.stringify({passed:receipt.passed,images:images.map(i=>({component:i.component,imageId:i.imageId})),checks:checks.map(c=>({name:c.name,passed:c.passed})),receipt:path.join(target,'container-qualification.json')}));
}
