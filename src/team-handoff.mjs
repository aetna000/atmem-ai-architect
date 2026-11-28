import {zipFiles} from './handoff-zip.mjs';
export {zipFiles} from './handoff-zip.mjs';
import {buildReview} from './build-review.mjs';
import {blockSpecSections,interfaceFields} from './block-spec.mjs';
import {isDiagramRevision} from './records.mjs';
import {diagramFileStem} from './drawio-handoff.mjs';
import {handoffStyles} from './handoff-styles.mjs';
import brand from './runtime/handoff-brand.json' with {type:'json'};
import {rasterType,teamDocuments} from './handoff-documents.mjs';
import {connectionFigure} from './handoff-drawings.mjs';
import {html,fields,list,disclosure,fileLink,focusMap,websiteShell} from './handoff-presentation.mjs';

const text=value=>typeof value==='string'?value:new TextDecoder().decode(value);
const read=(files,path,fallback)=>Object.hasOwn(files,path)?JSON.parse(text(files[path])):fallback;
const p=value=>'<p>'+html(value)+'</p>';
const title=(name,lead='')=>'<h1>'+html(name)+'</h1>'+(lead?'<p class="lead">'+html(lead)+'</p>':'');
const heading=name=>'<h2>'+html(name)+'</h2>';
const empty=message=>'<p class="empty">'+html(message)+'</p>';
const sectionLink=(id,label)=>'<a class="inline-link" href="#'+id+'">'+html(label)+' <span aria-hidden="true">→</span></a>';
const slug=value=>String(value).normalize('NFKD').replace(/\p{M}/gu,'').toLowerCase().replace(/[^\p{L}\p{N}]+/gu,'-').replace(/^-|-$/g,'').slice(0,64).replace(/-$/,'')||'item';
export const teamFilename=(name,revision)=>slug(name)+'-r'+revision+'-team-handoff.zip';

