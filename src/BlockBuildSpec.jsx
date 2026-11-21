import {EngineeringModelView} from './EngineeringModelView.jsx';
import {architectureConsistency} from './architecture-consistency.mjs';
import React, {lazy, Suspense, useEffect, useMemo, useState} from 'react';
import { artifactWorkProjection } from './artifact-work.mjs';
import { ArtifactChecks } from './ArtifactChecks.jsx';
import { engineeringCall } from './engineering-client.mjs';
import { blockChildren, blockSpecSections, interfaceFields } from './block-spec.mjs';
import {BlockAgentHandoff} from './BlockAgentHandoff.jsx';

const DiagramPreview=lazy(()=>import('./DiagramPreview.jsx'));

export function NestedBlocks({ nodes, parent = null, selected, onOpen }) {
  return <ul className="nested-blocks">
    {blockChildren(nodes, parent).map(node => <li key={node.id}>
      <button aria-current={selected === node.id ? 'true' : undefined} onClick={() => onOpen(node.id)}>{node.data.label}</button>
      {nodes.some(child => child.data.parentBlockId === node.id) &&
        <NestedBlocks nodes={nodes} parent={node.id} selected={selected} onOpen={onOpen}/>}
    </li>)}
  </ul>;
}

export function BlockHierarchy({ nodes, node, busy, onOpen, onReparent }) {
  const parents = new Map(nodes.map(block => [block.id, block]));
  const ancestors = [];
  for (let current = parents.get(node.data.parentBlockId); current; current = parents.get(current.data.parentBlockId)) {
    if (ancestors.some(block => block.id === current.id)) break;
    ancestors.unshift(current);
  }

  function canParent(block) {
    const seen = new Set([node.id]);
    for (let current = block; current; current = parents.get(current.data.parentBlockId)) {
      if (current.data.kind === 'note' || seen.has(current.id)) return false;
      seen.add(current.id);
    }
    return true;
  }

  return <header className="module-overview">
    <nav className="module-breadcrumb" aria-label="Block hierarchy">
      <span>System</span>
      {ancestors.map(block => <React.Fragment key={block.id}>
        <span aria-hidden="true">/</span><button type="button" onClick={() => onOpen(block.id)}>{block.data.label}</button>
      </React.Fragment>)}
      <span aria-hidden="true">/</span><strong aria-current="page">{node.data.label}</strong>
    </nav>
    <div className="module-overview-body">
      <h3>{node.data.label}</h3>
      <label className="module-parent-picker">Nest under
        <select value={node.data.parentBlockId || ''} disabled={busy} onChange={event => onReparent(event.target.value || undefined)}>
          <option value="">System level</option>
          {nodes.filter(canParent).map(block => <option key={block.id} value={block.id}>{block.data.label}</option>)}
        </select>
      </label>
    </div>
  </header>;
}

