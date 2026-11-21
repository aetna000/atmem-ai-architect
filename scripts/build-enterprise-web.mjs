// Bundle one actual pinned OIDC dependency; no remote scripts in the runtime UI.
import fs from 'node:fs';
import path from 'node:path';
import{createHash}from'node:crypto';
import{build}from'esbuild';
const root=path.resolve('.'),entry='src/runtime/enterprise-web-entry.js',target='src/runtime/enterprise-web-app.js';
const result=await build({entryPoints:[entry],bundle:true,minify:true,format:'iife',platform:'browser',target:['es2022'],legalComments:'inline',write:false});
const bytes=result.outputFiles[0].contents,hash=value=>createHash('sha256').update(value).digest('hex');
const dependencyNames=['oidc-client-ts','jwt-decode','esbuild'];const dependencies=dependencyNames.map(name=>{const folder=path.join(root,'node_modules',name),pkg=JSON.parse(fs.readFileSync(path.join(folder,'package.json')));return {name,version:pkg.version,license:pkg.license,packageSha256:hash(fs.readFileSync(path.join(folder,'package.json')))};});
if(dependencies[0].version!=='3.5.0')throw Error('Use the reviewed exact OIDC client version');
const notices=['oidc-client-ts','jwt-decode'].map(name=>'# '+name+'\n\n'+fs.readFileSync(path.join(root,'node_modules',name,'LICENSE'),'utf8')).join('\n\n');
const proof={entry,entrySha256:hash(fs.readFileSync(entry)),bundleSha256:hash(bytes),buildScriptSha256:hash(fs.readFileSync('scripts/build-enterprise-web.mjs')),noticesSha256:hash(notices),packageLockSha256:hash(fs.readFileSync('package-lock.json')),dependencies,scope:'Pinned dependency bundle only; browser/runtime qualification is separate.'};
if(process.argv.includes('--check')){if(!fs.readFileSync(target).equals(Buffer.from(bytes))||fs.readFileSync('src/runtime/enterprise-web-notices.txt','utf8')!==notices||fs.readFileSync('src/runtime/enterprise-web-lock.json','utf8')!==JSON.stringify(proof,null,2)+'\n')throw Error('Enterprise web bundle is stale');}
else{fs.writeFileSync(target,bytes);fs.writeFileSync('src/runtime/enterprise-web-notices.txt',notices);fs.writeFileSync('src/runtime/enterprise-web-lock.json',JSON.stringify(proof,null,2)+'\n');}
console.log(JSON.stringify({bytes:bytes.length,sha256:proof.bundleSha256,dependencies}));
