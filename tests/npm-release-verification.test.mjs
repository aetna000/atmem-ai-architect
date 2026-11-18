import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import {createHash} from 'node:crypto';import {spawnSync} from 'node:child_process';
const script=new URL('../scripts/verify-npm-release.mjs',import.meta.url).href;
for(const mode of ['matching','changed-bytes','wrong-latest'])test('release verification: '+mode,()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'architect-publish-'));try{
  const artifact=path.join(dir,'atmem-architect-0.2.2.tgz'),bytes=Buffer.from('test-only accepted artifact');fs.writeFileSync(artifact,bytes);
  const document={'dist-tags':{latest:mode==='wrong-latest'?'0.2.1':'0.2.2'},versions:{'0.2.2':{dist:{integrity:mode==='changed-bytes'?'sha512-changed':'sha512-'+createHash('sha512').update(bytes).digest('base64')}}}};
  const code=`process.argv[2]=${JSON.stringify(artifact)};globalThis.fetch=async()=>({ok:true,json:async()=>(${JSON.stringify(document)})});await import(${JSON.stringify(script)});`;
  const result=spawnSync(process.execPath,['--input-type=module','-e',code],{encoding:'utf8',timeout:10000});
  if(mode==='matching'){assert.equal(result.status,0,result.stderr);assert.equal(JSON.parse(result.stdout).version,'0.2.2');}else{assert.notEqual(result.status,0);assert.match(result.stderr,mode==='changed-bytes'?/differs from the accepted CI artifact/:/latest points elsewhere/);}
 }finally{fs.rmSync(dir,{recursive:true,force:true})}
});

test('stable and beta publish to separate channels', async () => {
  const {releaseChannel} = await import('../scripts/npm-release-channel.mjs');
  assert.equal(releaseChannel('0.2.4'), 'latest');
  assert.equal(releaseChannel('0.2.5-beta.1'), 'beta');
  assert.throws(() => releaseChannel('0.2.5-unknown.1'));
});
