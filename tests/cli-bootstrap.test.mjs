import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {gzipSync} from 'node:zlib';
import {zipSync} from 'fflate';
import {parseArgs,platformTarget,extractUv,applicationHome,checkPort} from '../cli/runtime.mjs';
import {createServer} from 'node:net';
test('installer accepts explicit local paths/ports and refuses unknown or unsafe launch options',()=>{
 for(const args of [['--port','0'],['--port','65536'],['--port','5174x'],['--data-dir'],['--remote-host','0.0.0.0']])assert.throws(()=>parseArgs(args));
 assert.equal(parseArgs(['--port','5280','--no-open']).port,5280);assert.equal(parseArgs(['--no-open']).open,false);
});
test('all installer targets have pinned official downloads and native Windows executables',()=>{
 for(const platform of ['darwin','linux','win32'])for(const arch of ['x64','arm64']){
  const target=platformTarget(platform,arch,false);assert.match(target.url,/^https:\/\/github.com\/astral-sh\/uv\/releases\/download\/0\.13\.7\//);assert.match(target.sha256,/^[a-f0-9]{64}$/);assert.equal(target.binary,platform==='win32'?'uv.exe':'uv');
 }
 assert.notEqual(platformTarget('linux','x64',true).sha256,platformTarget('linux','x64',false).sha256);
 assert.throws(()=>platformTarget('freebsd','x64',false));
});
test('runtime extraction selects a single regular executable without unpacking other paths',()=>{
 const bytes=Buffer.from('verified fixture binary');const archive=zipSync({'bundle/uv.exe':bytes,'../../other.txt':Buffer.from('ignored')});assert.deepEqual(extractUv(archive,{archive:'zip',binary:'uv.exe'}),bytes);
 assert.throws(()=>extractUv(zipSync({'a/uv.exe':bytes,'b/uv.exe':bytes}),{archive:'zip',binary:'uv.exe'}));
 const header=Buffer.alloc(512);header.write('bundle/uv');header.write('00000000003',124);header.write('2',156);assert.throws(()=>extractUv(gzipSync(Buffer.concat([header,Buffer.alloc(512)])),{archive:'tar.gz',binary:'uv'}));
});
test('default data location preserves an existing legacy installation',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'atmem-home-test-'));try{assert.equal(applicationHome({},dir),path.join(dir,'.atmem-ai-architect'));fs.mkdirSync(path.join(dir,'.atforma'));assert.equal(applicationHome({},dir),path.join(dir,'.atforma'));assert.equal(applicationHome({ATMEM_ARCHITECT_HOME:path.join(dir,'custom')},dir),path.join(dir,'custom'));}finally{fs.rmSync(dir,{recursive:true});}
});
test('an occupied local port fails before setup and cannot terminate its owner',async()=>{
 const server=createServer();await new Promise(r=>server.listen(0,'127.0.0.1',r));try{await assert.rejects(checkPort(server.address().port),/already in use/);assert.ok(server.listening);}finally{await new Promise(r=>server.close(r));}
});
