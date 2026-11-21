import React, {useEffect, useId, useMemo, useRef, useState} from 'react';
import dagre from 'dagre';
import {ArrowUpRight, ArrowLeft, Plus, Play, Pause, SkipForward, ZoomIn, ZoomOut} from 'lucide-react';
import {interfaceFields} from './block-spec.mjs';
import {diagramElements, removeModelRecord, systemDiagramKinds, systemModelIndex, systemModelOnBoard} from './system-model.mjs';
import './system-model.css';

const labels = {actor:'Actor', component:'Logical component', function:'Logical function',
  componentPort:'Component port', functionPort:'Function port', componentExchange:'Component exchange',
  functionalExchange:'Functional exchange'};
const box = {width:216, height:82};
const shorten = (value, length = 29) => value.length > length ? value.slice(0,length-1)+'…' : value;

function selectProps(id, name, selected, select) {
  return {role:'button', tabIndex:0, 'aria-label':name, 'aria-pressed':selected===id,
    onClick:()=>select(id), onKeyDown:event=>{
      if (event.key==='Enter'||event.key===' ') {event.preventDefault();select(id);}
    }};
}

function ModelNode({element,x,y,selected,select,index,onPointerDown,width=box.width}) {
  return <g className="system-model-symbol" data-kind={element.kind} onPointerDown={onPointerDown} transform={`translate(${x},${y})`}
      {...selectProps(element.id,element.name,selected,select)}>
    <title>{element.name}</title>
    <rect className="system-model-shape" width={width} height={box.height} rx={element.kind==='function'?19:2}/>
    <text className="system-model-metaclass" x={14} y={22}>«{labels[element.kind]}»</text>
    <text className="system-model-node-name" x={14} y={44}>{shorten(element.name)}</text>
    {(element.parentId||element.allocatedTo)&&<text className="system-model-context" x={14} y={63}>
      {shorten(index.elements.get(element.parentId||element.allocatedTo).name,32)}
    </text>}
    {element.kind==='component'&&<path className="system-model-glyph" d={`M${width-28} 13h15v16h-15z m-4 3h8v4h-8z m0 7h8v4h-8z`}/>}
    {element.kind==='actor'&&<g className="system-model-actor" transform={`translate(${width-23},15)`}>
      <circle r="3"/><path d="M0 4v8m-6-4h12m-6 4-4 6m4-6 4 6"/>
    </g>}
  </g>;
}

