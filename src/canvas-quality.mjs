import {architectureConsistency} from './architecture-consistency.mjs';
import {sha256} from '@noble/hashes/sha2.js';
import {blockSpecSections,diagramText,scenarioDiagrams,validateScenarios} from './block-spec.mjs';
import {capturedDiagramSources} from './captured-diagrams.mjs';

export const systemSections = ['decomposition','infrastructure','operations','testing'];
const present = value => typeof value === 'string' && value.trim().length > 0;

export function readSystemSpec(value, nodes = []) {
  if (value == null) return null;
  if (typeof value !== 'object' || Array.isArray(value)
    || !present(value.title) || value.title.length > 200
    || systemSections.some(key=>!present(value[key]) || value[key].length>6000)
    || !Array.isArray(value.journeys)) throw Error('The system summary needs a title, infrastructure, operations, testing and journeys.');
  validateScenarios(value.journeys,40);
  const copy=Object.fromEntries(['title',...systemSections,'journeys'].map(key=>[key,value[key]]));
  if(value.stateMachines!==undefined){
    if(!Array.isArray(value.stateMachines)||value.stateMachines.length>12)throw Error('Use at most 12 state machines.');
    for(const machine of value.stateMachines){
      if(!present(machine?.name)||machine.name.length>150||!Array.isArray(machine.states)||machine.states.length<2
        ||machine.states.length>30||new Set(machine.states).size!==machine.states.length
        ||machine.states.some(state=>!present(state)||state.length>120)||!machine.states.includes(machine.initial)
        ||!Array.isArray(machine.transitions)||!machine.transitions.length||machine.transitions.length>60
        ||machine.transitions.some(step=>!machine.states.includes(step?.from)||!machine.states.includes(step.to)
          ||!present(step.event)||step.event.length>300))throw Error('A state machine needs named states and valid event transitions.');
    }
    copy.stateMachines=value.stateMachines;
  }
  if(value.deploymentUnits!==undefined){
    const ids=new Set(nodes.map(node=>node.id));
    if(!Array.isArray(value.deploymentUnits)||value.deploymentUnits.length>40)throw Error('systemSpec.deploymentUnits must contain at most 40 units.');
    value.deploymentUnits.forEach((unit,index)=>{
      const path=`systemSpec.deploymentUnits[${index}]`;
      for(const key of ['name','placement'])if(!present(unit?.[key])||unit[key].length>150)
        throw Error(`${path}.${key} needs 1–150 UTF-16 code units. Keep the complete rationale in infrastructure and specs/ documents.`);
      if(!Array.isArray(unit.blocks)||!unit.blocks.length||unit.blocks.length>100)throw Error(`${path}.blocks needs 1–100 existing block IDs.`);
      const missing=unit.blocks.filter(id=>!ids.has(id));
      if(missing.length)throw Error(`${path}.blocks contains unknown IDs: ${JSON.stringify(missing)}. Preserve scope using existing block IDs.`);
    });
    copy.deploymentUnits=value.deploymentUnits;
  }
  return copy;
}

export function architectureQuality(draft, sources, reviewCaptured) {
  const nodes = draft.addNodes.filter(node=>node.data.kind!=='note');
  const coverage = draft.requirements || [];
  const traced=[...coverage,...(draft.requirementCoverage||[])];
  const measurements = [
    ['Source traceability', 20, sources.filter(sha=>traced.some(row=>row.sourceSha256===sha)).length / sources.length],
    ['Requirements and acceptance', 15, coverage.filter(row=>present(row.acceptance)).length / coverage.length],
    ['Nonfunctional requirements', 10, coverage.some(row=>row.kind==='nonfunctional'&&present(row.acceptance))?1:0],
    ['Nested responsibilities', 10, nodes.some(node=>node.data.parentBlockId)?1:0],
    ['Block specification coverage', 20, nodes.filter(node=>blockSpecSections(node.data.buildSpec).every(section=>present(section.content))
      &&node.data.buildSpec?.scenarios?.length>1).length / nodes.length],
    ['Interface contracts', 10, draft.addEdges.filter(edge=>edge.interfaceSpec).length / draft.addEdges.length],
    ['System journeys and delivery', 8, draft.systemSpec?.journeys?.length>1?1:0],
    ['State and deployment views', 2, (Number(!!draft.systemSpec?.stateMachines?.length)+Number(!!draft.systemSpec?.deploymentUnits?.length))/2],
    ['Captured review', 5, reviewCaptured?1:0],
  ].map(([name,points,fraction])=>({name,points,earned:Math.round(points*(fraction||0))}));
  const consistency=architectureConsistency({nodes:draft.addNodes,edges:draft.addEdges,needs:coverage,extensions:{systemSpec:draft.systemSpec,engineeringModel:draft.engineeringModel,systemModel:draft.systemModel}});
  const gates = {
    behaviorReferencesConsistent:consistency.counts.errors===0,
    allSourcesTraced: sources.length>0&&sources.every(sha=>traced.some(row=>row.sourceSha256===sha)),
    requiredAcceptance: coverage.length>0&&coverage.filter(row=>row.priority==='must').every(row=>present(row.acceptance)),
    interfaceContracts: draft.addEdges.length>0&&draft.addEdges.every(edge=>edge.interfaceSpec),
    systemJourneyCoverage: !!draft.systemSpec&&draft.systemSpec.journeys.length>1,
    reviewedExactDraft: !!reviewCaptured,
  };
  const score=measurements.reduce((total,row)=>total+row.earned,0);
  return {reviewCaptured:!!reviewCaptured,behaviorConsistency:{status:consistency.status,counts:consistency.counts,errors:consistency.issues.filter(row=>row.severity==='error'),boundary:consistency.boundary},score,gates,ready:score>=90&&Object.values(gates).every(Boolean),measurements,
    boundary:'Structural handoff coverage. Review content, unverified assumptions and executed tests separately.'};
}

