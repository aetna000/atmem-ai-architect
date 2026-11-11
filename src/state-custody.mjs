import {protectedState,PROTECTED_BACKENDS} from './protected-state.mjs';
const plain=value=>!!value&&typeof value==='object'&&!Array.isArray(value)&&[Object.prototype,null].includes(Object.getPrototypeOf(value));
const only=(value,keys)=>{if(!plain(value)||Object.keys(value).some(k=>!keys.includes(k)))throw Error('Invalid Terraform state custody contract; no fields were discarded.');};
export function validateStateCustody(value){
 if(value===undefined)return;
 only(value,['version','environments']);if(value.version!==1)throw Error('Unsupported Terraform state custody version.');
 only(value.environments,['staging','production','qualification']);
 for(const entry of Object.values(value.environments)){
  only(entry,['backend','owner','residency','decisionId']);
  if(!PROTECTED_BACKENDS.includes(entry.backend))throw Error('Unsupported state backend; preserve its existing ownership and implement its adapter without substitution.');
  for(const [field,max]of [['owner',120],['residency',500],['decisionId',60]])if(typeof entry[field]!=='string'||!entry[field].trim()||[...entry[field]].length>max)throw Error('Invalid state custody '+field+'; no value was truncated.');
 }
}
export function stateCustody(project,environment){
 const value=project.extensions?.terraformState;validateStateCustody(value);return value?.environments[environment]||null;
}
export function applyStateCustody(project,environment,files){
 const selection=stateCustody(project,environment);if(!selection)return files;
 const config=JSON.parse(files['main.tf.json']),state=protectedState(selection.backend,{environment});
 if(config.terraform.cloud)throw Error('Preserve the existing cloud state owner; do not overwrite it with another backend.');
 config.terraform.backend=state.backend;
 config.terraform.required_version=[...new Set([...(config.terraform.required_version||'').split(', ').filter(Boolean),'>= 1.10.0','< 2.0.0'])].join(', ');
 const blocker='state-custody-and-operations-acceptance-required';
 config.locals??={};config.locals.unfinished_work=[...new Set([...(config.locals.unfinished_work||[]),blocker])];
 const decision=(project.decisions||[]).find(d=>d.id===selection.decisionId);
 const record={version:1,environment,selection:structuredClone(selection),decisionStatus:decision?.status||'missing',scope:'whole-project-root',acceptance:'not_verified',migrationAuthorized:false,backendAccessValidated:false,blocker,units:config.module?Object.keys(config.module).sort():[],boundary:'Explicit state contract and retained owner/residency intent, not account access, locking/recovery proof or migration approval.'};
 const guide='\n## Current state custody\n\nRead state-custody.json. Backend selection is explicit and independent of the application target cloud. Its owner, residency and linked decision remain design records, not verified backend behavior. No application resource is used as the state store. The acceptance blocker remains even if the linked decision is Accepted.\n\nKeep distinct state keys for environments and workspaces. Before any authorized migration: identify the current backend and workspace, record lineage/serial and a private encrypted backup digest, stop competing writers, test locking and recovery on an isolated approved state, review the migration, and verify lineage/resources after it. Never migrate or reconfigure merely to clear initialization errors. No cloud access, migration or apply is authorized by this package.\n';
 const ignore=(files['.gitignore']||'')+'\n# State custody: local backend metadata, plans and private inputs stay outside source.\n.terraform/\n*.tfstate*\n*.tfplan\nbackend.hcl\n';
 return {...files,...state.files,'.gitignore':ignore,'STATE.md':state.files['STATE.md']+guide,'state-custody.json':JSON.stringify(record,null,2)+'\n','main.tf.json':JSON.stringify(config,null,2)+'\n','README.md':(files['README.md']||'')+'\n## Explicit state custody\n\nRead STATE.md and state-custody.json for the selected whole-project backend. Its acceptance and operating responsibilities remain blocking; child units do not select state. This section governs state selection over any older adapter-default backend text above.\n'};
}