export function BlockBuildSpec({ project, node, busy, onOpen, onDraft, onInterface, onSaveInterface, onSaveSpec, onPrepareSources, renderComments, session }) {
  const [tab, setTab] = useState('specification');
  const [editingInterface, setEditingInterface] = useState(null);
  const [editingSpec, setEditingSpec] = useState(false);
  const [focusedOperation,setFocusedOperation]=useState(null);
  const operationNames=useMemo(()=>new Map((project.extensions?.engineeringModel?.elements||[]).flatMap(e=>(e.operations||[]).map(op=>[op.id,op.name]))),[project.extensions?.engineeringModel]);
  const consistency=useMemo(()=>architectureConsistency(project),[project]);
  const scope=new Set([node.id]);let expanded=true;
  while(expanded){expanded=false;for(const block of project.nodes)if(scope.has(block.data.parentBlockId)&&!scope.has(block.id)){scope.add(block.id);expanded=true;}}
  const issues=consistency.issues.filter(issue=>scope.has(issue.blockId)||issue.participantBlockIds?.some(id=>scope.has(id))||issue.requirementId&&project.needs?.some(row=>row.id===issue.requirementId&&row.links?.some(id=>scope.has(id))));
  const parents = new Map(project.nodes.map(block => [block.id, block]));
  const children = blockChildren(project.nodes, node.id);
  const edges = project.edges.filter(edge => edge.source === node.id || edge.target === node.id);
  const sections = blockSpecSections(node.data.buildSpec);
  return <div className="block-spec-content">
      <div className="block-spec-toolbar">
        <div className="module-facts" aria-label="Block contents">
          <span>{children.length} submodules</span><span>{edges.length} connections</span>
          <span>{node.data.buildSpec?.scenarios?.length || 0} {node.data.buildSpec?.scenarios?.length === 1 ? 'scenario' : 'scenarios'}</span>
          <span>{sections.filter(section=>section.content).length}/{sections.length} spec sections documented</span>
        </div>
        {renderComments?.({kind:'block',id:node.id},'Block comments')}
        <button className="btn" onClick={()=>setTab('handoff')}>Prepare agent handoff</button>
      </div>
      <nav className="block-spec-tabs" aria-label="Module details">
        {['specification','interfaces','model','diagrams','tests','handoff'].map(id=><button key={id} aria-pressed={tab===id} onClick={()=>setTab(id)}>{({specification:'Specification',interfaces:'Interfaces',model:'Design model',diagrams:'Diagrams',tests:'Test cases',handoff:'Agent handoff'})[id]}</button>)}
      </nav>
      <section hidden={tab!=='specification'} aria-label="Module specification">
      <div className="module-section-heading"><h4>Block specification</h4>
        <div className="row">
          <button className="btn" disabled={busy || editingSpec} onClick={()=>setEditingSpec(true)}>Edit specification</button>
          {onDraft && <button className="btn" disabled={busy || editingSpec} onClick={onDraft}>Ask AI to draft</button>}
        </div>
      </div>
      {editingSpec ? <SpecEditor node={node} busy={busy} onSave={onSaveSpec} onClose={()=>setEditingSpec(false)}/> :
        <BlockSpecProperties key={node.id} node={node} busy={busy} onSave={onSaveSpec} renderComments={renderComments}/>}
      {!!children.length && <section className="module-children" aria-label="Nested modules"><h4>Submodules</h4><NestedBlocks nodes={project.nodes} parent={node.id} onOpen={onOpen}/></section>}
      </section>
      <section hidden={tab!=='interfaces'} aria-label="Module interfaces">
      <div className="module-section-heading">
        <h4>Interfaces</h4>
        <button className="btn" type="button" disabled={busy || !!editingInterface || !project.nodes.some(other=>other.id!==node.id&&other.data.kind!=='note')}
          onClick={()=>setEditingInterface({})}>Add interface</button>
      </div>
      {editingInterface && <InterfaceEditor key={editingInterface.id || 'new'} edge={editingInterface} node={node}
        nodes={project.nodes} busy={busy} onSave={onSaveInterface} onClose={()=>setEditingInterface(null)}/>}
      {edges.map(edge => <details key={edge.id}>
        <summary>{parents.get(edge.source)?.data.label} → {parents.get(edge.target)?.data.label} · {edge.label || 'Interface'}</summary>
        {edge.interfaceSpec&&<dl>{Object.entries(interfaceFields).map(([key,title])=><React.Fragment key={key}><dt>{title}</dt><dd>{edge.interfaceSpec[key]}</dd></React.Fragment>)}</dl>}
        {renderComments?.({kind:'interface',id:edge.id},'Interface comments')}
        <div className="row">
          <button className="btn" type="button" disabled={busy || !!editingInterface} onClick={()=>setEditingInterface(edge)}>Edit interface</button>
          {onInterface && <button className="btn" type="button" disabled={busy || !!editingInterface} onClick={()=>onInterface(edge.id)}>Ask AI to draft</button>}
        </div>
      </details>)}
      {!edges.length && !editingInterface && <p>{project.nodes.some(other=>other.id!==node.id&&other.data.kind!=='note')?'No interfaces yet. Use Add interface to connect a block.':'Add another block to create an interface.'}</p>}
      </section>
      <section hidden={tab!=='tests'} aria-label="Module verification cases">
      <p>Specified cases · Execution not run</p>
      {!(node.data.buildSpec?.verificationCases?.length)&&<p>No structured cases yet. Refine this module’s test specification.</p>}
      {(node.data.buildSpec?.verificationCases||[]).map(row=><details key={row.id}><summary>{row.name} · {row.category}</summary><p>{row.id} · {row.requirementIds.join(', ')}</p><dl>{['environment','setup','input','action','expected','evidence'].map(key=><React.Fragment key={key}><dt>{key[0].toUpperCase()+key.slice(1)}</dt><dd style={{whiteSpace:'pre-wrap'}}>{row[key]}</dd></React.Fragment>)}</dl>{row.interfaceId&&<p>Interface: {row.interfaceId}</p>}{row.operationId&&<p>Operation: {row.operationId}</p>}</details>)}
      </section>
      <section hidden={tab!=='model'} aria-label="Module design model"><EngineeringModelView key={node.id+'-'+(focusedOperation||'')} model={project.extensions?.engineeringModel} blockId={node.id} focusId={focusedOperation} renderComments={renderComments}/></section>
      <section hidden={tab!=='diagrams'} aria-label="Module diagrams">
      <p>Behavior references: {issues.filter(row=>row.severity==='error').length} conflicts · {issues.filter(row=>row.severity==='review').length} links to review.</p>
      {!!issues.length&&<details><summary>Review behavior links</summary><ul>{issues.map((issue,index)=><li key={index}>{issue.journey?`${issue.journey}, step ${issue.stepIndex+1}: `:''}{issue.message}{issue.ref?` (${issue.ref})`:''}</li>)}</ul></details>}

      {(node.data.buildSpec?.scenarios || []).map((scenario, index) => <Scenario key={index} scenario={scenario} comments={(step)=>renderComments?.(step===undefined?{kind:'scenario',id:node.id,index}:{kind:'scenario-step',id:node.id,index,field:String(step)})} operationNames={operationNames} onOperation={id=>{setFocusedOperation(id);setTab('model');}}/>)}
      {!node.data.buildSpec?.scenarios?.length&&<p>No scenarios defined. Refine the block specification to generate diagrams.</p>}
      </section>
      <section hidden={tab!=='handoff'} aria-label="Module agent handoff">
      <BlockAgentHandoff key={node.id} project={project} node={node} busy={busy} session={session} onPrepareSources={onPrepareSources}/>
      {session?.engineeringEnabled&&project.extensions?.architectureWork?.artifactMappings?.length>0&&<details><summary>Recorded implementation evidence</summary><BlockEvidence project={project} blockId={node.id} session={session}/></details>}
      </section>
  </div>;
}

