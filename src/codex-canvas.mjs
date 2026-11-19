import {validateVerificationReferences} from './verification-cases.mjs';
import {sha256} from '@noble/hashes/sha2.js';
import {architectureQuality,readSystemSpec} from './canvas-quality.mjs';
import {unzipSync,strFromU8} from 'fflate';
import {validateImport} from './core.mjs';
import {findCredentials} from './project-file.mjs';
import {newQuestion,newRequirement} from './records.mjs';
import {captureDesignDocuments,isDesignDocument} from './design-documents.mjs';
import {amendCanvasGraph,allocateRequirements,appendAmendment} from './canvas-amendments.mjs';
import {reconcileEngineeringModel} from './engineering-model.mjs';
import {reconcileSystemModel} from './system-model.mjs';

const CANVAS_WRITE_BOUNDS = 'Canvas limits: each block spec section allows 4000 Unicode code points. If a block has no scenario, omit buildSpec.scenarios. Otherwise include 1–24 named scenarios; each scenario has 1–30 ordered steps, names and participants up to 150 code points, and actions up to 400 code points. When systemSpec is supplied, journeys must contain 1–40 scenarios with the same step bounds. Split a long journey into linked, named scenarios while retaining every operation in the full authored diagrams and specification. Never discard scope to fit a canvas field. System summary sections allow 6000 UTF-16 code units. Each deployment unit name and placement allows 150 UTF-16 code units and blocks must reference 1–100 existing node IDs. Keep complete placement rationale in systemSpec.infrastructure and specs/ documents; never truncate it. For every new or refined scenario step, declare messageKind (command, event, query or result), bind represented participants using senderBlockId and receiverBlockId, and declare interfaceId and requirementIds where applicable. Leave unresolved classification or external participant binding explicit for review; do not manufacture facts or references. Use exact existing or proposed IDs, not display labels. For modeled calls, declare operationId referring to the receiving class operation; results refer to that same operation owned by their sender. Preserve unresolved legacy links for review rather than guessing. Bind cross-block interactions to the declared interface; a result follows its request interface in reverse. Events describe facts that occurred, not instructions to act. Preserve unclassified legacy interactions until their source semantics are reviewed. Trace journey steps to existing requirement IDs. Never invent a reference or classify a message from its name alone.';

