import test from 'node:test';
import assert from 'node:assert/strict';
import {zipSync,strToU8} from 'fflate';
import {sha256} from '@noble/hashes/sha2.js';
import {canvasProposal,canvasBasis,canvasProposalRecords} from '../src/codex-canvas.mjs';
import {validateAmendmentHistory,appendAmendment,amendCanvasGraph} from '../src/canvas-amendments.mjs';
import {toProjectFile,fromProjectFile} from '../src/project-file.mjs';
import {deliveryPack} from '../src/delivery.mjs';
import {appliedQualityBasis,systemSpecFiles} from '../src/canvas-quality.mjs';
import {proposalDiff} from '../src/levels.mjs';
const hash=bytes=>Array.from(sha256(bytes),b=>b.toString(16).padStart(2,'0')).join('');
const source='a'.repeat(64),second='c'.repeat(64),context='b'.repeat(64);
const scenario={name:'Replay',steps:[{sender:'Client',receiver:'Ledger',action:'Retry with the same key'}]};
const spec={inputs:'Request key',outputs:'Stored receipt',behavior:'One effect per key',failures:'Recover prior receipt',
 implementation:'Transactional ledger',infrastructure:'Portable database',operations:'Backup and restore',tests:'Concurrent replay produces one effect',scenarios:[scenario,{...scenario,name:'Recovery'}]};
const node=(id,parent)=>({id,type:'resource',position:{x:70,y:90},data:{label:id,provider:'tools',kind:'resource',origin:'proposed',
 buildSpec:spec,...(parent?{parentBlockId:parent}:{})}});
const contract={transport:'Command',input:'Key',output:'Receipt',authorization:'Worker',failure:'Retry same key',verification:'Replay concurrently'};
const project={id:'laboratory',name:'Laboratory sample custody',version:1,revision:4,provider:'tools',
 nodes:[node('lab'),{...node('ledger','lab'),data:{...node('ledger','lab').data,origin:'existing',provider:'azure',service:'Existing ledger',deploymentMode:'reference',config:{region:'australiaeast',classification:'Restricted',customSetting:'Preserve'}}}],
 edges:[{id:'register',source:'lab',target:'ledger',label:'Register sample',interfaceSpec:contract}],
 needs:[{id:'once',statement:'Register a sample once.',acceptance:'Concurrent replay produces one durable receipt.',kind:'nonfunctional',priority:'must',status:'met',source:'user',links:['ledger'],rationale:'Accepted laboratory policy',basis:'Owner approved policy'}],
 decisions:[{id:'adr-one',title:'Keep existing ledger',decision:'Preserve the ledger and site placement.',status:'Accepted'}],openQuestions:[],
 extensions:{designSources:[{name:'Lab brief.txt',sha256:source,text:'1. Register samples once.'},{name:'Scanner interface.txt',sha256:second,text:'2. Replay scan acknowledgements after link recovery.'}],
 systemSpec:{title:'Laboratory custody',decomposition:'Site ledger and scanners',infrastructure:'Keep site data',operations:'Backup and restore',testing:'Concurrent recovery',journeys:[scenario,{...scenario,name:'Recovery'}],
 stateMachines:[{name:'Sample',states:['New','Registered'],initial:'New',transitions:[{from:'New',to:'Registered',event:'Sample registered'}]}],
 deploymentUnits:[{name:'Laboratory',placement:'on-prem',blocks:['lab','ledger']}]}}};
const draft={version:1,baseRevision:4,title:'Scanner recovery',sourceSlots:[1,2],addNodes:[],addEdges:[],requirements:[],
 updateNodes:[{id:'ledger',data:{buildSpec:{failures:'Read the durable receipt after the scanner link returns.'}}}],
 updateEdges:[{id:'register',interfaceSpec:{verification:'Disconnect after commit, then replay the same sample key.'}}],
 requirementCoverage:[{id:'once',sourceSlot:1,reference:'1. Registration',links:['ledger']},{id:'once',sourceSlot:2,reference:'2. Recovery',links:['ledger']}]};
