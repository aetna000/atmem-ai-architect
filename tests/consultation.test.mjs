import test from 'node:test';
import assert from 'node:assert/strict';
import {withDerived} from '../src/derive.mjs';
import {applyDecisionUpdates,applyRequirementDrafts,proposeCommentRevisions,resolveCommentRevision} from '../src/consultation.mjs';
import {applyPriceQuotes,storageNodes} from '../src/pricing.mjs';
import {estimate,setPrice} from '../src/estimate.mjs';
const node=(id,label,provider='tools',kind='source')=>({id,type:'resource',position:{x:0,y:0},data:{label,description:label,provider,kind,config:{region:{aws:'ap-southeast-2',azure:'australiaeast',gcp:'australia-southeast1',ibm:'au-syd'}[provider]||'To be selected',classification:'Internal'}}});
const project=()=>({version:1,revision:1,name:'HR assistant',provider:'tools',nodes:[node('files','Policy files'),node('agent','Answers policy questions','tools','agent')],edges:[]});
test('derive a small grounded set without arbitrary SLA targets or company policy claims',()=>{
 const p=withDerived(project());assert.ok(p.needs.length>0&&p.needs.length<10);assert.ok(p.needs.length<=2);assert.ok(p.needs.every(r=>r.rationale&&r.basis));assert.ok(p.needs.every(r=>r.source==='agent'&&r.status==='open'));assert.ok(p.needs.every(r=>!r.measure));assert.ok(!JSON.stringify(p).includes('99.5'));
 const empty=withDerived({...p,nodes:[]});assert.equal(empty.needs.length,0);
});
test('confirmed conversation requirements and dismissed proposals survive diagram edits',()=>{
 let p=withDerived(project());const r=p.needs[0];p.needs[0]={...r,source:'user',statement:'Only HR may access these documents'};p=withDerived(p);assert.equal(p.needs.find(x=>x.id===r.id).statement,'Only HR may access these documents');
 p.extensions={dismissedRequirements:['drv-data-location']};p=withDerived(p);assert.ok(!p.needs.some(x=>x.id==='drv-data-location'));
});
test('explicit cloud decisions supersede with a reason; unsupported quotes do not become choices',()=>{
 let p=applyDecisionUpdates(project(),[{subject:'platform.cloud',value:'aws',sourceText:'Use AWS'}],'Use AWS');
 p=applyDecisionUpdates(p,[{subject:'platform.cloud',value:'azure',sourceText:'Use Azure'}],'Use Azure');
 assert.equal(p.decisions.filter(d=>d.status==='Accepted').length,1);assert.equal(p.decisions[0].status,'Superseded');assert.equal(p.decisions[1].supersedes,p.decisions[0].id);
 assert.equal(applyDecisionUpdates(p,[{subject:'cloud.region',value:'us-east-1',sourceText:'unspoken'}],'hello').decisions.length,2);
});
test('all four cloud storage nodes participate; verified quotes apply only to matching provider and region',()=>{
 let p=project();p.nodes=[node('a','Amazon S3','aws'),node('b','Azure Blob Storage','azure'),node('c','Google Cloud Storage','gcp'),node('d','IBM Cloud Object Storage','ibm')];assert.equal(storageNodes(p).length,4);
 p=applyPriceQuotes(p,[{provider:'azure',region:'australiaeast',price:.02,currency:'USD',unit:'GB-month',source:'Azure Retail Prices API',url:'https://prices.azure.com/test',date:'2026-11-05',service:'Blob fixture meter',tierLimit:51200,coverage:'Synthetic test'}]);
 assert.equal(p.estimate.prices.b.price,.02);assert.equal(p.estimate.prices.a,undefined);assert.equal(p.estimate.prices.d,undefined);
 p.estimate.usage={data_gb:60000};assert.equal(estimate(p).lines.find(l=>l.id==='b').cost,null,'base tier cannot be extrapolated beyond coverage');
});