function InterfaceEditor({edge, node, nodes, busy, onSave, onClose}) {
  const [error, setError] = useState('');
  function save(event) {
    event.preventDefault();
    const fields = new FormData(event.currentTarget);
    const label = fields.get('label').trim();
    if (!label) { setError('Enter an interface name.'); return; }
    const peer = fields.get('peer');
    const incoming = fields.get('direction') === 'incoming';
    const interfaceSpec = Object.fromEntries(Object.keys(interfaceFields).map(key=>[key,fields.get(key).trim()]));
    const hasContract = Object.values(interfaceSpec).some(Boolean);
    if (hasContract && !Object.values(interfaceSpec).every(Boolean)) {
      setError('Complete all six fields to save the contract, or leave them blank to save only the connection.');
      return;
    }
    try {
      const identity = edge.id ? edge : {id:crypto.randomUUID(), type:'smoothstep',
        source:incoming ? peer : node.id, target:incoming ? node.id : peer};
      onSave({...identity, label, interfaceSpec:hasContract ? interfaceSpec : undefined});
      onClose();
    } catch (failure) { setError(failure.message); }
  }
  return <form className="module-manual-editor fields" aria-label={edge.id?'Edit interface':'New interface'} onSubmit={save}>
    {!edge.id && <>
      <label>Other block<select name="peer" aria-label="Other block" required disabled={busy} defaultValue="">
        <option value="" disabled>Select a block</option>
        {nodes.filter(other=>other.id!==node.id&&other.data.kind!=='note').map(other=><option key={other.id} value={other.id}>{other.data.label}</option>)}
      </select></label>
      <label>Direction<select name="direction" aria-label="Direction" disabled={busy}><option value="outgoing">Outgoing from this block</option><option value="incoming">Incoming to this block</option></select></label>
    </>}
    <label className="field-wide">Interface name<input name="label" maxLength={150} defaultValue={edge.label || ''} disabled={busy} required/></label>
    {Object.entries(interfaceFields).map(([key,title])=><label key={key}>{title}
      <textarea aria-label={title} name={key} rows={2} maxLength={4000} defaultValue={edge.interfaceSpec?.[key] || ''} disabled={busy}/>
    </label>)}
    {error && <p className="field-wide" role="alert">{error}</p>}
    <div className="row field-wide"><button className="btn primary" disabled={busy}>Save interface</button><button className="btn" type="button" onClick={onClose}>Cancel</button></div>
  </form>;
}

