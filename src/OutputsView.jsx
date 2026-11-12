import {FileTree} from './FileTree.jsx';
import {strFromU8} from 'fflate';
import {CodePreview} from './CodePreview.jsx';
import {BrainActivity} from "./BrainActivity.jsx";
import React,{useEffect,useState} from 'react';
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
export function OutputsView({project,run,environment,session,onDownload,onBack,emulation,onDiscuss,discussionBusy,onBuild,onSave,onDownloaded,onReview,checkReceipt,onNavigate}){
 const [exploration,setExploration]=useState(null);
 const [bundle,setBundle]=useState(null),[error,setError]=useState(''),[loading,setLoading]=useState(true),[retry,setRetry]=useState(0),[selected,setSelected]=useState('spec-kit/implementation-spec.md');
 useEffect(()=>{
   let active=true;setLoading(true);setError('');
   outputBundle(project,run,environment,checkReceipt).then(value=>{if(active){setBundle(value);setLoading(false);}}).catch(e=>{if(active){setError(e.message);setLoading(false);}});
   return ()=>{active=false;};
 },[project,run,environment,retry,checkReceipt]);
 const readiness=bundle?.files['spec-kit/readiness.json']?JSON.parse(bundle.files['spec-kit/readiness.json']):null;
 const fileValues=exploration?.project===project?exploration.files:bundle?.files||{};
 const selectedPath=fileValues[selected]!==undefined?selected:fileValues['START_HERE.md']?'START_HERE.md':Object.keys(fileValues).find(name=>name.endsWith('implementation-spec.md'))||Object.keys(fileValues)[0];
 const raw=fileValues[selectedPath],content=typeof raw==='string'?raw:raw&&/\.(?:md|txt|json|py|js|mjs|tf|sh|yaml|yml|toml|html|css)$/.test(selectedPath)?strFromU8(raw):raw;

 return <section className="doc outputs-view" aria-label="Outputs">
  <header className="doc-head"><h2>Delivery</h2></header>
  <button className="link" onClick={onReview||onBack}>Back to Review</button>
  {session?.engineeringEnabled&&<ImplementationDelivery key={project.id} project={project} session={session} onBuild={onBuild} onSave={onSave} contextBusy={discussionBusy} designBundle={loading?null:bundle} onDesignDownload={onDownload} onDownloaded={onDownloaded} checkReceipt={checkReceipt} onExplore={setExploration} onNavigate={onNavigate}/>}
  <section aria-label="Project file explorer"><h3>Explore files</h3>

  {!session?.engineeringEnabled&&<><p>Design package · no implementation generated.</p><button className="btn" disabled={!bundle||loading||!!error} onClick={()=>onDownload(bundle)}>Download project ZIP</button></>}

  {loading&&<p role="status"><BrainActivity/> Preparing the current outputs…</p>}
  {error&&<div role="alert"><p>{error}</p><button className="btn" onClick={()=>setRetry(n=>n+1)}>Retry preparing outputs</button></div>}
  {bundle&&!loading&&!error&&<>
   <p className="muted small">r{bundle.manifest.designRevision} · {Object.keys(bundle.files).length} design files</p>
   {readiness&&<details><summary>Remaining work</summary><aside aria-label="Handoff readiness"><strong>Engineering handoff — decisions and implementation remain</strong><p>{readiness.counts.priorityDecisions} priority decisions · {readiness.counts.generatedFoundations} generated foundations / {readiness.counts.components} logical components</p><p>Next: {readiness.nextAction}</p><button className="link" onClick={()=>setSelected('spec-kit/readiness.md')}>Review handoff gaps</button></aside></details>}
   <div className="outputs-browser" data-snapshot-id={bundle.manifest.snapshotId}>
    <FileTree files={fileValues} selected={selectedPath} onSelect={setSelected}/>
    <div className="output-preview" aria-label="Output preview"><h3>{selectedPath}</h3>{content!==undefined&&(typeof content==='string'||/\.(?:pdf|png|svg)$/.test(selectedPath)?<Preview key={selectedPath} name={selectedPath} content={content}/>:<p>{content.byteLength} bytes</p>)}</div>
   </div>
  </>}
  </section>
 </section>;
}
