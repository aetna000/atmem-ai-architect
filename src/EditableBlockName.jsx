import React,{useEffect,useRef,useState} from 'react';
export function EditableBlockName({name,onRename,disabled=false,label='Block name'}){
 const [draft,setDraft]=useState(name),[error,setError]=useState('');const saved=useRef(name);
 useEffect(()=>{saved.current=name;setDraft(name);setError('');},[name]);
 function save(){
  const value=draft.trim();if(disabled||value===saved.current)return;
  if(!value){setError('Enter a name.');return;}
  if(value.length>150){setError('Use 150 characters or fewer.');return;}
  try{onRename(value);saved.current=value;setDraft(value);setError('');}catch(failure){setError(failure.message);}
 }
 return <div className="editable-block-name"><label>{label}<input aria-label={label} value={draft} disabled={disabled} maxLength={150} onChange={e=>{setDraft(e.target.value);setError('');}} onBlur={save} onKeyDown={e=>{
  if(e.key==='Enter'){e.preventDefault();e.stopPropagation();save();}
  if(e.key==='Escape'){e.preventDefault();e.stopPropagation();setDraft(saved.current);setError('');}
 }}/></label>{draft.trim()!==saved.current&&<button className="btn" disabled={disabled} onMouseDown={e=>e.preventDefault()} onClick={save}>Save name</button>}{error&&<small role="alert">{error}</small>}</div>;
}
