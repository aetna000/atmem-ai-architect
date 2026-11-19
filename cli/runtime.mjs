import {ensureTerraform,terraformStatus} from './terraform-runtime.mjs';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import {spawn,spawnSync} from 'node:child_process';
import {createHash,randomUUID} from 'node:crypto';
import {createInterface} from 'node:readline';
import {Writable} from 'node:stream';
import {setTimeout as delay} from 'node:timers/promises';
import {inspectInstance,manageInstance,stopInstance} from './instance.mjs';
import {login,providerList} from './providers.mjs';
import {gunzipSync} from 'node:zlib';
import {unzipSync} from 'fflate';
import {createServer} from 'node:net';
export const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
export const memoryVersion=fs.readFileSync(path.join(root,'server/memory-requirements.txt'),'utf8').match(/^atmem==(\d+\.\d+\.\d+)$/m)?.[1];
if(!memoryVersion)throw Error('A stable AtMem runtime pin is required.');
export const metadata=JSON.parse(fs.readFileSync(path.join(root,'package.json'),'utf8'));
const lock=JSON.parse(fs.readFileSync(path.join(root,'packaging/uv-release-lock.json'),'utf8'));
export const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
export function platformTarget(platform=process.platform,arch=process.arch,musl=platform==='linux'&&!process.report.getReport().header.glibcVersionRuntime){
 const key=`${platform}-${arch}${platform==='linux'&&musl?'-musl':''}`;
 if(!lock.targets[key])throw Error(`No supported runtime for ${platform}/${arch}. Supported: Windows, macOS and Linux on x64/arm64.`);
 return lock.targets[key];
}
export function applicationHome(env=process.env,userHome=os.homedir()){
 return path.resolve(env.ATMEM_ARCHITECT_HOME||env.ATFORMA_HOME||(fs.existsSync(path.join(userHome,'.atforma'))?path.join(userHome,'.atforma'):path.join(userHome,'.atmem-ai-architect')));
}
const commands = new Set(['start','restart','stop','status','open','setup','doctor','version','help','login','providers']);
export function parseArgs(args){
 const options={command:'start',port:5174,open:true,json:false};
 let command;
 for(let i=0;i<args.length;i++){
  const arg=args[i];
  if(arg==='--no-open') options.open=false;
  else if(arg==='--json') options.json=true;
  else if(arg==='--help'||arg==='-h') options.help=true;
  else if(arg==='--version'||arg==='-v') options.version=true;
  else if(arg==='--port'){
   const value=args[++i];
   if(!/^\d+$/.test(value||'')||+value<1024||+value>65535)throw Error('--port needs a number from 1024 to 65535.');
   options.port=+value;
   options.customPort=true;
  }else if(arg==='--data-dir'){
   const value=args[++i];
   if(!value||value.startsWith('--'))throw Error('--data-dir needs a directory.');
   options.home=path.resolve(value);
  }else if(command==='login'&&!options.provider&&!arg.startsWith('-')){
   options.provider=arg;
  }else if(!command&&(commands.has(arg)||['--setup','--doctor'].includes(arg))){
   command=arg.replace(/^--/,'');
  }else throw Error(`Unknown argument: ${arg}. Run atmemai --help.`);
 }
 options.command=options.help?'help':options.version?'version':command||'start';
 const allowed=options.command==='help'||options.command==='version';
 if(!allowed&&options.customPort&&!['start','restart'].includes(options.command))throw Error('--port applies to start and restart.');
 if(!allowed&&!options.open&&!['start','restart'].includes(options.command))throw Error('--no-open applies to start and restart.');
 if(!allowed&&options.json&&!['status','doctor','providers'].includes(options.command))throw Error('--json applies to status, doctor and providers.');
 return options;
}

