import React, {useEffect,useRef,useState} from 'react';
import {MessageSquare} from 'lucide-react';
import {ReplyForm} from './RequirementsDocument.jsx';
import {commentKey} from './design-comments.mjs';

export function DesignComments({project,target,onSave,onRun,onApply,onReply,running,label="Comments"}){
  const [text,setText]=useState('');
  const [error,setError]=useState('');
  const details=useRef(null);
  const comments=(project.extensions?.designComments||[]).filter(row=>commentKey(row.target)===commentKey(target));
  const count=useRef(comments.length);
  useEffect(()=>{
    if(comments.length>count.current&&details.current)details.current.open=true;
    count.current=comments.length;
  },[comments.length]);
  if(!onSave)return null;
  function save(run){
    try{onSave(target,text,run);setText('');setError('');}
    catch(failure){setError(failure.message);}
  }
  return <details ref={details} className="design-comments">
    <summary><MessageSquare size={14}/> {label}{comments.length? ` (${comments.length})`:''}</summary>
    <div className="design-comment-body">
    <ul>{comments.map(comment=>{
      const active=running===comment.id;
      return <li key={comment.id}>
        {comment.quote&&<blockquote>{comment.quote}</blockquote>}<p>{comment.text}</p>
        {Array.isArray(comment.replies)&&comment.replies.map(reply=><p className="requirements-thread-reply" key={reply.id}>{String(reply.text||'')}</p>)}
        {onReply&&<ReplyForm onReply={value=>onReply(comment.id,value)}/>}
        <small role="status">{active?'AI is reviewing…':({queued:'Queued for Save',ready:'AI edit ready',answered:'AI response',applied:'AI edit applied',failed:'AI review failed'})[comment.status]}</small>
        {comment.error&&<p role="alert">{comment.error}</p>}
        {comment.proposal&&<><p>{comment.proposal.summary}</p>{comment.status==='ready'&&<>
          <dl>{Object.entries(comment.proposal.changes).map(([field,value])=><React.Fragment key={field}><dt>{field}</dt><dd>{Array.isArray(value)?value.join(', '):value}</dd></React.Fragment>)}</dl>
          <button type="button" className="btn primary" onClick={()=>{
            try{onApply(comment.id);setError('');}catch(failure){setError(failure.message);}
          }}>Apply AI edit</button>
        </>}</>}
        {!active&&['queued','failed','ready','answered'].includes(comment.status)&&<button type="button" className="link" onClick={()=>onRun(comment.id)}>
          {comment.status==='queued'?'Ask AI now':'Ask AI again'}</button>}
      </li>;
    })}</ul>
    <label>Comment<textarea rows={3} maxLength={1800} value={text} onChange={event=>setText(event.target.value)} placeholder="What should AI change here?"/></label>
    <div className="row">
      <button className="btn primary" type="button" disabled={!text.trim()} onClick={()=>save(true)}>Save &amp; ask AI</button>
      <button className="btn" type="button" disabled={!text.trim()} onClick={()=>save(false)}>Save for later</button>
    </div>
    {error&&<p role="alert">{error}</p>}
    </div>
  </details>;
}
