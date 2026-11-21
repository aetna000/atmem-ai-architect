import React from 'react';
// React escapes every token; previews never inject HTML or execute source.
export function CodePreview({content,name='',className=''}){
 const source=typeof content==='string'?content:String(content);
 const pattern=/("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\/\/[^\n]*|#[^\n]*|\b(?:true|false|null|resource|variable|output|provider|terraform|module|locals|data)\b|\b\d+(?:\.\d+)?\b)/g;
 const parts=source.split(pattern);
 return <pre className={`code-preview ${className}`} aria-label={name||'Code preview'}><code>{parts.map((text,i)=>i%2?<span key={i} className={/^['"]/.test(text)?(/^\s*:/.test(parts[i+1]||'')?'code-key':'code-string'):/^(\/\/|#)/.test(text)?'code-comment':/^\d/.test(text)?'code-number':'code-keyword'}>{text}</span>:text)}</code></pre>;
}
