import {usePendingWork} from './PendingFeedback.jsx';
import {withPendingWork} from './pending-work.mjs';
import {drawingInterior,interiorInsertGeometry} from './drawing-parents.mjs';
import {applyDrawingLayout} from './drawing-layout.mjs';
import {buildReviewFiles} from './build-review-files.mjs';
import {createPortal} from 'react-dom';
import React, {useEffect,useMemo,useRef,useState} from 'react';
import {ArrowLeft,ArrowRight,AlertCircle,Check,ChevronDown,Code2,Download,FileText,GitFork,Layers3,Maximize,Network,PanelRight,Plus,Redo2,Search,Sparkles,Undo2,X,ZoomIn,ZoomOut} from 'lucide-react';
import {DiagramPages,projectPages} from './DiagramPages.jsx';
import {DrawioCanvas} from './DrawioCanvas.jsx';
import {DrawioShapePalette} from './DrawioShapePalette.jsx';
import {DiagramMermaid} from './DiagramMermaid.jsx';
import {architectureGraph} from './architecture-diagram-geometry.mjs';
import {drawioFile,drawioShapes,graphMermaid} from './drawio-model.mjs';
import {drawioHandoffFiles} from './drawio-handoff.mjs';
import {applyMermaidPage,parseMermaidPage} from './mermaid-page.mjs';
import {diagramFromSelection,appendDiagramProposal,detailValue,diagramCatalogue,diagramGroups,diagramId,diagramProjection,diagramTypes,
  elementFields,emptyDiagramModel,kindLabel,relationFields} from './architecture-diagrams.mjs';
import {readAttachments} from './chat-attachments.mjs';
import {architectureDiagramHandoffFiles} from './architecture-diagram-handoff.mjs';
import {toProjectFile} from './project-file.mjs';
import './architecture-diagrams.css';

function download(name,blob){
  const url=URL.createObjectURL(blob);
  const link=document.createElement('a');
  link.href=url;link.download=name;link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}

function Modal({title,onClose,children,error}){
  const dialog=useRef(null);
  useEffect(()=>{dialog.current.showModal();},[]);
  return <dialog ref={dialog} aria-label={title} className="architecture-dialog" onCancel={event=>{event.preventDefault();onClose();}}>
    <header><h3>{title}</h3><button type="button" className="icon" aria-label="Close" onClick={onClose}><X size={18}/></button></header>
    {error&&<p role="alert" className="architecture-error">{error}</p>}
    {children}
  </dialog>;
}

export function DiagramPicker({model,onClose,onCreate,error,inline=false}){
  const [query,setQuery]=useState('');
  const [kind,setKind]=useState('context');
  const [name,setName]=useState('');
  const [starting,setStarting]=useState('blank');
  const [scope,setScope]=useState('');
  const type=diagramTypes.get(kind);
  const existing=model.elements.filter(row=>type.elements.includes(row.kind));
  const filter=query.trim().toLowerCase();
  const form=<form onSubmit={event=>{event.preventDefault();onCreate(kind,name.trim()||type.title,starting,scope);}}>
      <label className="architecture-search"><Search size={16}/><input autoFocus placeholder="Search all 28 types" aria-label="Search diagram types" value={query} onChange={event=>setQuery(event.target.value)}/></label>
      <div className="architecture-picker">
        {diagramGroups.map(group=>{
          const rows=diagramCatalogue.filter(row=>row.group===group&&[row.title,row.question,group].some(text=>text.toLowerCase().includes(filter)));
          if(!rows.length)return null;
          return <section key={group}><h4>{group}</h4><div className="architecture-type-options">
            {rows.map(row=><button type="button" key={row.id} className="architecture-type" aria-pressed={row.id===kind}
              onClick={()=>{setKind(row.id);setStarting('blank');setScope('');}}><span>{row.title}</span><small>{row.question}</small></button>)}
          </div></section>;
        })}
        {!diagramCatalogue.some(row=>[row.title,row.question,row.group].some(text=>text.toLowerCase().includes(filter)))&&<p>No matching diagram types.</p>}
      </div>
      <div className="architecture-form-grid">
        <label>Name<input maxLength={180} placeholder={type.title} value={name} onChange={event=>setName(event.target.value)}/></label>
        <label>Start with<select aria-label="Start with" value={starting} onChange={event=>setStarting(event.target.value)}>
          <option value="blank">Blank canvas</option>
          <option value="example">Editable example</option>
          {!!existing.length&&<option value="model">Matching project records</option>}
        </select></label>
      </div>
      {starting==='model'&&<label>Scope<select aria-label="Scope" value={scope} onChange={event=>setScope(event.target.value)}>
        <option value="">All matching records</option>
        {existing.map(row=><option key={row.id} value={row.id}>{row.name}</option>)}
      </select></label>}
      <footer><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn primary"><Plus size={16}/> Create diagram</button></footer>
    </form>;
  return inline?<section className="studio-diagram-picker" aria-label="New diagram">{error&&<p role="alert">{error}</p>}{form}</section>:
    <Modal title="New diagram" onClose={onClose} error={error}>{form}</Modal>;
}