function GraphView({diagram,index,selected,select,marker,onMove,zoom}) {
  const drag=useRef(null);
  const [moving,setMoving]=useState(null);
  const layout=useMemo(()=>{
    const graph=new dagre.graphlib.Graph({multigraph:true}).setGraph({
      rankdir:'LR', nodesep:58, ranksep:84, edgesep:36, marginx:34, marginy:38,
    }).setDefaultEdgeLabel(()=>({}));
    for(const id of diagram.elementIds) graph.setNode(id,{...box});
    for(const id of diagram.exchangeIds){
      const exchange=index.exchanges.get(id);
      const [from,to]=index.participants(exchange);
      graph.setEdge(from,to,{width:Math.min(220,shorten(exchange.name,32).length*7+14),height:22,labelpos:'c'},id);
    }
    dagre.layout(graph);
    return graph;
  },[diagram,index]);
  const placement=id=>{
    const node=layout.node(id);
    return (moving?.id===id?moving:diagram.positions?.[id])||{x:node.x-box.width/2,y:node.y-box.height/2};
  };
  const pointsOnView=diagram.elementIds.map(placement);
  const width=Math.max(layout.graph().width,...pointsOnView.map(point=>point.x+box.width+35));
  const height=Math.max(layout.graph().height,...pointsOnView.map(point=>point.y+box.height+35));
  const coordinate=event=>new DOMPoint(event.clientX,event.clientY).matrixTransform(event.currentTarget.getScreenCTM().inverse());
  function move(event){
    if(!drag.current)return;
    const point=coordinate(event);
    const {id,origin,start}=drag.current;
    const x=point.x-start.x,y=point.y-start.y;
    if(Math.hypot(x,y)<3&&!moving)return;
    setMoving({id,x:Math.min(100000,Math.max(0,Math.round(origin.x+x))),y:Math.min(100000,Math.max(0,Math.round(origin.y+y)))});
  }
  function finish(event){
    if(!drag.current)return;
    drag.current=null;
    if(moving&&event.type!=='pointercancel')onMove(moving.id,{x:moving.x,y:moving.y});
    setMoving(null);
  }
  return <svg aria-label={diagram.name} width={width*zoom} height={height*zoom} viewBox={`0 0 ${width} ${height}`}
    onPointerMove={move} onPointerUp={finish} onPointerCancel={finish}>
    <ArrowMarker id={marker}/>
    {diagram.elementIds.map(id=>{
      const origin=placement(id);
      return <ModelNode key={id} element={index.elements.get(id)} {...origin}
        onPointerDown={onMove?event=>{
          if(event.button!==0)return;
          const svg=event.currentTarget.ownerSVGElement;
          drag.current={id,origin,start:new DOMPoint(event.clientX,event.clientY).matrixTransform(svg.getScreenCTM().inverse())};
          svg.setPointerCapture(event.pointerId);
          select(id);
        }:undefined}
        selected={selected} select={select} index={index}/>;
    })}
    {layout.edges().map(key=>{
      const exchange=index.exchanges.get(key.name);
      let {x,y,points}=layout.edge(key);
      if([key.v,key.w].some(id=>diagram.positions?.[id]||moving?.id===id)){
        const a=placement(key.v),b=placement(key.w);
        const source={x:a.x+box.width/2,y:a.y+box.height/2},target={x:b.x+box.width/2,y:b.y+box.height/2};
        const dx=target.x-source.x,dy=target.y-source.y;
        const magnitude=Math.max(Math.abs(dx)/(box.width/2),Math.abs(dy)/(box.height/2),1);
        points=[{x:source.x+dx/magnitude,y:source.y+dy/magnitude},{x:target.x-dx/magnitude,y:target.y-dy/magnitude}];
        x=(points[0].x+points[1].x)/2;
        y=(points[0].y+points[1].y)/2;
      }
      const first=points[0],last=points.at(-1);
      return <g className="system-model-wire" key={exchange.id} {...selectProps(exchange.id,exchange.name,selected,select)}>
        <title>{exchange.name}</title>
        <polyline className="system-model-wire-hit" points={points.map(p=>`${p.x},${p.y}`).join(' ')}/>
        <polyline points={points.map(p=>`${p.x},${p.y}`).join(' ')} markerEnd={`url(#${marker})`}/>
        {[first,last].map((p,i)=><rect key={i} x={p.x-3.5} y={p.y-3.5} width={7} height={7}/>)}
        <text x={x} y={y-8} textAnchor="middle">{shorten(exchange.name,32)}</text>
      </g>;
    })}
  </svg>;
}

function ArrowMarker({id}) {
  return <defs><marker id={id} viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto">
    <path d="M0 1 9 5 0 9" className="system-model-arrow" fill="none" strokeWidth="1.4"/>
  </marker></defs>;
}

function SequenceView({diagram,index,selected,select,marker,step,onStep,zoom}) {
  const pitch=280,width=224,height=145+diagram.exchangeIds.length*57;
  const column=new Map(diagram.elementIds.map((id,i)=>[id,28+i*pitch+width/2]));
  const svg=useRef(null);
  useEffect(()=>{
    if(step>=0)svg.current?.querySelector('[data-playing="true"]')?.scrollIntoView({block:'nearest',inline:'nearest'});
  },[step]);
  return <svg ref={svg} aria-label={diagram.name} width={diagram.elementIds.length*pitch*zoom} height={height*zoom}
    viewBox={`0 0 ${diagram.elementIds.length*pitch} ${height}`}>
    <ArrowMarker id={marker}/>
    {diagram.elementIds.map(id=><g key={id}>
      <line className="system-model-lifeline" x1={column.get(id)} x2={column.get(id)} y1={box.height+22} y2={height-22}/>
      <ModelNode element={index.elements.get(id)} x={column.get(id)-width/2} y={22} width={width}
        selected={selected} select={select} index={index}/>
    </g>)}
    {diagram.exchangeIds.map((id,i)=>{
      const exchange=index.exchanges.get(id);
      const [from,to]=index.participants(exchange).map(id=>column.get(id));
      const y=142+i*57;
      return <g className="system-model-wire" data-playing={i===step} key={i} {...selectProps(id,`${i+1}. ${exchange.name}`,selected,value=>{select(value);onStep(i);})}>
        <title>{exchange.name}</title>
        <line className="system-model-wire-hit" x1={from} x2={to} y1={y} y2={y}/>
        <line x1={from} x2={to} y1={y} y2={y} markerEnd={`url(#${marker})`}/>
        <text x={(from+to)/2} y={y-9} textAnchor="middle">{i+1}. {shorten(exchange.name,34)}</text>
      </g>;
    })}
  </svg>;
}