export function appliedQualityBasis(project) {
  const value=[
    project.id,project.revision,project.provider,
    project.nodes.map(node=>({id:node.id,data:node.data})),
    project.edges.map(({id,source,target,label,integration,access,interfaceSpec})=>({id,source,target,label,integration,access,interfaceSpec})),
    project.needs||[],project.openQuestions||[],project.decisions||[],
    (project.extensions?.designSources||[]).map(source=>source.figureEvidence||source.visualEvidence?[source.sha256,source.figureEvidence,source.visualEvidence]:source.sha256),
    project.extensions?.systemSpec,
    ...(project.extensions?.engineeringModel?[project.extensions.engineeringModel]:[]),
    ...(project.extensions?.systemModel?[project.extensions.systemModel]:[]),
    ...(project.extensions?.architectureAmendments?[project.extensions.architectureAmendments]:[]),
    ...(project.extensions?.architectureDocuments?[project.extensions.architectureDocuments]:[]),
  ];
  const canonical=JSON.stringify(value,(_,item)=>item&&typeof item==='object'&&!Array.isArray(item)
    ? Object.fromEntries(Object.keys(item).sort().map(key=>[key,item[key]])) : item);
  return Array.from(sha256(new TextEncoder().encode(canonical)),byte=>byte.toString(16).padStart(2,'0')).join('');
}

export function systemSpecFiles(project,stamp) {
  const spec=readSystemSpec(project.extensions?.systemSpec,project.nodes);
  const quality=project.extensions?.architectureDraftQuality;
  const current=quality?.appliedBasis&&quality.appliedBasis===appliedQualityBasis(project);
  const figuresChecked=!(project.extensions?.designSources||[]).some(source=>source.mime==='application/pdf'||source.graphics?.length||source.figureEvidence?.figures?.length)||quality?.gates?.sourceFiguresDelivered===true;
  const diagramsChecked=!capturedDiagramSources(project.extensions?.architectureDocuments).length||quality?.gates?.authoredDiagramSyntax===true;
  const status=!current?'stale':!figuresChecked?'source_figures_pending':!diagramsChecked?'authored_diagrams_pending':'current';
  const files=quality?{'spec-kit/architecture-coverage.json':JSON.stringify({...quality,status,ready:!!current&&figuresChecked&&diagramsChecked&&quality.ready},null,2)+'\n'}:{};
  files['spec-kit/architecture-consistency.json']=JSON.stringify(architectureConsistency(project),null,2)+'\n';
  if(!spec)return files;
  const diagrams=spec.journeys.map((journey,index)=>{
    const diagram=scenarioDiagrams(journey);
    for(const [view,source] of Object.entries(diagram))files[`spec-kit/system/${index+1}-${view}.mmd`]=source+'\n';
    return `## ${journey.name}\n\n[Functional flow](${index+1}-functional.mmd) · [Sequence](${index+1}-sequence.mmd) · [Event flow](${index+1}-events.mmd)\n\n`+
      journey.steps.map((step,i)=>`${i+1}. ${step.sender} → ${step.receiver} · ${step.action}${step.operationId?` · operation ${step.operationId}`:''}`).join('\n');
  });
  const supplemental=[];
  for(const [index,machine] of (spec.stateMachines||[]).entries()){
    const ids=new Map(machine.states.map((state,i)=>[state,`state${i}`]));
    const path=`lifecycle-${index+1}.mmd`;
    files[`spec-kit/system/${path}`]=['stateDiagram-v2',...machine.states.map(state=>`  state "${diagramText(state)}" as ${ids.get(state)}`),
      `  [*] --> ${ids.get(machine.initial)}`,...machine.transitions.map(step=>`  ${ids.get(step.from)} --> ${ids.get(step.to)}: ${diagramText(step.event)}`)].join('\n')+'\n';
    supplemental.push(`[${machine.name} lifecycle](${path})`);
  }
  if(spec.deploymentUnits?.length){
    const ids=new Map(project.nodes.map((node,i)=>[node.id,`block${i}`]));
    const labels=new Map(project.nodes.map(node=>[node.id,node.data.label]));
    const shown=new Set();
    const groups=spec.deploymentUnits.flatMap((unit,index)=>{
      const blocks=unit.blocks.filter(id=>!shown.has(id));
      blocks.forEach(id=>shown.add(id));
      return [`  subgraph unit${index}["${diagramText(unit.name+' · '+unit.placement)}"]`,...blocks.map(id=>`    ${ids.get(id)}["${diagramText(labels.get(id))}"]`),'  end'];
    });
    const edges=project.edges.filter(edge=>shown.has(edge.source)&&shown.has(edge.target));
    files['spec-kit/system/deployment.mmd']=['flowchart LR',...groups,...edges.map(edge=>`  ${ids.get(edge.source)} --> ${ids.get(edge.target)}`)].join('\n')+'\n';
    supplemental.push('[Deployment topology](deployment.mmd)');
  }
  files['spec-kit/system/README.md']=[`# ${spec.title}\n\n${stamp}`,...systemSections.map(key=>`## ${key[0].toUpperCase()+key.slice(1)}\n\n${spec[key]}`),...diagrams,...(supplemental.length?['## State and deployment views',supplemental.join(' · ')]:[])].join('\n\n')+'\n';
  return files;
}
