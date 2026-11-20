import {EngineeringModelView} from './EngineeringModelView.jsx';
import {architectureConsistency} from './architecture-consistency.mjs';
import React, {lazy, Suspense, useEffect, useMemo, useState} from 'react';
import { artifactWorkProjection } from './artifact-work.mjs';
import { ArtifactChecks } from './ArtifactChecks.jsx';
import { engineeringCall } from './engineering-client.mjs';
import { blockChildren, blockSpecSections, interfaceFields } from './block-spec.mjs';
import {verificationCategories} from './verification-cases.mjs';
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
  const [editingCase,setEditingCase] = useState(null);
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
  const groups = [
    ['Block behavior', ['behavior','inputs','outputs','failures']],
    ['Implementation and operations', ['implementation','infrastructure','operations']],
    ['Acceptance criteria', ['tests']],
  ];
  const documented = sections.filter(section => section.content);
  const missing = sections.filter(section => !section.content);
  const linkedRequirements = (project.needs || []).filter(need => need.links?.includes(node.id));
  return <div className="block-spec-content">
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
      {renderComments?.({kind:'block',id:node.id},'Block comments')}
      {linkedRequirements.length > 0 && <details><summary>Linked requirements ({linkedRequirements.length})</summary>
        <ul>{linkedRequirements.map(need => <li key={need.id}><strong>{need.id}</strong> {need.statement}</li>)}</ul>
      </details>}
      {editingSpec ? <SpecEditor node={node} busy={busy} onSave={onSaveSpec} onClose={()=>setEditingSpec(false)}/> :
        <div className="module-spec-document">
          {groups.map(([title, keys]) => {
            const rows = keys.map(key => documented.find(section => section.key === key)).filter(Boolean);
            if (!rows.length) return null;
            return <section key={title}><h5>{title}</h5>
              <dl>{rows.map(section => <div key={section.key}>
                <dt>{section.title}</dt><dd>{section.content}</dd>
                <dd>{renderComments?.({kind:'specification',id:node.id,field:section.key})}</dd>
              </div>)}</dl>
            </section>;
          })}
          {!documented.length && <p>Start with what this block does. Choose Edit specification to add its behavior, inputs and outputs.</p>}
          {!!missing.length && <details><summary>Unspecified fields ({missing.length})</summary>
            <ul>{missing.map(section => <li key={section.key}>{section.title}{renderComments?.({kind:'specification',id:node.id,field:section.key})}</li>)}</ul>
          </details>}
        </div>}
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
      <div className="module-section-heading"><h4>Planned test cases</h4><button className="btn" disabled={busy || !!editingCase} onClick={()=>setEditingCase({})}>Add test case</button></div>
      {editingCase && <VerificationEditor row={editingCase} project={project} busy={busy} onClose={()=>setEditingCase(null)} onSave={row=>{
        const cases=node.data.buildSpec?.verificationCases || [];
        const verificationCases=editingCase.id ? cases.map(item=>item.id===row.id?row:item) : [...cases,row];
        onSaveSpec({...node.data.buildSpec,verificationCases});
        setEditingCase(null);
      }}/>}
      {!(node.data.buildSpec?.verificationCases?.length)&&<p>No test cases recorded.</p>}
      {(node.data.buildSpec?.verificationCases||[]).map(row=><details key={row.id}><summary>{row.name} · {row.category}</summary><p>{row.id} · {row.requirementIds.join(', ')}</p><dl>{['environment','setup','input','action','expected','evidence'].map(key=><React.Fragment key={key}><dt>{key[0].toUpperCase()+key.slice(1)}</dt><dd style={{whiteSpace:'pre-wrap'}}>{row[key]}</dd></React.Fragment>)}</dl>{row.interfaceId&&<p>Interface: {row.interfaceId}</p>}{row.operationId&&<p>Operation: {row.operationId}</p>}<button className="btn" disabled={busy || !!editingCase} onClick={()=>setEditingCase(row)}>Edit test case</button></details>)}
      <h4>Execution evidence</h4>
      {session?.engineeringEnabled && project.extensions?.architectureWork?.artifactMappings?.length
        ? tab==='tests' && <BlockEvidence project={project} blockId={node.id} session={session}/>
        : <p>No execution evidence linked.</p>}
      </section>
      <section hidden={tab!=='model'} aria-label="Module design model"><EngineeringModelView key={node.id+'-'+(focusedOperation||'')} model={project.extensions?.engineeringModel} blockId={node.id} focusId={focusedOperation} renderComments={renderComments}/></section>
      <section hidden={tab!=='diagrams'} aria-label="Module diagrams">
      <h4>Behavior scenarios</h4><p>Behavior references: {issues.filter(row=>row.severity==='error').length} conflicts · {issues.filter(row=>row.severity==='review').length} links to review.</p>
      {!!issues.length&&<details><summary>Review behavior links</summary><ul>{issues.map((issue,index)=><li key={index}>{issue.journey?`${issue.journey}, step ${issue.stepIndex+1}: `:''}{issue.message}{issue.ref?` (${issue.ref})`:''}</li>)}</ul></details>}

      {(node.data.buildSpec?.scenarios || []).map((scenario, index) => <Scenario key={index} scenario={scenario} comments={(step)=>renderComments?.(step===undefined?{kind:'scenario',id:node.id,index}:{kind:'scenario-step',id:node.id,index,field:String(step)})} operationNames={operationNames} onOperation={id=>{setFocusedOperation(id);setTab('model');}}/>)}
      {!node.data.buildSpec?.scenarios?.length&&<p>No scenarios defined. Refine the block specification to generate diagrams.</p>}
      </section>
      <section hidden={tab!=='handoff'} aria-label="Module agent handoff">
      <BlockAgentHandoff key={node.id} project={project} node={node} busy={busy} session={session} onPrepareSources={onPrepareSources}/>
      {tab==='handoff'&&session?.engineeringEnabled&&project.extensions?.architectureWork?.artifactMappings?.length>0&&<details><summary>Recorded implementation evidence</summary><BlockEvidence project={project} blockId={node.id} session={session}/></details>}
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

