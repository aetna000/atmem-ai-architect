import test from 'node:test';import assert from 'node:assert/strict';import {cleanRequirement} from '../src/records.mjs';import {validateImport} from '../src/core.mjs';import {toProjectFile,fromProjectFile} from '../src/project-file.mjs';import {toAgentProject} from '../src/local-agent.mjs';
test('requirements are retained or refused explicitly rather than shortened',()=>{
 const statement='x'.repeat(1000);assert.equal(cleanRequirement({statement}).statement,statement);assert.throws(()=>cleanRequirement({statement:statement+'x'}),/No content was truncated/);assert.throws(()=>cleanRequirement({statement:'Requirement',links:Array(51).fill('app')}),/no links were truncated/);
});
test('long notes and full conversation provenance survive export and model boundaries',()=>{
 const p={version:1,revision:1,name:'Notes',provider:'tools',requirements:'x'.repeat(12000),nodes:[{id:'note',position:{x:0,y:0},data:{kind:'note',label:'A detailed annotation. '.repeat(100),provider:'tools'}}],edges:[]};const clean=validateImport(p),round=fromProjectFile(toProjectFile(clean)).project;assert.equal(round.nodes[0].data.label,p.nodes[0].data.label);assert.equal(toAgentProject(clean).requirements,p.requirements);assert.throws(()=>validateImport({...p,requirements:'x'.repeat(64001)}),/no content was truncated/);
});
