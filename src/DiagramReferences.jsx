import React,{useEffect,useRef} from 'react';
import {diagramReferenceRows} from './diagram-labels.mjs';
export function DiagramReferences({scene,selected,onSelect,open,onToggle}){
 const host=useRef(null),rows=diagramReferenceRows(scene),selection=Array.isArray(selected)?selected:[selected];
 useEffect(()=>{if(open&&selected)host.current?.querySelector('[data-selected=true]')?.scrollIntoView({block:'nearest'});},[open,selected]);
 return <section className="diagram-references" aria-label="Diagram details">
  <button type="button" className="diagram-references-toggle" aria-expanded={open} onClick={onToggle}>Details &amp; connections <span>{rows.length}</span><span aria-hidden="true">{open?'▾':'▸'}</span></button>
  {open&&<div className="diagram-reference-content" ref={host}>
   <p>Numbers on lines match these connections. Select an element for its properties.</p>
   <ol>{rows.map(row=><li key={row.id} data-connection-reference={row.number} data-record-id={row.id} data-selected={selection.includes(row.recordId)||selection.includes(row.id)}>
    <button type="button" onClick={()=>onSelect?.(row.recordId)}><strong>{row.number}</strong><span>{row.from} → {row.to}</span></button>
    <p>{row.description}</p>{row.record?.details?.length>0&&<dl>{row.record.details.map((d,i)=><React.Fragment key={i}><dt>{d.name}</dt><dd>{d.value}</dd></React.Fragment>)}</dl>}
   </li>)}</ol>
   <details><summary>Element properties · {scene.vertices.filter(v=>v.selectable!==false).length}</summary>
    {scene.vertices.filter(v=>v.selectable!==false).map(v=><article key={v.id} data-selected={selection.includes(v.id)}>
     <button type="button" onClick={()=>onSelect?.(v.id)}>{v.name}</button><p>{v.detailBody||v.body}</p>
     {v.record&&<details><summary>Complete properties</summary><pre>{JSON.stringify(v.record,null,2)}</pre></details>}
    </article>)}
   </details>
  </div>}
 </section>;
}
