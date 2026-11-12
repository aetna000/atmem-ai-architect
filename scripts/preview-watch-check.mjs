// Regression for frozen previews whose ancestor directory is named .local.
import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {createServer} from 'node:net';
import assert from 'node:assert/strict';
const root=process.cwd(),dir=fs.mkdtempSync(path.join(root,'.local','preview-watch-'));
const socket=createServer();await new Promise(r=>socket.listen(0,'127.0.0.1',r));const port=socket.address().port;await new Promise(r=>socket.close(r));
fs.mkdirSync(path.join(dir,'src'));fs.writeFileSync(path.join(dir,'package.json'),'{"type":"module"}');fs.writeFileSync(path.join(dir,'index.html'),'<p>Watch regression</p>');fs.symlinkSync(path.join(root,'node_modules'),path.join(dir,'node_modules'),'dir');fs.copyFileSync('vite.config.mjs',path.join(dir,'vite.config.mjs'));
const probe=path.join(dir,'src','probe.css');fs.writeFileSync(probe,'.watch-probe{--test-version:before}');
const server=spawn(process.execPath,[path.join(root,'node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port',String(port),'--strictPort'],{cwd:dir,stdio:'ignore'});
try{
 const url=`http://127.0.0.1:${port}/src/probe.css`;let before;
 for(let i=0;i<60;i++){try{before=await(await fetch(url)).text();if(before.includes('--test-version:before'))break;}catch{}await new Promise(r=>setTimeout(r,100));}
 assert.ok(before?.includes('--test-version:before'));
 fs.writeFileSync(probe,'.watch-probe{--test-version:after}');let current='';
 for(let i=0;i<50;i++){current=await(await fetch(url)).text();if(current.includes('--test-version:after'))break;await new Promise(r=>setTimeout(r,100));}
 assert.ok(current.includes('--test-version:after'),'same module URL must serve changed CSS inside a .local preview');
 console.log(JSON.stringify({nestedLocalPreview:true,sameUrlModuleInvalidated:true}));
}finally{server.kill('SIGTERM');await new Promise(r=>server.once('exit',r));fs.rmSync(dir,{recursive:true,force:true});}
