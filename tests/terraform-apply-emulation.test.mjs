import test from 'node:test';
import assert from 'node:assert/strict';
import {applyStages,applyEmulationSummary,APPLY_LIFECYCLE,APPLY_STATUS_TITLES,applyTrack,applyNodeStates,applyResourceStates,applyCaption} from '../src/terraform-apply-emulation.mjs';
import {identityToken} from '../src/identifiers.mjs';

test('no stages are shown before a run',()=>{
  assert.deepEqual(applyStages([],null,false),[]);
});

test('live events show the running stage and pending remainder in lifecycle order',()=>{
  const stages=applyStages([{stage:'Provider initialization',status:'running'},{stage:'Provider initialization',status:'passed',seconds:3.1},{stage:'Schema validation',status:'running'}],null,true);
  assert.deepEqual(stages.map(s=>s.name),APPLY_LIFECYCLE);
  assert.deepEqual(stages.slice(0,3).map(s=>s.status),['passed','running','pending']);
  assert.equal(stages[0].detail,'3.1s');
});

test('a finished report marks unreached stages skipped, never passed',()=>{
  const report={status:'failed',stages:[{name:'Provider initialization',status:'passed',seconds:2},{name:'Schema validation',status:'failed',seconds:1,output:'bad'}],resources:[]};
  const stages=applyStages([],report,false);
  assert.deepEqual(stages.map(s=>s.status),['passed','failed','skipped','skipped','skipped','skipped','skipped','skipped']);
  assert.equal(applyEmulationSummary(report),null);
});

test('build and destroy-protection stages appear only when they ran',()=>{
  const report={status:'passed',stages:[{name:'Application build',status:'passed',seconds:9},{name:'Destroy protection',status:'passed',seconds:3,protectedResources:['aws_s3_bucket.a']},{name:'Destroy',status:'passed',seconds:5}],resources:[]};
  const names=applyStages([],report,false).map(s=>s.name);
  assert.equal(names[0],'Application build');
  assert.equal(names[names.indexOf('Destroy')-1],'Destroy protection');
  assert.match(applyStages([],report,false).find(s=>s.name==='Destroy protection').detail,/1 protected/);
});

test('summary counts only fully verified resources and surfaces gaps and errors',()=>{
  const report={status:'unsupported',cloudOperations:false,apiCalls:{total:42},
    resources:[
      {address:'aws_s3_bucket.a',type:'aws_s3_bucket',applied:true,checks:[{name:'x',passed:true}]},
      {address:'aws_sqs_queue.q',type:'aws_sqs_queue',applied:true,checks:[{name:'x',passed:true},{name:'y',passed:false}]},
      {address:'aws_x.y',type:'aws_x',applied:false,error:'EmulatorNotImplemented',emulatorGap:true},
    ],
    resourceTypes:{aws_s3_bucket:{planned:1,applied:1,sdkVerified:1}},
    emulatorGaps:{resourceTypes:['aws_x'],operations:['x:CreateY']}};
  const summary=applyEmulationSummary(report);
  assert.deepEqual(summary.facts.map(f=>f.value),['2/3','1','42','0']);
  assert.deepEqual(summary.gaps,['aws_x','x:CreateY']);
  assert.deepEqual(summary.failures.map(f=>f.address),['aws_x.y']);
});

test('every report status has a concise title and only passed says passed',()=>{
  for(const [status,title] of Object.entries(APPLY_STATUS_TITLES)){
    assert.ok(title.split(' ').length<=8);
    assert.equal(/passed/.test(title),status==='passed');
  }
});

const hex=id=>'block_'+identityToken(id);
const live=[
  {stage:'Plan',status:'passed',seconds:3},
  {planned:[{resource:`aws_s3_bucket.${hex('docs')}`,resourceType:'aws_s3_bucket'},{resource:`aws_s3_bucket_versioning.${hex('docs')}`,resourceType:'aws_s3_bucket_versioning'},{resource:'aws_sqs_queue.block_646c71',resourceType:'aws_sqs_queue',component:hex('worker')},{resource:'terraform_data.review_gate',resourceType:'terraform_data'}]},
  {stage:'Apply',status:'running',resources:4},
  {resource:`aws_s3_bucket.${hex('docs')}`,state:'creating',apiCalls:4},
  {resource:`aws_s3_bucket.${hex('docs')}`,state:'applied',apiCalls:19},
];