function SpecDialog({project,connected,onConnect,onDraft,onClose,initial}){
  const [text,setText]=useState(initial?.specification||'');
  const [useProject,setUseProject]=useState(initial?.useProject??Boolean(project.requirements||project.needs?.length||project.extensions?.designSources?.length||project.nodes.some(node=>node.data.kind!=='note')));
  const [files,setFiles]=useState(initial?.files||[]);
  const [reading,setReading]=useState(false);
  const [error,setError]=useState('');
  usePendingWork('Reading specifications…',reading);
  return <Modal title="Generate 28 diagrams" onClose={onClose}>
    <form onSubmit={event=>{event.preventDefault();onDraft({specification:text,useProject,files});}}>
      <p>AtMem drafts six groups using shared records and marks open design questions for review.</p>
      <label>Solution specification<textarea rows="6" maxLength={160000} placeholder="Paste the workflows, systems and constraints…" value={text} onChange={event=>setText(event.target.value)}/></label>
      <label className="architecture-upload"><FileText size={17}/><span>{files.length?files.map(row=>row.name).join(' · '):'Attach up to two specifications'}</span>
        <input type="file" accept=".pdf,.docx,.txt,.md,.csv,.json" multiple disabled={reading} onChange={async event=>{
          const added=[...event.target.files];if(!added.length)return;
          setError('');setReading(true);
          try{
            if(added.length>2)throw Error('Choose up to two specifications.');
            setFiles(await readAttachments(added));
          }catch(failure){setError(failure.message);}finally{setReading(false);}
        }}/>
      </label>
      {files.length>0&&<button type="button" className="btn architecture-clear-files" onClick={()=>setFiles([])}>Clear attachments</button>}
      <label className="architecture-checkbox"><input type="checkbox" checked={useProject} onChange={event=>setUseProject(event.target.checked)}/> Include current project requirements and design</label>
      {error&&<p role="alert" className="architecture-error">{error}</p>}
      <footer><button type="button" className="btn" onClick={onClose}>Cancel</button>{connected?
        <button className="btn primary" disabled={reading||(!text.trim()&&!files.length&&!useProject)}><Sparkles size={16}/> Generate set</button>:
        <button className="btn primary" type="button" onClick={()=>onConnect({specification:text,useProject,files})}>Connect a model <ArrowRight size={15}/></button>}</footer>
    </form>
  </Modal>;
}

function MermaidEditor({initial,editing,onClose,onApply}){
  const [source,setSource]=useState(initial);
  const [error,setError]=useState('');
  const [parsing,setParsing]=useState(false);
  usePendingWork('Parsing diagram…',parsing);
  return <Modal title={editing?'Edit Mermaid':'Insert Mermaid'} onClose={onClose} error={error}>
    <form onSubmit={async event=>{
      event.preventDefault();
      setParsing(true);setError('');
      try{await onApply(await parseMermaidPage(source));}
      catch(failure){setError(failure.message);}
      finally{setParsing(false);}
    }}>
      <label>Mermaid source<textarea className="mermaid-editor" rows={14} value={source} autoFocus spellCheck={false}
        onChange={event=>setSource(event.target.value)} placeholder={'flowchart LR\n  A[Request] --> B[Review]'}/></label>
      <footer><button className="btn" type="button" onClick={onClose}>Cancel</button>
        <button className="btn primary" disabled={!source.trim()||parsing}>{editing?'Apply changes':'Create page'}</button></footer>
    </form>
  </Modal>;
}

