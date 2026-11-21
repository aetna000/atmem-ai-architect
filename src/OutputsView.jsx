import {buildReview,designReadiness} from './build-review.mjs';
import {ReadyExampleChecklist} from './ReadyExample.jsx';
import {isReadyExample} from './ready-example.mjs';
import {FileTree} from './FileTree.jsx';
import {strFromU8} from 'fflate';
import {CodePreview} from './CodePreview.jsx';
import {BrainActivity} from "./BrainActivity.jsx";
import React,{useEffect,useState,useRef,useMemo} from 'react';
import {EmulationPanel} from './EmulationPanel.jsx';
import {outputBundle} from './output-bundle.mjs';
import {ImplementationDelivery} from './ImplementationDelivery.jsx';

// Render generated Markdown as text elements, never executable HTML.
function Document({text}){
  const lines=text.split('\n'),blocks=[];let paragraph=[],list=[],ordered=false,code=null;
  const clean=s=>s.replace(/\*\*|`/g,'');
  function flush(){if(paragraph.length){blocks.push(<p key={blocks.length}>{clean(paragraph.join(' '))}</p>);paragraph=[];}if(list.length){const List=ordered?'ol':'ul';blocks.push(<List key={blocks.length}>{list.map((line,i)=><li key={i}>{clean(line)}</li>)}</List>);list=[];}}
  for(const line of lines){
    if(line.startsWith('```')){flush();if(code!==null){blocks.push(<pre key={blocks.length}>{code.join('\n')}</pre>);code=null;}else code=[];continue;}
    if(code!==null){code.push(line);continue;}
    const heading=line.match(/^(#{1,6})\s+(.+)/);
    if(heading){flush();const Tag=`h${Math.min(heading[1].length+1,6)}`;blocks.push(<Tag key={blocks.length}>{heading[2]}</Tag>);}
    else if(/^\s*([-*]|\d+\.)\s/.test(line)){const nextOrdered=/^\s*\d+\./.test(line);if(paragraph.length||(list.length&&ordered!==nextOrdered))flush();ordered=nextOrdered;list.push(line.replace(/^\s*([-*]|\d+\.)\s/,''));}
    else if(line.startsWith('|')){flush();if(!/^\|[- :|]+\|$/.test(line))blocks.push(<p className="output-table-row" key={blocks.length}>{clean(line)}</p>);}
    else if(!line.trim())flush();else paragraph.push(line.replace(/^> /,''));
  }
  flush();return <article className="output-document">{blocks}</article>;
}
function Preview({name,content}){
 const [url,setUrl]=useState(null);
 const visual=/\.(pdf|png|svg)$/.test(name);
 useEffect(()=>{
   if(!visual){setUrl(null);return;}
   const type=name.endsWith('.pdf')?'application/pdf':name.endsWith('.svg')?'image/svg+xml':'image/png';
   const next=URL.createObjectURL(new Blob([content],{type}));setUrl(next);return ()=>URL.revokeObjectURL(next);
 },[name,content,visual]);
 if(visual)return !url?<p role="status"><BrainActivity/> Preparing preview…</p>:name.endsWith('.pdf')?<iframe className="output-pdf" src={url} title={`Preview ${name}`}/>:<img className="output-image" src={url} alt={`Preview ${name}`}/>;
 if(name.endsWith('.md'))return <Document text={content}/>;
 return <CodePreview className="output-code" content={content} name={name}/>;
}
export function OutputsView({project,run,environment,session,workStatus,onDownload,onBack,emulation,onDiscuss,discussionBusy,onBuild,onSave,onPrepareSources,onDownloaded,onReview,checkReceipt,onNavigate}){
 const [exploration,setExploration]=useState(null),[captureOpen,setCaptureOpen]=useState(false);
 const hasCapturedCode=!!project.extensions?.architectureWork?.artifactMappings?.length;
 const prepareSourcesRef=useRef(onPrepareSources);prepareSourcesRef.current=onPrepareSources;
 const projectRef=useRef(project);projectRef.current=project;
 const [packing,setPacking]=useState(false),[showFiles,setShowFiles]=useState(false);
 const designReview=useMemo(()=>buildReview(project),[project]);
 const verdict=designReadiness(designReview,!!project.extensions?.diagramCatalogueRequired);
 const [bundle,setBundle]=useState(null),[error,setError]=useState(''),[loading,setLoading]=useState(true),[retry,setRetry]=useState(0),[selected,setSelected]=useState('START_HERE.md');
 useEffect(()=>{
   let active=true;setLoading(true);setError('');
   outputBundle(project,run,environment,checkReceipt,{deferVisuals:true,session,prepareSources:expected=>prepareSourcesRef.current?.(expected)||session}).then(value=>{if(active){setBundle(value);setLoading(false);}}).catch(e=>{if(active){setError(e.message);setLoading(false);}});
   return ()=>{active=false;};
 },[project,run,environment,retry,checkReceipt,session?.token]);
 const generating=['running','starting'].includes(workStatus?.state);
 const populated=project.nodes.some(n=>n.data.kind!=='note');
 const readiness=bundle?.files['spec-kit/readiness.json']?JSON.parse(bundle.files['spec-kit/readiness.json']):null;
 const artifactMode=exploration?.project===project,prefix=artifactMode?'design-documents/':'';
 const fileValues=useMemo(()=>artifactMode?{...exploration.files,...Object.fromEntries(Object.entries(bundle?.files||{}).map(([name,value])=>[prefix+name,value]))}:bundle?.files||{},[artifactMode,exploration,bundle,prefix]);
 const treeFiles=useMemo(()=>({...Object.fromEntries((bundle?.visualPaths||[]).map(path=>[prefix+path,null])),...fileValues}),[bundle,fileValues,prefix]);
 async function selectFile(name){setSelected(name);if(treeFiles[name]===null){try{const full=await bundle.prepare();if(projectRef.current===project)setBundle(full);}catch(error){if(projectRef.current===project)setError(error.message);}}}
 async function downloadDesign(){if(packing)return;setPacking(true);setError('');try{const full=await bundle.prepare();if(projectRef.current!==project)throw Error('Design changed while preparing files. Download again.');setBundle(full);await onDownload(full);}catch(error){if(projectRef.current.id===project.id)setError(error.message);}finally{setPacking(false);}}
 const selectedPath=Object.hasOwn(treeFiles,selected)?selected:fileValues['START_HERE.md']?'START_HERE.md':Object.keys(fileValues).find(name=>name.endsWith('implementation-spec.md'))||Object.keys(fileValues)[0];
 const raw=treeFiles[selectedPath],content=typeof raw==='string'?raw:raw&&/\.(?:md|txt|json|py|js|mjs|tf|sh|yaml|yml|toml|html|css)$/.test(selectedPath)?strFromU8(raw):raw;

 return <section className="doc outputs-view" aria-label="Outputs">
  <header className="doc-head"><h2>Delivery</h2></header>
  <button className="link" onClick={onReview||onBack}>Back to Review</button>
  {generating&&<p role="status">Architecture generation is running. This download contains the currently accepted snapshot.</p>}
  {!populated&&<p role="status">No architecture applied. Open Review to inspect generation or recover the draft.</p>}
  <section className="delivery-reading-order" aria-label="Current design handoff">
   <h3>Start with the handoff</h3><aside className="handoff-verdict"><strong>{verdict.title}</strong>{verdict.gaps.length>0&&<ul>{verdict.gaps.map(g=><li key={g}>{g}</li>)}</ul>}</aside><p>Revision {project.revision} · {designReview.requirements.length} requirements · {designReview.counts.dedicatedCovered}/{designReview.requirements.length} dedicated · {designReview.counts.covered}/{designReview.requirements.length} linked · {designReview.counts.open} open owner decisions</p>
   <div>{[['Read scope','specification.md'],['Build work orders','spec-kit/implementation-spec.md'],['Review remaining work','spec-kit/readiness.md']].map(([name,file])=><button key={file} className="btn" disabled={!bundle} onClick={()=>setSelected(prefix+file)}>{name}</button>)}<button className="btn" onClick={onBack}>Open drawings</button></div>
  </section>
  {isReadyExample(project)&&<details><summary>Bundled runtime evidence</summary><ReadyExampleChecklist/></details>}
  {session?.engineeringEnabled&&(hasCapturedCode?<ImplementationDelivery key={project.id} project={project} session={session} workStatus={workStatus} onBuild={onBuild} onSave={onSave} contextBusy={discussionBusy} designBundle={loading?null:bundle} onDesignDownload={onDownload} onDownloaded={onDownloaded} checkReceipt={checkReceipt} onExplore={setExploration} onNavigate={onNavigate}/>:<details onToggle={event=>{setCaptureOpen(event.currentTarget.open);if(!event.currentTarget.open)setExploration(null);}}><summary>{isReadyExample(project)?'Checks for your edited project':'Captured workspace details'}</summary>{captureOpen&&<ImplementationDelivery key={project.id} project={project} session={session} workStatus={workStatus} onBuild={onBuild} onSave={onSave} contextBusy={discussionBusy} designBundle={loading?null:bundle} onDesignDownload={onDownload} onDownloaded={onDownloaded} checkReceipt={checkReceipt} onExplore={setExploration} onNavigate={onNavigate}/>}</details>)}
  <section aria-label="Project file explorer"><h3>Explore files</h3>

  {(!session?.engineeringEnabled||!hasCapturedCode)&&<><p>Current design, Spec Kit and recorded evidence. Check readiness before implementation.</p><button className="btn" disabled={!bundle||loading||!!error||packing} onClick={downloadDesign}>{packing?'Preparing ZIP…':populated?'Download project ZIP':'Download interim snapshot'}</button></>}

  {readiness?.capturedEvidence?.status==='unavailable'&&<p role="status">Capture evidence unavailable. Download again to retry; see captured-evidence.json.</p>}
  {loading&&<p role="status"><BrainActivity/> Preparing the current outputs…</p>}
  {error&&<div role="alert"><p>{error}</p><button className="btn" onClick={()=>setRetry(n=>n+1)}>Retry preparing outputs</button></div>}
  {bundle&&!loading&&!error&&<>
   <p className="muted small">r{bundle.manifest.designRevision} · {Object.keys(bundle.files).length} design files</p>
   {readiness&&<details><summary>Remaining work</summary><aside aria-label="Handoff readiness"><strong>Engineering handoff — decisions and implementation remain</strong><p>{readiness.counts.priorityDecisions} priority decisions · {readiness.counts.generatedFoundations} generated foundations / {readiness.counts.components} logical components</p><p>Next: {readiness.nextAction}</p><button className="link" onClick={()=>setSelected('spec-kit/readiness.md')}>Review handoff gaps</button></aside></details>}
   <button className="btn" aria-expanded={showFiles} onClick={()=>setShowFiles(v=>!v)}>{showFiles?'Hide file browser':'Browse all files'}</button>
   <div className="outputs-browser" style={{gridTemplateColumns:showFiles?'minmax(160px,25%) minmax(0,1fr)':'minmax(0,1fr)'}} data-snapshot-id={bundle.manifest.snapshotId}>
    {showFiles&&<FileTree files={treeFiles} selected={selectedPath} onSelect={selectFile}/>}
    <div className="output-preview" aria-label="Output preview"><h3>{selectedPath}</h3>{raw===null?<p role="status"><BrainActivity/> Preparing preview…</p>:content!==undefined&&(typeof content==='string'||/\.(?:pdf|png|svg)$/.test(selectedPath)?<Preview key={selectedPath} name={selectedPath} content={content}/>:<p>{content.byteLength} bytes</p>)}</div>
   </div>
  </>}
  </section>
 </section>;
}