function VerificationEditor({row,project,busy,onSave,onClose}) {
  const [error,setError]=useState('');
  function save(event) {
    event.preventDefault();
    const data=new FormData(event.currentTarget);
    if (!data.getAll('requirementIds').length) { setError('Choose at least one requirement covered by this case.'); return; }
    const fields=Object.fromEntries([...data.entries()].filter(([key])=>key!=='requirementIds').map(([key,value])=>[key,value.trim()]));
    try {
      onSave({...row,...fields,id:row.id || crypto.randomUUID(),requirementIds:data.getAll('requirementIds')});
    } catch (failure) { setError(failure.message); }
  }
  return <form className="module-manual-editor fields" aria-label="Test case" onSubmit={save}>
    <label>Case name<input name="name" defaultValue={row.name} required maxLength={150}/></label>
    <label>Category<select name="category" defaultValue={row.category || 'acceptance'}>{verificationCategories.map(category=><option key={category}>{category}</option>)}</select></label>
    <details className="field-wide"><summary>Choose requirements covered</summary>
      {!project.needs?.length && <p>Add a requirement in Requirements before saving a test case.</p>}
      {project.needs?.map(need=><label key={need.id}><input type="checkbox" name="requirementIds" value={need.id} defaultChecked={row.requirementIds?.includes(need.id)}/> {need.id} · {need.statement}</label>)}
    </details>
    {Object.entries({environment:'Environment',setup:'Setup',input:'Input',action:'Action',expected:'Expected result',evidence:'Evidence to collect'}).map(([key,label])=><label key={key}>{label}<textarea name={key} rows={2} defaultValue={row[key]} required maxLength={4000}/></label>)}
    {error && <p role="alert">{error}</p>}
    <div className="row field-wide"><button className="btn primary" disabled={busy || !project.needs?.length}>Save test case</button><button className="btn" type="button" onClick={onClose}>Cancel</button></div>
  </form>;
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
