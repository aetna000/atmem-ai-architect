import React, {useId, useState} from 'react';
// Small, non-HTML Markdown renderer: no remote images, raw HTML or executable URLs.
function inline(text){return text.split(/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\(https?:\/\/[^\s)]+\))/g).map((part,i)=>{
 if(part.startsWith('**')&&part.endsWith('**'))return <strong key={i}>{part.slice(2,-2)}</strong>;
 if(part.startsWith('`')&&part.endsWith('`'))return <code key={i}>{part.slice(1,-1)}</code>;
 const link=part.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/);if(link)return <a key={i} href={link[2]} target="_blank" rel="noopener noreferrer">{link[1]}</a>;
 return part;
});}
export function messagePreview(text){
 const words=text.trim().split(/\s+/);if(words.length<=20)return text;
 const questions=text.split(/\n+/).map(line=>line.trim()).filter(line=>line.includes('?')).map(line=>line.match(/(?:^|[.!]\s+)([^.!]*\?)/)?.[1]||line.slice(0,line.indexOf('?')+1));
 const question=questions.at(-1);if(question&&question.split(/\s+/).length<=20)return question;
 return words.slice(0,20).join(' ')+'…';
}
export function ChatMessage({text='',concise=false}){
 const [expanded,setExpanded]=useState(false);
 const detailId=useId();
 if(concise&&text.trim().split(/\s+/).length>20)return <div className="concise-answer"><div id={detailId}><ChatMessage text={expanded?text:messagePreview(text)}/></div><button type="button" className="link message-details" aria-expanded={expanded} aria-controls={detailId} onClick={()=>setExpanded(value=>!value)}>{expanded?'Less details':'More details'}</button></div>;

 const lines=text.split('\n'),blocks=[];let i=0;
 while(i<lines.length){
  if(!lines[i].trim()){i++;continue;}
  if(lines[i].startsWith('```')){const code=[];i++;while(i<lines.length&&!lines[i].startsWith('```'))code.push(lines[i++]);i++;blocks.push(<pre key={blocks.length}><code>{code.join('\n')}</code></pre>);continue;}
  const heading=lines[i].match(/^#{1,6}\s+(.+)$/);if(heading){blocks.push(<h4 key={blocks.length}>{inline(heading[1])}</h4>);i++;continue;}
  const list=lines[i].match(/^(?:[-*]|\d+[.)])\s+/);if(list){const ordered=/^\d/.test(list[0]),items=[];while(i<lines.length&&/^(?:[-*]|\d+[.)])\s+/.test(lines[i]))items.push(<li key={items.length}>{inline(lines[i++].replace(/^(?:[-*]|\d+[.)])\s+/,''))}</li>);blocks.push(ordered?<ol key={blocks.length}>{items}</ol>:<ul key={blocks.length}>{items}</ul>);continue;}
  const paragraph=[];while(i<lines.length&&lines[i].trim()&&!/^(?:```|#{1,6}\s|[-*]\s|\d+[.)]\s)/.test(lines[i]))paragraph.push(lines[i++]);blocks.push(<p key={blocks.length}>{paragraph.map((line,j)=><React.Fragment key={j}>{j>0&&<br/>}{inline(line)}</React.Fragment>)}</p>);
 }
 return <div className="chat-markdown">{blocks}</div>;
}
