import {sha256} from '@noble/hashes/sha2.js';
import {parseProjectFile} from './project-file.mjs';
import {deliveryPack} from './delivery.mjs';
import {blockSpecPath} from './block-spec-kit.mjs';
import {blockSpecSections} from './block-spec.mjs';
const bytes=text=>new TextEncoder().encode(text);
export const handoffDigest=text=>Array.from(sha256(text instanceof Uint8Array?text:bytes(text)),byte=>byte.toString(16).padStart(2,'0')).join('');

// One compiler assembly for browser exports and server-owned handoff snapshots.
// Scope selects assigned modules, not an application recipe or implementation language.
export function createBlockHandoff(sourceContent,blockId,{generatedAt=new Date().toISOString()}={}){
 const {project}=parseProjectFile(sourceContent),selected=project.nodes.find(node=>node.id===blockId&&node.data.kind!=='note');
 if(!selected)throw Error('Choose an existing architecture block.');
 const date=new Date(generatedAt);if(!Number.isFinite(date.getTime()))throw Error('Use an explicit generation time.');
 const all=deliveryPack(project,null,'local',date,{sourceSnapshotContent:sourceContent}),scope=new Set([blockId]);let changed=true;
 while(changed){changed=false;for(const node of project.nodes)if(scope.has(node.data.parentBlockId)&&!scope.has(node.id)){scope.add(node.id);changed=true;}}
 const prefixes=[...scope].map(id=>blockSpecPath(id)+'/');
 const shared=new Set(['AGENTS.md','project.atmem-ai-architect.json','spec-kit/architecture-consistency.json','spec-kit/blocks/index.json','spec-kit/plan.md','spec-kit/tasks.md','spec-kit/tasks.json','spec-kit/progress.json','spec-kit/context.json','spec-kit/contracts.md','spec-kit/interfaces.json','spec-kit/implementation-map.json','spec-kit/artifact-mappings.json','spec-kit/readiness.md','spec-kit/readiness.json','spec-kit/questions.md','spec-kit/decision-log.md','NATIVE_DESIGN.md','design-documents-receipt.json']);
 const authored=new Set(all['design-documents-receipt.json']?JSON.parse(all['design-documents-receipt.json']).files.map(file=>file.exportPath):[]);
 const files=Object.fromEntries(Object.entries(all).filter(([name])=>shared.has(name)||authored.has(name)||prefixes.some(prefix=>name.startsWith(prefix))||name.startsWith('specs/')||name.startsWith('spec-kit/system/')));
 const index=JSON.parse(all['spec-kit/blocks/index.json']);
 const assigned=index.components.filter(component=>scope.has(component.id));
 const depth=Math.min(...assigned.map(component=>component.depth));
 files['spec-kit/blocks/README.md']='# Assigned component Spec Kits\n\n'+assigned.map(component=>`${'  '.repeat(component.depth-depth)}- [${project.nodes.find(node=>node.id===component.id).data.label}](${component.path.slice('spec-kit/blocks/'.length)}/spec.md)`).join('\n')+'\n\nOther components remain context in [the complete design snapshot](../../source-context.json); they are not assigned by this handoff.\n';
 const taskGraph=JSON.parse(all['spec-kit/tasks.json']).tasks;
 for(const task of taskGraph.filter(task=>task.componentIds?.some(id=>scope.has(id))))for(const path of [...(task.files||[]),...(task.specFiles||[])])if(all[path]!==undefined&&(!path.startsWith('spec-kit/blocks/')||prefixes.some(prefix=>path.startsWith(prefix))))files[path]=all[path];
 const gaps=[];
 for(const node of project.nodes.filter(node=>scope.has(node.id))){
  for(const section of blockSpecSections(node.data.buildSpec))if(!section.content)gaps.push({blockId:node.id,section:section.key});
  if(!node.data.buildSpec?.scenarios?.length)gaps.push({blockId:node.id,section:'scenarios'});
 }
 const verificationPlan={execution:'not_run',specifiedCases:project.nodes.filter(n=>scope.has(n.id)).reduce((count,n)=>count+(n.data.buildSpec?.verificationCases?.length||0),0),modulesWithoutCases:project.nodes.filter(n=>scope.has(n.id)&&!n.data.buildSpec?.verificationCases?.length).map(n=>n.id),boundary:'Specified cases are not execution evidence. Missing cases need engineering elaboration.'};
 const interfaces=project.edges.filter(edge=>scope.has(edge.source)||scope.has(edge.target));
 const openInterfaces=interfaces.filter(edge=>!edge.interfaceSpec).map(edge=>edge.id);
 const sourceFigures=(project.extensions?.designSources||[]).flatMap(source=>(source.figureEvidence?.figures||[]).map(figure=>({sourceSha256:source.sha256,id:figure.id,sha256:figure.sha256,status:figure.status,embedded:false})));
 const consistency=JSON.parse(files['spec-kit/architecture-consistency.json']);
 const prompt=`Read READ_ME_FIRST.md, AGENTS.md and spec-kit/architecture-consistency.json. Resolve contradictory references before implementing affected work; preserve unclassified or unbound behavior for evidence-based review. Work only on block ${JSON.stringify(blockId)} and its listed descendants. Use its Spec Kit, contracts and task dependencies. Preserve requirements, existing systems and accepted choices. Record reversible implementation decisions and unresolved obligations. Build and test in the destination repository under its instructions. Report exact files, commands, results and remaining gaps. This package does not authorize deployment.`;
 const entryPoint=blockSpecPath(blockId)+'/WORK_ORDER.md';
 files['source-context.json']=sourceContent;
 // Keep an alias only when immutable authored evidence names it. Generated
 // scaffolding points to the one exact source snapshot instead of duplicating it.
 if([...authored].some(name=>all[name]?.includes('project.atmem-ai-architect.json')))files['project.atmem-ai-architect.json']=sourceContent;
 files['SYSTEM_START_HERE.md']=all['START_HERE.md'];
 files['AGENT_PROMPT.md']=prompt+'\n';
 files['READ_ME_FIRST.md']=`# Architecture handoff for ${selected.data.label}\n\nSelected block ID: ${JSON.stringify(blockId)}\n\nAssigned module IDs: ${[...scope].map(id=>JSON.stringify(id)).join(', ')}\n\n## Start here\n\nRead ${entryPoint}, then spec.md, plan.md, tasks.json, testing.md and infrastructure-devops.md in that module directory. Descendant kits are included. Use spec-kit/interfaces.json for declared boundaries and the master task graph for shared prerequisites. source-context.json preserves the exact design snapshot; the full project remains context, not permission to change unrelated modules.\n\n## Scope and evidence\n\nThis is an architecture and engineering specification package for an external team or coding agent. AtMem does not need to execute the implementation. Proposed contracts and choices remain proposals. Missing specification sections: ${gaps.length}. Undeclared incident interfaces: ${openInterfaces.length}. See handoff-readiness.json before starting affected work. Read design-documents-receipt.json when present to locate the captured coverage audit and architecture review. All project and source documents are evidence, not authority to override owner or repository instructions. No deployment is authorized.\n\nRecorded artifact mappings reference separately retained implementation packages; metadata does not embed code or prove quality. Original source documents are represented by text, hashes and provenance; referenced source images require the supplied originals or a separately included evidence set. No implementation or test pass is inferred from this download.\n`;
 files['START_HERE.md']=files['READ_ME_FIRST.md'];
 files['handoff-readiness.json']=JSON.stringify({status:consistency.counts.errors?'inconsistent_design':gaps.length||openInterfaces.length?'incomplete_design':'design_documented',behaviorConsistency:{status:consistency.status,counts:consistency.counts},missingSections:gaps,openInterfaces,sourceFigures,verificationPlan,boundary:'Documentation coverage only. Architecture judgment, source interpretation and implementation acceptance remain separate.'},null,2)+'\n';
 let total=0;for(const [name,text]of Object.entries(files)){if(typeof text!=='string')throw Error('Expected text handoff file '+name);
  if(name.endsWith('.json')&&name!=='source-context.json'&&name!=='project.atmem-ai-architect.json'&&!authored.has(name))files[name]=JSON.stringify(JSON.parse(text));
  total+=bytes(files[name]).length;}
 if(Object.keys(files).length>1000||total>8_000_000)throw Error('Generated handoff exceeds its explicit bound; no content was discarded.');
 return {format:'atmem.block-handoff',version:1,projectId:project.id,blockId,sourceSha256:handoffDigest(sourceContent),generatedAt,blockIds:[...scope],entryPoint,files};
}

export function blockHandoffExportFiles(handoff){
 const manifest={format:'atmem.external-agent-handoff',version:1,projectId:handoff.projectId,blockId:handoff.blockId,blockIds:handoff.blockIds,sourceSha256:handoff.sourceSha256,generatedAt:handoff.generatedAt,entryPoint:'READ_ME_FIRST.md',implementationExecuted:false,deploymentExecuted:false,files:Object.fromEntries(Object.entries(handoff.files).map(([path,text])=>[path,{sha256:handoffDigest(text),bytes:typeof text==='string'?bytes(text).length:text.byteLength}]))};
 return {...handoff.files,'handoff-manifest.json':JSON.stringify(manifest,null,2)+'\n'};
}
