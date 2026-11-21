import React,{useEffect,useRef} from 'react';

export function DiagramMermaid({code}){
  const box=useRef(null);
  useEffect(()=>{
    if(box.current)box.current.scrollTop=0;
  },[code]);
  return <label className="drawio-source">Mermaid source
    <textarea ref={box} readOnly value={code} aria-label="Mermaid source" spellCheck={false}/>
  </label>;
}