function Inspector({record,index,project,select,onOpenBlock}) {
  const {elements,exchanges,participants}=index;
  const block=project.nodes.find(node=>node.id===record.blockId);
  const edge=project.edges.find(edge=>edge.id===record.interfaceId);
  const byRequirement=new Map((project.needs||[]).map(row=>[row.id,row]));
  const portIds=[record.source,record.target].filter(Boolean);
  const allocatedTo=elements.get(record.allocatedTo);
  const children=[...elements.values()].filter(row=>[row.ownerId,row.allocatedTo,row.parentId].includes(record.id));
  const linked=[...exchanges.values()].filter(row=>row.componentExchangeId===record.id||
    row.id===record.componentExchangeId||row.source===record.id||row.target===record.id||participants(row).includes(record.id));
  const contractEdge=edge||project.edges.find(row=>row.id===exchanges.get(record.componentExchangeId)?.interfaceId);
  const cases=project.nodes.flatMap(node=>(node.data.buildSpec?.verificationCases||[])
    .filter(row=>contractEdge?row.interfaceId===contractEdge.id:node.id===block?.id&&row.requirementIds?.some(id=>record.requirementIds.includes(id)))
    .map(row=>({...row,blockId:node.id})));
  const openRow=id=>{
    const part=elements.get(id)||exchanges.get(id);
    return <button type="button" className="link" onClick={()=>select(id)}>{part.name}</button>;
  };
  const kind=record.kind+(exchanges.has(record.id)?'Exchange':'');
  return <>
    <span className="system-model-type">{labels[kind]} · {record.basis==='source'?'Source-backed':'Proposed'}</span>
    <h3>{record.name}</h3>
    <p>{record.description}</p>
    {record.parentId&&<p>Parent · {openRow(record.parentId)}</p>}
    {record.ownerId&&<p>Owner · {openRow(record.ownerId)}</p>}
    {record.direction&&<p>Direction · {record.direction}</p>}
    {allocatedTo&&<p>Allocated to · {openRow(allocatedTo.id)}</p>}
    {portIds.length>0&&<><h4>Ports</h4>{portIds.map(id=><div key={id}>{openRow(id)} · {elements.get(elements.get(id).ownerId).name}</div>)}</>}
    {!!record.items?.length&&<><h4>Exchange items</h4><ul>{record.items.map(item=><li key={item}>{item}</li>)}</ul></>}
    {record.blockId&&(block?(onOpenBlock?<button className="btn" onClick={()=>onOpenBlock(block.id)}>Open module <ArrowUpRight size={14}/></button>:<p>Module · {block.data.label}</p>):<p>Linked module is missing.</p>)}
    {record.interfaceId&&<><h4>Interface contract</h4>{edge?.interfaceSpec?
      <dl>{Object.entries(interfaceFields).filter(([field])=>edge.interfaceSpec?.[field]).map(([field,label])=>
        <React.Fragment key={field}><dt>{label}</dt><dd>{edge.interfaceSpec[field]}</dd></React.Fragment>)}</dl>:
      <p>{edge?'Interface contract details are open.':'Linked interface is missing.'}</p>}</>}
    {!!cases.length&&<><h4>Verification cases</h4><ul>{cases.map(row=><li key={row.blockId+'/'+row.id}>{row.name}</li>)}</ul></>}
    {!!record.requirementIds.length&&<><h4>Requirements</h4><ul>{record.requirementIds.map(id=><li key={id}>
      {byRequirement.get(id)?.statement||`Missing requirement · ${id}`}
    </li>)}</ul></>}
    {!!children.length&&<><h4>Owned and allocated elements</h4><ul>{children.map(row=><li key={row.id}>{openRow(row.id)}</li>)}</ul></>}
    {!!linked.length&&<><h4>Related exchanges</h4><ul>{linked.map(row=><li key={row.id}>{openRow(row.id)}</li>)}</ul></>}
  </>;
}