export function BlockSpecProperties({node,busy,onSave,renderComments,compact=false}){
  const [editing,setEditing]=useState(null),[value,setValue]=useState(''),[error,setError]=useState('');
  function save(event){
    event.preventDefault();
    try{
      const current=node.data.buildSpec||{};
      if((current[editing.key]||'')!==editing.original)throw Error('This property changed. Cancel and reopen it to edit the latest value.');
      const next={...current},text=value.trim();
      if(text)next[editing.key]=text;else delete next[editing.key];
      onSave(Object.keys(next).length?next:undefined);
      setEditing(null);setError('');
    }catch(failure){setError(failure.message);}
  }
  return <div className="block-property-list" aria-label="Block specification properties">
    {blockSpecSections(node.data.buildSpec).map(({key,title,content},index)=>{
      const editButton=onSave&&editing?.key!==key&&<button className="link" aria-label={'Edit '+title} disabled={busy||Boolean(editing)}
        onClick={()=>{setEditing({key,original:content||''});setValue(content||'');setError('');}}>Edit</button>;
      const field=<>
        {editing?.key===key?<form onSubmit={save}><textarea aria-label={title} value={value} onChange={event=>setValue(event.target.value)} maxLength={4000} rows={5} autoFocus/>
          {error&&<p role="alert">{error}</p>}<div className="row"><button className="btn primary" disabled={busy}>Save property</button>
          <button className="btn" type="button" onClick={()=>setEditing(null)}>Cancel</button></div></form>:<p>{content||'Not specified'}</p>}
        {compact&&editButton}
        {renderComments?.({kind:'specification',id:node.id,field:key})}
      </>;
      if(compact)return <details key={key} className="block-property" open={index===0?true:undefined}>
        <summary>{title}</summary>{field}</details>;
      return <section key={key} className="block-property"><div className="block-property-heading"><h4>{title}</h4>{editButton}</div>{field}</section>;
    })}
  </div>;
}