async function run(command,args,options={}){
 await new Promise((resolve,reject)=>{const child=spawn(command,args,{stdio:'inherit',windowsHide:true,...options});child.on('error',reject);child.on('exit',(code,signal)=>code===0?resolve():reject(Error(`${path.basename(command)} failed (${signal||code}). Setup was not marked complete; rerun to retry.`)));});
}
async function download(url){
 const response=await fetch(url,{signal:AbortSignal.timeout(120000)});if(!response.ok)throw Error(`Runtime download failed (${response.status}); check internet access and retry.`);
 const chunks=[];let total=0;
 for await(const chunk of response.body){total+=chunk.length;if(total>80*1024*1024)throw Error('Runtime archive exceeds its size limit.');chunks.push(chunk);}
 return Buffer.concat(chunks);
}
export function extractUv(bytes,target){
 if(target.archive==='zip'){
  const files=unzipSync(bytes,{filter:file=>{if(file.name.split('/').at(-1)!==target.binary)return false;if(file.originalSize>128*1024*1024)throw Error('Runtime binary exceeds its size limit.');return true;}}),matches=Object.entries(files).filter(([name])=>name.split('/').at(-1)===target.binary);
  if(matches.length!==1)throw Error('Expected one uv executable in its archive.');return Buffer.from(matches[0][1]);
 }
 const tar=gunzipSync(bytes,{maxOutputLength:256*1024*1024});const matches=[];
 for(let offset=0;offset+512<=tar.length;){
  const header=tar.subarray(offset,offset+512);if(header.every(b=>b===0))break;
  const text=(start,end)=>header.subarray(start,end).toString().replace(/\0.*$/s,'');const name=text(0,100),size=parseInt(text(124,136).trim()||'0',8),type=text(156,157);
  if(!Number.isSafeInteger(size)||size<0||offset+512+size>tar.length)throw Error('Invalid runtime archive entry.');
  if(name.split('/').at(-1)===target.binary){if(!['0',''].includes(type)||size>128*1024*1024)throw Error('Runtime executable is not a bounded regular file.');matches.push(tar.subarray(offset+512,offset+512+size));}
  offset+=512+Math.ceil(size/512)*512;
 }
 if(matches.length!==1)throw Error('Expected one uv executable in its archive.');return matches[0];
}
async function uvExecutable(home){
 const target=platformTarget(),folder=path.join(home,'runtime-tools',`uv-${lock.version}`),binary=path.join(folder,target.binary),receipt=path.join(folder,'receipt.json');
 try{const saved=JSON.parse(fs.readFileSync(receipt,'utf8'));if(saved.archiveSha256===target.sha256&&saved.binarySha256===digest(fs.readFileSync(binary)))return binary;}catch{}
 process.stdout.write('Preparing the private Python installer…\n');const archive=await download(target.url);
 if(digest(archive)!==target.sha256)throw Error('Runtime download checksum did not match the pinned release. Nothing was installed.');
 const data=extractUv(archive,target);fs.mkdirSync(folder,{recursive:true,mode:0o700});const temporary=binary+`.tmp-${process.pid}`;fs.writeFileSync(temporary,data,{mode:0o755});fs.renameSync(temporary,binary);
 fs.writeFileSync(receipt,JSON.stringify({archiveSha256:target.sha256,binarySha256:digest(data)},null,2)+'\n',{mode:0o600});return binary;
}
export function venvPython(folder,platform=process.platform){return path.join(folder,platform==='win32'?'Scripts':'bin',platform==='win32'?'python.exe':'python');}
export function runtimeDefinition(){
 const server=fs.readFileSync(path.join(root,'server/requirements.lock')),memory=fs.readFileSync(path.join(root,'server/memory-requirements.lock')),emulator=fs.readFileSync(path.join(root,'server/terraform-emulator-requirements.lock'));
 return {id:digest(Buffer.concat([server,memory,emulator,Buffer.from(`uv=${lock.version};python=3.13;${process.platform};${process.arch};${platformTarget().sha256}`)])).slice(0,20),server,memory,emulator};
}
export async function setupRuntime(home){
 const terraformBinary=process.env.ATMEM_ARCHITECT_TERRAFORM_BIN||process.env.ATFORMA_TERRAFORM_BIN||await ensureTerraform(home);
 const definition=runtimeDefinition(),folder=path.join(home,'runtimes',definition.id),serverPython=venvPython(path.join(folder,'server')),memoryPython=venvPython(path.join(folder,'memory')),emulatorPython=venvPython(path.join(folder,'emulator')),receipt=path.join(folder,'ready.json');
 try{const saved=JSON.parse(fs.readFileSync(receipt,'utf8'));if(saved.id===definition.id&&fs.existsSync(serverPython)&&fs.existsSync(memoryPython)&&fs.existsSync(emulatorPython))return {serverPython,memoryPython,emulatorPython,terraformBinary,folder};}catch{}
 fs.mkdirSync(folder,{recursive:true,mode:0o700});
 const lease=path.join(folder,'setup.lock');let descriptor;
 try{descriptor=fs.openSync(lease,'wx',0o600);fs.writeFileSync(descriptor,String(process.pid));}catch{throw Error(`Another setup is using ${folder}. Wait for it to finish; if it was interrupted, remove only its setup.lock and retry.`);}
 try{
  const uv=await uvExecutable(home),env={...process.env,UV_CACHE_DIR:path.join(home,'cache','uv'),UV_PYTHON_INSTALL_DIR:path.join(home,'runtime-tools','python'),UV_PYTHON_BIN_DIR:path.join(home,'runtime-tools','bin'),UV_NO_MODIFY_PATH:'1',UV_NO_PROGRESS:'1'};
  process.stdout.write('Preparing Python 3.13 and isolated application/AtMem environments…\n');
  await run(uv,['python','install','3.13'],{env});
  const found=spawnSync(uv,['python','find','--managed-python','3.13'],{env,encoding:'utf8',windowsHide:true});if(found.status!==0)throw Error('Managed Python could not be located.');const python=found.stdout.trim();
  for(const [name,requirements]of [['server','requirements.lock'],['memory','memory-requirements.lock'],['emulator','terraform-emulator-requirements.lock']]){
   const destination=path.join(folder,name);await run(uv,['venv','--python',python,destination],{env});
   await run(uv,['pip','install','--require-hashes','--python',venvPython(destination),'-r',path.join(root,'server',requirements),'--index-url','https://pypi.org/simple'],{env});
  }
  await run(serverPython,['-c','import fastapi,uvicorn; from server.attachments import extract; from server.engineering_routes import LocalEngineeringService'],{cwd:root,env:{...env,ATMEM_ARCHITECT_HOME:home}});
  await run(memoryPython,['-c',`from importlib.metadata import version; from atmem import Memory; assert version('atmem')==${JSON.stringify(memoryVersion)}`],{cwd:root,env});
  await run(emulatorPython,['-I','-m','ensurepip','--default-pip'],{cwd:root,env});
  await run(emulatorPython,['-I','-c',"import moto,flask,flask_cors,boto3;assert moto.__version__=='5.2.5'"],{cwd:root,env});
  fs.writeFileSync(receipt,JSON.stringify({id:definition.id,packageVersion:metadata.version,python:found.stdout.trim()},null,2)+'\n',{mode:0o600});return {serverPython,memoryPython,emulatorPython,terraformBinary,folder};
 }finally{if(descriptor!==undefined)fs.closeSync(descriptor);fs.rmSync(lease,{force:true});}
}
export async function checkPort(port){await new Promise((resolve,reject)=>{const server=createServer();server.once('error',()=>reject(Error(`Port ${port} is already in use. Try --port ${port+1}.`)));server.listen(port,'127.0.0.1',()=>server.close(resolve));});}
function openBrowser(url){
 const command=process.platform==='darwin'?'open':process.platform==='win32'?'rundll32.exe':'xdg-open',args=process.platform==='win32'?['url.dll,FileProtocolHandler',url]:[url];
 const child=spawn(command,args,{stdio:'ignore',windowsHide:true});child.on('error',()=>process.stdout.write(`Open ${url} in your browser.\n`));child.unref();
}
const help = `AtMem AI Architect ${metadata.version}

Usage: atmemai [command] [options]

  start       Start Architect and open the browser (default)
  restart     Confirm, then restart the running Architect
  stop        Confirm, then stop the running Architect
  status      Show the version, server state and storage paths
  open        Open the running Architect in your browser
  providers   List available model login methods
  login NAME  Start provider sign-in or enter an API key
  setup       Install the private runtimes without starting
  doctor      Show runtime and platform diagnostics
  version     Show the installed version
  help        Show this help

  --data-dir PATH  Select a data directory
  --port PORT      Server port for start or restart (default 5174)
  --no-open        Start or restart without opening a browser
  --json           Machine-readable status, doctor or providers output
  --help, --version

The first run installs private Python, AtMem and Terraform runtimes.
atmem-architect accepts the same commands.`;

