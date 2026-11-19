import test from 'node:test';
import assert from 'node:assert/strict';
import {zipSync,strToU8} from 'fflate';
import {captureDesignDocuments,designDocumentFiles,isDesignDocument} from '../src/design-documents.mjs';
import {canvasProposal,CANVAS_ARTIFACT} from '../src/codex-canvas.mjs';
import {toProjectFile,fromProjectFile} from '../src/project-file.mjs';
import {deliveryPack} from '../src/delivery.mjs';
import {appliedQualityBasis,systemSpecFiles} from '../src/canvas-quality.mjs';

const source='a'.repeat(64),context='b'.repeat(64);
const project={id:'theatre-design',version:1,revision:1,name:'Theatre',provider:'tools',nodes:[],edges:[],
  extensions:{designSources:[{name:'brief.txt',sha256:source,text:'Reserve a seat once.'}]}};

test('authored subsystem briefs survive captured canvas, project reopening and handoff without byte changes',()=>{
  const draft={version:1,baseRevision:1,sourceSlots:[1],title:'Reservations',addNodes:[{id:'holds',type:'resource',position:{x:0,y:0},data:{label:'Seat holds',provider:'tools',kind:'resource',origin:'proposed',buildSpec:{implementation:'Follow specs/reservations/plan.md.'}}}],addEdges:[],
    requirements:[{id:'reserve-once',statement:'Reserve a seat once.',sourceSlot:1,reference:'Section 1',links:['holds']}]};
  const plan='# Reservation plan\n\nUse an atomic ledger and independently race the final seat.\n';
  const proposal=canvasProposal(project,zipSync({[CANVAS_ARTIFACT]:strToU8(JSON.stringify(draft)),
    'specs/reservations/plan.md':strToU8(plan),'README.md':strToU8('[Reservation plan](specs/reservations/plan.md)'),
    'architecture.coverage.md':strToU8('Section 1 maps to holds.'),'private-key.bin':strToU8('Excluded binary')}),'artifact',context);
  const saved={...proposal.next,needs:proposal.sourceRequirements,extensions:{...project.extensions,architectureDocuments:proposal.designDocuments}};
  const reopened=fromProjectFile(toProjectFile(saved)).project;
  const files=deliveryPack(reopened,null);
  assert.equal(files['specs/reservations/plan.md'],plan);
  assert.equal(files['NATIVE_DESIGN.md'],'[Reservation plan](specs/reservations/plan.md)');
  assert.equal(files['private-key.bin'],undefined);
  assert.match(files['START_HERE.md'],/Captured source design/);
  assert.ok(JSON.parse(files['manifest.json']).files.includes('specs/reservations/plan.md'));
  assert.equal(JSON.parse(files['design-documents-receipt.json']).contextSha256,context);
  const before=appliedQualityBasis(reopened);
  reopened.extensions.architectureDocuments.files[0].content+='changed';
  assert.notEqual(appliedQualityBasis(reopened),before);
  assert.throws(()=>toProjectFile(reopened),/integrity/);
});

test('retained documents cannot install instructions, traverse paths or silently truncate large briefs',()=>{
  for(const path of ['../specs/plan.md','specs/../plan.md','/docs/plan.md','docs/AGENTS.md','docs/agents.md','docs/CON.md','docs/.agents/SKILL.md','docs/script.js'])assert.equal(isDesignDocument(path),false);
  const receipt=captureDesignDocuments({'docs/plan.md':strToU8('Plan')},'artifact','a'.repeat(64),context);
  const duplicate={...receipt,files:[...receipt.files,...receipt.files]};
  assert.throws(()=>designDocumentFiles(duplicate),/duplicate/);
  assert.throws(()=>captureDesignDocuments({'docs/plan.md':new Uint8Array(250001)},'artifact','a'.repeat(64),context),/bound/);
  assert.throws(()=>captureDesignDocuments({'docs/plan.md':new Uint8Array([255])},'artifact','a'.repeat(64),context));
  const bom=strToU8('\ufeffWindows brief\r\n');
  const retained=captureDesignDocuments({'docs/bom.md':bom},'artifact','a'.repeat(64),context);
  assert.deepEqual(strToU8(designDocumentFiles(retained)['docs/bom.md']),bom);
});

test('older structural scores cannot mark unparsed authored diagrams ready',()=>{
  const documents=captureDesignDocuments({'specs/plan.md':strToU8('```mermaid\nflowchart LR\nA-->B\n```')},'artifact','a'.repeat(64),context);
  const p={...project,extensions:{...project.extensions,architectureDocuments:documents,
    architectureDraftQuality:{ready:true,score:99,gates:{}}}};
  p.extensions.architectureDraftQuality.appliedBasis=appliedQualityBasis(p);
  const result=JSON.parse(systemSpecFiles(p,'fixture')['spec-kit/architecture-coverage.json']);
  assert.equal(result.ready,false);assert.equal(result.status,'authored_diagrams_pending');
});