function archive(value,docs={}){
 const bytes=strToU8(JSON.stringify(value));
 return zipSync({'architecture.canvas.json':bytes,'architecture.review.md':strToU8('Draft SHA-256: '+hash(bytes)),...Object.fromEntries(Object.entries(docs).map(([p,v])=>[p,strToU8(v)]))});
}
const propose=(value=draft,p=project)=>canvasProposal(p,archive(value),'artifact-2',context);
const apply=(p,proposal)=>({...proposal.next,...canvasProposalRecords(p,proposal),revision:p.revision+1});

test('source-backed updates refine existing blocks and contracts while preserving identity, runtime, ownership and accepted scope',()=>{
 const before=structuredClone(project),proposal=propose(),result=apply(project,proposal);
 assert.equal(result.nodes.length,2);assert.equal(result.edges.length,1);
 const old=project.nodes[1],changed=result.nodes[1];
 assert.deepEqual(changed,{...old,data:{...old.data,buildSpec:{...old.data.buildSpec,failures:draft.updateNodes[0].data.buildSpec.failures}}});
 assert.deepEqual(result.edges[0],{...project.edges[0],interfaceSpec:{...contract,verification:draft.updateEdges[0].interfaceSpec.verification}});
 assert.deepEqual(result.needs,project.needs);assert.deepEqual(result.decisions,project.decisions);
 assert.deepEqual(result.extensions.systemSpec,project.extensions.systemSpec);assert.deepEqual(project,before);
 assert.equal(proposal.quality.score,100);assert.equal(proposal.quality.ready,true);
 assert.deepEqual(proposalDiff(project,result).changed,['ledger']);
 const receipt=result.extensions.architectureAmendments[0];
 assert.deepEqual(receipt.changes[0].before,old);assert.deepEqual(receipt.changes[0].after,changed);
 assert.equal(receipt.contextSha256,context);assert.equal(receipt.coverage.length,2);
});

test('a new module receives existing requirement allocations without duplicating or rewriting that requirement',()=>{
 const value={...draft,addNodes:[node('scanner','lab')],addEdges:[{id:'scan',source:'scanner',target:'ledger',label:'Scan sample',interfaceSpec:contract}],
 requirementCoverage:[...draft.requirementCoverage,{id:'once',sourceSlot:2,reference:'2. Recovery',links:['scanner','ledger']}]};
 const result=apply(project,propose(value));
 assert.deepEqual(result.needs,[{...project.needs[0],links:['ledger','scanner']}]);
 assert.equal(result.nodes[2].data.parentBlockId,'lab');
 assert.equal(result.extensions.architectureAmendments[0].coverage[2].sourceSha256,second);
});

test('amendments reject ownership changes, deletion, requirement rewrites and interface endpoint changes instead of ignoring them',()=>{
 for(const field of ['removeNodes','removeEdges','updateRequirements','removeRequirements','needs','decisions','provider']){
  assert.throws(()=>propose({...draft,[field]:[]}),/cannot remove scope/);
 }
 for(const field of ['provider','origin','config','label','service','deploymentMode','approvalProfile','implementation']){
  assert.throws(()=>propose({...draft,updateNodes:[{id:'ledger',data:{[field]:'changed'}}]}),/Unsupported.*fields/);
 }
 assert.throws(()=>propose({...draft,updateEdges:[{id:'register',target:'lab',interfaceSpec:contract}]}),/Unsupported/);
 assert.throws(()=>propose({...draft,requirementCoverage:[{...draft.requirementCoverage[0],statement:'Erase policy'}]}),/coverage needs/);
 assert.throws(()=>propose({...draft,requirements:[{...project.needs[0],sourceSlot:2,reference:'Replacement'}]}),/unique ID/);
 assert.throws(()=>propose({...draft,systemSpec:null}),/cannot clear/);
});

