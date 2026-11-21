import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fromProjectFile} from '../src/project-file.mjs';
const root=path.resolve('examples/cloud-qualification');
test('cloud archives retain immutable hashes, evidence kinds and loadable projects',()=>{
 const manifest=JSON.parse(fs.readFileSync(path.join(root,'manifest.json')));assert.equal(manifest.cloudOperations,false);assert.ok(manifest.runs.length>=7);
 let projects=0;
 for(const run of manifest.runs){assert.ok(['real-model-browser-run','synthetic-contract-fixture','exact-model-output-native-validation','fixture-model-browser-regression'].includes(run.kind));for(const file of run.files){assert.ok(!file.path.includes('..'));const data=fs.readFileSync(path.join(root,file.path));assert.equal(createHash('sha256').update(data).digest('hex'),file.sha256,file.path);if(file.path.endsWith('project.atmem-ai-architect.json')){assert.ok(fromProjectFile(JSON.parse(data)).project.nodes.length);projects++;}}}
 assert.ok(projects>=40);
});
test('AI matrix cannot turn a diagram or absent runtime checks into deployed evidence',()=>{
 const matrix=JSON.parse(fs.readFileSync(path.join(root,'ai-assessment.json')));assert.equal(matrix.results.length,40);
 for(const row of matrix.results){if(!row.project)continue;assert.equal(row.deployment,'not_run');assert.equal(row.cloudPlan,'not_run');if(row.status==='bounded_runtime_pass'){assert.equal(row.runtimeStatus,'passed');assert.ok(row.runtimeChecks>0);}assert.ok(row.staticAssessment.limitations.length);}
});
