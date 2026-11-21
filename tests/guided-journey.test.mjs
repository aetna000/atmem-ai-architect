import test from 'node:test';
import assert from 'node:assert/strict';
import {journey,advanceJourney,cloudMapping,DESIGN_SECTIONS,designSection,journeyAction,journeySectionId,completedStages} from '../src/journey.mjs';
import {emulationPreflight} from '../src/emulation-guidance.mjs';
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
test('Board review actions navigate before acknowledging scope, risk or cost checkpoints',()=>{
 for(const [id,label]of [['scope','Review requirements'],['review','Review design'],['estimate','Review costs'],['delivery','Review delivery']]){
  const guidance={id,checkpoint:id,continueLabel:'Continue'};
  assert.deepEqual(journeyAction(guidance),{kind:'navigate',section:journeySectionId(id),label});
  if(id!=='delivery')assert.deepEqual(journeyAction(guidance,journeySectionId(id)),{kind:'continue',label:'Continue'});
  assert.equal(journeyAction(guidance,'location'),null);
 }
});
test('unfamiliar named services can reach draft review while implementation and provider boundaries remain separate',()=>{
 for(const [provider,service]of [['aws','AWS Batch'],['azure','Azure Batch'],['gcp','Dataproc'],['ibm','IBM Cloud Schematics']]){
  let project=choose(p(),'platform.cloud',provider);
  project.nodes=[{...node('batch','Processing service',provider,'Reviewed candidate region'),position:{x:0,y:0},data:{...node('batch','Processing service',provider,'Reviewed candidate region').data,service}}];
  const mapping=cloudMapping(project);assert.equal(mapping.ready,true);assert.equal(mapping.boundary,'named_working_draft_only');
  assert.equal(emulationPreflight(project)?.action,'build-and-test','a named draft cannot invent an implementation');
  project.nodes[0].data.provider=provider==='aws'?'azure':'aws';assert.equal(cloudMapping(project).ready,false);
 }
 const unknown=choose(p(),'platform.cloud','unknown-provider');unknown.nodes=[{...node('a','Example','unknown-provider','somewhere'),data:{...node('a','Example','unknown-provider','somewhere').data,service:'Named service'}}];assert.equal(cloudMapping(unknown).ready,false);
});


test('five stages group location, cost and generated infrastructure without marking visits complete',()=>{
 assert.deepEqual(DESIGN_SECTIONS.map(s=>s.label),['Board','Requirements','Choices','Review','Delivery']);
 assert.equal(designSection('design','location').id,'cloud');
 assert.equal(designSection('design','terraform').id,'review');
 assert.equal(designSection('estimate','board').id,'review');
 const project=p();assert.deepEqual(completedStages(project),{board:false,scope:false,cloud:false,review:false,delivery:false});
 project.nodes=[node('a','Storage')];assert.equal(completedStages(project).board,true);
 const next=advanceJourney(project,'scope');assert.equal(completedStages(next).scope,true);
 next.needs=[{id:'new',source:'user',statement:'Preserve regional data'}];assert.equal(completedStages(next).scope,false);
});
