import test from 'node:test';
import assert from 'node:assert/strict';
import {applyCommentProposal, commentBasis, commentPrompt, commentTarget, parseCommentProposal} from '../src/design-comments.mjs';
import {parseProjectFile,toProjectFile} from '../src/project-file.mjs';
import {reservationSystemModel} from './fixtures/system-model.mjs';

const fixture=()=>({id:'design-feedback',name:'Reservations',version:1,revision:1,provider:'tools',
  nodes:['Ledger','Reservations'].map((id,i)=>({id,type:'resource',position:{x:i*200,y:0},data:{
    label:id,kind:'resource',provider:'tools',buildSpec:{behavior:'Current responsibility.',
      scenarios:[{name:'Reserve',steps:[{sender:'Clerk',receiver:'Ledger',action:'Request a hold'}]}]},
  }})),
  edges:[{id:'reserve',source:'Ledger',target:'Reservations',label:'Reserve'}],
  needs:[{id:'unique-reservation',statement:'Preserve a single reservation.'}],
  extensions:{systemModel:reservationSystemModel()},
});

function proposal(project,target,changes) {
  const binding=commentTarget(project,target);
  return {id:'change-1',target,text:'Edit only this part.',status:'ready',basis:commentBasis(binding),
    proposal:parseCommentProposal(JSON.stringify({summary:'Scoped correction',changes}),binding)};
}

test('saved feedback round-trips and changes one shared element only after approval',()=>{
  const project=fixture();
  const comment=proposal(project,{kind:'element',id:'ledger'},{name:'Availability ledger'});
  project.extensions.designComments=[comment];
  const reopened=parseProjectFile(JSON.stringify(toProjectFile(project))).project;
  assert.deepEqual(reopened.extensions.designComments,[comment]);
  assert.deepEqual(reopened.extensions.systemModel,project.extensions.systemModel);
  const next=applyCommentProposal(reopened,comment);
  assert.equal(next.extensions.systemModel.elements.find(row=>row.id==='ledger').name,'Availability ledger');
  assert.deepEqual(next.extensions.systemModel.diagrams,reopened.extensions.systemModel.diagrams);
  assert.equal(next.extensions.systemModel.elements.find(row=>row.id==='allocator').name,'Reservation allocator');
  assert.throws(()=>applyCommentProposal(next,comment),/changed/);
});

test('scope checks reject unrelated fields, invalid link edits and reordered sequence targets',()=>{
  const project=fixture();
  assert.throws(()=>proposal(project,{kind:'block',id:'Ledger'},{provider:'aws'}),/outside/);
  assert.throws(()=>applyCommentProposal(project,proposal(project,{kind:'diagram',id:'logical'},
    {elementIds:['missing']})),/invalid diagram elements/);
  const target={kind:'step',id:'scenario',index:1,exchangeId:'reserve-item'};
  const comment=proposal(project,target,{exchangeId:'submit'});
  assert.deepEqual(applyCommentProposal(project,comment).extensions.systemModel.diagrams[2].exchangeIds,['submit','submit']);
  project.extensions.systemModel.diagrams[2].exchangeIds.reverse();
  assert.throws(()=>applyCommentProposal(project,comment),/changed/);
});

test('specification comments change one section and the prompt retains the full user comment',()=>{
  const project=fixture();
  const target={kind:'specification',id:'Ledger',field:'behavior'};
  const comment=proposal(project,target,{behavior:'Persist the decision before returning.'});
  const result=applyCommentProposal(project,comment);
  assert.equal(result.nodes[0].data.buildSpec.behavior,'Persist the decision before returning.');
  assert.deepEqual(result.nodes[0].data.buildSpec.scenarios,project.nodes[0].data.buildSpec.scenarios);
  const longComment={...comment,text:'x'.repeat(1800)};
  const message=commentPrompt(project,longComment,commentTarget(project,target));
  const payload=JSON.parse(message.slice(message.indexOf('\n')+1));
  assert.equal(payload.comment,longComment.text);
  assert.ok(message.length<8000);
});
