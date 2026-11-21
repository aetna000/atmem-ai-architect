import {spawn} from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
const home=fs.mkdtempSync(path.join(os.tmpdir(),'atforma-memory-e2e-'));
const root=path.resolve(import.meta.dirname,'..');
const env={...process.env,ATMEM_ARCHITECT_HOME:home,ATMEM_ARCHITECT_PORT:'5175',ATMEM_ARCHITECT_SIDECAR_PORT:'8767'};
const logs=fs.openSync(path.join(home,'servers.log'),'a');
const children=[];
const start=(cmd,args)=>{const child=spawn(cmd,args,{cwd:root,env,stdio:['ignore',logs,logs]});children.push(child);return child;};
async function wait(url){for(let n=0;n<150;n++){try{const r=await fetch(url);if(r.ok)return;}catch{}await new Promise(r=>setTimeout(r,100));}throw Error('Test service did not start: '+url);}
try{
 start(path.join(root,process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python'),['-m','uvicorn','server.tests.e2e_app:app','--host','127.0.0.1','--port','8767','--no-access-log']);
 start(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5175']);
 await Promise.all([wait('http://127.0.0.1:8767/api/session'),wait('http://127.0.0.1:5175')]);
 const test=spawn(process.execPath,['scripts/memory-e2e.mjs'],{cwd:root,env,stdio:'inherit'});
 const code=await new Promise(resolve=>test.on('exit',resolve));
 if(code!==0){console.error(fs.readFileSync(path.join(home,'servers.log'),'utf8').slice(-5000));process.exitCode=code||1;}
 console.log('Isolated AtMem test store:',home);
}catch(error){console.error(fs.readFileSync(path.join(home,'servers.log'),'utf8').slice(-3000));throw error;}finally{for(const child of children)child.kill('SIGTERM');fs.closeSync(logs);}
