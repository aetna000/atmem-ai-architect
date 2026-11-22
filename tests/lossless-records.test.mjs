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

test('large project records and stable requirement numbers survive derivation, save and reload',async()=>{
 const {withDerived,requirementNumber}=await import('../src/derive.mjs');
 for(const domain of ['Museum archive','Equipment maintenance']){
  const p={version:1,revision:1,name:domain,provider:'tools',nodes:[],edges:[],
   needs:Array.from({length:1000},(_,i)=>({id:'req-'+i,statement:domain+' required behavior '+i,priority:'must',source:'user'})),
   assumptions:Array.from({length:350},(_,i)=>({id:'assumption-'+i,statement:'Assumption '+i})),
   openQuestions:Array.from({length:350},(_,i)=>({id:'question-'+i,question:'Who owns item '+i+'?',status:'open'})),
   facts:Array.from({length:350},(_,i)=>({id:'fact-'+i,name:'throughput.'+i,value:i,text:'Recorded measurement '+i})),
   decisions:Array.from({length:350},(_,i)=>({id:'decision-'+i,subject:'policy.'+i,title:'Policy '+i,decision:'Preserve item '+i,status:'Accepted'}))};
  const prepared=withDerived(validateImport(p));
  const round=withDerived(fromProjectFile(JSON.parse(JSON.stringify(toProjectFile(prepared)))).project);
  for(const name of ['needs','assumptions','openQuestions','facts','decisions'])assert.deepEqual(round[name],prepared[name],domain+' '+name);
  assert.equal(round.needs.length,1000);assert.equal(requirementNumber(round,'req-999'),'REQ-1000');
 }
});