function SpecEditor({node, busy, onSave, onClose}) {
  const [error, setError] = useState('');
  function save(event) {
    event.preventDefault();
    const fields = new FormData(event.currentTarget);
    try {
      const next = {};
      for (const {key} of blockSpecSections()) {
        const value = fields.get(key).trim();
        if (value) next[key] = value;
      }
      for (const key of ['scenarios','verificationCases']) {
        const value = fields.get(key).trim();
        if (value) next[key] = JSON.parse(value);
      }
      onSave(Object.keys(next).length ? next : undefined);
      onClose();
    } catch (failure) { setError(failure.message); }
  }
  return <form className="module-manual-editor fields" aria-label="Edit block specification" onSubmit={save}>
    {blockSpecSections(node.data.buildSpec).map(({key,title,content})=><label key={key}>{title}
      <textarea aria-label={title} name={key} rows={3} maxLength={4000} defaultValue={content || ''} disabled={busy}/>
    </label>)}
    <details className="field-wide"><summary>Scenarios and test case records</summary>
      <label>Scenarios (JSON)<textarea aria-label="Scenarios (JSON)" name="scenarios" rows={5} disabled={busy} defaultValue={node.data.buildSpec?.scenarios ? JSON.stringify(node.data.buildSpec.scenarios,null,2) : ''}/></label>
      <label>Verification cases (JSON)<textarea aria-label="Verification cases (JSON)" name="verificationCases" rows={5} disabled={busy} defaultValue={node.data.buildSpec?.verificationCases ? JSON.stringify(node.data.buildSpec.verificationCases,null,2) : ''}/></label>
    </details>
    {error && <p className="field-wide" role="alert">{error}</p>}
    <div className="row field-wide"><button className="btn primary" disabled={busy}>Save specification</button><button className="btn" type="button" onClick={onClose}>Cancel</button></div>
  </form>;
}

function Scenario({scenario,operationNames,onOperation,comments}) {
  const [open,setOpen]=useState(false);
  return <details onToggle={event=>setOpen(event.currentTarget.open)}>
    <summary>{scenario.name}</summary>{comments?.()}
    {open&&<Suspense fallback={<p role="status">Loading diagram…</p>}><DiagramPreview scenario={scenario}/></Suspense>}
    <ol>{scenario.steps.map((step,index)=><li key={index}>{step.sender} → {step.receiver} · {step.action}{comments?.(index)}{step.operationId&&<button className="link" onClick={()=>onOperation(step.operationId)}>Inspect operation {operationNames.get(step.operationId)||step.operationId}</button>}</li>)}</ol>
  </details>;
}

function BlockEvidence({project, blockId, session}) {
  const [snapshot, setSnapshot] = useState(null);
  const linked = useMemo(() => {
    if (!project.extensions?.architectureWork?.artifactMappings?.length) return [];
    const {coverage} = artifactWorkProjection(project);
    return coverage.find(row => row.ref === 'block:' + blockId)?.references || [];
  }, [project, blockId]);
  useEffect(() => {
    if (!linked.length) return;
    const controller = new AbortController();
    engineeringCall(session,'delivery',{projectId:project.id},{signal:controller.signal})
      .then(report => {
        if (!controller.signal.aborted) setSnapshot({report,linked});
      }).catch(error => {
        if (!controller.signal.aborted) setSnapshot({error:error.message,linked});
      });
    return () => controller.abort();
  }, [project.id, session, linked]);
  if (!linked.length) return <p role="status">Block checks pending · build and link implementation files.</p>;
  const current = snapshot?.linked === linked ? snapshot : null;
  if (current?.error) return <p role="status">Block checks unavailable · {current.error}</p>;
  const report = current?.report;
  if (report?.relation !== 'matches_saved_design' || !linked.some(ref => ref.artifactId === report.artifact?.id))
    return <p role="status">{report ? 'Block checks pending · capture the current build.' : 'Looking up block evidence…'}</p>;
  const handoff=report.workOrderHandoffEvidence;
  return <>
    {handoff?.blockId===blockId&&<p role="status">Verified Spec Kit reads · {handoff.completeRequiredFiles}/{handoff.requiredFileCount} required files</p>}
    <ArtifactChecks key={report.artifact.id} session={session} projectId={project.id} sessionId={report.session.id} artifact={report.artifact} blockId={blockId} readOnly/>
  </>;
}
