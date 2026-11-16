// Presentation of the Terraform apply emulation report. Never upgrades a result.
export const APPLY_LIFECYCLE=['Provider initialization','Schema validation','Plan','Apply','Independent API read-back','Convergence plan','Destroy','Leak check'];
export const APPLY_STATUS_TITLES={passed:'Apply emulation passed',failed:'Apply emulation failed',unsupported:'Emulator cannot run this design yet',blocked:'Apply emulation is blocked',unavailable:'Apply emulation is not available'};

const seconds=value=>Number.isFinite(value)?`${value}s`:'';

// Merge live progress events and the final report into one ordered stage list.
export function applyStages(events=[],report=null,running=false){
  const seen=new Map();
  for(const event of events)if(event?.stage)seen.set(event.stage,{name:event.stage,status:event.status,detail:event.status==='running'?(event.resources?`${event.resources} resources`:''):seconds(event.seconds)});
  for(const stage of report?.stages||[])seen.set(stage.name,{name:stage.name,status:stage.status,detail:stageDetail(stage)});
  if(!seen.size&&!running)return [];
  const names=[...new Set([...[...seen.keys()].filter(name=>!APPLY_LIFECYCLE.includes(name)&&name==='Application build'),...APPLY_LIFECYCLE.flatMap(name=>name==='Destroy'&&seen.has('Destroy protection')?['Destroy protection',name]:[name])])];
  const finished=!!report&&!running;
  return names.map(name=>seen.get(name)||{name,status:finished?'skipped':'pending',detail:''});
}

function stageDetail(stage){
  if(stage.name==='Apply'&&Number.isFinite(stage.planned))return `${stage.applied}/${stage.planned} resources · ${seconds(stage.seconds)}`;
  if(stage.name==='Independent API read-back'&&Number.isFinite(stage.sdkVerified))return `${stage.sdkVerified} by SDK · ${stage.providerRefreshOnly} by refresh`;
  if(stage.name==='Destroy protection'&&stage.protectedResources)return `${stage.protectedResources.length} protected · verified`;
  if(stage.name==='Convergence plan'&&stage.drift?.length)return `${stage.drift.length} still changing`;
  return seconds(stage.seconds);
}

export function applyEmulationSummary(report){
  if(!report?.resources?.length)return null;
  const resources=report.resources,applied=resources.filter(item=>item.applied).length;
  const verified=resources.filter(item=>item.checks?.length&&item.checks.every(check=>check.passed)).length;
  const types=Object.entries(report.resourceTypes||{}).map(([type,row])=>({type,...row}));
  return {
    facts:[
      {label:'resources applied',value:`${applied}/${resources.length}`},
      {label:'verified by SDK read-back',value:String(verified)},
      {label:'API calls, all loopback',value:String(report.apiCalls?.total??0)},
      {label:'cloud operations',value:report.cloudOperations===false?'0':'unknown'},
    ],
    types,
    gaps:[...(report.emulatorGaps?.resourceTypes||[]),...(report.emulatorGaps?.operations||[])],
    failures:resources.filter(item=>item.error).map(item=>({address:item.address,error:item.error.slice(0,600)})),
  };
}

// ---- Board dock and diagram animation -------------------------------------

export const APPLY_TRACK=[
  {label:'Plan',stages:['Application build','Provider initialization','Schema validation','Plan']},
  {label:'Apply',stages:['Apply']},
  {label:'Verify',stages:['Independent API read-back','Convergence plan']},
  {label:'Destroy',stages:['Destroy protection','Destroy','Leak check']},
];

// Each track step is current while one of its stages runs and complete only when all that ran passed.
export function applyTrack(events=[],report=null,running=false){
  const stages=new Map(applyStages(events,report,running).map(stage=>[stage.name,stage.status]));
  return APPLY_TRACK.map(step=>{
    const all=step.stages.map(name=>stages.get(name)).filter(Boolean),seen=all.filter(status=>status!=='pending'&&status!=='skipped');
    const waiting=running&&all.includes('pending');
    const state=seen.includes('failed')?'failed':seen.includes('running')?'current':!seen.length?'':seen.every(status=>status==='passed')&&!waiting?'complete':running?'current':'';
    return {label:step.label,state};
  });
}