// Inspect the emitted reader, including links back from individual work orders.
// Raw captured code stays in its original archive and is never executed here.
export function verifyTeamLinks(files){
  const anchors=new Map();
  for(const [path,body] of Object.entries(files)){
    if(path.endsWith('.html'))anchors.set(path,new Set([...body.matchAll(/<[a-z][^>]*?\sid="([^"]+)"/gi)].map(match=>match[1])));
  }
  for(const path of anchors.keys()){
    for(const [,tag,href] of files[path].matchAll(/<(a|img|source|link)\b[^>]*?\s(?:href|src|srcset)="([^"]+)"/gi)){
      if(tag==='a'&&/^https?:\/\//i.test(href))continue;
      const target=new URL(href,'https://handoff.invalid/'+path);
      const name=decodeURIComponent(target.pathname.slice(1));
      if(target.origin!=='https://handoff.invalid'||!Object.hasOwn(files,name)||
        (target.hash&&!anchors.get(name)?.has(decodeURIComponent(target.hash.slice(1)))))throw Error('Unresolved handoff link in '+path+' to '+href);
    }
  }
}

function namedFile(files,dir,label,extension,content){
  const stem=slug(label).replace(/^(con|prn|aux|nul|com[1-9]|lpt[1-9])$/i,'$1-file');
  let name=dir+'/'+stem+extension;
  for(let i=2;Object.hasOwn(files,name);i++)name=dir+'/'+stem+'-'+i+extension;
  files[name]=content;
  return name;
}
function money(estimate){
  if(!estimate||estimate.expected==null)return estimate?.mixedCurrencies?'Mixed currencies':'Unpriced';
  return (estimate.currency||'')+' '+estimate.expected.toLocaleString('en',{maximumFractionDigits:2})+(estimate.complete?'':' · partial');
}
function sourceLinks(project){
  const sources=new Set();
  for(const row of [...(project.extensions?.architectureDiagrams?.elements||[]),...(project.extensions?.architectureDiagrams?.relations||[])]){
    if(typeof row.source==='string'&&/^https:\/\/[^\s]+$/i.test(row.source))sources.add(row.source);
  }
  return [...sources].map(source=>{
    let url;try{url=new URL(source);}catch{return '';}
    if(url.username||url.password)return '';
    const parts=url.pathname.split('/').filter(Boolean);
    const page=parts.at(-1)||'Homepage';
    const label=url.hostname==='github.com'&&parts.length>=2?parts.slice(0,2).join('/')+' · '+page:
      page.replace(/^rfc(\d+)$/i,'RFC $1').replace(/[-_]+/g,' ');
    return '<li><a rel="noreferrer" href="'+html(url.href)+'">'+html(label.charAt(0).toUpperCase()+label.slice(1))+'</a> <small>'+html(url.hostname)+'</small></li>';
  }).join('');
}

const designReaders=new WeakMap();
export function designHandoffWebsite(bundle){
  if(!designReaders.has(bundle)){
    const files=teamHandoffFiles(bundle).catch(error=>{designReaders.delete(bundle);throw error;});
    designReaders.set(bundle,files);
  }
  return designReaders.get(bundle);
}
function makeWorkOrder(node,interfaces,requirements,tasks,labels,revision){
  const cases=node.data.buildSpec?.verificationCases||[];
  const back='<a class="inline-link" href="../index.html#build">← Project build plan</a>';
  const body=back+title(node.data.label,node.data.description)+heading('Assignment')+
    fields(blockSpecSections(node.data.buildSpec).map(s=>[s.title,s.content||'Needs definition.']))+
    heading('Interfaces')+(interfaces.map(r=>disclosure(r.from+' → '+r.to,r.name,fields(Object.entries(interfaceFields).map(([k,name])=>[name,r.contract[k]||'Needs definition.'])))).join('')||empty('No interfaces recorded.'))+
    heading('Linked requirements')+list(requirements.map(r=>r.statement),'No linked requirements.')+
    heading('Build sequence')+(tasks.map(t=>disclosure(t.title,t.phase,fields([['Depends on',t.dependsOn?.map(id=>labels.get(id)||id).join(', ')||'No earlier task'],['Completion criteria',t.acceptance?.join('\n')]])+list(t.steps||[],'No steps recorded.'))).join('')||empty('No assigned tasks.'))+
    heading('Verification')+(cases.map(c=>disclosure(c.name,c.category,fields(['environment','setup','input','action','expected','evidence'].map(k=>[k[0].toUpperCase()+k.slice(1),c[k]])))).join('')||empty('No verification cases recorded.'))+back;
  return websiteShell({title:'Work order',name:node.data.label,revision,root:'..',sections:[{id:'assignment',label:'Assignment',glyph:'build',body}]});
}

// Keep the engineering archive byte-for-byte when one already exists. Team files
// use presentation names only; machine IDs, owners and receipts remain canonical.
export async function teamHandoffFiles(bundle,{archive,blockIds,focusId,captureRelation}={}){
  const {files:raw}=bundle,project=bundle.snapshot||bundle.project;
  const allNodes=project.nodes.filter(n=>n.data.kind!=='note'),scope=blockIds&&new Set(blockIds);
  const nodes=scope?allNodes.filter(n=>scope.has(n.id)):allNodes;
  const edges=scope?project.edges.filter(e=>scope.has(e.source)||scope.has(e.target)):project.edges;
  const review=buildReview(project),incident=new Set(edges.map(e=>e.id));
  const interfaces=review.interfaces.filter(r=>incident.has(r.id)).map(r=>({...r,from:r.from||r.source,to:r.to||r.target}));
  const cases=review.cases.filter(c=>!scope||scope.has(c.blockId));
  const caseNames=new Map(review.cases.map(c=>[c.blockId+'\0'+c.id,c.name]));
  const caseRequirements=new Set(cases.flatMap(c=>c.requirementIds));
  const requirements=review.requirements.filter(r=>!scope||r.links?.some(id=>scope.has(id))||caseRequirements.has(r.id));
  const requirementIds=new Set(requirements.map(r=>r.id));
  const decisions=review.decisions.filter(q=>!scope||q.links?.some(id=>scope.has(id))||q.requirementIds?.some(id=>requirementIds.has(id))||q.interfaceIds?.some(id=>incident.has(id)));
  const open=decisions.filter(q=>q.status==='open');
  const byId=new Map(allNodes.map(n=>[n.id,n.data.label]));
  const allTasks=read(raw,'spec-kit/tasks.json',{}).tasks||[];
  const tasks=scope?allTasks.filter(t=>t.componentIds?.some(id=>scope.has(id))):allTasks;
  const taskNames=new Map(allTasks.map(t=>[t.id,t.title]));
  const phases=new Map();
  for(const task of tasks){
    const phase=task.phase||'General';
    if(!phases.has(phase))phases.set(phase,[]);
    phases.get(phase).push(task);
  }
  const system=project.extensions?.systemSpec;
  const units=(system?.deploymentUnits||[]).filter(unit=>!scope||unit.blocks.some(id=>scope.has(id)));
  const files={'index.html':'',...brand.files,'assets/handoff.css':brand.foundation+'\n'+handoffStyles,
    'engineering/project-package.zip':archive??await zipFiles(raw)};
  const link=(path,label)=>fileLink(path,label,files);
  const knownImages=new Map();
  const copies=[['specification.pdf','documents/solution-specification.pdf'],['spec-kit/implementation-spec.pdf','documents/implementation-plan.pdf'],['architecture.drawio','diagrams/editable-drawings.drawio']];
  for(const [from,to]of copies)if(Object.hasOwn(raw,from))files[to]=raw[from];
  const chartAudit=read(raw,'diagram-readability.json',{}),drawings=(chartAudit.pages||[]).map((page,i)=>{
    const source='diagrams/figures/'+diagramFileStem(page.name,i)+'.svg';
    const path=Object.hasOwn(raw,source)?namedFile(files,'diagrams',page.name,'.svg',raw[source]):null;
    if(path){
      knownImages.set(source,path);
      const full='diagrams/'+diagramFileStem(page.name,i)+'.svg';
      if(Object.hasOwn(raw,full))knownImages.set(full,path);
      if(!i&&Object.hasOwn(raw,'diagram.svg'))knownImages.set('diagram.svg',path);
    }
    return {...page,path};
  });
  if(!drawings.length&&nodes.length){
    const peers=new Set(edges.flatMap(e=>[e.source,e.target]));
    const vertices=allNodes.filter(n=>!scope||scope.has(n.id)||peers.has(n.id)).map(n=>({id:n.id,name:n.data.label}));
    const wires=edges.map(e=>({...e,name:e.label})),name=scope?'Module interfaces':'Component connections';
    const path=namedFile(files,'diagrams',name,'.svg',connectionFigure({name,vertices,wires}).svg);
    drawings.push({name,path,nodes:vertices.length,connections:wires.length,presentation:'connections',references:interfaces.map((r,i)=>({number:i+1,from:r.from,to:r.to,description:r.name}))});
  }
  const sourceNames=new Map((project.extensions?.designSources||[]).map(s=>[s.sha256,s.name]));
  const sourceReceipt=read(raw,'source-figures.json',null);
  const sourceRows=sourceReceipt?.figures||(project.extensions?.designSources||[]).flatMap(s=>(s.figureEvidence?.figures||[]).map(f=>({...f,sourceSha256:s.sha256})));
  const figures=sourceRows.map(row=>{
    const name=(sourceNames.get(row.sourceSha256)||'Source document')+' · '+row.id;
    const path=row.embedded&&row.exportStatus==='verified'&&row.path&&Object.hasOwn(raw,row.path)&&rasterType(raw[row.path])==='.png'?namedFile(files,'source-images',name,'.png',raw[row.path]):null;
    if(path)knownImages.set(row.path,path);
    return {name,path,reason:row.embedded&&!path?'image_bytes_unavailable':row.exportStatus||row.status||'unavailable',location:(row.locations||[]).join(', ')};
  });
  const authored=await teamDocuments(project,raw,files,namedFile,knownImages);
  const missing=figures.filter(f=>!f.path);
  const workOrders=new Map(nodes.map(n=>{
    const connections=interfaces.filter(r=>r.source===n.id||r.target===n.id);
    const related=requirements.filter(r=>r.links?.includes(n.id));
    const work=tasks.filter(t=>t.componentIds?.includes(n.id));
    return [n.id,namedFile(files,'work-orders',n.data.label,'.html',makeWorkOrder(n,connections,related,work,taskNames,project.revision))];
  }));
  const docs=read(raw,'estimate.json',{}), readiness=read(raw,'spec-kit/readiness.json',{}),moduleReadiness=read(raw,'handoff-readiness.json',{});
  const scopedFindings=(readiness.findings||[]).filter(f=>{
    if(!scope)return true;
    if(f.componentIds?.length||f.requirementIds?.length)return f.componentIds?.some(id=>scope.has(id))||f.requirementIds?.some(id=>requirementIds.has(id));
    return !f.questionId||decisions.some(d=>d.id===f.questionId);
  });
  const projectName=scope?(byId.get(focusId)||project.name):project.name;
  const goal=scope?nodes.find(n=>n.id===focusId)?.data.description:project.brief?.application||(!project.requirements?.includes('\n')&&project.requirements);
  const mappedNodes=scope?allNodes.filter(n=>scope.has(n.id)||edges.some(e=>e.source===n.id||e.target===n.id)):nodes;
  function metric(count,label,id){return '<a href="#'+id+'"><strong>'+count+'</strong><span>'+html(label)+'</span></a>';}
  const missingCount=missing.length+authored.missing.length;
  const warning=missingCount?'<p class="note">'+missingCount+' image reference'+(missingCount===1?' needs':'s need')+' attention. '+sectionLink('evidence','Review missing evidence')+'</p>':'';
  const overview=(scope?'<p class="eyebrow">Module assignment · '+html(project.name)+'</p>':'')+title(projectName,goal||'The project outcome needs definition.')+
    '<div class="stats">'+metric(nodes.length,scope?'Assigned components':'Components','build')+metric(interfaces.length,'Interfaces','diagrams')+metric(requirements.length,'Requirements','scope')+metric(open.length,'Open decisions','scope')+'</div>'+
    focusMap(mappedNodes,edges,focusId)+'<div class="section-line"><span class="case-note">Arrows follow the recorded interface direction.</span>'+sectionLink('diagrams','Explore diagrams')+'</div>'+warning+
    heading('Next decision')+(open.length?'<div class="note"><strong>'+html(open[0].question)+'</strong>'+html([open[0].owner,open[0].decisionBy].filter(Boolean).join(' · ')||'Owner needed')+'</div>':p('No open owner decisions recorded.'))+
    '<div class="cards"><div class="tile"><h3>Build the project</h3><p>Component responsibilities, work orders and dependencies.</p>'+sectionLink('build','Open build plan')+'</div><div class="tile"><h3>Verify the design</h3><p>Acceptance cases, source material and outstanding checks.</p>'+sectionLink('evidence','Review evidence')+'</div></div>';
  const designPages=new Map(review.diagrams.flatMap(type=>type.pages.map(page=>[page.id,page])));
  const diagramModel=project.extensions?.architectureDiagrams;
  const authoredPages=new Map(diagramModel?.views?.map(v=>[v.id,v]));
  const authoredElements=new Map(diagramModel?.elements?.map(e=>[e.id,e]));
  const contextDrawing=drawings.find(d=>authoredPages.get(d.id)?.kind==='context');
  const readingOrder=contextDrawing?[contextDrawing,...drawings.filter(d=>d!==contextDrawing&&authoredPages.has(d.id)),...drawings.filter(d=>!authoredPages.has(d.id))]:drawings;
  const sheet=(drawing,index)=>{
    const count=drawing.connections||0,refs=drawing.references||[];
    const findings=designPages.get(drawing.id)?.findings||[];
    const elements=(authoredPages.get(drawing.id)?.elementIds||[]).map(id=>authoredElements.get(id)).filter(Boolean);
    const graphic=drawing.path?'<label class="sizing"><input type="checkbox"> Read at original size</label><div class="drawing-frame" tabindex="0" role="region" aria-label="'+html(drawing.name)+'"><img loading="lazy" src="./'+html(drawing.path)+'" alt="'+html(drawing.name)+'"></div>':empty('Drawing file unavailable. Use the connection records below.');
    return '<details class="sheet record" name="drawing" '+(index===0?'open':'')+'><summary><strong>'+html(drawing.name)+'</strong><small>'+drawing.nodes+' elements · '+count+' connections</small></summary><div class="sheet-body">'+
      (drawing.passed===false?p('Reading view supplied. The saved layout needs review.'):'')+graphic+
      (refs.length?disclosure('Connection key',refs.length+' relationships','<ol>'+refs.map(r=>'<li><strong>'+html(r.from)+' → '+html(r.to)+'</strong> · '+html(r.description)+'</li>').join('')+'</ol>'):'')+
      (elements.length?disclosure('Element details',elements.length+' records',elements.map(e=>'<h3>'+html(e.name)+'</h3>'+fields([['Type',e.kind],['Design basis',e.basis],...e.details.map(d=>[d.name,d.value])])).join('')):'')+
      (findings.length?disclosure('Open diagram questions',findings.length+' findings',list(findings,'')):'')+
      (drawing.path?'<div class="links">'+link(drawing.path,'Open drawing')+'</div>':'')+'</div></details>';
  };
  const atlas=title('Diagrams','Follow the connections, then inspect the contract behind each interface.')+
    (readingOrder.length?readingOrder.map(sheet).join(''):focusMap(mappedNodes,edges,focusId))+
    (!scope&&system?.stateMachines?.length?heading('State transitions')+system.stateMachines.map(machine=>disclosure(machine.name,'Starts in '+machine.initial,
      '<ol>'+machine.transitions.map(step=>'<li><strong>'+html(step.from)+' → '+html(step.to)+'</strong> · '+html(step.event)+'</li>').join('')+'</ol>')).join(''):'')+
    heading('Interface contracts')+(interfaces.length?interfaces.map(r=>disclosure(r.from+' → '+r.to,r.name,
      fields(Object.entries(interfaceFields).map(([k,label])=>[label,r.contract[k]||'Needs definition']))+
      (r.pending?.length?p('Owner review needed for '+r.pending.join(', ')):'')
    )).join(''):empty('No interfaces recorded.'))+'<div class="links">'+link('diagrams/editable-drawings.drawio','Open editable drawings')+'</div>';
  const adr=(project.decisions||[]).filter(d=>!isDiagramRevision(d));
  const useCases=project.useCases||[];
  const scopePage=title('Scope & decisions')+(useCases.length?heading(scope?'Project boundaries':'Scope boundaries')+useCases.map(u=>disclosure(u.title,u.verdict,p(u.reason))).join(''):'')+heading('Requirements')+(requirements.length?requirements.map(r=>disclosure(r.statement,[r.priority,r.status,r.source==='agent'?'Proposed by Architect':null].filter(Boolean).join(' · '),fields([
    ['Acceptance',r.acceptance],['Measure',r.measure&&[r.measure.metric,r.measure.op,r.measure.target,r.measure.unit].filter(v=>v!=null).join(' ')],['Rationale',r.rationale],['Basis',r.basis],['Components',r.links?.map(id=>byId.get(id)||id).join(', ')],['Verification',r.cases.map(ref=>caseNames.get(ref.blockId+'\0'+ref.id)||ref.id).join(', ')||'Case definition needed'],
  ]))).join(''):empty('No requirements recorded.'))+
    heading('Owner decisions')+(decisions.length?decisions.map(q=>disclosure(q.question,q.status,fields([['Owner',q.owner||'Unassigned'],['Needed before',q.decisionBy],['Interim action',q.interim],['Answer',q.answer],['Affected components',q.blocks?.join(', ')]]))).join(''):empty('No owner decisions recorded.'))+
    heading(scope?'Project decision history':'Decision history')+(adr.length?adr.map(d=>disclosure(d.title||d.subject,d.status,fields([['Decision',d.decision],['Context',d.context],['Options',d.options],['Reason',d.reason],['Consequences',d.consequences],['Owner',d.owner],['Date',d.date]]))).join(''):empty('No architecture decisions recorded.'))+
    heading('Assumptions')+list((project.assumptions||[]).map(a=>a.statement+(a.owner?' — '+a.owner:'')),'No assumptions recorded.');
  const scenarios=[...(!scope?system?.journeys||[]:[]).map(s=>({...s,owner:'System journey'})),
    ...nodes.flatMap(n=>(n.data.buildSpec?.scenarios||[]).map(s=>({...s,owner:n.data.label})))];
  const build=title('Build plan',scope?'The assignment covers the selected module and its descendants.':'Start with a component work order. Check each dependency before starting its task.')+
    (!scope&&system?.decomposition?heading('Implementation approach')+p(system.decomposition):'')+
    (scenarios.length?heading('Working sequences')+scenarios.map(s=>disclosure(s.name,s.owner,'<ol>'+s.steps.map(step=>'<li><strong>'+html(step.sender)+' → '+html(step.receiver)+'</strong> · '+html(step.action)+'</li>').join('')+'</ol>')).join(''):'')+
    heading('Component work orders')+(nodes.length?'<ul class="work-index">'+nodes.map(n=>'<li><div>'+link(workOrders.get(n.id),n.data.label)+'<small>'+html(n.data.origin||'Ownership unrecorded')+'</small></div>'+p(n.data.description||'Responsibility needs definition.')+'</li>').join('')+'</ul>':empty('No components recorded.'))+
    heading('Delivery phases')+(tasks.length?p('File paths in task instructions refer to the engineering package.')+'<div class="links">'+link('engineering/project-package.zip','Engineering package')+'</div>'+
      [...phases].map(([phase,rows])=>disclosure(phase,rows.length+(rows.length===1?' task':' tasks'),rows.map(t=>disclosure(t.title,t.status,
        fields([['Depends on',t.dependsOn?.map(id=>taskNames.get(id)||id).join(', ')||'No preceding task'],['Completion criteria',t.acceptance?.join('\n')]])+list(t.steps||[],'No steps recorded.'))).join(''))).join(''):empty('No build tasks recorded.'));
  const controls=requirements.filter(r=>['security','compliance'].includes(r.category));
  const operations=title('Operations & cost')+(!scope&&system?heading('Deployment and recovery')+fields([['Infrastructure',system.infrastructure],['Operating model',system.operations]]):'')+
    (units.length?heading('Deployment units')+units.map(unit=>disclosure(unit.name,unit.placement,fields([['Components',unit.blocks.map(id=>byId.get(id)||id).join(', ')]]))).join(''):'')+
    heading('Operating procedures')+(nodes.filter(n=>n.data.buildSpec?.operations||n.data.buildSpec?.failures).map(n=>disclosure(n.data.label,'Runbook',fields([['Operations',n.data.buildSpec.operations],['Failure and recovery',n.data.buildSpec.failures],['Infrastructure',n.data.buildSpec.infrastructure]]))).join('')||empty('Operating and recovery procedures need definition.'))+
    heading('Security and privacy')+(controls.length?controls.map(r=>disclosure(r.statement,r.category,fields([['Acceptance',r.acceptance||'Needs definition'],['Responsible components',r.links?.map(id=>byId.get(id)||id).join(', ')]]))).join(''):empty('No security or compliance requirements recorded.'))+
    heading(scope?'Project cost assumptions':'Cost assumptions')+'<div class="cards"><div class="tile"><h3>Monthly operating cost</h3><p>'+html(money(docs.cloud))+'</p></div><div class="tile"><h3>One-time delivery cost</h3><p>'+html(money(docs.consulting))+'</p></div></div>'+
    (docs.cloud?.gaps?.length?disclosure('Unpriced or incomplete items',docs.cloud.gaps.length+' items',list(docs.cloud.gaps,'')):'')+
    (docs.cloud?.lines?.length?disclosure('Recurring charges',docs.cloud.maturity,fields(docs.cloud.lines.map(line=>{
      const quantity=line.quantity==null?'':[line.quantity.toLocaleString('en',{maximumFractionDigits:6}),line.unit].filter(Boolean).join(' ');
      const price=line.cost==null?line.status:[line.price?.currency,line.cost.toLocaleString('en',{maximumFractionDigits:2})].filter(value=>value!=null).join(' ');
      return [line.component+' · '+line.driver,[quantity,price].filter(Boolean).join(' · ')];
    }))):'')+
    (docs.consulting?.lines?.length?disclosure('Delivery effort','One-time work',fields(docs.consulting.lines.map(l=>[l.label,l.complete?l.days+' days · '+docs.consulting.currency+' '+l.expected:'Estimate needed']))):'');
  const checks=cases.map(c=>disclosure(c.name,[c.blockName,c.category].filter(Boolean).join(' · '),fields(['environment','setup','input','action','expected','evidence'].map(k=>[k[0].toUpperCase()+k.slice(1),c[k]])))).join('');
  const sourceList=sourceLinks(project);
  const receipts=['design-evidence.json','captured-evidence.json','terraform/validation-receipt.json'].filter(path=>Object.hasOwn(raw,path));
  const evidence=title('Evidence & checks','Case definitions describe what to test. Execution requires a result tied to this revision.')+
    (!scope&&system?.testing?heading('Test strategy')+p(system.testing):'')+
    (captureRelation?p('Captured workspace · '+captureRelation.replaceAll('_',' ')):'')+
    heading('Acceptance cases')+(checks||empty('No acceptance cases recorded.'))+
    heading('Readiness')+fields(Object.entries(readiness.stages||{}).map(([k,v])=>[k.replace(/([a-z])([A-Z])/g,'$1 $2'),String(v).replaceAll('_',' ')]))+
    (moduleReadiness.status?p('Module status · '+moduleReadiness.status.replaceAll('_',' ')):'')+
    (scopedFindings.length?disclosure('Outstanding engineering findings',scopedFindings.length+' items','<ul>'+scopedFindings.map(f=>'<li><strong>'+html(f.message)+'</strong> '+html(f.action)+'</li>').join('')+'</ul>'):'')+
    (receipts.length?heading('Recorded receipts')+fields(receipts.map(path=>{const r=read(raw,path,{});return [path,r.status||r.state||'Included in the engineering package'];})): '')+
    heading('Source images')+(figures.length?figures.map(f=>f.path?'<figure><figcaption>'+html([f.name,f.location].filter(Boolean).join(' · '))+'</figcaption><img class="source-image" loading="lazy" src="./'+html(f.path)+'" alt="'+html(f.name)+'"></figure>':'<div class="note"><strong>'+html(f.name)+'</strong>Unavailable · '+html(f.reason.replaceAll('_',' '))+'. Restore the original source in Architect and export again.</div>').join(''):!authored.displayed&&!authored.missing.length?p('No source images referenced.'):'')+
    (authored.displayed?p(authored.displayed+' image references resolved in the source documents.'):'')+
    (authored.missing.length?heading('Images referenced by documents')+authored.missing.map(f=>disclosure(f.name,f.reason,fields([['Document',f.document],['Reference',f.reference],['Next step','Supply the original image alongside its document and regenerate the handoff.']]))).join(''):'')+
    (sourceList?heading('Design sources')+'<ul>'+sourceList+'</ul>':'');
  const library=title('Project files','Open individual documents here. The engineering package contains the editable snapshot, original paths and recorded evidence.')+
    '<div class="cards"><div class="tile"><h3>Engineering package</h3><p>Extract the ZIP and open its start guide.</p>'+link('engineering/project-package.zip','Download engineering package')+'</div></div>'+
    (files['documents/solution-specification.pdf']?heading('Specifications')+'<div class="links">'+link('documents/solution-specification.pdf','Solution specification')+link('documents/implementation-plan.pdf','Implementation plan')+'</div>':'')+
    (authored.guides.length?heading('Source documents')+'<div class="links">'+authored.guides.map(g=>link(g.path,g.name)).join('')+'</div>':'')+
    heading('Work orders')+'<div class="links">'+nodes.map(n=>link(workOrders.get(n.id),n.data.label)).join('')+'</div>';
  files['index.html']=websiteShell({title:'Team handoff',name:projectName,revision:project.revision,sections:[
    {id:'overview',label:'Overview',glyph:'overview',body:overview},{id:'diagrams',label:'Diagrams',glyph:'diagrams',body:atlas},{id:'scope',label:'Scope & decisions',glyph:'scope',body:scopePage},{id:'build',label:'Build plan',glyph:'build',body:build},{id:'operations',label:'Operations & cost',glyph:'operations',body:operations},{id:'evidence',label:'Evidence & checks',glyph:'evidence',body:evidence},{id:'files',label:'Project files',glyph:'files',body:library},
  ]});
  verifyTeamLinks(files);
  return files;
}