test('invalid identities, contracts, partial clears and cyclic nesting fail without touching the saved design',()=>{
 const before=structuredClone(project);
 for(const updateNodes of [[{id:'unknown',data:{description:'Unknown'}}],[draft.updateNodes[0],draft.updateNodes[0]],
  [{id:'ledger',data:{buildSpec:null}}],[{id:'ledger',data:{buildSpec:{tests:''}}}],[{id:'ledger',data:{}}],
  [{id:'lab',data:{parentBlockId:'ledger'}}]])assert.throws(()=>propose({...draft,updateNodes}));
 for(const updateEdges of [[{id:'unknown',interfaceSpec:contract}],[draft.updateEdges[0],draft.updateEdges[0]],[{id:'register',interfaceSpec:{failure:''}}]])assert.throws(()=>propose({...draft,updateEdges}));
 assert.throws(()=>propose({...draft,addNodes:[node('ledger')]}),/Invalid component/);
 assert.throws(()=>propose({...draft,requirementCoverage:[{id:'unknown',sourceSlot:1,reference:'1',links:['ledger']}]}),/coverage needs/);
 assert.throws(()=>propose({...draft,requirementCoverage:[{...draft.requirementCoverage[0],sourceSlot:3}]}),/coverage needs/);
 assert.deepEqual(project,before);
});

test('each source must be traced anew, and pure updates are assessed against the complete retained graph',()=>{
 assert.equal(propose({...draft,requirementCoverage:[draft.requirementCoverage[0]]}).quality.ready,false);
 assert.equal(propose({...draft,requirementCoverage:[]}).quality.gates.allSourcesTraced,false);
 assert.equal(propose().quality.gates.interfaceContracts,true);
 const changed={...project,nodes:project.nodes.map(n=>n.id==='ledger'?{...n,data:{...n.data,description:'Changed without bumping revision'}}:n)};
 assert.notEqual(canvasBasis(changed),canvasBasis(project));
});

test('amendment history and source allocations survive project reopening and normal handoff with evidence invalidation',()=>{
 const result=apply(project,propose({...draft,addNodes:[node('scanner','lab')],requirementCoverage:draft.requirementCoverage.map(row=>({...row,links:['ledger','scanner']}))}));
 result.extensions.architectureDraftQuality={...propose().quality,appliedBasis:appliedQualityBasis(result)};
 const reopened=fromProjectFile(toProjectFile(result)).project;
 assert.deepEqual(reopened.extensions.architectureAmendments,result.extensions.architectureAmendments);
 assert.deepEqual(reopened.needs[0].links,['ledger','scanner']);assert.equal(reopened.needs[0].status,'met');
 const files=deliveryPack(reopened,null),receipt=JSON.parse(files['spec-kit/architecture-amendments.json']);
 assert.deepEqual(receipt.revisions,result.extensions.architectureAmendments);
 const before=appliedQualityBasis(reopened);reopened.extensions.architectureAmendments[0].coverage[0].reference='Different evidence';
 assert.notEqual(appliedQualityBasis(reopened),before);
 assert.equal(JSON.parse(systemSpecFiles(reopened,'fixture')['spec-kit/architecture-coverage.json']).status,'stale');
});

test('subsequent updates retain prior authored document identities and reject nonmonotonic history',()=>{
 const first=canvasProposal(project,archive(draft,{'specs/custody/plan.md':'# Preserve site ledger\n'}),'artifact-2',context);
 const current=apply(project,first),value={...draft,baseRevision:5};
 const secondProposal=canvasProposal(current,archive(value,{'specs/custody/plan.md':'# Preserve site ledger and scanner replay\n'}),'artifact-3',context);
 const receipt=secondProposal.amendmentHistory[1];
 assert.equal(receipt.previousDocuments.artifactId,'artifact-2');
 assert.equal(receipt.previousDocuments.files.find(f=>f.path==='specs/custody/plan.md').sha256,hash(strToU8('# Preserve site ledger\n')));
 assert.throws(()=>validateAmendmentHistory([receipt,receipt]),/invalid/);
 assert.throws(()=>validateAmendmentHistory(Array(41).fill(receipt)),/receiving bound/);
 assert.throws(()=>toProjectFile({...current,extensions:{...current.extensions,architectureAmendments:[{...receipt,changes:['x'.repeat(500001)]}]}}),/receiving bound/);
});