function RecordForm({action,record,view,projection,model,onSubmit,onClose,error,endpoints,preferredKind,preferredParent}){
  const type=projection.type;
  const relation=action==='connect'||model.relations.some(row=>row.id===record?.id);
  const [kind,setKind]=useState(record?.kind||(relation?type.relations[0]:preferredKind||type.elements[0]));
  const [from,setFrom]=useState(record?.from||endpoints?.source||projection.nodes[0]?.id||'');
  const [to,setTo]=useState(record?.to||endpoints?.target||projection.nodes[1]?.id||projection.nodes[0]?.id||'');
  const fields=[...new Set([...(record?.details.map(row=>row.name)||[]),...((relation?relationFields:elementFields)[kind]||[])])];
  const available=action==='reuse'?model.elements.filter(row=>type.elements.includes(row.kind)&&!view.elementIds.includes(row.id)):
    model.relations.filter(row=>type.relations.includes(row.kind)&&view.elementIds.includes(row.from)&&view.elementIds.includes(row.to)&&
      (type.layout==='timeline'||!view.relationIds.includes(row.id)));
  return <Modal title={{add:'Add element',connect:'Add relationship',edit:'Edit shared record',reuse:'Reuse an element','reuse-connection':'Reuse a relationship'}[action]} onClose={onClose} error={error}>
    <form onSubmit={event=>{
      event.preventDefault();
      const data=new FormData(event.currentTarget);
      if(data.has('reuse'))return onSubmit(data.get('reuse'));
      const value=name=>String(data.get(name)||'').trim();
      if(!value('name'))return;
      const next={id:record?.id||diagramId(),name:value('name'),kind,basis:record?.basis||'manual',source:value('source'),
        details:fields.flatMap((name,index)=>value('detail-'+index)?[{name,value:value('detail-'+index)}]:[])};
      if(next.basis==='specified'&&!next.source)next.basis='manual';
      if(relation)Object.assign(next,{from,to});
      else if(value('parent'))next.parentId=value('parent');
      onSubmit(next,relation);
    }}>
      {['reuse','reuse-connection'].includes(action)?<label>Shared record<select name="reuse" required defaultValue="">
        <option value="" disabled>Select a record</option>{available.map(row=><option key={row.id} value={row.id}>{row.name} · {kindLabel(row.kind)}</option>)}
      </select></label>:<>
        <div className="architecture-form-grid"><label>Name<input name="name" required maxLength={180} autoFocus defaultValue={record?.name}/></label>
          <label>Type<select aria-label="Type" value={kind} disabled={Boolean(record)} onChange={event=>setKind(event.target.value)}>
            {(relation?type.relations:type.elements).map(value=><option key={value} value={value}>{kindLabel(value)}</option>)}
          </select></label></div>
        {relation?<div className="architecture-form-grid">
          <label>From<select value={from} onChange={event=>setFrom(event.target.value)}>{projection.nodes.map(row=><option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
          <label>To<select value={to} onChange={event=>setTo(event.target.value)}>{projection.nodes.map(row=><option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
        </div>:<label>Nest under<select name="parent" defaultValue={preferredParent||record?.parentId||''}>
          <option value="">None</option>
          {model.elements.filter(row=>row.id!==record?.id&&(view.elementIds.includes(row.id)||row.id===record?.parentId)).map(row=><option key={row.id} value={row.id}>{row.name}</option>)}
        </select></label>}
        <label>Source reference<input name="source" maxLength={500} placeholder="Requirement ID or specification section" defaultValue={record?.source}/></label>
        {fields.length>0&&<details open={action==='edit'}><summary>Notation details</summary>
          <div className="architecture-field-details">{fields.map((field,index)=><label key={field}>{field}<textarea name={'detail-'+index} rows="2" maxLength={1600} defaultValue={record?detailValue(record,field):''}/></label>)}</div>
        </details>}
      </>}
      <footer><button className="btn" type="button" onClick={onClose}>Cancel</button><button className="btn primary">
        {action==='edit'?'Save changes':action==='connect'?'Connect':'Add to diagram'}</button></footer>
    </form>
  </Modal>;
}

function Inspector({projection,record,view,mermaid,editable,onEdit,onRemove,onShift,onResetPin,onComments,onRename,onClose,onAddInside}){
  return <aside className="architecture-inspector" aria-label="Diagram inspector">
    <header><h3>{record?'Record details':'Diagram details'}</h3><button className="icon" aria-label="Close inspector" onClick={onClose}><X size={15}/></button></header>
    {record?<><span className="architecture-tag">{kindLabel(record.kind)} · {kindLabel(record.basis)}</span>
      <h4>{record.name}</h4>
      {record.source&&<p>{record.source}</p>}
      {record.details.length>0&&<dl>{record.details.map(row=><React.Fragment key={row.name}><dt>{row.name}</dt><dd>{row.value}</dd></React.Fragment>)}</dl>}
      {editable&&<div className="architecture-inspector-actions">
        <button className="btn" onClick={onEdit}>Edit shared record</button>
        {onAddInside&&<button className="btn" onClick={onAddInside}><Plus size={15}/> Add inside</button>}
        {view.positions?.[record.id]&&<button className="btn" onClick={onResetPin}>Reset position</button>}
        {onShift&&<><button className="btn" onClick={()=>onShift(-1)}>Move earlier</button><button className="btn" onClick={()=>onShift(1)}>Move later</button></>}
        <button className="btn" onClick={onRemove}>Remove from view</button>
      </div>}
    </>:<><p>{projection.type.rule}</p>
      {editable&&<button className="btn" onClick={onRename}>Rename diagram</button>}
      {onComments?.({kind:'diagram',id:view.id},'Diagram comments')}
    </>}
    <DiagramMermaid code={mermaid}/>
    {projection.diagnostics.length>0&&<details open={!record}><summary>{projection.diagnostics.length} items to review</summary>
      <ul>{projection.diagnostics.map(issue=><li key={issue}>{issue}</li>)}</ul></details>}
  </aside>;
}

export function ArchitectureDiagramWorkspace({project,onLayoutPage,onGroupsPage,onBack,onSave,onSaveProject,onUndo,onRedo,canUndo,canRedo,
  onDraft,connected,onConnect,onLegacy,onComments,locked,onPage,librarySlot,onNewPage,initialPage=null,initiallyGenerating=false,initiallyCreating=false,initialMermaid=false}){
  const saved=project.extensions?.architectureDiagrams;
  const empty=useMemo(emptyDiagramModel,[]);
  const model=saved||empty;
  const [active,setActive]=useState(initialPage);
  const [interiorTrail,setInteriorTrail]=useState([]);const interiorScope=interiorTrail.at(-1)||null;
  const [selected,setSelected]=useState(null),[picked,setPicked]=useState([]);
  const [inspect,setInspect]=useState(false);
  const [dialog,setDialog]=useState(initiallyGenerating?'spec':initialMermaid?'mermaid-insert':initiallyCreating?'new':null);
  const [shapeDraft,setShapeDraft]=useState(null);
  const [parentDraft,setParentDraft]=useState(null);
  const [endpoints,setEndpoints]=useState(null);
  const [query,setQuery]=useState('');
  const [progress,setProgress]=useState(null);
  usePendingWork('Generating diagrams…',Boolean(progress));
  const [specInput,setSpecInput]=useState(null);
  const [proposal,setProposal]=useState(null);
  const [error,setError]=useState('');
  const abort=useRef(null), graphApi=useRef(null),checkpoint=useRef(null);
  useEffect(()=>()=>abort.current?.abort(),[]);
  const visible=proposal?.model||model;
  const view=visible.views.find(row=>row.id===active)||visible.views[0];
  const projection=useMemo(()=>view?diagramProjection(visible,view):null,[visible,view]);
  const scene=useMemo(()=>projection?architectureGraph(projection,view):null,[projection,view]);
  const fullScene=useMemo(()=>scene?applyDrawingLayout(scene,project.extensions?.drawingLayouts?.pages?.['view/'+view.id],project.extensions?.drawingLayouts?.groups?.['view/'+view.id],project.extensions?.drawingLayouts?.parents?.['view/'+view.id]):null,[scene,project.extensions?.drawingLayouts,view?.id]);
  const displayedScene=useMemo(()=>fullScene?drawingInterior(fullScene,interiorScope):null,[fullScene,interiorScope]);
  const timeline=projection?.type.layout==='timeline';
  const record=visible.elements.find(row=>row.id===selected)||visible.relations.find(row=>row.id===selected);
  const editable=Boolean(!locked&&!proposal&&!progress);
  const displayed=visible.views.filter(row=>row.name.toLowerCase().includes(query.toLowerCase())||diagramTypes.get(row.kind).title.toLowerCase().includes(query.toLowerCase()));
  const setView=id=>{setActive(id);setSelected(null);setPicked([]);setInteriorTrail([]);};
  const closeDialog=()=>{setParentDraft(null);setDialog(null);setShapeDraft(null);setEndpoints(null);setError('');};
  function addShape(tool,point){
    if(!editable||!view)return;
    const typed=tool.startsWith('element:');
    if(!typed&&!Object.hasOwn(drawioShapes,tool))return;
    const shape=typed?undefined:tool;
    const preferred=typed?tool.slice('element:'.length):{actor:'actor',cylinder:'store',rhombus:'decision',note:'rule',swimlane:'lane'}[shape];
    const kind=projection.type.elements.includes(preferred)?preferred:undefined;
    if(typed&&!kind)return;
    setShapeDraft({shape,kind,point});
    setDialog('add');
  }
  function moveCells(positions){
    const changes=Object.fromEntries(positions.map(({id,x,y})=>[id,{x:Math.max(0,Math.min(100000,x)),y:Math.max(0,Math.min(100000,y))}]));
    updateView(row=>({...row,positions:{...row.positions,...changes}}));
  }
  const select=id=>{setSelected(id);setInspect(true);};
  function commit(next){
    try{
      onSave(next,saved);
      setError('');
      return true;
    }catch(failure){setError(failure.message);return false;}
  }
  const updateView=(change,base=model)=>commit({...base,views:base.views.map(row=>row.id===view.id?change(row):row)});
  function create(kind,name,starting,scope){
    const result=diagramFromSelection(model,kind,name,starting,scope);
    if(commit(result.model)){setDialog(null);setQuery('');setView(result.view.id);}
  }
  async function generate(input){
    const controller=new AbortController();
    abort.current=controller;
    setSpecInput(input);checkpoint.current=input.resume||null;setDialog(null);setError('');setProgress({done:0,total:28,group:'Reading the specification'});
    try{
      const next=await onDraft(input,controller.signal,value=>{if(value.checkpoint)checkpoint.current=value.checkpoint;setProgress(value);});
      setProposal({model:next,base:saved,revision:project.revision,requirements:project.requirements,needs:project.needs,
        decisions:project.decisions,sources:project.extensions?.designSources});setQuery('');setView(next.views[0].id);
    }catch(failure){if(!controller.signal.aborted)setError(failure.message);if(checkpoint.current)setSpecInput({...input,resume:checkpoint.current});}
    finally{abort.current=null;setProgress(null);}
  }
  function applyProposal(){
    if(proposal.base!==saved||proposal.revision!==project.revision||proposal.requirements!==project.requirements||
      proposal.needs!==project.needs||proposal.decisions!==project.decisions||proposal.sources!==project.extensions?.designSources){
      setError('The project changed. Discard this preview and generate again.');
      return;
    }
    try{
      const next=appendDiagramProposal(model,proposal.model);
      if(commit(next)){setView(next.views[model.views.length].id);setProposal(null);}
    }catch(failure){setError(failure.message);}
  }
  function saveRecord(row,relation){
    const collection=relation?'relations':'elements';
    const existing=model[collection].some(value=>value.id===row.id);
    const next={...model,[collection]:existing?model[collection].map(value=>value.id===row.id?row:value):[...model[collection],row]};
    const key=relation?'relationIds':'elementIds';
    if(!relation)next.views=next.views.map(v=>v.id===view.id&&v.groups?{...v,groups:v.groups.filter(g=>g.elementId!==row.id)}:v);
    const done=existing?commit(next):updateView(value=>{
      const added={...value,[key]:[...value[key],row.id]};
      if(!relation&&shapeDraft){
        if(shapeDraft.shape)added.drawioShapes={...value.drawioShapes,[row.id]:shapeDraft.shape};
        if(shapeDraft.point&&!timeline)added.positions={...value.positions,[row.id]:{
          x:Math.max(0,Math.min(100000,Math.round(shapeDraft.point.x))),y:Math.max(0,Math.min(100000,Math.round(shapeDraft.point.y))),
        }};
      }
      return added;
    },next);
    if(done){if(!relation&&interiorScope)onLayoutPage?.('view/'+view.id,interiorInsertGeometry(fullScene,interiorScope,row.id,shapeDraft?.point,{width:280,height:100}),{parents:{[row.id]:interiorScope}});if(!relation&&(row.parentId||model.elements.find(e=>e.id===row.id)?.parentId))onLayoutPage?.('view/'+view.id,null);closeDialog();select(row.id);
      if(!relation&&row.parentId)requestAnimationFrame(()=>requestAnimationFrame(()=>graphApi.current?.fit({nodes:[{id:row.parentId}],minZoom:.1,maxZoom:1})));
    }
  }
  function removeRecord(){
    const ids=new Set(model.relations.filter(row=>row.from===selected||row.to===selected||row.id===selected).map(row=>row.id));
    if(updateView(value=>{
      const {positions={},groups,scopeId,drawioShapes:shapes,...rest}=value;
      return {...rest,...(scopeId&&scopeId!==selected?{scopeId}:{}),
        ...(groups?{groups:groups.filter(row=>row.elementId!==selected&&row.groupId!==selected)}:{}),
        ...(shapes?{drawioShapes:Object.fromEntries(Object.entries(shapes).filter(([key])=>key!==selected))}:{}),
        positions:Object.fromEntries(Object.entries(positions).filter(([key])=>key!==selected)),
        elementIds:value.elementIds.filter(id=>id!==selected),relationIds:value.relationIds.filter(id=>!ids.has(id))};
    }))setSelected(null);
  }
  async function exportViewWork(format){
    if(!scene)return;
    try{
      const name=view.name.replace(/[^a-z0-9]+/gi,'-').replace(/^-|-$/g,'').toLowerCase()||'diagram';
      if(format==='mmd'){
        const content=format==='drawio'?drawioFile([{id:view.id,name:view.name,...scene}]):graphMermaid(scene,{timeline});
        download(name+'.'+format,new Blob([content],{type:format==='drawio'?'application/xml':'text/plain'}));
        return;
      }
      const {renderDiagramSvg}=await import('./drawio-render.mjs');
      const drawing=await renderDiagramSvg(displayedScene,{name:view.name,revision:project.revision});
      if(format==='drawio'){download(name+'.drawio',new Blob([drawioFile([{id:view.id,name:view.name,...drawing.scene}])],{type:'application/xml'}));return;}
      if(format==='svg'){download(name+'.svg',new Blob([drawing.svg],{type:'image/svg+xml'}));return;}
      const {pngOf}=await import('./visual-export.mjs');
      const png=await pngOf(drawing);
      download(name+'.png',new Blob([png],{type:'image/png'}));
    }catch(failure){setError(failure.message);}
  }

  const exportView=(...args)=>withPendingWork('Exporting diagrams…',()=>exportViewWork(...args));
  async function exportSetWork(){
    try{
      const [{projectSceneFiles},{zipSync,strToU8}]=await Promise.all([
        import('./architecture-scene-export.jsx'),import('fflate'),
      ]);
      const files={
        ...architectureDiagramHandoffFiles(project.name,project.revision,model),
        ...buildReviewFiles(project,model),
        'project.atmem-ai-architect.json':JSON.stringify(toProjectFile(project),null,2),
        ...drawioHandoffFiles(project,model),
        ...await projectSceneFiles({...project,extensions:{...project.extensions,architectureDiagrams:model}}),
      };
      const archive=zipSync(Object.fromEntries(Object.entries(files).map(([name,content])=>[name,strToU8(content)])));
      const slug=project.name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')||'project';
      download(slug+'-architecture.zip',new Blob([archive],{type:'application/zip'}));
    }catch(failure){setError(failure.message);}
  }

  const newPage=onNewPage||(()=>setDialog('new'));  const exportSet=(...args)=>withPendingWork('Exporting diagrams…',()=>exportSetWork(...args));

  return <section className="architecture-workspace" aria-label="Architecture diagrams">
    <header className="architecture-header">
      <button className="icon" onClick={onBack} aria-label="Back to Board"><ArrowLeft size={21}/></button>
      <div className="architecture-title"><h2>Architecture diagrams</h2><span>{project.name}</span></div>
      <div className="architecture-header-actions">
        <button className="icon" title="Undo" aria-label="Undo" disabled={!canUndo||!editable} onClick={onUndo}><Undo2 size={17}/></button>
        <button className="icon" title="Redo" aria-label="Redo" disabled={!canRedo||!editable} onClick={onRedo}><Redo2 size={17}/></button>
        <button className="btn" onClick={onSaveProject}>Save project</button>
        {!!model.views.length&&!proposal&&<button className="btn" onClick={exportSet}><Download size={15}/> Download set</button>}
        <button className="btn" disabled={!editable} onClick={newPage}><Plus size={16}/> New diagram</button>
        {!view&&<button className="btn" disabled={!editable} onClick={()=>setDialog('mermaid-insert')}><Code2 size={15}/> Insert Mermaid</button>}
        <button className="btn primary" disabled={!editable} onClick={()=>setDialog('spec')}><Sparkles size={16}/> Generate from spec</button>
      </div>
    </header>
    {progress&&<div className="architecture-progress" role="status"><Sparkles size={16}/><strong>{progress.group}</strong>
      <progress value={progress.done} max={28}/><span>{progress.done} of 28</span><button className="btn" onClick={()=>abort.current?.abort()}>Stop</button></div>}
    {proposal&&<div className="architecture-progress"><Sparkles size={16}/><strong>Review AtMem’s 28 diagrams</strong>
      <span>{visible.views.filter(row=>row.elementIds.length>0).length} with content</span>
      <button className="btn" onClick={()=>{setProposal(null);setError('');}}>Discard draft</button>
      <button className="btn primary" onClick={applyProposal}><Check size={15}/> Add to project</button></div>}
    {specInput?.resume&&!progress&&<div className="architecture-progress"><strong>{specInput.resume.views.length} checked pages retained</strong><button className="btn" disabled={!editable} onClick={()=>{try{commit(appendDiagramProposal(model,specInput.resume,{complete:false}));}catch(error){setError(error.message);}}}>Save completed pages</button><button className="btn primary" onClick={()=>generate(specInput)}>Resume remaining diagrams</button></div>}
    {error&&!dialog&&<div className="architecture-error" role="alert">{error}<button className="icon" onClick={()=>setError('')} aria-label="Dismiss error"><X size={15}/></button></div>}
    <div className="architecture-body">
      <nav className="architecture-library" aria-label="Project diagrams">
        {editable&&view&&(librarySlot?createPortal(<DrawioShapePalette onAdd={addShape} elementKinds={projection.type.elements}/>,librarySlot):<DrawioShapePalette onAdd={addShape} elementKinds={projection.type.elements}/>)}
        <div className="architecture-library-title"><Layers3 size={16}/><strong>{proposal?'Draft diagrams':'Project diagrams'}</strong><span>{visible.views.length}</span></div>
        {!!visible.views.length&&<label className="architecture-search"><Search size={15}/><input placeholder="Find a diagram" aria-label="Find a diagram" value={query} onChange={event=>setQuery(event.target.value)}/></label>}
        {diagramGroups.map(group=>{
          const entries=displayed.filter(row=>diagramTypes.get(row.kind).group===group);
          if(!entries.length)return null;
          return <section key={group}><h3>{group}</h3>{entries.map(row=><button key={row.id} aria-current={row.id===view?.id?'page':undefined}
            onClick={()=>setView(row.id)}><GitFork size={14}/><span>{row.name}</span></button>)}</section>;
        })}
        {onLegacy&&<button className="architecture-legacy" onClick={onLegacy}><Layers3 size={15}/> System model views <ArrowRight size={14}/></button>}
      </nav>
      <main className="architecture-editor">
        {view?<><div className="architecture-viewbar">
          <div><nav className="drawing-breadcrumbs" aria-label="Drawing location"><button onClick={()=>setInteriorTrail([])}>{view.name}</button>{interiorTrail.map((id,i)=><React.Fragment key={id}><span>/</span><button onClick={()=>setInteriorTrail(t=>t.slice(0,i+1))}>{visible.elements.find(e=>e.id===id)?.name||'Group'}</button></React.Fragment>)}</nav><h3>{view.name}</h3><p>{projection.type.title} · {projection.nodes.length} elements</p></div>
          <div className="architecture-view-actions">
            {projection.diagnostics.length>0&&<button className="btn architecture-review-button" onClick={()=>{setSelected(null);setInspect(true);}}>
              <AlertCircle size={15}/> {projection.diagnostics.length} to review
            </button>}
            {editable&&<><button className="btn" onClick={()=>{setShapeDraft(null);setDialog('add');}}><Plus size={15}/> Add element</button>
              <div className="diagram-mermaid-actions" role="group" aria-label="Mermaid tools">
                <button className="btn" onClick={()=>setDialog('mermaid-insert')}><Code2 size={15}/> Insert Mermaid</button>
                <button className="btn" onClick={()=>setDialog('mermaid-edit')} disabled={!projection.nodes.length}>Edit Mermaid</button>
              </div>
              {projection.nodes.length>0&&<button className="btn" onClick={()=>{setEndpoints(null);setDialog('connect');}}>Connect</button>}
              <details className="architecture-menu"><summary className="btn">Reuse <ChevronDown size={13}/></summary><div>
                <button disabled={!model.elements.some(row=>projection.type.elements.includes(row.kind)&&!view.elementIds.includes(row.id))} onClick={()=>setDialog('reuse')}>Shared element</button>
                <button disabled={!model.relations.some(row=>projection.type.relations.includes(row.kind)&&view.elementIds.includes(row.from)&&view.elementIds.includes(row.to)&&
                  (projection.type.layout==='timeline'||!view.relationIds.includes(row.id)))} onClick={()=>setDialog('reuse-connection')}>Shared relationship</button>
              </div></details></>}
            {!!projection.nodes.length&&<details className="architecture-menu"><summary className="btn"><Download size={15}/> Export</summary><div>
              <button onClick={()=>exportView('drawio')}>Download editable diagram</button><button onClick={()=>exportView('mmd')}>Download Mermaid</button><button onClick={()=>exportView('svg')}>Download SVG</button><button onClick={()=>exportView('png')}>Download PNG</button>
            </div></details>}

          </div>
        </div>
        <div className="architecture-drawing drawio-diagram-page">
          <DrawioCanvas properties={view&&<Inspector projection={projection} record={record} view={view} mermaid={graphMermaid(scene,{selected:selected||undefined,timeline})} editable={editable}
        onAddInside={editable&&!timeline&&projection.type.layout!=='stages'&&projection.nodes.some(n=>n.id===record?.id)?()=>{setShapeDraft(null);setParentDraft(record.id);setDialog('add');}:null}
        onEdit={()=>setDialog('edit')} onRemove={removeRecord} onClose={()=>setInspect(false)}
        onRename={()=>setDialog('rename')} onComments={proposal?null:onComments}
        onResetPin={()=>updateView(row=>({...row,positions:Object.fromEntries(Object.entries(row.positions).filter(([key])=>key!==selected))}))}
        onShift={projection.type.layout==='timeline'&&view.relationIds.includes(selected)?delta=>updateView(row=>{
          const relationIds=[...row.relationIds],index=relationIds.indexOf(selected),target=index+delta;
          if(target>=0&&target<relationIds.length)[relationIds[index],relationIds[target]]=[relationIds[target],relationIds[index]];
          return {...row,relationIds};
        }):null}/>} scopeId={interiorScope} onOpenInside={!timeline?id=>{graphApi.current?.fit({nodes:[{id}],minZoom:.2,maxZoom:1});setInteriorTrail(trail=>[...trail,id]);setSelected(null);setPicked([]);setInspect(false);requestAnimationFrame(()=>graphApi.current?.fit({minZoom:.2}));}:null} key={view.id} graphRef={graphApi} scene={displayedScene} label={view.name} onLayout={editable?(changes,options)=>onLayoutPage?.('view/'+view.id,changes,options):null}
            groups={project.extensions?.drawingLayouts?.groups?.['view/'+view.id]||[]} onGroupsChange={editable&&onGroupsPage?(groups,options)=>onGroupsPage('view/'+view.id,groups,options):null}
            selected={picked.length?picked:selected} onSelectMany={ids=>{setPicked(ids);setSelected(ids[0]||null);}} onSelect={(id,event)=>{if(event?.shiftKey||event?.metaKey||event?.ctrlKey)setPicked(current=>{const ids=new Set(current.length?current:selected?[selected]:[]);if(ids.has(id))ids.delete(id);else if(id)ids.add(id);return[...ids];});else setPicked([]);if(id)select(id);else setSelected(null);}}
            onEditRecord={editable?id=>{select(id);setDialog('edit');}:null}
            onDoubleClick={editable?id=>{select(id);setDialog('edit');}:null}
            onMove={editable&&!timeline?moveCells:null}
            onConnect={editable&&!timeline?(source,target)=>{setEndpoints({source,target});setDialog('connect');}:null}
            onDropShape={editable?addShape:null}/>
          {!projection.nodes.length&&<div className="architecture-blank drawio-empty">
            <span className="architecture-empty-icon"><Network size={25}/></span>
            <h3>{proposal?'Source details needed':'Start with an element'}</h3><p>{projection.type.question}</p>
            {editable&&<button className="btn primary" onClick={()=>setDialog('add')}><Plus size={16}/> Add element</button>}
            {projection.diagnostics.length>0&&<button className="btn" onClick={()=>setInspect(true)}>Review open items</button>}
          </div>}

        </div>
        <DiagramPages pages={projectPages(visible.views,project.extensions?.systemModel?.diagrams,project.extensions?.engineeringModel?.diagrams)} active={'view/'+view.id}
          onSelect={key=>key.startsWith('view/')?setView(key.slice(5)):key==='board'?onBack():onPage(key)}
          onAdd={editable?newPage:null}/></>:<div className="architecture-drawing architecture-start">
          <div className="architecture-blank"><span className="architecture-empty-icon"><Network size={30}/></span>
            <h3>Start your architecture</h3>
            <p>Create one diagram by hand, or give AtMem a specification to draft all 28.</p>
            <div><button className="btn primary" disabled={!editable} onClick={()=>setDialog('spec')}><Sparkles size={16}/> Generate from spec</button>
              <button className="btn" disabled={!editable} onClick={newPage}><Plus size={16}/> Browse diagram types</button></div>
          </div>
        </div>}
      </main>

    </div>
    {['mermaid-insert','mermaid-edit'].includes(dialog)&&<MermaidEditor editing={dialog==='mermaid-edit'} onClose={closeDialog}
      initial={dialog==='mermaid-edit'?graphMermaid(scene,{timeline}):''} onApply={parsed=>{
        const result=applyMermaidPage(model,parsed,dialog==='mermaid-edit'?{view,scene}:{});
        if(!commit(result.model))throw Error('The project changed. Try again from the current page.');
        closeDialog();setView(result.view.id);
      }}/>}
    {dialog==='new'&&<DiagramPicker model={model} error={error} onClose={closeDialog} onCreate={create}/>}
    {dialog==='spec'&&<SpecDialog project={project} connected={connected} initial={specInput}
      onConnect={input=>{setSpecInput(input);checkpoint.current=input.resume||null;setDialog(null);onConnect();}} onClose={closeDialog} onDraft={generate}/>}
    {dialog==='rename'&&<Modal title="Rename diagram" onClose={closeDialog} error={error}><form onSubmit={event=>{
      event.preventDefault();const name=String(new FormData(event.currentTarget).get('name')).trim();
      if(name&&updateView(row=>({...row,name})))setDialog(null);
    }}><label>Name<input name="name" defaultValue={view.name} autoFocus maxLength={180} required/></label>
      <footer><button className="btn primary">Save name</button></footer></form></Modal>}
    {['add','connect','edit','reuse','reuse-connection'].includes(dialog)&&<RecordForm action={dialog} record={dialog==='edit'?record:null}
      model={model} view={view} projection={projection} error={error} onClose={closeDialog} endpoints={endpoints} preferredKind={shapeDraft?.kind||(parentDraft?model.elements.find(e=>e.id===parentDraft)?.kind:undefined)} preferredParent={dialog==='edit'&&record?projection.parentOf(record):parentDraft}
      onSubmit={(row,relation)=>{
        if(typeof row!=='string')return saveRecord(row,relation);
        const key=dialog==='reuse'?'elementIds':'relationIds';
        if(updateView(value=>({...value,[key]:[...value[key],row]}))){setDialog(null);select(row);}
      }}/>}
  </section>;
}
