import {inspectContainerConfiguration} from './container-inspection.mjs';
import {inspectTerraformModules} from './terraform-admission.mjs';
import {existingDeployment} from './deployment-ownership.mjs';
import catalogue from '../agent-skills/generation-capabilities.json' with {type:'json'};
import skillDigests from '../agent-skills/specialists/manifest.json' with {type:'json'};
import lifecycle from '../agent-skills/service-lifecycle.json' with {type:'json'};
import {generationProviders} from './generation-provider.mjs';
import {artifactWorkProjection} from './artifact-work.mjs';
export function generationQuality(project,plan,files){
 const config=JSON.parse(files['main.tf.json']);
 const providers=generationProviders(project),findings=[];
 const add=(code,message,componentId)=>findings.push({code,message,...(componentId?{componentId}:{})});
 const sources={aws:'hashicorp/aws',azurerm:'hashicorp/azurerm',azuread:'hashicorp/azuread',azapi:'azure/azapi',google:'hashicorp/google','google-beta':'hashicorp/google-beta',ibm:'ibm-cloud/ibm'};
 const admission=inspectTerraformModules(project,plan,files,config,add);
 const prefixes={aws:'aws_',azure:'azurerm_',gcp:'google_',ibm:'ibm_'},emitted=[];
 for(const scope of admission.configs){
  const current=scope.config;
  for(const [name,body]of Object.entries(current.terraform?.required_providers||{}))if(sources[name]!==String(body.source||'').toLowerCase())add('unreviewed-provider',`Provider ${name} in ${scope.path||'root'} is not the reviewed official provider source.`);
  for(const [name,values]of Object.entries(current.provider||{}))for(const body of Array.isArray(values)?values:[values])for(const key of ['access_key','secret_key','token','client_secret','credentials','ibmcloud_api_key'])if(body?.[key])add('embedded-provider-credential',`Provider ${name} in ${scope.path||'root'} contains ${key}; use the operator credential chain.`);
  for(const [type,items]of Object.entries(current.resource||{}))for(const [name,body]of Object.entries(items))if(body?.provisioner)add('execution-hook',`${scope.prefix}${type}.${name} contains an unreviewed provisioner.`);
  if(current.data?.external||current.data?.terraform_remote_state)add('external-execution-or-state','External execution and remote-state readers require a separately reviewed adapter.');
  for(const rule of lifecycle.rules)if(!rule.newCustomerDefaultAllowed&&rule.resourceTypes.some(type=>Object.keys(current.resource?.[type]||{}).length))add('service-eligibility-unverified',`${rule.id}: ${rule.requiredEvidence} Source: ${rule.source.url}`);
  for(const [type,items]of Object.entries(current.resource||{}).filter(([type])=>type!=='terraform_data')){
   emitted.push([scope.prefix+type,items]);const owner=/^(azuread_|azapi_)/.test(type)?'azure':Object.keys(prefixes).find(p=>type.startsWith(prefixes[p]));
   if(!owner||!providers.includes(owner)||scope.provider&&scope.provider!==owner)add('provider-mismatch',`Resource ${scope.prefix}${type} does not match its requested deployment provider.`);
  }
 }
 for(const node of project.nodes.filter(n=>n.data.kind!=='note'))if(plan.rows.filter(r=>r.id===node.id).length!==1)add('unregistered-implementation','The resource schedule must retain each component identity exactly once.',node.id);
 const components=plan.rows.map(row=>{
  const node=project.nodes.find(n=>n.id===row.id),d=node?.data||{},scope=admission.scopes.get(row.id),actual=scope?.config||(admission.composed?{}:config),prefix=scope?.prefix||'';
  if(node)inspectContainerConfiguration(node,row,actual,plan,add,{root:config,scope});
  if(!node||row.provider!==d.provider||!!row.existing!==!!(node&&existingDeployment(node)))add('unregistered-implementation','The schedule changed a component provider or ownership identity.',row.id);
  const contracts=catalogue.contracts.filter(c=>c.provider===d.provider&&(!c.service||c.service===row.service)&&(!c.implementation||c.implementation===d.implementation));
  if(!row.existing&&row.implemented){
   if(!contracts.length)add('unregistered-implementation',`No reviewed compiler contract matches the claimed implementation for ${row.label}.`,row.id);
   for(const c of contracts){
    for(const type of c.resources)if(!actual.resource?.[type]?.[row.address])add('missing-resource',`Compiler claims ${c.id} for ${row.label}, but ${prefix}${type}.${row.address} is absent.`,row.id);
    for(const instance of c.resourceInstances||[]){const name=row.address+instance.suffix;if(!actual.resource?.[instance.type]?.[name])add('missing-resource',`Compiler claims ${c.id} for ${row.label}, but required deployment unit ${prefix}${instance.type}.${name} is absent.`,row.id);}
   }
  }
  return {id:row.id,...(scope?{terraformModule:scope.module}:{}),provider:row.provider,ownership:row.existing?'existing':'proposed',contracts:contracts.map(c=>c.id),coverage:row.existing?'reference_or_external_contract':row.implemented?'generated_unverified':'implementation_required'};
 });
 for(const row of plan.rows.filter(r=>!r.implemented))add('implementation-required',`${row.label}: implementation remains required.`,row.id);
 for(const edge of plan.connections.filter(e=>!e.generated))add('connection-required',`Connection ${edge.id} has no generated integration.`);
 const unfinished=config.locals?.unfinished_work||[];
 if(!Array.isArray(unfinished))add('missing-work-gate','Unfinished scope must remain an explicit array of blockers.');
 for(const gap of plan.gapDetails||[]){add('unfinished-scope',gap.message);if(!Array.isArray(unfinished)||!unfinished.includes(gap.id))add('missing-work-gate','The root configuration omits required unfinished scope: '+gap.id+'.');}
 const skills=[...new Set([...catalogue.skills,...providers])].filter(id=>skillDigests[id]).map(id=>({id,sha256:skillDigests[id]}));
 const fatalCodes=new Set(['container-constraint-mismatch','provider-mismatch','missing-resource','unreviewed-provider','embedded-provider-credential','execution-hook','external-execution-or-state','unreviewed-module','unregistered-implementation','service-eligibility-unverified','missing-work-gate']);
 const artifactMappings=artifactWorkProjection(project);
 return {version:1,modules:[...admission.scopes].map(([id,scope])=>({id,module:scope.module,path:scope.path})),fatalFindings:findings.filter(f=>fatalCodes.has(f.code)),designRevision:project.revision,catalogueVersion:catalogue.version,providers,skills,skillUsage:"Referenced reviewed guidance; model execution of skills is not attested by this export.",components,findings,artifactMappings:{file:'architecture-artifact-mappings.json',references:artifactMappings.mappings.map(m=>({id:m.id,artifactId:m.artifactId,artifactSha256:m.artifactSha256,contextStatus:m.contextStatus,recordIds:m.records.map(r=>r.id)})),boundary:artifactMappings.boundary},infrastructureComplete:findings.length===0&&unfinished.length===0&&emitted.length>0,validation:{schema:'not_run',runtime:'not_run',cloudPlan:'not_run'},deploymentCandidate:false,evidenceBoundary:catalogue.evidenceBoundary};
}
