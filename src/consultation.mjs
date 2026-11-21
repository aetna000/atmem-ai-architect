import { cleanRequirement } from './records.mjs';
import { newDecision } from './engagement.mjs';
// Only explicit current user choices become accepted decisions; drawing changes are separate.
export function applyDecisionUpdates(project,updates,message){
 let p=project;
 for(const update of updates||[]){
  if(!update.sourceText || !message.includes(update.sourceText))continue;
  const current=(p.decisions||[]).find(d=>d.subject===update.subject&&d.status==='Accepted');
  if(current?.decision===update.value)continue;
  const next={...newDecision(p),subject:update.subject,title:update.subject,decision:update.value,status:'Accepted',context:`User statement: ${update.sourceText}`,reason:current?`User changed the choice: ${update.sourceText}`:'Chosen in the conversation',supersedes:current?.id||null};
  p={...p,decisions:[...(p.decisions||[]).map(d=>d===current?{...d,status:'Superseded',supersededBy:next.id}:d),next]};
 }
 return p;
}

// Model-authored requirements remain proposals until the user confirms them in chat.
export function applyRequirementDrafts(project, drafts) {
 const nodeIds=new Set(project.nodes.map(n=>n.id));
 const needs=[...(project.needs||[])];
 for(const draft of drafts||[]) {
  if(!/^ai-[A-Za-z0-9-]{1,55}$/.test(draft.id))continue;
  const index=needs.findIndex(r=>r.id===draft.id);
  if(index>=0 && needs[index].source!=='agent')continue;
  const row=cleanRequirement({...draft,source:'agent',status:'open',links:(draft.links||[]).filter(id=>nodeIds.has(id))});
  if(index>=0)needs[index]=row;else needs.push(row);
 }
 return {...project,needs};
}

// Document feedback creates a reviewable proposal; only explicit acceptance edits text.
export function proposeCommentRevisions(project, snapshot, updates) {
 const comments=(project.extensions?.requirementComments||[]).map(c=>{
  const sent=snapshot.extensions?.requirementComments?.find(x=>x.id===c.id && x.text===c.text);
  const update=updates.find(u=>u.id===c.requirementId && u.sourceText===c.text);
  const before=snapshot.needs?.find(r=>r.id===c.requirementId)?.statement;
  const current=project.needs?.find(r=>r.id===c.requirementId)?.statement;
  if(!sent || !update || c.status!=='open' || before!==current || !before)return c;
  if(update.statement===before)return {...c,reviewMessage:'The suggested wording is unchanged. Discuss this comment to clarify what should change.'};
  return {...c,status:'proposed',before,after:update.statement,explanation:update.rationale || 'Suggested wording based on your comment. Review it before applying.'};
 });
 return {...project,extensions:{...project.extensions,requirementComments:comments}};
}
export function resolveCommentRevision(project,commentId,accept) {
 const comments=project.extensions?.requirementComments || [];
 const c=comments.find(x=>x.id===commentId);
 if(!c || c.status!=='proposed')return project;
 const r=project.needs.find(x=>x.id===c.requirementId);
 const stale=!r || r.statement!==c.before;
 const status=!accept?'dismissed':stale?'open':'reviewed';
 return {...project,needs:accept&&!stale?project.needs.map(x=>x.id===r.id?{...x,statement:c.after,source:'user',basis:`Accepted revision from your feedback: ${c.text}`}:x):project.needs,
  extensions:{...project.extensions,requirementComments:comments.map(x=>x.id===c.id?{...x,status,...(stale?{reviewMessage:'This requirement changed. Review your comment again against the current wording.'}:{})}:x)}};
}
