import catalogue from '../agent-skills/generation-capabilities.json' with {type:'json'};
import skillDigests from '../agent-skills/specialists/manifest.json' with {type:'json'};
import lifecycle from '../agent-skills/service-lifecycle.json' with {type:'json'};
import {generationProviders} from './generation-provider.mjs';
export function generationQuality(project,plan,files){
 const config=JSON.parse(files['main.tf.json']);
 const providers=generationProviders(project),findings=[];
 const add=(code,message,componentId)=>findings.push({code,message,...(componentId?{componentId}:{})});
 const sources={aws:'hashicorp/aws',azurerm:'hashicorp/azurerm',azuread:'hashicorp/azuread',google:'hashicorp/google','google-beta':'hashicorp/google-beta',ibm:'ibm-cloud/ibm'};
 for(const [name,body] of Object.entries(config.terraform?.required_providers||{}))if(sources[name]!==String(body.source||'').toLowerCase())add('unreviewed-provider',`Provider ${name} is not the reviewed official provider source.`);
 for(const [name,body] of Object.entries(config.provider||{}))for(const key of ['access_key','secret_key','token','client_secret','credentials','ibmcloud_api_key'])if(body?.[key])add('embedded-provider-credential',`Provider ${name} contains ${key}; use the operator credential chain.`);
 for(const [type,items] of Object.entries(config.resource||{}))for(const [name,body] of Object.entries(items))if(body?.provisioner)add('execution-hook',`${type}.${name} contains an unreviewed provisioner.`);
 if(config.data?.external||config.data?.terraform_remote_state)add('external-execution-or-state','External execution and remote-state readers require a separately reviewed adapter.');
 if(Object.keys(config.module||{}).length)add('unreviewed-module','Module dependencies require a pinned, reviewed adapter; arbitrary module sources are not admitted.');
 const prefixes={aws:'aws_',azure:'azurerm_',gcp:'google_',ibm:'ibm_'};
 const emitted=Object.entries(config.resource||{}).filter(([type])=>type!=='terraform_data');
 for(const rule of lifecycle.rules)if(!rule.newCustomerDefaultAllowed&&rule.resourceTypes.some(type=>Object.keys(config.resource?.[type]||{}).length))add('service-eligibility-unverified',`${rule.id}: ${rule.requiredEvidence} Source: ${rule.source.url}`);
 for(const [type] of emitted){const owner=type.startsWith('azuread_')?'azure':Object.keys(prefixes).find(p=>type.startsWith(prefixes[p]));if(!owner||!providers.includes(owner))add('provider-mismatch',`Resource ${type} does not match the requested deployment providers.`);}
 const components=plan.rows.map(row=>{
  const node=project.nodes.find(n=>n.id===row.id),d=node.data;
  const contracts=catalogue.contracts.filter(c=>c.provider===d.provider&&(!c.service||c.service===row.service)&&(!c.implementation||c.implementation===d.implementation));
  if(!row.existing&&row.implemented){
   if(!contracts.length)add('unregistered-implementation',`No reviewed compiler contract matches the claimed implementation for ${row.label}.`,row.id);
   for(const c of contracts)for(const type of c.resources)if(!config.resource?.[type]?.[row.address])add('missing-resource',`Compiler claims ${c.id} for ${row.label}, but ${type}.${row.address} is absent.`,row.id);
  }
  return {id:row.id,provider:row.provider,ownership:row.existing?'existing':'proposed',contracts:contracts.map(c=>c.id),coverage:row.existing?'reference_or_external_contract':row.implemented?'generated_unverified':'implementation_required'};
 });
 for(const row of plan.rows.filter(r=>!r.implemented))add('implementation-required',`${row.label}: implementation remains required.`,row.id);
 for(const edge of plan.connections.filter(e=>!e.generated))add('connection-required',`Connection ${edge.id} has no generated integration.`);
 const unfinished=config.locals?.unfinished_work||[];
 const skills=[...new Set([...catalogue.skills,...providers])].filter(id=>skillDigests[id]).map(id=>({id,sha256:skillDigests[id]}));
 const fatalCodes=new Set(['provider-mismatch','missing-resource','unreviewed-provider','embedded-provider-credential','execution-hook','external-execution-or-state','unreviewed-module','unregistered-implementation','service-eligibility-unverified']);
 return {version:1,fatalFindings:findings.filter(f=>fatalCodes.has(f.code)),designRevision:project.revision,catalogueVersion:catalogue.version,providers,skills,skillUsage:"Referenced reviewed guidance; model execution of skills is not attested by this export.",components,findings,infrastructureComplete:findings.length===0&&unfinished.length===0&&emitted.length>0,validation:{schema:'not_run',runtime:'not_run',cloudPlan:'not_run'},deploymentCandidate:false,evidenceBoundary:catalogue.evidenceBoundary};
}