export const CANVAS_ARTIFACT = 'architecture.canvas.json';
export const CANVAS_REVIEW = 'architecture.review.md';
const MAX_CANVAS_ARTIFACT_BYTES = 2_000_000;
const ENGINEERING_MODEL_AUTHORING = 'At each design/refinement, read the current modeling-grammar through atmem_reference_read and follow digest-pinned pages when supplied. Preserve creation-pinned workspace resources unchanged. Provide responsibility descriptions for assigned implementation-bearing types and reconcile signatures, authorization context, nullability, cardinality and result shapes with interfaces and data records. For each implementation module, populate buildSpec.verificationCases using the per-module contract in the same grammar: concrete environment, setup, input, action, expected and evidence with requirement links. Include nominal, denial, failure/recovery and relevant concurrency cases. These specify tests, never executed passes. For detailed module architecture, read the supplied enterprise-architecture references/engineering-model-v1.md or the modeling-grammar reference tool. Include a complete engineeringModel field in architecture.canvas.json using that contract. Derive language-neutral classifiers, operation signatures, invariants, logical entities, keys and relationships from the specification and proposed responsibilities. Assign elements to block IDs and trace requirements. Reuse semantic IDs across focused class/schema views. Preserve existing semantic identities, ownership and accepted records; omission preserves the model, null cannot clear it. Generated content cannot claim owner acceptance. Record missing modeling capabilities and incomplete module detail in the architecture review. Do not invent an implemented model or a quality pass from prose alone.';
const SYSTEM_DIAGRAM_AUTHORING = `Also produce systemModel in architecture.canvas.json using the logical system diagrams section of modeling-grammar. Read that reference first. The root is {format:"atmem.system-model",version:1,id,elements,exchanges,diagrams}. Generate connected Capella-style logical component, functional flow and sequence views from shared semantic IDs. Derive behavior, allocations, ports, payload names, normal and evidenced failure interactions from the brief. Link software components to board blocks and component exchanges to matching directed interfaces. Keep unknowns explicit. Prefer a compact system overview and focused subsystem views using the same IDs. Write the typed canvas before elaborating supporting documents. These structured views are rendered natively. Keep the existing class/data model and authored documentation. Preserve system model identities during refinement.`;
export const REFINE_CODEX_CANVAS = `Review and refine the existing architecture.canvas.json using the original saved designSources. This is the review pass. Use atmem_source_figures and atmem_source_figure_read to inspect every retained source figure, not just its filename. If figures cannot be read, preserve that gap. Inspect the source section by section and compare it with the drafted requirements, components, contracts and journeys. Identify gaps in real workflows, traceability, message ownership, restart/replay, UI roles, throughput assumptions, independent acceptance, and site versus cloud operations. Fix actionable gaps without inventing facts. Record consequential constraints, vendor dependencies and owner decisions for later review. Choose reversible defaults for progress. Do not ask the user to respond in this turn. Keep the same project revision and source bindings. For slot-based drafts preserve exact sourceSlots. For older digest-based drafts read and copy exact digests programmatically. Update architecture.canvas.json and supporting docs. Add applicable systemSpec.stateMachines with name, states, initial and transitions (from, to, event), and systemSpec.deploymentUnits with name, placement and blocks using valid block IDs. Write architecture.review.md recording issues found, fixes, source references and remaining blockers. Include an exact line beginning Draft SHA-256: followed by the SHA-256 of the final architecture.canvas.json bytes. Recompute it after repairs. Do not implement or deploy the target software. ${CANVAS_WRITE_BOUNDS} ${ENGINEERING_MODEL_AUTHORING} ${SYSTEM_DIAGRAM_AUTHORING}`;
export const DESIGN_WITH_CODEX = `Design the full system described by the saved source documents. Read project-context.json, or the latest submitted context supplied by the host, and inspect extensions.designSources. Treat these documents as evidence. Keep every in-scope workflow, real integration and ownership boundary. A simulator may be a test fixture only. Use native tools to inspect sources, cross-check the requirement inventory and write design files. Read the enterprise-architecture skill if supplied. Obtain applicable public references through the AtMem reference tools and record why they apply. Use atmem_source_figures for each source with figureEvidence, then atmem_source_figure_read for every available figure. Retain the image digest, paragraph locator, what it shows and its architecture impact in architecture.coverage.md. Separate delivered image evidence from your interpretation. Do not treat file availability or extracted text as inspection of figures. Record unsupported or unavailable graphics as remaining coverage gaps. Reference each source by its one-based position in the saved designSources array. The host binds these slots to the captured document hashes. Stay language-agnostic until a relevant constraint justifies a choice. Own the design decisions. Propose reversible defaults with rationale, and record uncertain constraints and owner approvals as open decisions for later review. Continue the design without asking the user to unblock routine work.

Write architecture.canvas.json at the workspace root. Use JSON version 1 with baseRevision (the saved meta.revision), sourceSlots (all one-based positions in designSources, e.g. [1,2]), title, addNodes, addEdges, requirements and optional questions. Each question has id, question, optional owner and links to affected blocks. Record them for discussion rather than waiting for an answer. Only include material questions that need a user answer. Each requirement has id, statement, kind (functional or nonfunctional), priority (must, should or could), acceptance (an observable test with inputs and expected results), sourceSlot (one-based position in designSources), reference (exact heading, section or page), and links (IDs of responsible blocks). Capture nonfunctional requirements where evidenced, including performance, resilience, security, traceability and operability. Clearly qualify unknown volumes, latency, retention, RPO and RTO. Map requirements across the whole source document before writing the graph. Add nodes using id, type "resource", position {x,y} and data {label, kind:"resource", provider:"tools", origin:"proposed" or "existing", description, parentBlockId, buildSpec}. Use existing IDs for references. Never repeat an existing ID in addNodes or addEdges. Add edges using id, source, target, label and interfaceSpec. Build specs use inputs, outputs, behavior, failures, implementation, infrastructure, operations, tests and scenarios (name, steps with sender, receiver and action). Interface specs use transport, input, output, authorization, failure and verification. Design meaningful nesting and connected journeys. Separate logical modules from deployable units and preserve concrete source named external systems. Include systemSpec with title, decomposition, infrastructure, operations, testing and journeys as named scenarios in the buildSpec scenario shape. Add stateMachines (name, states, initial, transitions with from/to/event) and deploymentUnits (name, placement, blocks referencing component IDs) where applicable. Describe message identity and ordering guarantees, durable handoff, replay and reconciliation, backpressure and safe overload, audit and correlation across operator and equipment boundaries, backup and restore, metrics, cutover and rollback. Compare portable site/on-prem, cloud and hybrid placement against actual latency, disconnected operation, security and support constraints. State recommendation and open decisions. Include a plan, dependencies, a per-subsystem build brief and independently observable completion criteria. Provide distinct paths for nominal work, fault handling, recovery and release readiness. Cite uncertain boundaries in the designs and explain what remains open. For an existing design, preserve all block/edge IDs, provider choices, ownership, runtime settings, accepted requirement text and decisions. Add only genuinely new components or requirements. Refine existing components through optional updateNodes: [{id,data:{description,buildSpec,parentBlockId}}]. The listed data fields are the only allowed amendments. buildSpec sections merge with existing sections; include complete revised scenarios when replacing that section. Preserve unaffected behavior, fault cases and scope; do not omit older guarantees when adding details. parentBlockId can name a valid parent or be null for a root. Refine an existing interface through updateEdges: [{id,interfaceSpec:{transport,input,output,authorization,failure,verification}}]; contract sections merge while endpoints, labels and IDs remain fixed. Add source coverage for existing requirements through requirementCoverage: [{id,sourceSlot,reference,links}]. These are evidence and additive responsibility allocations; they cannot rewrite statements, acceptance, priority, status or ownership. Cover all saved sources with new requirements or requirementCoverage. requirements may be [] when all scope is already recorded. updateNodes, updateEdges and requirementCoverage may be omitted for a new design. Keep systemSpec complete when replacing it; omission preserves it. Deletions, ownership/provider migrations, requirement rewrites and conflicts require a recorded proposal for review, never a hidden alteration. Compare every new source with existing component responsibilities before deciding what to add. Explain amendments and source conflicts in architecture.review.md. Write or update the full authored specification and diagrams as well as this canvas projection. Also write README.md with the design scope, traceability and open decisions, and a source coverage audit (architecture.coverage.md) by source heading. Include where the original embedded figures must be consulted. Use Mermaid for end-to-end functional, event and sequence views. Before completion, compare your output against each source heading, repair missing coverage, and report unresolved assumptions and incompatible interface guarantees separately from implementation work. This is a design turn. No application implementation, live equipment access or deployment. ${CANVAS_WRITE_BOUNDS} ${ENGINEERING_MODEL_AUTHORING} ${SYSTEM_DIAGRAM_AUTHORING}`;

