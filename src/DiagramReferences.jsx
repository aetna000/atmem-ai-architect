import React,{useEffect,useRef,useState} from 'react';
import {diagramReferenceRows} from './diagram-labels.mjs';
export function DiagramReferences({scene,selected,onSelect,onEdit,open,onToggle,properties,propertiesVisible}){
 const [pane,setPane]=useState('properties');
 useEffect(()=>{if(propertiesVisible)setPane('properties');},[propertiesVisible]);
 const host=useRef(null),rows=diagramReferenceRows(scene),selection=Array.isArray(selected)?selected:[selected];
 useEffect(()=>{if(open&&selected)host.current?.querySelector('[data-selected=true]')?.scrollIntoView({block:'nearest'});},[open,selected]);
 useEffect(()=>{if(scene.wires.some(w=>selection.includes(w.id)||selection.includes(w.recordId)))setPane('connections');else if(scene.vertices.some(v=>selection.includes(v.id)))setPane('properties');},[selected]);
 return <section className="diagram-references" data-open={open} aria-label="Diagram details">
  <header className="drawing-properties-header">
   <button type="button" className="drawing-properties-toggle" aria-label={open?'Hide properties':'Show properties'} aria-expanded={open} onClick={onToggle}><span aria-hidden="true">{open?'‹':'›'}</span><span>Properties</span></button>
  </header>
  {open&&<div className="drawing-bottom-tabs" role="group" aria-label="Drawing details">
   <button type="button" className="diagram-references-toggle" aria-pressed={pane==='properties'} onClick={()=>setPane('properties')}>Properties</button>
   <button type="button" className="diagram-references-toggle" aria-pressed={pane==='connections'} onClick={()=>setPane('connections')}>Connections <span>{rows.length}</span></button>
  </div>}
  {open&&pane==='properties'&&<div className="diagram-reference-content drawing-bottom-properties">{properties||<p>Select an element.</p>}</div>}
  {open&&pane==='connections'&&<div className="diagram-reference-content" ref={host}>
   <p>Numbers on lines match these connections. Select an element for its properties.</p>
   <ol>{rows.map(row=><li key={row.id} data-connection-reference={row.number} data-record-id={row.id} data-selected={selection.includes(row.recordId)||selection.includes(row.id)}>
    <button type="button" onClick={()=>onSelect?.(row.recordId)}><strong>{row.number}</strong><span>{row.from} → {row.to}</span></button>
    {onEdit&&<button className="diagram-reference-edit" type="button" aria-label={'Edit connection '+row.number} onClick={()=>{onSelect?.(row.recordId);onEdit(row.recordId);}}>Edit connection</button>}
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
