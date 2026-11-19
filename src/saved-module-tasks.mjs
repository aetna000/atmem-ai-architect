import {blockSpecSections,interfaceFields} from './block-spec.mjs';
import {blockSpecPath} from './block-spec-kit.mjs';

// Refine execution guidance from explicit saved contracts, never labels/domain recipes.
// This does not accept a proposal, generate code, choose a provider or clear a gate.
export function applySavedModuleTasks(project,resources,tasks){
 const nodes=new Map(project.nodes.map(node=>[node.id,node]));
 const edges=new Map(project.edges.map(edge=>[edge.id,edge]));
 const portableBlock=id=>{
  const node=nodes.get(id),row=resources.rows.find(row=>row.id===id);
  return node?.data.provider==='tools'&&!!node.data.buildSpec&&!row?.implemented&&!node.data.implementation;
 };
 for(const task of tasks){
  const edge=task.edgeIds?.length===1?edges.get(task.edgeIds[0]):null;
  if(task.componentIds?.length&&task.componentIds.every(portableBlock)
    &&!(task.edgeIds||[]).some(id=>resources.connections.find(row=>row.id===id)?.generated))
   task.files=task.edgeIds?.length?['spec-kit/interfaces.json']:[];
  if(edge?.interfaceSpec&&task.phase==='Contracts'){
   const generated=!!resources.connections.find(row=>row.id===edge.id)?.generated;
   const savedSteps=[
    `Read the saved proposed design contract for ${edge.id} in spec-kit/interfaces.json. Preserve its direction and original ownership; proposed detail is not external-service qualification.`,
    ...Object.entries(interfaceFields).map(([field,label])=>`${label}: ${edge.interfaceSpec[field]}`),
    'Version the wire schema, sanitized examples and executable producer/consumer tests in the destination repository. Resolve only details still open in the saved contract; record reversible defaults and keep unverified counterpart guarantees explicit.',
    'Test valid, malformed and unauthorized messages plus the declared failure, duplicate, ordering and recovery behavior. Retain exact commands, versions, observed outcomes and evidence paths.',
   ];
   if(generated)task.steps.push('Compare the saved proposal below with the emitted compiler contract. Retain generated safeguards and record any conflict before changing implementation.',...savedSteps);
   else{
    task.title=`Specify and test ${nodes.get(edge.source)?.data.label} → ${nodes.get(edge.target)?.data.label}`;
    task.steps=savedSteps;
   }
   task.acceptance.push('The saved contract fields and source requirement IDs are retained; implementation deviations are recorded for review.');
   if(!generated)task.files=['spec-kit/interfaces.json'];
  }
  if(edge?.interfaceSpec&&task.phase==='Integration'){
   task.steps.unshift(`Use the versioned contract for ${edge.id} and its saved proposal in spec-kit/interfaces.json; preserve ${edge.source} → ${edge.target}, identities, failure/retry semantics and declared verification.`);
  }
  if(task.phase!=='Components'||task.componentIds?.length!==1)continue;
  const node=nodes.get(task.componentIds[0]),spec=node?.data.buildSpec;
  if(!spec)continue;
  const row=resources.rows.find(row=>row.id===node.id),path=blockSpecPath(node.id);
  const portable=portableBlock(node.id);
  const facts=blockSpecSections(spec).filter(section=>section.content).map(section=>`${section.title}: ${section.content}`);
  if(portable){
   const existing=node.data.origin==='existing'||row?.existing;
   task.steps=[
    `Read ${path}/WORK_ORDER.md, spec.md, plan.md, testing.md and infrastructure-devops.md, and the linked source requirements.`,
    'Read spec-kit/artifact-mappings.json. Reverify linked captured packages through their owning session service and inspect the immutable files and current context before deciding what remains. Preserve accepted implementation; metadata alone is not executable source or acceptance.',
    existing?'Preserve the existing owned system. Implement only the authorized adapter or maintenance boundary; do not recreate it or assume access to its runtime.':'Implement this saved responsibility in the destination repository. Use the system deployment-unit map to distinguish a logical grouping from a standalone process.',
    ...facts,
    'Inspect the destination repository and reuse accepted language, runtime and build conventions. If absent, select a reversible implementation toolchain, record rationale and concrete target files before coding; do not invent a cloud or destination resource.',
    'Build local unit and producer/consumer contract tests with explicit dependency doubles. Cover nominal operation, denial, failure and successful authorized recovery. Record what doubles cannot establish.',
    'Retain requirement IDs, changed files, exact commands, exit status, counts, results and rollback instructions. Keep full-system, real-counterpart, capacity and deployment acceptance separate.',
   ];
   task.files=[];
   task.outputs=[`Repository-defined implementation or authorized adapter for block ${node.id}`,`Local build/test commands, contract fixtures and artifact-bound evidence for ${node.id}`,'Recorded implementation defaults, unresolved obligations and operational handoff'];
  }else{
   task.steps.push(...facts);
  }
 }
 const hasSelectedProvider=project.nodes.some(node=>node.data.kind!=='note'&&['aws','azure','gcp','ibm','cloudnative'].includes(node.data.provider));
 if(!hasSelectedProvider&&project.nodes.some(node=>node.data.buildSpec)){
  const setup=tasks.find(task=>task.id==='TASK-SETUP');
  setup.steps=setup.steps.map(step=>step.startsWith('Pin dependencies and Terraform/provider versions;')?'Pin the chosen application/test dependencies and configure formatting, linting, unit tests and secret scanning. Select and pin an infrastructure tool only when the deployment profile needs one.':step);
  const checks=tasks.find(task=>task.id==='TASK-INFRA-STATIC');
  checks.title='Establish local deployment-configuration checks';
  checks.steps=['Use the saved deployment-unit inventory and proposed infrastructure/operations contracts. Select the appropriate configuration or IaC tooling for the chosen profile; do not assume Terraform or a cloud.',
   'Pin the selected tools and validate configuration, permissions, secret references and policy using local checks and explicit fixtures. If Terraform is selected, use backend-disabled initialization and retain provider locks.',
   'Record exact commands, versions, inputs and limits. A configuration check does not qualify physical placement, counterpart services or deployed behavior.'];
  const infra=tasks.find(task=>task.id==='TASK-INFRA-VALIDATION');
  infra.title='Complete and validate the selected deployment profile';
  infra.steps=['Map every saved deployment unit, owned/external dependency and connection to its selected site, cloud or hybrid configuration. Preserve unresolved provider/runtime choices and ownership.',
   'Implement and test the chosen configuration and packaging, identity/network boundaries, secret references, telemetry, storage and recovery settings. Include denied and failure cases without account access.',
   'Keep environment/state isolation, migration and rollback procedures explicit. Run the selected configuration/schema/policy checks and retain their artifact identity and logs.',
   'If the profile uses Terraform, inspect its generated resource schedule, implement all missing resources, preserve unfinished-work gates and run backend-disabled initialization, validation and appropriate tests. No cloud access or deployment is authorized here.'];
  infra.outputs=['Selected deployment-profile implementation and inventory','Local configuration checks, evidence and explicit destination qualification gaps'];
 }
}
