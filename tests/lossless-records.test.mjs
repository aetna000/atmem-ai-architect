import test from 'node:test';import assert from 'node:assert/strict';import {cleanRequirement,slugSubject,reviseDecision,decisionHistory} from '../src/records.mjs';import {validateImport} from '../src/core.mjs';import {toProjectFile,fromProjectFile} from '../src/project-file.mjs';import {toAgentProject} from '../src/local-agent.mjs';import {newDecision} from '../src/engagement.mjs';
test('requirements are retained or refused explicitly rather than shortened',()=>{
 const statement='x'.repeat(1000);assert.equal(cleanRequirement({statement}).statement,statement);assert.throws(()=>cleanRequirement({statement:statement+'x'}),/No content was truncated/);assert.throws(()=>cleanRequirement({statement:'Requirement',links:Array(51).fill('app')}),/no links were truncated/);
});
test('long notes and full conversation provenance survive export and model boundaries',()=>{
 const p={version:1,revision:1,name:'Notes',provider:'tools',requirements:'x'.repeat(12000),nodes:[{id:'note',position:{x:0,y:0},data:{kind:'note',label:'A detailed annotation. '.repeat(100),provider:'tools'}}],edges:[]};const clean=validateImport(p),round=fromProjectFile(toProjectFile(clean)).project;assert.equal(round.nodes[0].data.label,p.nodes[0].data.label);assert.equal(toAgentProject(clean).requirements,p.requirements);assert.throws(()=>validateImport({...p,requirements:'x'.repeat(64001)}),/no content was truncated/);
});
test('long proposal titles generate bounded distinct subjects without losing decision content or history',()=>{
 const prefix='Preserve existing workforce identity and private data ownership while connecting the application';
 const titles=[prefix+' to the museum catalogue',prefix+' to the weather catalogue','設計🙂'.repeat(30)];
 const decisions=titles.map((title,i)=>newDecision({revision:2,decisions:Array.from({length:i},(_,n)=>({id:`adr-00${n+1}`}))},{subject:`design.${slugSubject(title)}`,title,status:'Accepted',context:'Full proposal context',decision:'Applied as design revision 2.'}));
 assert.equal(new Set(decisions.map(d=>d.subject)).size,titles.length);
 for(const d of decisions){assert(d.subject.length<=87);assert.equal(slugSubject(d.title),slugSubject(d.title));}
 assert.equal(slugSubject('Keep existing identity'), 'keep-existing-identity');
 const p=validateImport({version:1,revision:2,name:'Long proposal',provider:'tools',nodes:[],edges:[],decisions});
 assert.deepEqual(p.decisions.map(d=>d.title),titles);
 const round=fromProjectFile(toProjectFile(p)).project;
 assert.deepEqual(round.decisions,decisions);
 const revised=reviseDecision(round,decisions[0].id,{decision:'Updated implementation'},'A new accepted requirement');
 assert.deepEqual(decisionHistory(revised.decisions,decisions[0].subject).map(d=>d.title),[titles[0],titles[0]]);
});
