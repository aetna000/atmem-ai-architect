// Independent component checks inside the original generated image.
import assert from 'node:assert/strict';import fs from 'node:fs';import os from 'node:os';import {createHash}from 'node:crypto';
const inputs=JSON.parse(fs.readFileSync(0,'utf8')),actual={};
for(const [file,digest]of Object.entries(inputs.sourceHashes)){const bytes=fs.readFileSync('/app/'+file);actual[file]=createHash('sha256').update(bytes).digest('hex');assert.equal(actual[file],digest,file);}
assert.equal(process.version,'v26.13.0');assert.equal(process.arch,'x64');assert.equal(process.platform,'linux');assert.equal(process.getuid(),1000);
const modules={};for(const name of ['contracts','config','identity','azure','server'])modules[name]=await import('file:///app/app/'+name+'.mjs');
const {validInput,validSuggestion,parseJson}=modules.contracts;const checks=[];
for(const size of [20000,20480])assert(validInput({ticket:'x'.repeat(size)}));assert(!validInput({ticket:'x'.repeat(20481)}));checks.push('actual image accepts required20000 and documented20480 UTF8 bytes;20481 denied');
assert(validInput({ticket:'🙂'.repeat(5120)}));assert(!validInput({ticket:'🙂'.repeat(5121)}));checks.push('actual UTF8 input bound includes non-BMP Unicode');
for(const ticket of ['',false,1,null,{},[],String.fromCharCode(0xd800)])assert(!validInput({ticket}));assert(!validInput({ticket:'text',provider:'aws'}));checks.push('empty/type/surrogate/extra-control inputs denied');
const result={summary:'🙂'.repeat(480),topic:'access',urgency:'normal',uncertainty:{level:'high',reason:'🖼'.repeat(240)}};assert(validSuggestion(result));checks.push('valid output reaches480/240 Unicode code points despite UTF16 length');
for(const bad of [{...result,summary:'🙂'.repeat(481)},{...result,uncertainty:{...result.uncertainty,reason:'🖼'.repeat(241)}},{...result,topic:'unknown'},{...result,urgency:'unknown'},{...result,extra:true},{...result,uncertainty:{...result.uncertainty,extra:true}}])assert(!validSuggestion(bad));checks.push('oversized outputs/enums/extra fields denied');
for(const text of ['{"ticket":1,"ticket":2}','{"ti\\u0063ket":1,"ticket":2}','{"outer":{"key":1,"key":2}}'])assert.throws(()=>parseJson(text));assert.equal(parseJson('{"ticket":"valid"}').ticket,'valid');checks.push('duplicate raw/escaped/nested keys denied');
console.log(JSON.stringify({passed:true,sourceHashes:actual,node:process.version,architecture:os.machine(),uid:process.getuid(),imports:Object.keys(modules),checks,cloudOperations:false,boundary:'Unchanged original Azure Linux AMD64 runtime image and direct independent contract/module checks. No actual HTTP/browser/native identity/model transport journey or complete-project acceptance.'}));
