import React,{useState} from 'react';
import {Box,Search,Shapes} from 'lucide-react';
import {kindLabel} from './architecture-diagrams.mjs';
import {architectureShape,shapeLibraries} from './drawio-model.mjs';

const generalExtras=['mxgraph.basic.document','mxgraph.basic.rectangular_callout','mxgraph.basic.parallelepiped',
  'mxgraph.flowchart.predefined_process','mxgraph.flowchart.card','mxgraph.basic.trapezoid','mxgraph.flowchart.delay','mxgraph.basic.wave'];
const shapes=Object.assign({},...Object.values(shapeLibraries));
const general=Object.entries(shapeLibraries.General).concat(generalExtras.map(id=>[id,shapes[id]]));
const libraries={...shapeLibraries,General:Object.fromEntries(general)};

function ShapePreview({id}){
  return <svg aria-hidden="true" viewBox="0 0 38 30"><use href={import.meta.env.BASE_URL+'drawio/shape-previews.svg#'+id}/></svg>;
}

export function DrawioShapePalette({onAdd,elementKinds=[],blocks,disabled=false,boardTarget=false}){
  const [search,setSearch]=useState('');
  const [mode,setMode]=useState('shapes');
  const [expanded,setExpanded]=useState({General:true});
  const query=search.trim().toLowerCase();
  const elements=blocks||elementKinds.map(kind=>({id:kind,label:kindLabel(kind),shape:architectureShape(kind)}));
  function tool(id,label,icon){
    return <button type="button" key={id} title={label} aria-label={'Add '+label.toLowerCase()} disabled={disabled} draggable={!disabled}
      onDragStart={event=>{event.dataTransfer.setData('application/atmem-shape',id);event.dataTransfer.effectAllowed='copy';}}
      onClick={()=>onAdd(id)}>{icon}<span>{label}</span></button>;
  }
  function group(name,entries){
    const matches=entries.filter(([,label])=>label.toLowerCase().includes(query)||name.toLowerCase().includes(query));
    if(!matches.length)return null;
    const open=Boolean(query||expanded[name]);
    return <div className="drawing-shape-group" key={name}>
      <button className="drawing-group-toggle" type="button" aria-label={name} aria-expanded={open}
        onClick={()=>setExpanded(current=>({...current,[name]:!current[name]}))}>{name}</button>
      {open&&<div className="drawio-shapes">{matches.map(([id,label])=>tool(id,label,<ShapePreview id={id}/>))}</div>}
    </div>;
  }
  const libraryGroups=Object.entries(libraries).map(([name,entries])=>group(name,Object.entries(entries))).filter(Boolean);
  const matched=elements.filter(row=>(row.label+' '+(row.provider||'')).toLowerCase().includes(query));
  const shapeMode=mode==='shapes';
  const prompt=shapeMode?'Find a shape':'Find an element';
  return <section aria-label="Shape library" className="drawio-library">
    {boardTarget&&<h3>Place on Board</h3>}
    {(blocks||elementKinds.length>0)&&<div className="diagram-library-tabs" role="group" aria-label="Drawing tools">
      <button type="button" aria-pressed={shapeMode} onClick={()=>{setMode('shapes');setSearch('');}}><Shapes size={14}/> Shapes</button>
      <button type="button" aria-pressed={!shapeMode} onClick={()=>{setMode('elements');setSearch('');}}><Box size={14}/> Elements</button>
    </div>}
    <label className="architecture-search"><Search size={14}/><input value={search} onChange={event=>setSearch(event.target.value)} aria-label={prompt} placeholder={prompt}/></label>
    {shapeMode?libraryGroups:<div className="drawing-element-list">{matched.map(row=>tool('element:'+row.id,row.label,row.shape?<ShapePreview id={row.shape}/>:<Box size={15}/>))}</div>}
    {!(shapeMode?libraryGroups:matched).length&&<p className="diagram-library-empty">No matches</p>}
  </section>;
}
