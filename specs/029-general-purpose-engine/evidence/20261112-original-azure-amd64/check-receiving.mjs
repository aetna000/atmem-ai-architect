// Documented clean-package build in the actual target image; no source patching.
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {spawnSync}from 'node:child_process';import {createHash}from 'node:crypto';
const files=JSON.parse(fs.readFileSync(0,'utf8'));assert.equal(process.version,'v26.13.0');assert.equal(process.arch,'x64');assert.equal(process.getuid(),1000);
const root=fs.mkdtempSync('/tmp/receiving-');
for(const[name,text]of Object.entries(files)){
 assert(!path.isAbsolute(name)&&!name.split('/').includes('..'));
 const target=path.join(root,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,text);
}
const result=spawnSync('npm',['run','build'],{cwd:root,encoding:'utf8',env:{PATH:process.env.PATH,HOME:'/tmp',NO_UPDATE_NOTIFIER:'1',npm_config_update_notifier:'false'},timeout:30000});
assert.equal(result.status,0,result.stdout+result.stderr);const manifest=JSON.parse(fs.readFileSync(root+'/dist/runtime-manifest.json','utf8'));
for(const[name,digest]of Object.entries(manifest)){const raw=fs.readFileSync(root+'/dist/runtime/'+name);assert.equal(createHash('sha256').update(raw).digest('hex'),digest);assert.equal(raw.toString(),files[name]);}
for(const[name,text]of Object.entries(files))assert.equal(fs.readFileSync(root+'/'+name,'utf8'),text);
console.log(JSON.stringify({passed:true,node:process.version,arch:process.arch,uid:process.getuid(),originalFiles:Object.keys(files).length,buildManifestFiles:Object.keys(manifest).length,sourcesUnchanged:true,cloudOperations:false,
 boundary:'Actual documented npm run build from clean unchanged archive in declared Linux AMD64 Node26.13 image; no network or host mounts. Runtime/browser qualified separately; no account, generated-suite or deployed rollback acceptance.'}));
