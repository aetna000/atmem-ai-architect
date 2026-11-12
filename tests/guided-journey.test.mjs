import test from 'node:test';
import assert from 'node:assert/strict';
import {journey,advanceJourney,cloudMapping,DESIGN_SECTIONS,designSection} from '../src/journey.mjs';
const p=()=>({id:'journey-test',requirements:'Answer staff policy questions',nodes:[],edges:[],needs:[],decisions:[]});
const node=(id,label,provider='tools',region='To be selected')=>({id,data:{kind:'resource',label,provider,config:{region},description:'Serve policy questions',origin:'proposed'}});
const choose=(project,subject,decision)=>({...project,decisions:[...project.decisions.filter(d=>d.subject!==subject),{subject,decision,status:'Accepted'}]});
test('every design destination is uniquely reachable without advancing an incomplete project',()=>{
 const project=p(),before=structuredClone(project);
 assert.equal(new Set(DESIGN_SECTIONS.map(s=>s.id)).size,DESIGN_SECTIONS.length);
 for(const section of DESIGN_SECTIONS){
  assert.equal(designSection(section.mode,section.view),section);
  assert.equal(journey(project).id,'idea');
 }
 assert.deepEqual(project,before);
 assert.equal(designSection('design','decisions').id,'cloud');
 assert.equal(designSection('deploy','board').id,'delivery');
 assert.ok(Object.isFrozen(DESIGN_SECTIONS));
 assert.ok(DESIGN_SECTIONS.every(Object.isFrozen));
});
test('journey reveals later stages only after scope, concrete mapping and working-draft checkpoints',()=>{
 let project=p();assert.equal(journey(project).id,'idea');assert.deepEqual(journey(project).availableModes,['design']);
 project.nodes=[node('a','Document store')];assert.equal(journey(project).id,'scope');
 project=advanceJourney(project,'scope');assert.equal(journey(project).id,'cloud');
 project=choose(project,'platform.cloud','aws');assert.equal(journey(project).id,'location');
 project=choose(project,'data.country','Australia');assert.equal(journey(project).id,'architecture');assert.equal(journey(project).checkpoint,null);
 project.nodes=[node('a','Amazon S3','aws','ap-southeast-2')];assert.equal(journey(project).checkpoint,'architecture');assert.deepEqual(journey(project).availableModes,['design']);
 project=advanceJourney(project,'architecture');assert.equal(journey(project).id,'review');assert.deepEqual(journey(project).availableModes,['design','review']);
 project=advanceJourney(project,'review');assert.equal(journey(project).id,'estimate');assert.ok(!journey(project).availableModes.includes('deploy'));
 project=advanceJourney(project,'estimate');assert.equal(journey(project).id,'delivery');assert.ok(journey(project).availableModes.includes('deploy'));
 project.nodes[0].data.config.region='ap-southeast-4';assert.equal(journey(project).id,'architecture');assert.deepEqual(journey(project).availableModes,['design']);
});
test('generic boxes do not count as a cloud architecture, and all four providers support named service mapping',()=>{
 for(const [provider,label,region] of [['aws','Amazon S3','ap-southeast-2'],['azure','Azure Blob Storage','australiaeast'],['gcp','Google Cloud Storage','australia-southeast1'],['ibm','IBM Cloud Object Storage','au-syd']]){
  let project=choose(p(),'platform.cloud',provider);project.nodes=[node('a','Storage',provider,region)];assert.equal(cloudMapping(project).ready,false);
  project.nodes[0].data.label=label;assert.equal(cloudMapping(project).ready,true);
  project.nodes[0].data.config.region='To be selected';assert.equal(cloudMapping(project).ready,false);
 }
});
test('scope changes reopen the document step; visits and unrelated checkpoint names do not advance it',()=>{
 let project=p();project.nodes=[node('a','Amazon S3','aws','ap-southeast-2')];assert.equal(advanceJourney(project,'review'),project);
 project=advanceJourney(project,'scope');project.needs=[{id:'r1',source:'user',statement:'Only HR can access documents'}];assert.equal(journey(project).id,'scope');
});