const newId=()=>crypto.randomUUID();
const blankModel=()=>({format:'atmem.system-model',version:1,id:newId(),authoring:'manual',elements:[],exchanges:[],diagrams:[]});
const baseRecord=(kind,name,description)=>({id:newId(),kind,name,description,basis:'proposed',requirementIds:[]});

export function SystemModelWorkspace({project,onBack,onOpenBlock,onGenerate,onSave,onSaveProject,renderComments,onUndo,onRedo,canUndo,canRedo}) {
  const savedModel=project.extensions?.systemModel;
  const model=useMemo(()=>savedModel?systemModelOnBoard(savedModel,project):blankModel(),[savedModel,project.nodes,project.edges]);
  const index=useMemo(()=>systemModelIndex(model),[model]);
  const marker=useId();
  const [viewId,setView]=useState(null);
  const [selected,setSelected]=useState(null);
  const [fit,setFit]=useState(true);
  const [zoom,setZoom]=useState(1);
  const [editing,setEditing]=useState(null);
  const inspector=useRef(null);
  useEffect(()=>{
    if(!editing||!inspector.current)return;
    inspector.current.scrollTop=0;
    if(window.matchMedia('(max-width: 1000px)').matches)inspector.current.scrollIntoView({block:'nearest'});
  },[editing]);
  const [error,setError]=useState('');
  const [step,setStep]=useState(-1);
  const [playing,setPlaying]=useState(false);
  const diagram=model.diagrams.find(row=>row.id===viewId)||model.diagrams[0];
  const record=index.elements.get(selected)||index.exchanges.get(selected);
  const containing=record&&model.diagrams.filter(row=>row.elementIds.includes(record.id)||row.exchangeIds.includes(record.id));
  const count=diagram?.kind==='sequence'?diagram.exchangeIds.length:0;
  useEffect(()=>{
    if(!playing)return;
    if(step>=count-1){setPlaying(false);return;}
    const timer=setTimeout(()=>setStep(step+1),700);
    return ()=>clearTimeout(timer);
  },[playing,step,count]);

  function openView(id){
    setView(id);setSelected(null);setStep(-1);setPlaying(false);setEditing(null);setError('');
  }
  function apply(transform){
    if(!onSave)return false;
    try{
      const snapshot=savedModel||model;
      onSave({...transform(snapshot),authoring:'manual'});
      setError('');
      return true;
    }catch(failure){setError(failure.message);return false;}
  }
  function updateView(transform){
    return apply(snapshot=>({...snapshot,diagrams:snapshot.diagrams.map(row=>row.id===diagram.id?transform(row):row)}));
  }
  function edit(action){setError('');setEditing(action);}
  function selectRecord(id){setSelected(id);edit(null);}
  function zoomBy(delta){setFit(false);setZoom(value=>Math.min(2,Math.max(.25,value+delta)));}
  function submit(event){
    event.preventDefault();
    const data=new FormData(event.currentTarget);
    const value=key=>String(data.get(key)||'').trim();
    if(editing==='new-view'){
      const view={id:newId(),name:value('name'),kind:value('kind'),elementIds:[],exchangeIds:[]};
      if(apply(model=>({...model,diagrams:[...model.diagrams,view]})))openView(view.id);
      return;
    }
    if(editing==='rename-view'){
      if(updateView(view=>({...view,name:value('name')})))setEditing(null);
      return;
    }
    if(editing==='reuse'){
      if(updateView(view=>({...view,elementIds:[...view.elementIds,value('element')]})))setEditing(null);
      return;
    }
    if(editing==='message'){
      if(updateView(view=>({...view,exchangeIds:[...view.exchangeIds,value('exchange')]})))setEditing(null);
      return;
    }
    const name=value('name'),description=value('description');
    if(!name||!description){setError('Enter a name and description.');return;}
    if(editing==='edit'){
      const collection=index.exchanges.has(record.id)?'exchanges':'elements';
      function update(row){
        if(row.id!==record.id)return row;
        const next={...row,name,description};
        if(collection==='exchanges'){
          next.items=value('items').split('\n').map(item=>item.trim()).filter(Boolean);
          next.source=value('source');
          next.target=value('target');
        }
        next.requirementIds=data.getAll('requirements');
        if('direction' in row)next.direction=value('direction');
        for(const key of ['parentId','allocatedTo','blockId','interfaceId','componentExchangeId']){
          if(!data.has(key))continue;
          if(value(key))next[key]=value(key);else delete next[key];
        }
        return next;
      }
      if(apply(model=>({...model,[collection]:model[collection].map(update)})))setEditing(null);
      return;
    }
    if(editing==='exchange'){
      const next={...baseRecord(diagram.kind==='functions'?'functional':'component',name,description),
        source:value('source'),target:value('target'),items:value('items').split('\n').map(item=>item.trim()).filter(Boolean)};
      if(apply(model=>({...model,exchanges:[...model.exchanges,next],diagrams:model.diagrams.map(view=>
        view.id===diagram.id?{...view,exchangeIds:[...view.exchangeIds,next.id]}:view)}))){
        setSelected(next.id);setEditing(null);
      }
      return;
    }
    const isPort=editing==='port';
    const next=baseRecord(isPort?(record.kind==='function'?'functionPort':'componentPort'):value('kind'),name,description);
    if(isPort)Object.assign(next,{ownerId:record.id,direction:value('direction')});
    if(apply(model=>({...model,elements:[...model.elements,next],
      diagrams:isPort?model.diagrams:model.diagrams.map(view=>view.id===diagram.id?
        {...view,elementIds:[...view.elementIds,next.id]}:view)}))){
      setSelected(next.id);setEditing(null);
    }
  }
  function shiftStep(delta){
    const next=step+delta;
    if(step<0||next<0||next>=count)return;
    if(updateView(view=>{
      // Earlier board edits may hide messages. Preserve their locations in the saved view.
      const ids=[...view.exchangeIds];
      const offsets=exchangeOffsets(view,diagram);
      const a=offsets[step],b=offsets[next];
      [ids[a],ids[b]]=[ids[b],ids[a]];
      return {...view,exchangeIds:ids};
    }))setStep(next);
  }
  function exchangeOffsets(saved,visible){
    let current=0;
    return saved.exchangeIds.flatMap((id,i)=>id===visible.exchangeIds[current]?(current++,[i]):[]);
  }
  const available=diagram?model.elements.filter(element=>diagramElements[diagram.kind].includes(element.kind)&&!diagram.elementIds.includes(element.id)):[];
  const ports=diagram?model.elements.filter(element=>diagram.elementIds.includes(element.ownerId)):[];
  const availableExchanges=diagram?model.exchanges.filter(exchange=>
    exchange.kind===(diagram.kind==='functions'?'functional':'component')&&
    index.participants(exchange).every(id=>diagram.elementIds.includes(id))&&
    (diagram.kind==='sequence'||!diagram.exchangeIds.includes(exchange.id))):[];
  const portOptions=direction=>ports.filter(port=>port.direction===direction||port.direction==='inout');

  return <section className="system-model-workspace" aria-labelledby="system-model-heading">
    <header className="system-model-header">
      <div className="system-model-heading"><button className="icon" aria-label="Back to Board" onClick={onBack}><ArrowLeft size={19}/></button>
        <div><h2 id="system-model-heading">System diagrams</h2><span>{project.name}</span></div></div>
      <div className="row">{renderComments&&<button className="btn" onClick={onSaveProject}>Save</button>}{onSave&&<>
        <button className="btn" disabled={!canUndo} onClick={()=>{onUndo();setEditing(null);setError('');}}>Undo</button>
        <button className="btn" disabled={!canRedo} onClick={()=>{onRedo();setEditing(null);setError('');}}>Redo</button>
        <button className="btn primary" onClick={()=>edit('new-view')}><Plus size={16}/> New diagram</button>
      </>}</div>
    </header>
    <div className="system-model-layout">
      <nav aria-label="System diagram views" className="system-model-views">
        {Object.entries(systemDiagramKinds).map(([kind,label])=><section key={kind}><h3>{label}</h3>
          {model.diagrams.filter(row=>row.kind===kind).map(row=><button key={row.id} type="button"
            aria-current={row.id===diagram?.id?'true':undefined} onClick={()=>openView(row.id)}>{row.name}</button>)}
        </section>)}
      </nav>
      <div className="system-model-main">
        {diagram?<><div className="system-model-caption"><div><strong>{diagram.name}</strong><span>{systemDiagramKinds[diagram.kind]}</span></div>
          <div className="row system-model-zoom">
            <button type="button" className="icon" aria-label="Zoom out" onClick={()=>zoomBy(-.25)}><ZoomOut size={16}/></button>
            <button type="button" className="btn" onClick={()=>{setZoom(1);setFit(!fit);}}>{fit?'Actual size':'Fit width'}</button>
            <button type="button" className="icon" aria-label="Zoom in" onClick={()=>zoomBy(.25)}><ZoomIn size={16}/></button>
            {!fit&&<span>{Math.round(zoom*100)}%</span>}
          </div>
        </div>
        {onSave&&<div className="system-model-tools" aria-label="Diagram tools">
          <button className="btn" onClick={()=>edit('element')}>Add element</button>
          <button className="btn" disabled={!available.length} onClick={()=>edit('reuse')}>Place existing</button>
          <button className="btn" disabled={!portOptions('out').some(a=>portOptions('in').some(b=>a.ownerId!==b.ownerId))} onClick={()=>edit('exchange')}>Connect ports</button>
          {diagram.kind!=='sequence'&&<button className="btn" disabled={!availableExchanges.length} onClick={()=>edit('message')}>Place existing exchange</button>}
          {diagram.kind==='sequence'&&diagram.elementIds.includes(selected)&&[-1,1].map(delta=>{
            const position=diagram.elementIds.indexOf(selected),target=position+delta;
            return <button className="btn" key={delta} disabled={target<0||target>=diagram.elementIds.length} onClick={()=>{
              updateView(view=>{
                const ids=[...view.elementIds];
                const from=ids.indexOf(selected),to=ids.indexOf(diagram.elementIds[target]);
                [ids[from],ids[to]]=[ids[to],ids[from]];
                return {...view,elementIds:ids};
              });
            }}>Move lifeline {delta===-1?'left':'right'}</button>;
          })}
          <button className="btn" onClick={()=>edit('rename-view')}>Rename diagram</button>
          {diagram.positions&&<button className="btn" onClick={()=>updateView(({positions,...view})=>view)}>Reset layout</button>}
          <button className="btn" onClick={()=>edit('delete-view')}>Delete diagram</button>
        </div>}
        {diagram.kind==='sequence'&&<div className="system-model-tools" aria-label="Sequence controls">
          <button className="btn" disabled={!count} onClick={()=>{if(!playing&&(step<0||step>=count-1))setStep(0);setPlaying(!playing);}}>
            {playing?<Pause size={14}/>:<Play size={14}/>} {playing?'Pause':'Play sequence'}</button>
          <button className="btn" disabled={!count||step>=count-1} onClick={()=>{setPlaying(false);setStep(step+1);}}><SkipForward size={14}/> Next step</button>
          <span role="status">{step>=0&&step<count?`${step+1} of ${count} · ${index.exchanges.get(diagram.exchangeIds[step]).name}`:`${count} steps`}</span>
          {onSave&&<>
            <button className="btn" disabled={!availableExchanges.length} onClick={()=>edit('message')}>Add existing message</button>
            <button className="btn" disabled={step<=0||step>=count} onClick={()=>shiftStep(-1)}>Move earlier</button>
            <button className="btn" disabled={step<0||step>=count-1} onClick={()=>shiftStep(1)}>Move later</button>
            <button className="btn" disabled={step<0||step>=count} onClick={()=>{
              if(updateView(view=>({...view,exchangeIds:view.exchangeIds.filter((_,i)=>i!==exchangeOffsets(view,diagram)[step])})))setStep(-1);
            }}>Remove step</button>
          </>}
        </div>}
        <div className="system-model-drawing" data-fit={fit} tabIndex={0} aria-label="Scrollable diagram">
          {!diagram.elementIds.length?<p className="system-model-empty">Add or place an element to start this diagram.</p>:diagram.kind==='sequence'?
            <SequenceView {...{diagram,index,selected,marker,step,zoom}} onStep={i=>{setPlaying(false);setStep(i);}} select={selectRecord}/>:
            <GraphView {...{diagram,index,selected,marker,zoom}} select={selectRecord}
              onMove={onSave? (id,point)=>updateView(view=>({...view,positions:{...view.positions,[id]:point}})):undefined}/>}
        </div></>:<div className="system-model-empty">
          <p>Create a diagram or generate one from a specification.</p>
          {onGenerate&&<button className="btn" onClick={onGenerate}>Generate from specification</button>}
        </div>}
      </div>
      <aside ref={inspector} className="system-model-inspector" aria-label="System model properties">
        {error&&<p role="alert">{error}</p>}
        {!editing&&diagram&&renderComments?.({kind:'diagram',id:diagram.id},'Diagram comments')}
        {!editing&&record&&renderComments?.({kind:index.exchanges.has(record.id)?'exchange':'element',id:record.id},index.exchanges.has(record.id)?'Exchange comments':'Element comments')}
        {!editing&&step>=0&&step<count&&renderComments?.({kind:'step',id:diagram.id,
          index:exchangeOffsets(savedModel.diagrams.find(row=>row.id===diagram.id),diagram)[step],
          exchangeId:diagram.exchangeIds[step]},'Step comments')}
        {editing==='delete-view'||editing==='delete-record'?<div className="system-model-form">
          <p>{editing==='delete-view'?'Delete this diagram? Its shared elements remain available.':'Delete this element from every view and remove its incident exchanges?'}</p>
          <button className="btn danger" onClick={()=>{
            const done=editing==='delete-view'?apply(model=>({...model,diagrams:model.diagrams.filter(view=>view.id!==diagram.id)})):
              apply(model=>removeModelRecord(model,record.id));
            if(done)openView(editing==='delete-view'?null:diagram.id);
          }}>Confirm delete</button>
          <button className="btn" onClick={()=>setEditing(null)}>Cancel</button>
        </div>:editing?<ModelForm {...{editing,diagram,record,index,project,available,availableExchanges,portOptions,submit}} onCancel={()=>edit(null)}/>:
          record?<><Inspector {...{record,index,project,onOpenBlock}} select={selectRecord}/>
          {onSave&&<div className="system-model-tools">
            <button className="btn" onClick={()=>edit('edit')}>Edit properties</button>
            {['actor','function','component'].includes(record.kind)&&<button className="btn" onClick={()=>edit('port')}>Add port</button>}
            {containing.some(view=>view.id===diagram?.id)&&diagram&&(diagram.elementIds.includes(record.id)||diagram.kind!=='sequence')&&
              <button className="btn" onClick={()=>{if(apply(model=>removeModelRecord(model,record.id,diagram.id)))setSelected(null);}}>Remove from diagram</button>}
            <button className="btn danger" onClick={()=>edit('delete-record')}>Delete from model</button>
          </div>}
          {!!containing.length&&<><h4>Appears in</h4><ul>{containing.map(row=><li key={row.id}>
            <button type="button" className="link" onClick={()=>{setView(row.id);setStep(-1);setPlaying(false);}}>{row.name}</button>
          </li>)}</ul></>}</>:<p>Select an element or exchange to inspect it.</p>}
      </aside>
    </div>
  </section>;
}

