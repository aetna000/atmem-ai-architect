import test from 'node:test';
import assert from 'node:assert/strict';
import {pdmTemplate} from '../src/core.mjs';
import {cleanRequirement,measureProblem,missingLinks,linkedTo,reviseDecision,currentDecision,decisionHistory,newRequirement,newAssumption} from '../src/records.mjs';
import {newDecision,keepEngagement} from '../src/engagement.mjs';
test('requirements are sanitised and measures validated',()=>{
  const r=cleanRequirement({kind:'evil',category:'performance',statement:'x',measure:{metric:'p95',op:'<=',target:'fast'}});
  assert.equal(r.kind,'functional');assert.equal(r.measure,undefined);
  assert.equal(measureProblem({metric:'p95',op:'<=',target:'2'}),'Use a number for >= and <= targets.');
  assert.equal(measureProblem({metric:'grounded',op:'==',target:true}),null);
  assert.deepEqual(cleanRequirement({statement:'x',measure:{metric:'availability',op:'>=',target:99.9,unit:'%'}}).measure,{metric:'availability',op:'>=',target:99.9,unit:'%'});
});
test('records linked to removed components are kept and flagged; detail lists linked records',()=>{
  const p={...pdmTemplate(),needs:[newRequirement({links:['sensors','gone']})],assumptions:[newAssumption({links:['sensors']})]};
  assert.deepEqual(missingLinks(p,p.needs[0]),['gone']);
  const l=linkedTo(p,'sensors');assert.equal(l.needs.length,1);assert.equal(l.assumptions.length,1);
});
function decided(){const p=pdmTemplate();return {...p,decisions:[newDecision(p,{subject:'cloud.region',title:'Region',status:'Accepted',decision:'eu-west-1'})]};}
test('three-step revision chain: one current decision, ordered history',()=>{
  let p=decided();
  p=reviseDecision(p,'adr-001',{decision:'eu-central-1'},'Data residency');
  p=reviseDecision(p,'adr-002',{decision:'eu-north-1'},'Lower carbon');
  const cur=currentDecision(p.decisions,'cloud.region');
  assert.equal(cur.id,'adr-003');assert.equal(cur.decision,'eu-north-1');assert.equal(cur.reason,'Lower carbon');
  assert.deepEqual(decisionHistory(p.decisions,'cloud.region').map(d=>[d.id,d.status]),[['adr-001','Superseded'],['adr-002','Superseded'],['adr-003','Accepted']]);
  assert.equal(p.decisions[0].supersededBy,'adr-002');assert.equal(p.decisions[0].decision,'eu-west-1');
  assert.equal(p.decisions.filter(d=>d.subject==='cloud.region'&&d.status!=='Superseded').length,1);
});
test('a revision needs a reason and a current decision',()=>{
  const p=decided();
  assert.throws(()=>reviseDecision(p,'adr-001',{decision:'x'},'  '),/reason/);
  const q=reviseDecision(p,'adr-001',{decision:'x'},'why');
  assert.throws(()=>reviseDecision(q,'adr-001',{decision:'y'},'again'),/already superseded/);
});
test('proposals and templates keep records',()=>{
  const cur={...decided(),needs:[newRequirement()],assumptions:[newAssumption()],openQuestions:[{id:'q',question:'?',status:'open',owner:'',answer:'',links:[]}]};
  const next=keepEngagement(pdmTemplate('ibm'),cur);
  for(const k of ['needs','assumptions','openQuestions','decisions'])assert.deepEqual(next[k],cur[k]);
});