async function readAnswer(prompt, hidden=false) {
 if(!process.stdin.isTTY) return null;
 const output=hidden?new Writable({write(_chunk,_encoding,done){done();}}):process.stdout;
 const input=createInterface({input:process.stdin,output,terminal:true,historySize:0});
 process.stdout.write(prompt);
 const answer=await new Promise(resolve=>{
  input.once('close',()=>resolve(null));
  input.once('SIGINT',()=>input.close());
  input.question('',resolve);
 });
 input.close();
 if(hidden||answer===null)process.stdout.write('\n');
 return answer;
}

function storage(home) {
 return {
  data:home,package:root,projects:path.join(home,'projects'),trash:path.join(home,'bin'),
  workspaces:path.join(home,'workspaces'),memory:path.join(home,'memory'),
  memoryDatabase:path.join(home,'memory','memories.db'),memoryState:path.join(home,'memory','state.sqlite'),
  runtimes:path.join(home,'runtimes'),
 };
}
const serverUrl = port=>`http://127.0.0.1:${port}`;
const isActive = instance=>['starting','running','stopping'].includes(instance.state);
const printJson = value=>console.log(JSON.stringify(value,null,2));

async function showStatus(home, options, instance) {
 const {receipt,instanceId,...server}=instance;
 const paths=storage(home);
 const data={
  version:metadata.version,memoryVersion,paths,server:{
   ...server,...(receipt?{pid:receipt.pid,url:serverUrl(receipt.port)}:{}),
  },
 };
 if(options.command==='doctor'){
  const definition=runtimeDefinition();
  printJson({...data,home,node:process.version,platform:process.platform,arch:process.arch,
   runtimeReady:fs.existsSync(path.join(paths.runtimes,definition.id,'ready.json')),
   terraform:terraformStatus(home),modelAuthentication:"Run atmemai providers to see model sign-in options",providers:providerList()});
 }else if(options.json)printJson(data);
 else {
  console.log(`AtMem AI Architect ${data.version}
AtMem memory ${data.memoryVersion}
Server ${server.state}${receipt?` · ${data.server.url} · PID ${receipt.pid}`:''}`);
  if(server.version&&server.version!==data.version)console.log(`Running version ${server.version}`);
  for(const [label,location] of Object.entries({
   'Data':paths.data,'Package':paths.package,'Projects':paths.projects,'Workspaces':paths.workspaces,
   'AtMem memory':paths.memory,'Memory database':paths.memoryDatabase,'Memory state':paths.memoryState,'Runtimes':paths.runtimes,
  })) console.log(`${label}  ${location}`);
 }
}

