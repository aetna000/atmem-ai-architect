import {prefillAcceptedSettings} from './engineering-defaults.mjs';
// Small, grounded working requirements. Unknown targets become conversation topics,
// not invented company policies or a large list of fields for the user to complete.
import { roleOf } from './review.mjs';
import { cleanRequirement } from './records.mjs';
export const usesModels=project=>project.nodes.some(node=>node.data.kind!=='note'&&['llm','model'].includes(roleOf(node)));
export function deriveRequirements(project) {
  const nodes=project.nodes.filter(n=>n.data.kind!=='note');
  if(!nodes.length)return [];
  const out=[];
  const group=(roles)=>nodes.filter(n=>roles.includes(roleOf(n))).map(n=>n.id);
  const add=(id,category,statement,links)=>{if(links.length)out.push(cleanRequirement({id:`drv-${id}`,source:'agent',kind:'nonfunctional',category,priority:'should',status:'open',statement,links}));};
  add('data-access','security','Agree who can access the data and which content each person is allowed to use.',group(['data','index','llm']));
  add('data-location','compliance',usesModels(project)?'Confirm where source data, model requests and logs may be processed and stored.':'Confirm where project data and logs may be processed and stored.',group(['data','index','llm']));

  return out.map(r=>({...r,rationale:r.id==='drv-data-access' ? 'The design uses information that people may have different rights to access. Clarifying this early helps prevent inappropriate disclosure.' : 'The design processes and stores information. We need to establish any location constraints before choosing services and regions.',basis:'Proposed from the components on the board. Confirm the applicable policy with its owner.'}));
}
export function withDerived(project){
 project=prefillAcceptedSettings(project);
 const mine=(project.needs||[]).filter(r=>!(r.source==='agent'&&r.id.startsWith('drv-')));
 const excluded=new Set([...(project.extensions?.dismissedRequirements||[]),...mine.map(r=>r.id)]);
 const needs=[...mine,...(mine.some(r=>r.id.startsWith("ai-")) ? [] : deriveRequirements(project)).filter(r=>!excluded.has(r.id))];
 const numbers={...(project.extensions?.requirementNumbers || {})};
 let next=Object.values(numbers).reduce((max,n)=>Number.isSafeInteger(n)&&n>max?n:max,0)+1;
 for(const r of needs)if(!Number.isSafeInteger(numbers[r.id]) || numbers[r.id]<1)numbers[r.id]=next++;
 return {...project,needs,extensions:{...project.extensions,requirementNumbers:numbers}};
}

export function requirementNumber(project,id) {
 const value=project.extensions?.requirementNumbers?.[id];
 return Number.isSafeInteger(value)&&value>0 ? `REQ-${String(value).padStart(3,'0')}` : 'Requirement';
}
