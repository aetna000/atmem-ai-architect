import {stateCustody} from './state-custody.mjs';
import {generationProviders} from './generation-provider.mjs';
import stateProbe from './runtime/state-contract-check-source.json' with {type:'json'};
import {sha256} from '@noble/hashes/sha2.js';
const stable=value=>JSON.stringify(value,(_,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,v[k]])):v);
// Independent backend/settings closure. Never trust emitted custody metadata as
// authority to select an endpoint, weaken TLS/auth/locking or accept migration.
export function inspectStateCustody(project,plan,files,root,environment,add){
 const fail=message=>add('state-custody-mismatch',message),selection=stateCustody(project,environment);
 for(const path of Object.keys(files))if(/(^|\/)backend[.]hcl$|[.]tfstate(?:[.]|$)|[.]tfplan$|(^|\/)[.]terraform\//.test(path))fail('Private backend inputs, local metadata, state and saved plans do not belong in generated source.');
 const policies={s3:{encrypt:true,use_lockfile:true},azurerm:{use_azuread_auth:true},gcs:{},http:{}};
 let expected;
 if(selection)expected={[selection.backend]:policies[selection.backend]};
 else if(environment==='production'&&!plan.composition&&!project.nodes.some(n=>n.data.implementation==='container-service')){
  if(plan.invoicePlan?.entries.length===1){const provider=plan.invoicePlan.entries[0].row.provider;expected={[{aws:'s3',azure:'azurerm',gcp:'gcs',ibm:'http'}[provider]]:policies[{aws:'s3',azure:'azurerm',gcp:'gcs',ibm:'http'}[provider]]};}
  else if(generationProviders(project).join(',')==='aws'&&!plan.publicFaqPlan?.entries.length&&!project.nodes.some(n=>n.data.implementation==='invoice-workflow'))expected={s3:policies.s3};
 }
 if(root.terraform?.cloud!==undefined||stable(root.terraform?.backend)!==stable(expected))fail('Root state configuration does not match explicit project custody or the established adapter policy. No destination, credential or TLS/locking override is admitted.');
 if(!selection){if(files['state-custody.json']!==undefined)fail('Custody metadata claims an absent project state selection.');return;}
 let record;try{record=JSON.parse(files['state-custody.json']);}catch{fail('The root state custody record is missing or invalid.');return;}
 const decision=(project.decisions||[]).find(d=>d.id===selection.decisionId);
 if(record.version!==1||record.blocker!=='state-custody-and-operations-acceptance-required'||record.environment!==environment||stable(record.selection)!==stable(selection)||record.scope!=='whole-project-root'||record.decisionStatus!==(decision?.status||'missing')||record.acceptance!=='not_verified'||record.migrationAuthorized!==false||record.backendAccessValidated!==false||stable(record.units)!==stable(Object.keys(root.module||{}).sort()))fail('State custody metadata changed owner, residency, decision, unit scope or unverified acceptance.');
 const probe=files['state-contract-check.py'];
 const hash=typeof probe==='string'?Array.from(sha256(new TextEncoder().encode(probe)),v=>v.toString(16).padStart(2,'0')).join(''):null;
 if(hash!==stateProbe.sha256||stable(record.localProbe)!==stable({file:'state-contract-check.py',sha256:stateProbe.sha256,scope:'isolated-loopback-http-state-protocol',status:'not_run',selectedBackendVerified:false}))fail('The local state protocol probe changed its reviewed source or falsely claims selected-backend verification.');
 if(!root.locals?.unfinished_work?.includes('state-custody-and-operations-acceptance-required'))fail('Selecting a state backend cannot clear custody/operations acceptance.');
 if(root.variable?.review_approved?.default!==false)fail('State selection cannot grant deployment review approval.');
 for(const name of ['STATE.md','backend.hcl.example'])if(typeof files[name]!=='string'||!files[name].trim())fail('The explicit state backend is missing its operating guide or private input example.');
 if(!files['.gitignore']?.split('\n').includes('backend.hcl'))fail('Private backend inputs must remain outside source control.');
 const examples={s3:['bucket','key','region'],azurerm:['storage_account_name','container_name','key','tenant_id','subscription_id'],gcs:['bucket','prefix'],http:['address','lock_address','unlock_address','lock_method','unlock_method','retry_wait_min']};
 const values={};
 for(const line of (files['backend.hcl.example']||'').trim().split('\n')){
  const match=/^([a-z_]+) = ("[^"\r\n]*"|[0-9]+)$/.exec(line);
  if(!match||Object.hasOwn(values,match[1])){fail('The backend input example contains unreviewed expressions, fields or duplicate settings.');continue;}
  values[match[1]]=JSON.parse(match[2]);
 }
 if(stable(Object.keys(values).sort())!==stable(examples[selection.backend].sort()))fail('The backend input example changed its reviewed field contract.');
 if(selection.backend==='http'){
  const base='https://REVIEWED_PRIVATE_STATE_SERVICE/EXACT_PROJECT_'+environment.toUpperCase()+'_STATE';
  if(values.address!==base||values.lock_address!==base+'/lock'||values.unlock_address!==base+'/lock'||values.lock_method!=='POST'||values.unlock_method!=='DELETE'||values.retry_wait_min!==5)fail('The HTTP example lost its environment-specific HTTPS state/lock protocol.');
 }else{
  for(const value of Object.values(values))if(typeof value!=='string'||!value.startsWith('REVIEWED_')||/[${}\s]/.test(value))fail('The committed backend input example must remain placeholders without credentials or expressions.');
  if(['s3','azurerm'].includes(selection.backend)&&!values.key?.endsWith('/'+environment+'.tfstate')||selection.backend==='gcs'&&!values.prefix?.endsWith('/'+environment))fail('The backend example lost its environment-specific state namespace.');
 }
}
