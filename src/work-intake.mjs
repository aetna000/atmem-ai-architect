// User intent is logged immediately; one coherent writer applies the combined design.
export function restoreQueuedMessages(messages,projectId){
 return messages.filter(m=>m.role==='user'&&m.requestId&&['queued','processing'].includes(m.workState)).map(m=>({id:m.requestId,projectId,text:m.text,attachments:m.attachments||[]}));
}
export function nextIntakeBatch(queue,projectId,maxChars=8000){
 const items=[];let files=0;
 for(const item of queue.filter(q=>q.projectId===projectId)){
  if(item.attachments.some(a=>!a.data))return items.length?batch(items):{blocked:item.id,reason:'Attach the files again or continue with the text.'};
  const candidate=[...items,item],message=combine(candidate);
  if(items.length&&(message.length>maxChars||files+item.attachments.length>4))break;
  if(!items.length&&item.text.length>maxChars)throw Error('A queued message exceeds the request limit; no text was discarded.');
  items.push(item);files+=item.attachments.length;
  if(items.length>=8)break;
 }
 return items.length?batch(items):null;
}
function combine(items){return items.length===1?items[0].text:'Apply these user updates together, in order. Later explicit corrections take precedence. Preserve the rest of the agreed scope.\n\n'+items.map((x,i)=>`${i+1}. ${x.text}`).join('\n\n');}
function batch(items){return {items,message:combine(items),attachments:items.flatMap(x=>x.attachments),ids:items.map(x=>x.id)};}

export function restoreIntakePaused(messages){
 const terminal=messages.filter(m=>m.role==='user'&&['failed','complete','superseded'].includes(m.workState)).at(-1);
 return terminal?.workState==='failed';
}
