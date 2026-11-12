import React,{useState} from 'react';
import {CheckCircle2, CircleHelp, Circle, RefreshCw, ChevronLeft, ChevronRight, MessageCircle, Plus, AlertCircle} from 'lucide-react';
import {reviewIssueLabel} from './component-review.mjs';
function QuestionAnswer({question,busy,onResolve}){
 const [answer,setAnswer]=useState('');
 return <details><summary>Record answer</summary><form onSubmit={e=>{e.preventDefault();if(answer.trim())onResolve(question.id,answer.trim());}}><label>Answer<textarea aria-label={`Answer: ${question.text}`} maxLength={2000} value={answer} onChange={e=>setAnswer(e.target.value)}/></label><button className="btn ghost" disabled={busy||!answer.trim()}>Save answer</button></form></details>;
}
function DetailAnswer({question,busy,onSave}){
 const [answer,setAnswer]=useState('');const ownership=question.id==='detail-Ownership recorded',region=question.id==='detail-Cloud region selected';
 return <form className="block-question-form" onSubmit={e=>{e.preventDefault();if(answer.trim())onSave(ownership?{origin:answer}:region?{config:{region:answer.trim()}}:{description:answer.trim()});}}><label>{ownership?'System ownership':region?'Cloud region':'Block responsibility'}{ownership?<select aria-label="System ownership" value={answer} onChange={e=>setAnswer(e.target.value)}><option value="">Choose…</option><option value="existing">Existing system</option><option value="proposed">Proposed component</option></select>:<textarea aria-label={region?'Cloud region answer':'Block responsibility answer'} maxLength={region?100:16000} value={answer} onChange={e=>setAnswer(e.target.value)}/>}</label><button className="btn ghost" disabled={busy||!answer.trim()}>Save detail</button></form>;
}
export function ReviewBadge({item,onClick}){
 const Icon={reviewed:CheckCircle2,questions:CircleHelp,issues:AlertCircle,ready:Circle,changed:RefreshCw}[item.status];
 const label=item.issues.length?reviewIssueLabel(item.issues):item.statusLabel,tone=item.status==='issues'?'questions':item.status;
 return onClick?<button className={`block-review-badge ${tone} nodrag`} aria-label={`Review ${item.label}: ${label}`} title={`${label} · design review, not runtime validation`} onClick={e=>{e.stopPropagation();onClick();}}><Icon size={13}/>{label}</button>:<span className={`block-review-badge ${tone}`}><Icon size={14}/>{label}</span>;
}
export function ComponentReview({item,items,busy,onOpen,onConfirm,onDiscuss,onQuestion,onResolve,onDetailAnswer}){
 const [adding,setAdding]=useState(false),[question,setQuestion]=useState('');const index=items.findIndex(r=>r.id===item.id);
 return <section className="component-review" aria-label="Block design review">
  <div className="block-review-heading"><strong>Block {index+1} of {items.length}</strong><ReviewBadge item={item}/></div>
  <div className="block-review-progress"><progress aria-label="Blocks reviewed" max={items.length} value={items.filter(r=>r.status==='reviewed').length}/><small>{items.filter(r=>r.status==='reviewed').length} reviewed</small></div>
  {item.status==='changed'&&<p>The block or its context changed. Check it again.</p>}
  {item.architectNote&&<div className="block-architect-note"><strong>{item.architectNoteCurrent?'Architect’s review':'Previous review · context changed'}</strong><p>{item.architectNote}</p></div>}
  <ul className="block-review-checks">{item.checks.map(c=><li key={c.label} className={c.passed?'complete':'incomplete'}>{c.passed?<CheckCircle2 size={14}/>:<CircleHelp size={14}/>} {c.label}</li>)}</ul>
  {!!item.issues.length&&<ul className="block-review-questions">{item.issues.map(q=><li key={q.id}><strong>{q.kind==='finding'?'Design issue':'Question'}</strong><span>{q.text}</span>{q.action&&<small>Suggested next step: {q.action}</small>}{q.kind==='question'&&<QuestionAnswer question={q} busy={busy} onResolve={onResolve}/>} {q.kind==='detail'&&<DetailAnswer question={q} busy={busy} onSave={onDetailAnswer}/>} {q.kind==='finding'&&<button className="link" disabled={busy} onClick={()=>onDiscuss(q)}>Ask Architect to plan this fix</button>}</li>)}</ul>}
  <div className="block-review-actions"><button className="btn primary" disabled={busy||item.issues.length>0||item.status==='reviewed'} onClick={onConfirm}><CheckCircle2 size={14}/>{item.status==='reviewed'?'Design reviewed':'Looks good'}</button><button className="btn ghost" disabled={busy} onClick={onDiscuss}><MessageCircle size={14}/>Ask Architect</button><button className="btn ghost" disabled={busy} onClick={()=>setAdding(!adding)}><Plus size={14}/>Question</button></div>
  {adding&&<form className="block-question-form" onSubmit={e=>{e.preventDefault();if(question.trim()){onQuestion(question.trim());setQuestion('');setAdding(false);}}}><label>Question about this block<textarea aria-label="Question about this block" maxLength={1000} value={question} onChange={e=>setQuestion(e.target.value)} autoFocus/></label><button className="btn" disabled={busy||!question.trim()}>Save question</button></form>}
  <small className="block-review-boundary">Design review only. Implementation and runtime checks are separate.</small>
  <nav className="block-review-navigation" aria-label="Review blocks one by one"><button className="btn ghost" disabled={index===0} onClick={()=>onOpen(items[index-1].id)}><ChevronLeft size={14}/>Previous</button><button className="btn ghost" disabled={index===items.length-1} onClick={()=>onOpen(items[index+1].id)}>Next block<ChevronRight size={14}/></button></nav>
 </section>;
}
