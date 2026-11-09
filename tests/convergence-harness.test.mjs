import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import path from 'node:path';import os from 'node:os';import {spawnSync} from 'node:child_process';
import {keepEngagement} from '../src/engagement.mjs';import {structuredWebProject} from './fixtures/structured-web-project.mjs';
const corpus=JSON.parse(fs.readFileSync(new URL('../benchmarks/convergence/scenarios.json',import.meta.url)));
const bridge=request=>{const r=spawnSync('node',['scripts/convergence-bridge.mjs'],{input:JSON.stringify(request),encoding:'utf8'});assert.equal(r.status,0,r.stderr);return JSON.parse(r.stdout);};
test('invalid benchmark selectors fail before snapshotting or invoking a model',()=>{
 const dir=path.join(os.tmpdir(),'atmem-invalid-case-'+Date.now());
 const r=spawnSync(path.resolve('.venv/bin/python'),['scripts/evaluate-convergence.py','--live','--case','azure-02-meeting-actions','--output',dir],{encoding:'utf8'});
 assert.notEqual(r.status,0);assert.match(r.stderr,/Unknown benchmark case IDs/);assert.equal(fs.existsSync(dir),false);
});
test('the stronger evaluation protocol supplies all remaining business facts once before final export',()=>{
 const code=`import importlib.util\nspec=importlib.util.spec_from_file_location('driver','scripts/evaluate-convergence.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\nscenario={'facts':{'location':'Stay in Australia.','users':'Ten staff.','quality':'Return explicit uncertainty.'}};used={'location'}\ntext=m.complete_client_facts(scenario,used)\nassert 'Ten staff.' in text and 'Return explicit uncertainty.' in text and 'Stay in Australia.' not in text\nassert used==set(scenario['facts'])\nassert m.complete_client_facts(scenario,used) is None\n`;
 const r=spawnSync(path.resolve('.venv/bin/python'),['-c',code],{encoding:'utf8'});assert.equal(r.status,0,r.stderr);
});
test('the frozen benchmark contains 28 distinct provider/scenario cases and the requested difficulty distribution',()=>{
 assert.deepEqual(Object.keys(corpus.providers).sort(),['aws','azure','gcp','ibm']);assert.equal(corpus.scenarios.length,7);
 const cases=Object.keys(corpus.providers).flatMap(p=>corpus.scenarios.map(s=>p+'-'+s.id));assert.equal(new Set(cases).size,28);
 assert.deepEqual(corpus.scenarios.reduce((a,s)=>(a[s.difficulty]=(a[s.difficulty]||0)+1,a),{}),{simple:2,medium:3,hard:2});
 for(const s of corpus.scenarios){assert.ok(s.intent);assert.ok(s.acceptance.length>=3);assert.ok(Object.keys(s.facts).length>=4);}
});
test('model proposals cannot overwrite the original brief at the engagement boundary',()=>{
 const old={requirements:'Keep the existing website and payment boundary',needs:[{id:'privacy',statement:'Protect private data'}]},next={requirements:'A smaller demo',nodes:[],edges:[]};
 const kept=keepEngagement(next,old);assert.equal(kept.requirements,old.requirements);assert.deepEqual(kept.needs,old.needs);
});
test('real bridge preserves intent, exports coherent artifacts and independent assessor detects byte tampering',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'atmem-eval-'));
 try{
  const project=structuredWebProject();const initial=bridge({action:'prepare',project,message:'Keep the staff workflow and privacy requirement'}).project;
  const proposal={...initial,requirements:'Discard original scope'};
  const applied=bridge({action:'apply',project:initial,message:'continue',response:{message:'Proposal',proposal:{baseRevision:initial.revision,next:proposal}}});assert.equal(applied.scopePreserved,true);
  const exported=bridge({action:'export',project:applied.project,output:path.join(dir,'handoff')});assert.deepEqual(exported.missingDependencies,[]);
  fs.writeFileSync(path.join(dir,'project.json'),JSON.stringify(applied.project));fs.writeFileSync(path.join(dir,'export-assessment.json'),JSON.stringify(exported));
  const assess=()=>{const r=spawnSync(path.resolve('.venv/bin/python'),['scripts/assess-convergence-package.py',dir],{encoding:'utf8'});assert.equal(r.status,0,r.stderr);return JSON.parse(r.stdout);};
  let a=assess();assert.ok(!a.findings.some(f=>f.code==='artifact-digest-mismatch'));assert.equal(a.nearDeploymentQualified,false);
  fs.appendFileSync(path.join(dir,'handoff/terraform/main.tf.json'),'\n ');a=assess();assert.ok(a.findings.some(f=>f.code==='artifact-digest-mismatch'));
  const tasksFile=path.join(dir,'handoff/spec-kit/tasks.json'),tasks=JSON.parse(fs.readFileSync(tasksFile));tasks.tasks[0].dependsOn=[tasks.tasks[1].id];tasks.tasks[1].dependsOn=[tasks.tasks[0].id];fs.writeFileSync(tasksFile,JSON.stringify(tasks));
  a=assess();assert.ok(a.findings.some(f=>f.code==='task-cycle'));assert.equal(a.staticChecksPassed,false);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
