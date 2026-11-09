import catalogue from '../agent-skills/generation-capabilities.json' with {type:'json'};
import skillDigests from '../agent-skills/specialists/manifest.json' with {type:'json'};
import {generationProviders} from './generation-provider.mjs';
export function generationQuality(project,plan,files){
 const config=JSON.parse(files['main.tf.json']);
 const providers=generationProviders(project),findings=[];
 const add=(code,message,componentId)=>findings.push({code,message,...(componentId?{componentId}:{})});
 const prefixes={aws:'aws_',azure:'azurerm_',gcp:'google_',ibm:'ibm_'};
 const emitted=Object.entries(config.resource||{}).filter(([type])=>type!=='terraform_data');
 for(const [type] of emitted){const owner=Object.keys(prefixes).find(p=>type.startsWith(prefixes[p]));if(!owner||!providers.includes(owner))add('provider-mismatch',`Resource ${type} does not match the requested deployment providers.`);}
 const components=plan.rows.map(row=>{
  const node=project.nodes.find(n=>n.id===row.id),d=node.data;
  const contracts=catalogue.contracts.filter(c=>c.provider===d.provider&&(!c.service||c.service===row.service)&&(!c.implementation||c.implementation===d.implementation));
  if(!row.existing&&row.implemented){
   for(const c of contracts)for(const type of c.resources)if(!config.resource?.[type]?.[row.address])add('missing-resource',`Compiler claims ${c.id} for ${row.label}, but ${type}.${row.address} is absent.`,row.id);
  }
  return {id:row.id,provider:row.provider,ownership:row.existing?'existing':'proposed',contracts:contracts.map(c=>c.id),coverage:row.existing?'reference_or_external_contract':row.implemented?'generated_unverified':'implementation_required'};
 });
 for(const row of plan.rows.filter(r=>!r.implemented))add('implementation-required',`${row.label}: implementation remains required.`,row.id);
 for(const edge of plan.connections.filter(e=>!e.generated))add('connection-required',`Connection ${edge.id} has no generated integration.`);
 const unfinished=config.locals?.unfinished_work||[];
 const skills=[...new Set([...catalogue.skills,...providers])].filter(id=>skillDigests[id]).map(id=>({id,sha256:skillDigests[id]}));
 return {version:1,designRevision:project.revision,catalogueVersion:catalogue.version,providers,skills,skillUsage:"Referenced reviewed guidance; model execution of skills is not attested by this export.",components,findings,infrastructureComplete:findings.length===0&&unfinished.length===0&&emitted.length>0,validation:{schema:'not_run',runtime:'not_run',cloudPlan:'not_run'},deploymentCandidate:false,evidenceBoundary:catalogue.evidenceBoundary};
}