async function serve(home,port,open,runtime) {
 let child,exited,stopped=false;
 const stop=()=>{
  if(stopped) return;
  stopped=true;
  child?.kill('SIGTERM');
 };
 const instanceId=randomUUID();
 const manager=await manageInstance(home,{port,version:metadata.version,memoryVersion,instanceId,onStop:stop});
 process.on('SIGINT',stop);
 process.on('SIGTERM',stop);
 try{
  const workspaces=storage(home).workspaces;
  fs.mkdirSync(workspaces,{recursive:true,mode:0o700});
  const env={...process.env,ATMEM_ARCHITECT_HOME:home,ATMEM_ARCHITECT_PORT:String(port),ATMEM_ARCHITECT_SIDECAR_PORT:String(port),
   ATMEM_ARCHITECT_INSTANCE_ID:instanceId,ATMEM_ARCHITECT_MEMORY_PYTHON:runtime.memoryPython,
   ATMEM_ARCHITECT_TERRAFORM_EMULATOR_PYTHON:runtime.emulatorPython,ATMEM_ARCHITECT_TERRAFORM_BIN:runtime.terraformBinary,
   ATMEM_ARCHITECT_PROVIDER_CACHE:process.env.ATMEM_ARCHITECT_PROVIDER_CACHE||process.env.ATFORMA_PROVIDER_CACHE||path.join(home,'cache','terraform-providers'),
   ATMEM_ARCHITECT_ENABLE_ENGINEERING:'1',ATMEM_ARCHITECT_ENGINEERING_WORKSPACE_ROOT:workspaces};
  child=spawn(runtime.serverPython,['-m','uvicorn','server.packaged_app:app','--host','127.0.0.1','--port',String(port),'--no-access-log','--timeout-graceful-shutdown','20'],{cwd:root,env,stdio:'inherit',windowsHide:true});
  const exit=new Promise(resolve=>{
   child.once('error',error=>{exited={error};resolve(exited);});
   child.once('exit',(code,signal)=>{exited={code,signal};resolve(exited);});
  });
  try {
   const url=serverUrl(port);
   let ready=false;
   for(let count=0;count<90&&!stopped&&!exited;count++){
    try{
     const response=await fetch(url+'/api/cli-ready',{signal:AbortSignal.timeout(1200),redirect:'error'});
     ready=response.ok&&(await response.json()).instanceId===instanceId;
    }catch{}
    if(ready) break;
    await delay(500);
   }
   if(!stopped&&!ready)throw exited?.error||Error(exited?`Architect exited during startup (${exited.signal||exited.code}).`:'Architect startup timed out.');
   if(!stopped){
    manager.ready(child.pid);
    console.log(`AtMem AI Architect ${metadata.version}
Open ${url}
Press Ctrl+C to stop.`);
    if(open)openBrowser(url);
   }
   const result=await exit;
   if(!stopped&&(result.code!==0||result.error))throw result.error||Error(`Architect stopped (${result.signal||result.code}).`);
  }finally{
   if(!exited) {stop();await exit;}
  }
 }finally{
  process.removeListener('SIGINT',stop);
  process.removeListener('SIGTERM',stop);
  await manager.close();
 }
}

