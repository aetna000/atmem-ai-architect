import React,{useEffect,useRef} from 'react';
import {Layers3,Plus} from 'lucide-react';

export function DiagramPages({pages,active,onSelect,onAdd}){
  const strip=useRef(null);
  useEffect(()=>{
    const current=strip.current?.querySelector('[aria-selected=true]');
    if(current)strip.current.scrollLeft+=current.getBoundingClientRect().left-strip.current.getBoundingClientRect().left;
  },[active]);
  return <nav className="drawing-pagebar" aria-label="Diagram pages">
    {onAdd&&<button className="drawing-add-page" type="button" aria-label="Add diagram page" title="Add page" onClick={onAdd}><Plus size={16}/><span>Page</span></button>}
    <div ref={strip} className="drawio-pages" role="tablist" aria-label="Drawing pages">
      {pages.map(page=><button key={page.id} type="button" role="tab" aria-selected={page.id===active} onClick={()=>onSelect(page.id)}>{page.name}</button>)}
    </div>
    {pages.length>1&&<label className="drawing-page-jump" title="Go to page"><Layers3 size={16}/><select aria-label="Go to page" value={active} onChange={event=>onSelect(event.target.value)}>
      {pages.map(page=><option key={page.id} value={page.id}>{page.name}</option>)}
    </select></label>}
  </nav>;
}

export function projectPages(views=[],legacy=[],engineering=[]){
  return [{id:'board',name:'Board'},...views.map(page=>({id:'view/'+page.id,name:page.name})),
    ...legacy.map(page=>({id:'system/'+page.id,name:page.name})),...engineering.map(page=>({id:'engineering/'+page.id,name:page.name}))];
}
