import {caseSpecificityIssues} from './verification-cases.mjs';
import {isDiagramRevision} from './records.mjs';
import {diagramCatalogue, diagramProjection} from './architecture-diagrams.mjs';
import {interfaceFields} from './block-spec.mjs';
import skills from '../agent-skills/specialists/architecture-diagrams/skills.json' with {type:'json'};

const skillsByType = new Map(skills.map(skill => [skill.id,skill]));
const provisional = /\b(?:TBD|TBC|placeholder|unconfirmed|provisional|pending (?:confirmation|qualification|approval)|(?:transport|schema|wire|contract|interface) (?:is )?pending|requires? (?:owner |customer |vendor )?(?:approval|confirmation)|to be confirmed)\b|\/proposed\//i;

function reviewFields(record, required) {
  const fields = new Map(record.details.map(({name,value}) => [name.toLowerCase(),value]));
  const missing = [], pending = [];
  for (const name of required || []) {
    const value = fields.get(name.toLowerCase());
    if (!value?.trim()) missing.push(name);
    else if (provisional.test(value)) pending.push(name);
  }
  return [
    ...(missing.length ? [record.name + ' · Missing ' + missing.join(', ')] : []),
    ...(pending.length ? [record.name + ' · Confirm ' + pending.join(', ')] : []),
  ];
}

export function buildReview(project, model = project.extensions?.architectureDiagrams) {
  const blocks = new Map(project.nodes.map(node => [node.id,node.data.label]));
  const cases = project.nodes.flatMap(node => (node.data.buildSpec?.verificationCases || []).map(row => ({
    ...row, blockId:node.id, blockName:node.data.label,
  })));
  const requirements = (project.needs || []).map(need => ({
    ...need, interfaceIds:[...new Set(project.nodes.flatMap(n=>(n.data.buildSpec?.scenarios||[]).flatMap(s=>(s.steps||[]).filter(step=>step.requirementIds?.includes(need.id)&&step.interfaceId).map(step=>step.interfaceId))))], cases:cases.filter(row=>row.requirementIds.includes(need.id)).map(row=>({id:row.id,blockId:row.blockId})),
  }));
  const decisions = (project.openQuestions || []).map(row => ({
    ...row, status:row.status==='answered' && row.answer?.trim() ? 'answered' : 'open',
    blocks:(row.links||[]).map(id=>blocks.get(id)||id),
  }));
  const interfaces = project.edges.map(edge => {
    const contract = edge.interfaceSpec || {};
    const missing = Object.entries(interfaceFields).filter(([key])=>!contract[key]?.trim()).map(([,name])=>name);
    const pending = Object.entries(interfaceFields).filter(([key])=>provisional.test(contract[key]||'')).map(([,name])=>name);
    return {id:edge.id,name:edge.label||edge.id,source:edge.source,target:edge.target,
      from:blocks.get(edge.source),to:blocks.get(edge.target),contract,missing,pending};
  });
  const pages = (model?.views||[]).map(view => {
    const {nodes,edges,diagnostics} = diagramProjection(model,view);
    const skill = skillsByType.get(view.kind);
    const findings = [...diagnostics,
      ...nodes.flatMap(row=>reviewFields(row,skill?.expectedElementFields?.[row.kind])),
      ...edges.flatMap(row=>reviewFields(row,skill?.expectedRelationFields?.[row.kind]))];
    return {id:view.id,kind:view.kind,name:view.name,populated:nodes.length>0,
      exampleOnly:nodes.length>0 && nodes.every(row=>row.basis==='example'),
      findings:[...new Set(findings)]};
  });
  const diagrams = diagramCatalogue.map(type => ({
    id:type.id,name:type.title,group:type.group,check:skillsByType.get(type.id).buildCheck,
    pages:pages.filter(view=>view.kind===type.id),
  }));
  const engine = project.extensions?.engineeringModel;
  return {version:1,projectId:project.id,revision:project.revision,name:project.name,
    decisions,interfaces,requirements,cases,diagrams,caseSpecificityIssues:caseSpecificityIssues(cases),
    counts:{
      open:decisions.filter(q=>q.status==='open').length,
      covered:requirements.filter(r=>r.cases.length).length,
      dedicatedCovered:requirements.filter(r=>cases.some(c=>c.requirementIds.length===1&&c.requirementIds[0]===r.id)).length,
      types:diagrams.filter(type=>type.pages.some(p=>p.populated&&!p.exampleOnly)).length,
      contractReviews:interfaces.filter(row=>row.missing.length||row.pending.length).length,
      engineeringEntities:engine?.elements.filter(row=>['entity','table'].includes(row.kind)).length||0,
    },
  };
}

// Design review is distinct from test execution and deployment readiness.
export function designReadiness(review, catalogueRequired=false){
 const gaps=[];
 if(!review.requirements.length)gaps.push('Requirements missing');
 if(review.counts.covered<review.requirements.length)gaps.push((review.requirements.length-review.counts.covered)+' requirements need case definitions');
 if(catalogueRequired&&review.counts.dedicatedCovered<review.requirements.length)gaps.push((review.requirements.length-review.counts.dedicatedCovered)+' requirements need dedicated case definitions');
 if(review.caseSpecificityIssues?.length)gaps.push(review.caseSpecificityIssues.length+' groups of duplicated dedicated fixtures need review');
 if(review.counts.contractReviews)gaps.push(review.counts.contractReviews+(review.counts.contractReviews===1?' contract needs review':' contracts need review'));
 if(review.counts.open)gaps.push(review.counts.open+' owner decisions remain');
 if(catalogueRequired&&review.counts.types<28)gaps.push((28-review.counts.types)+' diagram types need content');
 return {title:gaps.length?'Design gaps remain':'Design defined · execution evidence required',gaps};
}
export function reviewDecisions(project,review=buildReview(project)){
 return [...new Map([...review.decisions,...(project.decisions||[]).filter(d=>d.status!=='Superseded'&&!isDiagramRevision(d)).map(d=>({id:d.id,name:d.title||d.subject,status:d.status,owner:d.owner||'Recorded project decision',answer:d.decision,blocks:[]}))].map(d=>[d.id,d])).values()];
}
