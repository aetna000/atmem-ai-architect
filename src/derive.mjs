import {prefillAcceptedSettings} from './engineering-defaults.mjs';
// Small, grounded working requirements. Unknown targets become conversation topics,
// not invented company policies or a large list of fields for the user to complete.
import { roleOf } from './review.mjs';
import { cleanRequirement } from './records.mjs';
export function deriveRequirements(project) {
  const nodes=project.nodes.filter(n=>n.data.kind!=='note');
  if(!nodes.length)return [];
  const out=[];
  const group=(roles)=>nodes.filter(n=>roles.includes(roleOf(n))).map(n=>n.id);
  const add=(id,category,statement,links)=>{if(links.length)out.push(cleanRequirement({id:`drv-${id}`,source:'agent',kind:'nonfunctional',category,priority:'should',status:'open',statement,links}));};
  add('data-access','security','Agree who can access the data and which content each person is allowed to use.',group(['data','index','llm']));
  add('data-location','compliance','Confirm where source data, model requests and logs may be processed and stored.',group(['data','index','llm']));

  return out.map(r=>({...r,rationale:r.id==='drv-data-access' ? 'The design uses information that people may have different rights to access. Clarifying this early helps prevent inappropriate disclosure.' : 'The design processes and stores information. We need to establish any location constraints before choosing services and regions.',basis:'Inferred from the data and AI components on the board; this is a question to validate, not an established company policy.'}));
}
export function withDerived(project){
 project=prefillAcceptedSettings(project);
 const mine=(project.needs||[]).filter(r=>!(r.source==='agent'&&r.id.startsWith('drv-')));
 const excluded=new Set([...(project.extensions?.dismissedRequirements||[]),...mine.map(r=>r.id)]);
 const needs=[...mine,...(mine.some(r=>r.id.startsWith("ai-")) ? [] : deriveRequirements(project)).filter(r=>!excluded.has(r.id))].slice(0,300);
 const numbers={...(project.extensions?.requirementNumbers || {})};
 let next=Math.max(0,...Object.values(numbers).filter(n=>Number.isSafeInteger(n)&&n>0))+1;
 for(const r of needs)if(!Number.isSafeInteger(numbers[r.id]) || numbers[r.id]<1)numbers[r.id]=next++;
 return {...project,needs,extensions:{...project.extensions,requirementNumbers:numbers}};
}

export function requirementNumber(project,id) {
 const value=project.extensions?.requirementNumbers?.[id];
 return Number.isSafeInteger(value)&&value>0 ? `REQ-${String(value).padStart(3,'0')}` : 'Requirement';
}