test('source-backed gate allocations add blockers without rewriting questions or reusing an old answer',()=>{
 const gate={id:'peer-qualification',question:'Approve scanner protocol and custody policy.',owner:'Laboratory owner',status:'open',links:['lab'],requirementIds:[],interim:'Keep scanner disabled.'};
 const p={...project,openQuestions:[gate]},allocation={id:gate.id,sourceSlot:2,reference:'2. Recovery',requirementIds:['once'],interfaceIds:['register'],links:['ledger']};
 const value={...draft,questionCoverage:[allocation]},proposal=propose(value,p),result=apply(p,proposal);
 assert.deepEqual(result.openQuestions,[{...gate,links:['lab','ledger'],requirementIds:['once'],interfaceIds:['register']}]);
 assert.deepEqual(p.openQuestions,[gate]);assert.equal(proposal.amendmentHistory.at(-1).changes.find(c=>c.kind==='questionCoverage').sourceSha256,second);
 for(const bad of [{...allocation,owner:'Changed owner'},{...allocation,question:'Changed scope'},{...allocation,requirementIds:['foreign']},{...allocation,interfaceIds:['unknown']},{...allocation,sourceSlot:99}])assert.throws(()=>propose({...draft,questionCoverage:[bad]},p));
 assert.throws(()=>propose(value,{...p,openQuestions:[{...gate,status:'answered',answer:'Approved for the original scope'}]}),/unanswered/);
 assert.throws(()=>propose({...draft,questionCoverage:[allocation,allocation]},p),/one unanswered/);
});
test('a rejected case removal identifies the exact module and missing IDs for repair without discarding the original',()=>{
 const p=structuredClone(project);p.nodes[1].data.buildSpec.verificationCases=[{id:'scanner-disconnect'}];
 assert.throws(()=>amendCanvasGraph(p,{...draft,updateNodes:[{id:'ledger',data:{buildSpec:{verificationCases:[]}}}]}),e=>{
  assert.deepEqual(JSON.parse(e.canvasDiagnostic),{code:'verification_case_removal',blockId:'ledger',caseIds:['scanner-disconnect']});return /cannot silently remove/.test(e.message);
 });
 assert.deepEqual(p.nodes[1].data.buildSpec.verificationCases,[{id:'scanner-disconnect'}]);
});

test('large laboratory and payment amendments retain verifiable before/after references without duplicating captured specifications',()=>{
 const prior=propose().amendmentHistory;
 for(const [kind,id,collection,updates] of [['block','ledger','nodes','updateNodes'],['interface','payment-contract','edges','updateEdges']]){
  const before={id,specification:'Original evidence '.repeat(20_000)},after={...before,specification:'Refined evidence '.repeat(25_000)};
  const receipt={...prior[0],baseRevision:5,artifactId:'new-artifact',changes:[{kind,id,before,after}]};
  const p={...project,extensions:{...project.extensions,architectureAmendments:prior}};
  const history=appendAmendment(p,receipt),change=history[1].changes[0];
  assert.deepEqual(history[0],prior[0]);assert.deepEqual(p.extensions.architectureAmendments,prior);
  assert.ok(JSON.stringify(history).length<10_000);
  assert.equal(change.beforeRef.sha256,hash(strToU8(JSON.stringify(before))));
  assert.equal(change.afterRef.sha256,hash(strToU8(JSON.stringify(after))));
  assert.equal(change.beforeRef.collection,'design.'+collection);assert.equal(change.afterRef.collection,updates);
  assert.equal(change.afterRef.mode,'merge-with-before');assert.equal(change.afterRef.artifactId,'new-artifact');
  assert.equal(change.beforeRef.contextSha256,context);
  for(const bad of [{beforeRef:{...change.beforeRef,contextSha256:'c'.repeat(64)}},{afterRef:{...change.afterRef,id:'another-record'}},{after}]){
   assert.throws(()=>validateAmendmentHistory([history[0],{...history[1],changes:[{...change,...bad}]}]),/invalid/);
  }
  assert.throws(()=>appendAmendment(project,{...receipt,contextSha256:null}),e=>e.hostStorageBound===true&&/receiving bound/.test(e.message));
 }
});