test('editing a retrieved rate clears its vendor provenance and tier claim',()=>{
 const p={...project(),estimate:{prices:{files:{price:.02,source:'Azure Retail Prices API',url:'https://prices.azure.com/test',tierLimit:51200,note:'Verified public tier',currency:'USD'}}}};
 const changed=setPrice(p,'files',{price:.03}).estimate.prices.files;
 assert.equal(changed.source,'entered by you');assert.equal(changed.url,undefined);assert.equal(changed.tierLimit,undefined);
});

test('model requirements replace fallback labels, link real components and preserve confirmed answers',()=>{
 let p=withDerived(project());
 const draft={id:'ai-access',statement:'Enforce document access permissions before retrieval.',kind:'nonfunctional',category:'security',priority:'must',links:['files','missing']};
 p=withDerived(applyRequirementDrafts(p,[draft]));assert.equal(p.needs.length,1);assert.deepEqual(p.needs[0].links,['files']);assert.equal(p.needs[0].source,'agent');assert.equal(p.needs[0].status,'open');
 p.needs[0]={...p.needs[0],source:'user',statement:'Only HR can retrieve documents'};
 p=withDerived(applyRequirementDrafts(p,[draft]));assert.equal(p.needs[0].statement,'Only HR can retrieve documents');
});

test('requirement numbers remain stable across revisions, reorder and saved project round trip',async()=>{
 const {toProjectFile,fromProjectFile}=await import('../src/project-file.mjs');
 let p=withDerived(project());const numbers={...p.extensions.requirementNumbers};
 p=withDerived({...p,nodes:[...p.nodes].reverse()});for(const r of p.needs)assert.equal(p.extensions.requirementNumbers[r.id],numbers[r.id]);
 const previousMax=Math.max(...Object.values(numbers));p=withDerived(applyRequirementDrafts(p,[{id:'ai-audit',statement:'Record access decisions for audit',kind:'nonfunctional',category:'security',links:['files']}]));
 assert.ok(p.extensions.requirementNumbers['ai-audit']>previousMax);
 assert.deepEqual(fromProjectFile(toProjectFile(p)).project.extensions.requirementNumbers,p.extensions.requirementNumbers);
 const {recordsSection}=await import("../src/pack.mjs");assert.ok(recordsSection(p).includes(`REQ-${String(p.extensions.requirementNumbers["ai-audit"]).padStart(3,"0")}`));
});

test('feedback proposals require acceptance, preserve history and reject stale or removed comments',()=>{
 let p=withDerived(project());const id=p.needs[0].id,before=p.needs[0].statement;
 const comment={id:'c1',requirementId:id,text:'Only managers',status:'open'};
 p.extensions.requirementComments=[comment];const snapshot=structuredClone(p);
 const updates=[{id,statement:'Only managers may access documents',sourceText:comment.text,rationale:'Limit access to the named group'}];
 let proposed=proposeCommentRevisions(p,snapshot,updates);
 assert.equal(proposed.needs[0].statement,before);assert.equal(proposed.extensions.requirementComments[0].status,'proposed');
 const dismissed=resolveCommentRevision(proposed,'c1',false);assert.equal(dismissed.needs[0].statement,before);assert.equal(dismissed.extensions.requirementComments[0].status,'dismissed');
 const applied=resolveCommentRevision(proposed,'c1',true);assert.equal(applied.needs[0].statement,updates[0].statement);assert.equal(applied.extensions.requirementComments[0].before,before);assert.equal(applied.extensions.requirementComments[0].status,'reviewed');
 proposed.needs[0]={...proposed.needs[0],statement:'Newer user choice'};
 const stale=resolveCommentRevision(proposed,'c1',true);assert.equal(stale.needs[0].statement,'Newer user choice');assert.equal(stale.extensions.requirementComments[0].status,'open');
 const removed={...p,extensions:{...p.extensions,requirementComments:[]}};assert.equal(proposeCommentRevisions(removed,snapshot,updates).extensions.requirementComments.length,0);
});
