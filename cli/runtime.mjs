import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import {spawn,spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {unzipSync} from 'fflate';
import {createServer} from 'node:net';
export const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
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
export function parseArgs(args){
 const options={port:5174,open:true,setup:false,doctor:false};
 for(let i=0;i<args.length;i++){
  const arg=args[i];if(arg==='--no-open')options.open=false;
  else if(arg==='--setup')options.setup=true;
  else if(arg==='--doctor')options.doctor=true;
  else if(arg==='--help'||arg==='-h')options.help=true;
  else if(arg==='--version'||arg==='-v')options.version=true;
  else if(arg==='--port'){const value=args[++i];if(!/^\d+$/.test(value||'')||+value<1024||+value>65535)throw Error('--port needs a number from 1024 to 65535.');options.port=+value;}
  else if(arg==='--data-dir'){const value=args[++i];if(!value||value.startsWith('--'))throw Error('--data-dir needs a directory.');options.home=path.resolve(value);}
  else throw Error(`Unknown option: ${arg}. Run atmem-architect --help.`);
 }
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
 const server=fs.readFileSync(path.join(root,'server/requirements.lock')),memory=fs.readFileSync(path.join(root,'server/memory-requirements.lock'));
 return {id:digest(Buffer.concat([server,memory,Buffer.from(`uv=${lock.version};python=3.13;${process.platform};${process.arch};${platformTarget().sha256}`)])).slice(0,20),server,memory};
}
export async function setupRuntime(home){
 const definition=runtimeDefinition(),folder=path.join(home,'runtimes',definition.id),serverPython=venvPython(path.join(folder,'server')),memoryPython=venvPython(path.join(folder,'memory')),receipt=path.join(folder,'ready.json');
 try{const saved=JSON.parse(fs.readFileSync(receipt,'utf8'));if(saved.id===definition.id&&fs.existsSync(serverPython)&&fs.existsSync(memoryPython))return {serverPython,memoryPython,folder};}catch{}
 fs.mkdirSync(folder,{recursive:true,mode:0o700});
 const lease=path.join(folder,'setup.lock');let descriptor;
 try{descriptor=fs.openSync(lease,'wx',0o600);fs.writeFileSync(descriptor,String(process.pid));}catch{throw Error(`Another setup is using ${folder}. Wait for it to finish; if it was interrupted, remove only its setup.lock and retry.`);}
 try{
  const uv=await uvExecutable(home),env={...process.env,UV_CACHE_DIR:path.join(home,'cache','uv'),UV_PYTHON_INSTALL_DIR:path.join(home,'runtime-tools','python'),UV_PYTHON_BIN_DIR:path.join(home,'runtime-tools','bin'),UV_NO_MODIFY_PATH:'1',UV_NO_PROGRESS:'1'};
  process.stdout.write('Preparing Python 3.13 and isolated application/AtMem environments…\n');
  await run(uv,['python','install','3.13'],{env});
  const found=spawnSync(uv,['python','find','--managed-python','3.13'],{env,encoding:'utf8',windowsHide:true});if(found.status!==0)throw Error('Managed Python could not be located.');const python=found.stdout.trim();
  for(const [name,requirements]of [['server','requirements.lock'],['memory','memory-requirements.lock']]){
   const destination=path.join(folder,name);await run(uv,['venv','--python',python,destination],{env});
   await run(uv,['pip','install','--require-hashes','--python',venvPython(destination),'-r',path.join(root,'server',requirements),'--index-url','https://pypi.org/simple'],{env});
  }
  await run(serverPython,['-c','import fastapi,uvicorn; from server.attachments import extract; from server.engineering_routes import LocalEngineeringService'],{cwd:root,env:{...env,ATMEM_ARCHITECT_HOME:home}});
  await run(memoryPython,['-c',"from importlib.metadata import version; from atmem import Memory; assert version('atmem')=='2.3.10'"],{cwd:root,env});
  fs.writeFileSync(receipt,JSON.stringify({id:definition.id,packageVersion:metadata.version,python:found.stdout.trim()},null,2)+'\n',{mode:0o600});return {serverPython,memoryPython,folder};
 }finally{if(descriptor!==undefined)fs.closeSync(descriptor);fs.rmSync(lease,{force:true});}
}
export async function checkPort(port){await new Promise((resolve,reject)=>{const server=createServer();server.once('error',()=>reject(Error(`Port ${port} is already in use. Try --port ${port+1}.`)));server.listen(port,'127.0.0.1',()=>server.close(resolve));});}
function openBrowser(url){
 const command=process.platform==='darwin'?'open':process.platform==='win32'?'rundll32.exe':'xdg-open',args=process.platform==='win32'?['url.dll,FileProtocolHandler',url]:[url];
 const child=spawn(command,args,{stdio:'ignore',windowsHide:true});child.on('error',()=>process.stdout.write(`Open ${url} in your browser.\n`));child.unref();
}
export async function main(args=process.argv.slice(2)){
 const options=parseArgs(args);
 if(options.version){console.log(metadata.version);return;}
 if(options.help){console.log(`AtMem AI Architect ${metadata.version}\n\nUsage: atmem-architect [--port 5174] [--no-open] [--data-dir PATH]\n       atmem-architect --setup | --doctor | --version\n\nFirst run downloads a checksum-verified Python installer, Python and pinned app/AtMem dependencies.\nData and runtimes stay in your app data directory; no administrator access is needed.\nA model login/API key is selected in the UI. No cloud deployment is performed.`);return;}
 const home=options.home||applicationHome(),definition=runtimeDefinition();
 if(options.doctor){console.log(JSON.stringify({version:metadata.version,node:process.version,platform:process.platform,arch:process.arch,home,runtimeReady:fs.existsSync(path.join(home,'runtimes',definition.id,'ready.json')),modelAuthentication:'Select a model and sign in from Connections'},null,2));return;}
 if(!options.setup)await checkPort(options.port);
 const runtime=await setupRuntime(home);if(options.setup){console.log('Architect and AtMem are installed. Run atmem-architect to open the app.');return;}
 const workspaces=path.join(home,'workspaces');fs.mkdirSync(workspaces,{recursive:true,mode:0o700});
 const env={...process.env,ATMEM_ARCHITECT_HOME:home,ATMEM_ARCHITECT_PORT:String(options.port),ATMEM_ARCHITECT_SIDECAR_PORT:String(options.port),ATMEM_ARCHITECT_MEMORY_PYTHON:runtime.memoryPython,ATMEM_ARCHITECT_ENABLE_ENGINEERING:'1',ATMEM_ARCHITECT_ENGINEERING_WORKSPACE_ROOT:workspaces};
 const child=spawn(runtime.serverPython,['-m','uvicorn','server.packaged_app:app','--host','127.0.0.1','--port',String(options.port),'--no-access-log'],{cwd:root,env,stdio:'inherit',windowsHide:true});
 let stopped=false;const stop=()=>{stopped=true;child.kill('SIGTERM');};process.once('SIGINT',stop);process.once('SIGTERM',stop);
 try{
  const url=`http://127.0.0.1:${options.port}`;
  await new Promise((resolve,reject)=>{child.once('error',reject);child.once('exit',code=>reject(Error(`Architect exited before startup (${code}).`)));let count=0;const poll=async()=>{if(stopped)return resolve();try{const response=await fetch(url+'/api/session',{signal:AbortSignal.timeout(1500)});if(response.ok){console.log(`AtMem AI Architect ${metadata.version}\nOpen ${url}\nPress Ctrl+C to stop.`);if(options.open)openBrowser(url);return resolve();}}catch{}if(++count>90)return reject(Error('Architect startup timed out.'));setTimeout(poll,500);};void poll();});
  if(!stopped)await new Promise((resolve,reject)=>{child.once('exit',code=>code===0||stopped?resolve():reject(Error(`Architect stopped (${code}).`)));});
 }finally{stop();process.removeListener('SIGINT',stop);process.removeListener('SIGTERM',stop);}
}