function ModelForm({editing,diagram,record,index,project,available,availableExchanges,portOptions,submit,onCancel}){
  const elements=[...index.elements.values()];
  const titles={'new-view':'New diagram','rename-view':'Rename diagram',reuse:'Place existing element',message:diagram?.kind==='sequence'?'Add existing message':'Place existing exchange',
    edit:'Edit properties',exchange:'Connect ports',port:'Add port',element:'Add element'};
  const select=(label,name,options,current='',optional=false)=><label>{label}<select name={name} aria-label={label} defaultValue={current} required={!optional}>
    <option value="">{optional?'None':'Select…'}</option>{options.map(({id,name})=><option key={id} value={id}>{name}</option>)}
  </select></label>;
  const options=values=>values.map(id=>({id,name:labels[id]||id}));
  const kinds=Object.entries(systemDiagramKinds).map(([id,name])=>({id,name}));
  const chosen=editing==='edit'?record:null;
  const hasItems=editing==='exchange'||(chosen&&index.exchanges.has(chosen.id));
  const exchangePorts=direction=>{
    const source=chosen?.source&&index.elements.get(chosen.source);
    const ports=chosen?elements.filter(port=>port.kind===source?.kind&&(port.direction===direction||port.direction==='inout')):portOptions(direction);
    return ports.map(port=>({...port,name:`${index.elements.get(port.ownerId).name} / ${port.name}`}));
  };
  const requirementIds=new Map((project.needs||[]).map(row=>[row.id,row.statement]));
  for(const id of chosen?.requirementIds||[])if(!requirementIds.has(id))requirementIds.set(id,id);
  const textFields=['new-view','rename-view','element','port','exchange','edit'].includes(editing);
  return <form key={editing+(chosen?.id||'')} className="system-model-form" onSubmit={submit}>
    <h3>{titles[editing]}</h3>
    {textFields&&<label>Name<input name="name" maxLength={150} defaultValue={chosen?.name||(editing==='rename-view'?diagram.name:'')} required autoFocus/></label>}
    {textFields&&!['new-view','rename-view'].includes(editing)&&<label>Description<textarea name="description" rows={4} maxLength={2000} defaultValue={chosen?.description} required/></label>}
    {editing==='new-view'&&select('View type','kind',kinds)}
    {editing==='element'&&select('Element type','kind',options(diagramElements[diagram.kind]),diagramElements[diagram.kind][0])}
    {editing==='reuse'&&select('Element','element',available)}
    {editing==='message'&&select('Exchange','exchange',availableExchanges)}
    {(editing==='port'||chosen?.direction)&&select('Direction','direction',options(['in','out','inout']),chosen?.direction||'inout')}
    {chosen&&['component','function'].includes(chosen.kind)&&select('Parent','parentId',elements.filter(row=>row.id!==chosen.id&&row.kind===chosen.kind),chosen.parentId,true)}
    {chosen?.kind==='component'&&index.elements.has(chosen.id)&&select('Board block','blockId',project.nodes.filter(n=>n.data.kind!=='note').map(n=>({id:n.id,name:n.data.label})),chosen.blockId,true)}
    {chosen?.kind==='function'&&select('Allocated to','allocatedTo',elements.filter(row=>['component','actor'].includes(row.kind)),chosen.allocatedTo,true)}
    {hasItems&&<>
      {select('Source port','source',exchangePorts('out'),chosen?.source)}
      {select('Target port','target',exchangePorts('in'),chosen?.target)}
    </>}
    {chosen&&requirementIds.size>0&&<label>Requirements<select name="requirements" multiple defaultValue={chosen.requirementIds}>
      {[...requirementIds].map(([id,name])=><option key={id} value={id}>{name}</option>)}
    </select></label>}
    {chosen&&index.exchanges.has(chosen.id)&&chosen.kind==='component'&&select('Board interface','interfaceId',project.edges.filter(edge=>{
      const [a,b]=index.participants(chosen).map(id=>index.elements.get(id).blockId);
      return a===edge.source&&b===edge.target;
    }).map(edge=>({id:edge.id,name:edge.label||edge.id})),chosen.interfaceId,true)}
    {chosen?.kind==='functional'&&index.exchanges.has(chosen.id)&&select('Carrying exchange','componentExchangeId',[...index.exchanges.values()].filter(exchange=>{
      if(exchange.kind!=='component')return false;
      const [a,b]=index.participants(chosen).map(id=>index.elements.get(id).allocatedTo);
      return index.participants(exchange).every((id,i)=>id===[a,b][i]);
    }),chosen.componentExchangeId,true)}
    {hasItems&&<label>Exchange items, one per line<textarea name="items" rows={3} defaultValue={chosen?.items?.join('\n')} required/></label>}
    <div className="row"><button className="btn primary" type="submit">Apply</button><button type="button" className="btn" onClick={onCancel}>Cancel</button></div>
  </form>;
}