// The design block a resource belongs to: its own block_<token> name, else its Component tag.
function blockOf(address,component,byToken){
  const name=String(address).split('.').pop().replace(/\[.*$/,'');
  for(const candidate of [name,component])if(typeof candidate==='string'&&candidate.startsWith('block_')&&byToken.has(candidate.slice(6)))return byToken.get(candidate.slice(6));
  return null;
}

// Latest reported state of every resource, in event order. Nothing is inferred between events.
export function applyResourceStates(events=[],report=null){
  const resources=new Map();
  const put=(item,state)=>{const previous=resources.get(item.resource)||{};resources.set(item.resource,{type:item.resourceType||previous.type,component:item.component||previous.component,state});};
  for(const event of events){
    if(Array.isArray(event?.planned))for(const item of event.planned)put(item,'planned');
    else if(event?.resource&&event.state)put(event,event.state);
  }
  for(const item of report?.resources||[]){
    const previous=resources.get(item.address);
    if(!previous)resources.set(item.address,{type:item.type,component:item.component,state:item.error?'failed':item.applied?'applied':'planned'});
    else if(item.error)previous.state='failed';
  }
  return resources;
}

const LIVE_ORDER=['failed','creating','destroying'];

// Diagram state per design block. While running it follows live resource events;
// when finished it shows the outcome (passed/failed) of that block's resources.
export function applyNodeStates(nodeIds,tokenOf,events=[],report=null,running=false){
  const byToken=new Map(nodeIds.map(id=>[tokenOf(id),id])),groups=new Map();
  for(const [address,resource] of applyResourceStates(events,report)){
    const node=blockOf(address,resource.component,byToken);
    if(node)groups.set(node,[...(groups.get(node)||[]),resource.state]);
  }
  const lifecyclePassed=report?.status==='passed',states={},counts={};
  for(const [node,list] of groups){
    const live=LIVE_ORDER.find(state=>list.includes(state));
    const settled=list.filter(state=>state==='applied'||state==='verified').length,gone=list.filter(state=>state==='destroyed').length;
    counts[node]=`${gone?list.length-gone:settled}/${list.length}`;
    if(!running&&report){states[node]=list.includes('failed')?'failed':lifecyclePassed?'passed':report.status==='unsupported'||report.status==='failed'?(list.every(state=>state!=='planned')?'applied':'skipped'):'idle';continue;}
    states[node]=live||(gone===list.length?'gone':gone?'destroying':settled===list.length?(list.includes('verified')?'verified':'applied'):settled?'creating':'planned');
  }
  return {states,counts};
}

// One short, factual line for the dock. Counts come from events, never estimates.
export function applyCaption(events=[],report=null,running=false){
  if(!running&&report)return report.message||'';
  if(!running)return 'Real Terraform and AWS provider. Loopback cloud API. No account or cost.';
  const resources=[...applyResourceStates(events).values()],total=resources.length;
  const calls=events.reduce((latest,event)=>Number.isFinite(event?.apiCalls)?event.apiCalls:latest,0);
  const current=[...events].reverse().find(event=>event?.stage&&event.status==='running')?.stage;
  if(current==='Apply')return `Creating resources: ${resources.filter(item=>item.state==='applied'||item.state==='verified').length}/${total}. ${calls} API calls, all loopback.`;
  if(current==='Destroy')return `Destroying: ${resources.filter(item=>item.state==='destroyed').length}/${total} gone. ${calls} API calls, all loopback.`;
  if(current==='Independent API read-back')return 'Reading resources back through the AWS SDK.';
  if(current==='Convergence plan')return 'Planning again. Any proposed change means drift.';
  if(current==='Destroy protection')return 'Checking that prevent_destroy blocks teardown.';
  if(current==='Leak check')return 'Querying service inventories. Nothing may remain.';
  return current?`${current}…`:'Starting a private loopback cloud and workspace.';
}