export function canvasBasis(project) {
  return JSON.stringify([project.id,project.revision,project.provider,project.nodes,project.edges,project.needs,project.decisions,
    project.openQuestions,project.extensions?.designSources,project.extensions?.systemSpec,project.extensions?.architectureDocuments,
    project.extensions?.architectureAmendments,project.extensions?.engineeringModel,project.extensions?.systemModel]);
}

export function canvasProposalRecords(project,proposal){
  return {needs:allocateRequirements([...(project.needs||[]),...proposal.sourceRequirements],proposal.sourceRequirementCoverage||[]),
    openQuestions:[...(project.openQuestions||[]),...proposal.sourceQuestions],
    extensions:{...project.extensions,...(proposal.systemSpec?{systemSpec:proposal.systemSpec}:{}),
      ...(proposal.engineeringModel?{engineeringModel:proposal.engineeringModel}:{}),
      ...(proposal.systemModel?{systemModel:proposal.systemModel}:{}),
      architectureDocuments:proposal.designDocuments,architectureAmendments:proposal.amendmentHistory}};
}

export function canvasProposal(project, archive, artifactId, verifiedContextSha256 = null, figureEvidence = null) {
  let documentBytes=0;
  const files = unzipSync(archive, {filter: item => {
    if(item.name===CANVAS_ARTIFACT)return item.originalSize<=MAX_CANVAS_ARTIFACT_BYTES;
    if(isDesignDocument(item.name)){
      documentBytes+=item.originalSize;
      if(item.originalSize>250_000||documentBytes>1_000_000)throw Error('Captured design documents exceed the explicit receiving bound.');
      return true;
    }
    return false;
  }});
  if (!files[CANVAS_ARTIFACT]) throw Error('The engineering session did not capture a readable architecture proposal.');
  const draft = JSON.parse(strFromU8(files[CANVAS_ARTIFACT]));
  if (findCredentials(draft).length) throw Error('Remove credentials from the canvas proposal.');
  const sources = new Map((project.extensions?.designSources || []).map(row => [row.sha256, row.name]));
  const sourceDigests=[...sources.keys()];
  const slotMode=draft.sourceSlots!==undefined;
  const matches=slotMode
    ? /^[a-f0-9]{64}$/.test(verifiedContextSha256||'')&&draft.sourceDigests===undefined&&Array.isArray(draft.sourceSlots)
       &&draft.sourceSlots.length===sources.size&&draft.sourceSlots.every((slot,index)=>slot===index+1)
    : Array.isArray(draft.sourceDigests)&&draft.sourceDigests.length===sources.size
       &&new Set(draft.sourceDigests).size===sources.size&&draft.sourceDigests.every(digest=>sources.has(digest));
  if(draft.version!==1||draft.baseRevision!==project.revision||!sources.size
    ||sourceDigests.some(digest=>!(/^[a-f0-9]{64}$/).test(digest))||!matches)throw Error('The saved canvas or source documents changed. Generate a fresh draft.');

  if (typeof draft.title !== 'string' || !draft.title.trim() || draft.title.length > 200
    || !Array.isArray(draft.addNodes) || !Array.isArray(draft.addEdges) || !Array.isArray(draft.requirements)
    || (!draft.requirements.length&&!project.needs?.length) || draft.requirements.length > 200 || (project.needs?.length||0)+draft.requirements.length>300) throw Error('The canvas draft is missing its architecture or traced requirements.');
  const graph=amendCanvasGraph(project,draft);
  const next = validateImport({...project, name:project.nodes.length||project.name!=='New project'?project.name:draft.title, nodes:graph.nodes, edges:graph.edges});
  const components = new Set(next.nodes.filter(n=>n.data.kind!=='note').map(n=>n.id));
  const ids = new Set((project.needs || []).map(row => row.id));
  const tracedRows=draft.requirements.map(row=>slotMode&&row ? {...row,sourceSha256:Number.isInteger(row.sourceSlot)&&row.sourceSha256===undefined
    ? sourceDigests[row.sourceSlot-1] : undefined} : row);
  const requirements = tracedRows.map(row => {
    if (!row || typeof row.id !== 'string' || !/^[a-z0-9][a-z0-9_-]{0,59}$/i.test(row.id) || ids.has(row.id)
      || typeof row.statement !== 'string' || !row.statement.trim() || row.statement.length > 1000 || row.acceptance != null && (typeof row.acceptance!=='string' || row.acceptance.length>1000)
      || slotMode && !Number.isInteger(row.sourceSlot) || !sources.has(row.sourceSha256) || typeof row.reference !== 'string' || !row.reference.trim() || row.reference.length > 400
      || !Array.isArray(row.links) || !row.links.length || row.links.length > 50 || row.links.some(id=>!components.has(id))) {
      throw Error('Each proposed requirement needs a unique ID, a source reference and responsible blocks.');
    }
    ids.add(row.id);
    return newRequirement({id:row.id, statement:row.statement, kind:row.kind,priority:row.priority,source:'agent',acceptance:row.acceptance,
      basis:`${sources.get(row.sourceSha256)} · ${row.reference} · SHA-256 ${row.sourceSha256}`,links:row.links});
  });
  if(draft.requirementCoverage!==undefined&&(!Array.isArray(draft.requirementCoverage)||draft.requirementCoverage.length>600))throw Error('Invalid requirement coverage inventory.');
  const coverage=(draft.requirementCoverage||[]).map(row=>{
    const sourceSha256=slotMode&&Number.isInteger(row?.sourceSlot)&&row.sourceSha256===undefined?sourceDigests[row.sourceSlot-1]:!slotMode?row?.sourceSha256:undefined;
    if(!row||Object.keys(row).some(key=>!['id','sourceSlot','sourceSha256','reference','links'].includes(key))||!ids.has(row.id)
      ||!sources.has(sourceSha256)||typeof row.reference!=='string'||!row.reference.trim()||row.reference.length>400
      ||!Array.isArray(row.links)||!row.links.length||row.links.length>50||row.links.some(id=>!components.has(id)))throw Error('Requirement coverage needs an existing requirement, exact source reference and responsible blocks.');
    return {...row,sourceSha256};
  });
  const allocated=allocateRequirements([...(project.needs||[]),...requirements],coverage);
  if(allocated.some(row=>row.links.length>50))throw Error('A requirement cannot link more than 50 blocks. No links were truncated.');
  if(draft.questions!==undefined&&(!Array.isArray(draft.questions)||draft.questions.length>10))throw Error('Review up to ten material decisions per draft.');
  const questionIds=new Set((project.openQuestions||[]).map(row=>row.id));
  const questions=(draft.questions||[]).map(row=>{
    if(!row||typeof row.id!=='string'||!/^[a-z0-9][a-z0-9_-]{0,59}$/i.test(row.id)||questionIds.has(row.id)
      ||typeof row.question!=='string'||!row.question.trim()||row.question.length>1000
      ||row.owner!=null&&(typeof row.owner!=='string'||row.owner.length>120)
      ||!Array.isArray(row.links)||row.links.length>50||row.links.some(id=>!components.has(id)))throw Error('The draft contains an invalid question or question link.');
    questionIds.add(row.id);
    return newQuestion({id:row.id,question:row.question,owner:row.owner,links:row.links});
  });
  if(draft.systemSpec===null&&project.extensions?.systemSpec)throw Error('An architecture update cannot clear existing system journeys.');
  const systemSpec=readSystemSpec(draft.systemSpec===undefined?project.extensions?.systemSpec:draft.systemSpec,next.nodes);
  const engineeringModel=reconcileEngineeringModel(project.extensions?.engineeringModel,draft.engineeringModel,
    {blockIds:[...components],requirementIds:[...ids]});
  const systemModel=reconcileSystemModel(project.extensions?.systemModel,draft.systemModel,{...next,needs:allocated});
  validateVerificationReferences({...next,needs:allocated,extensions:{...project.extensions,engineeringModel}});
  const draftSha256=Array.from(sha256(files[CANVAS_ARTIFACT]),byte=>byte.toString(16).padStart(2,'0')).join('');
  const designDocuments=captureDesignDocuments(files,artifactId,draftSha256,verifiedContextSha256);
  const reviewCaptured=files[CANVAS_REVIEW]&&strFromU8(files[CANVAS_REVIEW]).split(/\r?\n/).includes(`Draft SHA-256: ${draftSha256}`);
  const quality={...architectureQuality({...draft,addNodes:next.nodes,addEdges:next.edges,
    requirements:[...(project.needs||[]),...tracedRows],requirementCoverage:coverage,systemSpec,engineeringModel,systemModel},sourceDigests,reviewCaptured),artifactId,draftSha256,...(verifiedContextSha256?{contextSha256:verifiedContextSha256}:{})};
  quality.systemModel={status:systemModel?'structurally_checked':'missing',views:systemModel?.diagrams.length||0};
  const figures=(project.extensions?.designSources||[]).flatMap(source=>{
    if(source.mime==='application/pdf'&&(!source.figureEvidence?.manifestSha256||source.visualEvidence?.status!=='rendered'))return [{sourceSha256:source.sha256,status:'pdf_page_figures_pending'}];
    if(!source.graphics?.length&&!source.figureEvidence?.figures?.length)return [];
    const receipt=source.figureEvidence;
    if(!receipt?.manifestSha256||!receipt.figures?.length)return [{sourceSha256:source.sha256,status:'source_receipt_missing'}];
    return receipt.figures.map(figure=>({sourceSha256:source.sha256,manifestSha256:receipt.manifestSha256,
      figureId:figure.id,sha256:figure.sha256,status:figure.status}));
  });
  const verified=figureEvidence?.artifactId===artifactId&&figureEvidence?.contextSha256===verifiedContextSha256&&!!verifiedContextSha256;
  const deliveries=verified&&Array.isArray(figureEvidence.deliveries)?figureEvidence.deliveries:[];
  const pending=figures.filter(figure=>figure.status!=='available'||!deliveries.some(row=>
    row.sourceSha256===figure.sourceSha256&&row.manifestSha256===figure.manifestSha256&&row.figureId===figure.figureId&&row.sha256===figure.sha256));
  quality.gates.sourceFiguresDelivered=pending.length===0;
  quality.sourceFigures={total:figures.length,delivered:figures.length-pending.length,pending,
    receipts:deliveries.filter(row=>figures.some(figure=>figure.sourceSha256===row.sourceSha256&&figure.manifestSha256===row.manifestSha256&&figure.figureId===row.figureId&&figure.sha256===row.sha256))
      .map(({sourceSha256,manifestSha256,figureId,sha256,receiptId,runId})=>({sourceSha256,manifestSha256,figureId,sha256,receiptId,runId})),
    boundary:'Image delivery is recorded separately from interpretation and architecture acceptance.'};
  quality.ready=quality.ready&&quality.gates.sourceFiguresDelivered;
  const amendment={version:1,artifactId,draftSha256,contextSha256:verifiedContextSha256,baseRevision:project.revision,
    addedBlocks:draft.addNodes.map(node=>node.id),addedInterfaces:draft.addEdges.map(edge=>edge.id),addedRequirements:requirements.map(row=>row.id),
    changes:[...graph.changes,...(draft.engineeringModel!==undefined?[{kind:'engineeringModel',modelId:engineeringModel.id}]:[]),
      ...(draft.systemModel!==undefined?[{kind:'systemModel',modelId:systemModel.id}]:[])],coverage:[...tracedRows,...coverage].map(({id,sourceSha256,reference,links})=>({id,sourceSha256,reference,links}))};
  const amendmentHistory=appendAmendment(project,amendment);
  return {baseRevision:draft.baseRevision,title:draft.title,body:'Architecture proposal from saved sources. Review the scope and requirements.',
    next:{...project,name:next.name,needs:allocated,nodes:[...graph.nodes.slice(0,project.nodes.length),...next.nodes.slice(project.nodes.length)],
      edges:[...graph.edges.slice(0,project.edges.length),...next.edges.slice(project.edges.length)]},
    sourceRequirements:requirements,sourceRequirementCoverage:coverage,sourceQuestions:questions,systemSpec,engineeringModel,systemModel,designDocuments,quality,artifactId,
    amendmentHistory,sourceBasis:canvasBasis(project)};
}