export async function main(args=process.argv.slice(2)){
 const options=parseArgs(args),{command}=options;
 if(command==='version'){console.log(metadata.version);return;}
 if(command==='help'){console.log(help);return;}
 const home=options.home||applicationHome();
 if(command==='providers'){
  const available=providerList();
  if(options.json)printJson(available);
  else for(const provider of available)console.log(`${provider.name.padEnd(14)} ${provider.method}`);
  return;
 }
 if(command==='login'){
  await login(options.provider,{readAnswer, instance:()=>inspectInstance(home),serverUrl});
  return;
 }
 if(command==='setup'){
  await setupRuntime(home);
  console.log('Architect and AtMem are installed. Run atmemai to open the app.');
  return;
 }
 const instance=await inspectInstance(home);
 if(command==='status'||command==='doctor')return showStatus(home,options,instance);
 if(instance.state==='unverified')throw Error('Architect instance identity could not be verified. Check atmemai status or stop the original launcher from its terminal.');
 if(command==='open'){
  if(instance.state!=='running')throw Error('Architect is not ready. Run atmemai start.');
  openBrowser(serverUrl(instance.port));
  return;
 }
 if(command==='stop'&&!isActive(instance)){console.log('Architect is stopped.');return;}
 if(instance.state==='stopping')throw Error('Architect is already shutting down. Retry shortly.');
 if(isActive(instance)){
  const action=command==='stop'?'Stop':'Restart';
  if(!process.stdin.isTTY)throw Error(`${action} requires confirmation from an interactive terminal. The running instance was left alone.`);
  const answer=await readAnswer(`${action} Architect at ${serverUrl(instance.port)}? Save your work first. [y/N] `);
  if(!/^(y|yes)$/i.test(answer?.trim()||'')){
   console.log('Architect is still running.');
   return;
  }
  if(command==='stop'){
   await stopInstance(home,instance.receipt);
   console.log('Architect stopped.');
   return;
  }
 }
 const port=options.customPort?options.port:instance.receipt?.port||options.port;
 if(instance.state==='stale'&&port!==instance.receipt.port) await checkPort(instance.receipt.port);
 if(!isActive(instance)||port!==instance.port)await checkPort(port);
 const runtime=await setupRuntime(home);
 if(isActive(instance)){
  await stopInstance(home,instance.receipt);
  await checkPort(port);
 }
 await serve(home,port,options.open,runtime);
}
