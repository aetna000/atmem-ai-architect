import {newQuestion} from './records.mjs';
import {review} from './review.mjs';

export const REVIEW_LABELS={questions:'Questions',ready:'Needs review',reviewed:'Looks good',changed:'Review again'};
const canonical=value=>JSON.stringify(value,(_,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,v[k]])):v);
// UI change token, not a security signature or runtime evidence receipt.
function token(value){let a=2166136261,b=5381;for(const c of canonical(value)){a=Math.imul(a^c.charCodeAt(0),16777619);b=Math.imul(b,33)^c.charCodeAt(0);}return (a>>>0).toString(16).padStart(8,'0')+(b>>>0).toString(16).padStart(8,'0');}
function signature(project,node){
 const edges=project.edges.filter(e=>e.source===node.id||e.target===node.id).map(({id,source,target,label,integration,access})=>({id,source,target,label,integration,access})).sort((a,b)=>a.id.localeCompare(b.id));
 const neighbors=new Set(edges.flatMap(e=>[e.source,e.target]));
 const fields=({id,data:d})=>({id,label:d.label,description:d.description,kind:d.kind,provider:d.provider,service:d.service,origin:d.origin,binding:d.binding,implementation:d.implementation,deploymentMode:d.deploymentMode,role:d.role,config:{timeout:5000,...d.config},poc:!!d.poc});
 return token({node:fields(node),edges,neighbors:project.nodes.filter(n=>n.id!==node.id&&neighbors.has(n.id)).map(fields).sort((a,b)=>a.id.localeCompare(b.id)),needs:(project.needs||[]).filter(r=>r.links?.includes(node.id)),questions:(project.openQuestions||[]).filter(q=>q.links?.includes(node.id)),decisions:project.decisions||[]});
}
export function componentReviews(project){
 const findings=review(project).filter(f=>f.status==='open'&&['blocker','major'].includes(f.severity));
 return project.nodes.filter(n=>n.data.kind!=='note').map(node=>{
  const d=node.data,checks=[{label:'Purpose described',passed:!!d.description?.trim()},{label:'Ownership recorded',passed:['existing','proposed'].includes(d.origin)}];
  if(d.origin!=='existing'&&['aws','azure','gcp','ibm'].includes(d.provider))checks.push({label:'Cloud region selected',passed:!!d.config?.region&&!/to be|undecided|unknown|select/i.test(d.config.region)});
  const questions=(project.openQuestions||[]).filter(q=>q.status!=='answered'&&q.links?.includes(node.id)).map(q=>({id:q.id,text:q.question,kind:'question'}));
  const issues=[...checks.filter(c=>!c.passed).map(c=>({id:'detail-'+c.label,text:c.label==='Purpose described'?'What is this block responsible for?':c.label==='Ownership recorded'?'Is this an existing system or a proposed component?':'Which cloud region should this block use?',kind:'detail'})),...questions,...findings.filter(f=>f.components?.includes(node.id)).map(f=>({id:f.key,text:f.statement,action:f.action,kind:'finding'}))];
  const fingerprint=signature(project,node),record=project.extensions?.componentReviews?.[node.id];
  const status=issues.length?'questions':record?.fingerprint===fingerprint?'reviewed':record?'changed':'ready';
  const note=project.extensions?.componentReviewNotes?.[node.id];
  return {id:node.id,label:d.label,status,statusLabel:REVIEW_LABELS[status],checks,issues,fingerprint,reviewedAt:record?.reviewedAt,architectNote:note?.summary||null,architectNoteCurrent:note?.fingerprint===fingerprint};
 });
}
export function markComponentReviewed(project,id){
 const item=componentReviews(project).find(r=>r.id===id);
 if(!item||item.issues.length)throw Error('Resolve this block’s questions before marking its design reviewed.');
 return {...project,extensions:{...project.extensions,componentReviews:{...project.extensions?.componentReviews,[id]:{version:1,fingerprint:item.fingerprint,reviewedAt:new Date().toISOString(),scope:'user_design_review_not_runtime_validation'}}}};
}

export function applyComponentReview(project,target,result){
 const current=componentReviews(project).find(r=>r.id===target.id);
 if(!current||current.fingerprint!==target.fingerprint||result.componentId!==target.id)throw Error('This block changed during the review. Review its current version again.');
 if(typeof result.summary!=='string'||!result.summary.trim()||result.summary.length>2000||!Array.isArray(result.questions)||result.questions.length>6||result.questions.some(q=>typeof q!=='string'||!q.trim()||q.length>1000))throw Error('The block review needs a valid summary and bounded questions.');
 const questions=[...(project.openQuestions||[])];
 for(const text of result.questions){if(!questions.some(q=>q.links?.includes(target.id)&&q.question.trim()===text.trim()))questions.push(newQuestion({id:'block-q-'+token([target.id,text.trim()]),question:text.trim(),links:[target.id]}));}
 if(questions.length>300)throw Error('Too many project questions; no block questions were discarded.');
 const next={...project,openQuestions:questions};const fingerprint=componentReviews(next).find(r=>r.id===target.id).fingerprint;
 return {...next,extensions:{...next.extensions,componentReviewNotes:{...next.extensions?.componentReviewNotes,[target.id]:{summary:result.summary.trim(),fingerprint,reviewedAt:new Date().toISOString(),scope:'model_design_advice_not_runtime_validation'}}}};
}

export function editBlockRequirement(project,nodeId,id,statement){
 const record=(project.needs||[]).find(r=>r.id===id&&r.links?.includes(nodeId));
 if(!record)throw Error('This requirement is no longer linked to the block.');
 if(typeof statement!=='string'||!statement.trim()||statement.length>1000)throw Error('Use 1–1,000 characters for the requirement.');
 const edits=project.extensions?.requirementEditHistory||[];
 if(edits.length>=300)throw Error('Requirement edit history is full; archive the project before adding more edits.');
 return {...project,needs:project.needs.map(r=>r.id===id?{...r,statement:statement.trim(),source:'user',status:'open',basis:'Edited by the user in block review; implementation must be re-evaluated.'}:r),extensions:{...project.extensions,requirementEditHistory:[...edits,{requirementId:id,nodeId,previousStatement:record.statement,statement:statement.trim(),at:new Date().toISOString()}]}};
}
