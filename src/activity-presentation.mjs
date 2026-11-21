const toolNames={'project.read':'Read the current design','memory.lookup':'Looked up project memory','knowledge.lookup':'Looked up engineering sources','skills.lookup':'Checked engineering guidance','pricing.lookup':'Checked provider pricing evidence','pricing.aws_s3':'Checked provider pricing evidence'};
export function publicStepText(event){
 const names={context_started:'Reading the design context',context_ready:'Design context ready',pass_started:'Preparing the next response',model_started:'Preparing a response',model_checked:'Checked the response',response_repair:'Retrying the reply format',response_ready:'Response ready',failed:'Could not finish',cancelled:'Stopped waiting'};
 if(event.kind==='model_message')return event.text;
 if(event.details?.tool){const label=toolNames[event.details.tool]||'Checked supporting evidence';return (event.kind==='tool_started'?label.replace('Looked up','Looking up').replace('Checked','Checking').replace('Read the','Reading the'):label)+(event.kind==='tool_cached'?' · used a saved result':event.kind==='tool_finished'&&event.details.success===false?' · evidence unavailable':'');}
 return names[event.kind]||event.text||'Work update recorded';
}
const detail=event=>[...(event.details?.recordCount!==undefined?[event.details.recordCount+' relevant memory references']:[]),...(event.details?.skillIds?.length?['Guidance: '+event.details.skillIds.join(', ')]:[])].join(' · ');
export function architectureSteps(events){
 const steps=[],pending=new Map();
 for(const event of events){
  const tool=event.details?.tool;
  if(event.kind==='tool_started'&&tool){
   // Without call IDs, overlapping starts are ambiguous and stay separate.
   if(pending.has(tool))pending.set(tool,null);else pending.set(tool,steps.length);
  }
  if(['tool_finished','tool_cached'].includes(event.kind)&&tool&&pending.get(tool)!=null){
   const index=pending.get(tool);steps[index]={...steps[index],text:publicStepText(event),detail:detail(event)||steps[index].detail,sources:[...steps[index].sources,event.sequence]};pending.delete(tool);continue;
  }
  if(['tool_finished','tool_cached'].includes(event.kind)&&tool)pending.delete(tool);
  steps.push({id:event.sequence,text:publicStepText(event),message:event.kind==='model_message',sources:[event.sequence],...(detail(event)?{detail:detail(event)}:{})});
 }
 return steps;
}
export function architectureActivityLabel(turn,state,active){
 const current=turn.clientStatus==='response_received'&&state==='running'?'response_ready':state;
 return ({running:active?'Working':'Awaiting details',response_ready:'Response received',failed:'Could not finish',cancelled:'Stopped waiting',recovery_required:'Outcome unknown after restart',details_unavailable:'Some details unavailable'}[current])||({submitted:active?'Working':'Awaiting details',response_received:'Response received',failed:'Request failed',cancelled:'Stopped waiting'}[turn.clientStatus])||'Activity';
}
