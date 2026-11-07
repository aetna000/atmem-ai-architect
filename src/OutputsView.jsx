import React,{useEffect,useState} from 'react';
import {EmulationPanel} from './EmulationPanel.jsx';
import {outputBundle} from './output-bundle.mjs';

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
 if(visual)return !url?<p>Preparing preview…</p>:name.endsWith('.pdf')?<iframe className="output-pdf" src={url} title={`Preview ${name}`}/>:<img className="output-image" src={url} alt={`Preview ${name}`}/>;
 if(name.endsWith('.md'))return <Document text={content}/>;
 return <pre className="output-code"><code>{content}</code></pre>;
}
export function OutputsView({project,run,environment,session,onDownload,onBack}){
 const [bundle,setBundle]=useState(null),[error,setError]=useState(''),[loading,setLoading]=useState(true),[retry,setRetry]=useState(0),[selected,setSelected]=useState('spec-kit/implementation-spec.md');
 useEffect(()=>{
   let active=true;setLoading(true);setError('');
   outputBundle(project,run,environment).then(value=>{if(active){setBundle(value);setLoading(false);}}).catch(e=>{if(active){setError(e.message);setLoading(false);}});
   return ()=>{active=false;};
 },[project,run,environment,retry]);
 const readiness=bundle?.files['spec-kit/readiness.json']?JSON.parse(bundle.files['spec-kit/readiness.json']):null;
 const groups=bundle?[['Spec Kit',Object.keys(bundle.files).filter(n=>n.startsWith('spec-kit/')).sort((a,b)=>Number(b.includes('implementation-spec'))-Number(a.includes('implementation-spec')))],['Specification & handoff',Object.keys(bundle.files).filter(n=>!n.includes('/')&&!/^diagram\./.test(n))],['Design',Object.keys(bundle.files).filter(n=>/^diagram\./.test(n))],['Terraform',Object.keys(bundle.files).filter(n=>n.startsWith('terraform/'))]]:[];
 return <section className="doc outputs-view" aria-label="Outputs">
  <header className="doc-head"><h2>Outputs</h2><p className="muted">Review the specification, Spec Kit, design and Terraform files before downloading the package.</p></header>
  <div className="row"><button className="link" onClick={onBack}>Back to architecture</button><button className="btn primary" disabled={!bundle||loading||!!error} onClick={()=>onDownload(bundle)}>Download reviewed ZIP</button></div>
  <EmulationPanel project={project} environment={environment} session={session}/>
  {loading&&<p role="status">Preparing the current outputs…</p>}
  {error&&<div role="alert"><p>{error}</p><button className="btn" onClick={()=>setRetry(n=>n+1)}>Retry preparing outputs</button></div>}
  {bundle&&!loading&&!error&&<>
   <p className="muted small">Design r{bundle.manifest.designRevision} · {Object.keys(bundle.files).length} files · Generated {new Date(bundle.manifest.generatedAt).toLocaleString()}. Changes to the project refresh this directory. Download contains these exact files.</p>
   {readiness&&<aside aria-label="Handoff readiness"><strong>Engineering handoff — decisions and implementation remain</strong><p>{readiness.counts.priorityDecisions} priority decisions · {readiness.counts.generatedFoundations} generated foundations / {readiness.counts.components} logical components</p><p>Next: {readiness.nextAction}</p><button className="link" onClick={()=>setSelected('spec-kit/readiness.md')}>Review handoff gaps</button></aside>}
   <div className="outputs-browser" data-snapshot-id={bundle.manifest.snapshotId}>
    <nav className="outputs-directory" aria-label="Output files">{groups.map(([title,names])=><details key={title} open><summary>{title}</summary>{names.map(name=><button type="button" key={name} aria-current={selected===name?'page':undefined} onClick={()=>setSelected(name)} title={name}>{name.includes('/')?name.split('/').at(-1):name}</button>)}</details>)}</nav>
    <div className="output-preview" aria-label="Output preview"><h3>{selected}</h3>{bundle.files[selected]!==undefined&&<Preview key={selected} name={selected} content={bundle.files[selected]}/>}</div>
   </div>
  </>}
 </section>;
}