test('diagram follows live resource events and maps resources to design blocks',()=>{
  const view=(events,report,running=true)=>applyNodeStates(['docs','worker','operator'],identityToken,events,report,running);
  let {states,counts}=view(live);
  assert.deepEqual(states,{docs:'creating',worker:'planned'});      // one of two bucket resources applied
  assert.deepEqual(counts,{docs:'1/2',worker:'0/1'});
  assert.equal(states.operator,undefined);                           // no resources: untouched
  ({states}=view([...live,{resource:`aws_s3_bucket_versioning.${hex('docs')}`,state:'applied'}]));
  assert.equal(states.docs,'applied');
  ({states}=view([...live,{resource:`aws_s3_bucket_versioning.${hex('docs')}`,state:'applied'},{resource:`aws_s3_bucket.${hex('docs')}`,state:'verified'}]));
  assert.equal(states.docs,'verified');
  ({states}=view([...live,{resource:'aws_sqs_queue.block_646c71',state:'failed',component:hex('worker')}]));
  assert.equal(states.worker,'failed');                               // derived resource reaches its block through the Component tag
  ({states,counts}=view([...live,{resource:`aws_s3_bucket_versioning.${hex('docs')}`,state:'destroyed'},{resource:`aws_s3_bucket.${hex('docs')}`,state:'destroying'}]));
  assert.deepEqual([states.docs,counts.docs],['destroying','1/2']);
  ({states}=view([...live,{resource:`aws_s3_bucket_versioning.${hex('docs')}`,state:'destroyed'},{resource:`aws_s3_bucket.${hex('docs')}`,state:'destroyed'}]));
  assert.equal(states.docs,'gone');
});

test('finished diagram shows the outcome and never passes a block in a failed run',()=>{
  const resources=[{address:`aws_s3_bucket.${hex('docs')}`,type:'aws_s3_bucket',applied:true},{address:'aws_sqs_queue.block_646c71',type:'aws_sqs_queue',component:hex('worker'),applied:false,error:'boom'}];
  const failed=applyNodeStates(['docs','worker'],identityToken,[],{status:'failed',resources},false).states;
  assert.deepEqual(failed,{docs:'applied',worker:'failed'});
  const passed=applyNodeStates(['docs'],identityToken,[],{status:'passed',resources:[resources[0]]},false).states;
  assert.deepEqual(passed,{docs:'passed'});
  assert.equal(applyResourceStates([],{resources}).get('aws_sqs_queue.block_646c71').state,'failed');
});

test('track marks only finished steps complete',()=>{
  const labels=track=>track.map(step=>step.state);
  assert.deepEqual(labels(applyTrack([],null,false)),['','','','']);
  assert.deepEqual(labels(applyTrack([{stage:'Provider initialization',status:'passed',seconds:1},{stage:'Schema validation',status:'running'}],null,true)),['current','','','']);
  assert.deepEqual(labels(applyTrack(live,null,true)),['current','current','','']);   // init/validate not reported in this trace
  const done={status:'failed',stages:[...['Provider initialization','Schema validation','Plan','Apply','Independent API read-back'].map(name=>({name,status:'passed',seconds:1})),{name:'Convergence plan',status:'failed',seconds:1}],resources:[]};
  assert.deepEqual(labels(applyTrack([],done,false)),['complete','complete','failed','']);
});

test('caption reports counts from events and stays within twenty words',()=>{
  assert.equal(applyCaption(live,null,true),'Creating resources: 1/4. 19 API calls, all loopback.');
  assert.equal(applyCaption([],{message:'Done.'},false),'Done.');
  for(const stage of ['Destroy','Independent API read-back','Convergence plan','Destroy protection','Leak check','Plan'])
    assert.ok(applyCaption([...live,{stage,status:'running'}],null,true).split(' ').length<=20);
  assert.ok(applyCaption([],null,false).split(' ').length<=20);
});
