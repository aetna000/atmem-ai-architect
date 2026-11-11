import {relocateTerraformValues} from './terraform-expressions.mjs';
// Stable, injective identity. Labels, business domains and array order never dispatch.
export const deliveryUnitName=id=>{
 if(typeof id!=='string'||!id||new TextEncoder().encode(id).length>512)throw Error('Use a nonempty delivery-unit identity within 512 UTF-8 bytes; no identity was clipped.');
 return 'unit_'+Array.from(new TextEncoder().encode(id),b=>b.toString(16).padStart(2,'0')).join('');
};
const encode=value=>JSON.stringify(value,null,2)+'\n';
const expr=value=>'${'+value+'}';
function safePath(path){return typeof path==='string'&&path.length>0&&!path.startsWith('/')&&!path.includes('\\')&&!path.split('/').some(s=>!s||s==='.'||s==='..'||s==='.terraform'||s.includes('\0'));}
function locks(text=''){
 const result=new Map();
 for(const match of text.matchAll(/provider\s+"([^"]+)"\s*\{([^}]+)\}/g)){
  const version=/\bversion\s*=\s*"([^"]+)"/.exec(match[2])?.[1];
  if(!version)throw Error('A composed provider lock is missing its reviewed version.');
  result.set(match[1].toLowerCase(),{version,text:match[0]});
 }
 return result;
}
// Adapter output enters through an explicit package contract. It is generated source,
// never client-supplied Terraform. Linking emits no account plan and invokes no tools.
export function composeTerraformUnits(project,units,{environment='staging',gaps=[]}={}){
 if(!Array.isArray(units)||units.length<2||units.length>64)throw Error('Composition requires 2–64 explicitly compiled delivery units.');
 const names=units.map(u=>deliveryUnitName(u.id));if(new Set(names).size!==names.length)throw Error('Duplicate delivery-unit identity; no files were overwritten.');
 const root={terraform:{required_version:'>= 1.17.1, < 2.0.0',required_providers:{}},provider:{},variable:{review_approved:{type:'bool',default:false}},locals:{unfinished_work:[...gaps,...(environment==='production'?['composition-state-custody-and-operations-review-required']:[])]},resource:{terraform_data:{review_gate:{input:{design_revision:project.revision,environment},lifecycle:{precondition:[{condition:'${var.review_approved && length(local.unfinished_work) == 0}',error_message:'Review the whole composition and implement all preserved scope before planning. Production state and operations require separate acceptance.'}]}}}},module:{},output:{}};
 const files={},examples={review_approved:false},manifest=[],providerLocks=new Map();
 for(const unit of [...units].sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0)){
  if(!unit.files||typeof unit.files['main.tf.json']!=='string')throw Error('A delivery unit must contain its generated main.tf.json.');
  const name=deliveryUnitName(unit.id),path='units/'+name,config=JSON.parse(unit.files['main.tf.json']);
  if(config.terraform?.required_version)root.terraform.required_version=[...new Set([...root.terraform.required_version.split(', '),...config.terraform.required_version.split(', ')])].join(', ');
  if(config.module&&Object.keys(config.module).length)throw Error('Nested modules need a separately reviewed composition contract.');
  if(config.terraform?.backend||config.terraform?.cloud)throw Error('A child delivery unit cannot choose whole-composition state custody. Compile its staging package before linking.');
  if(!config.variable?.review_approved||config.variable.review_approved.type!=='bool'||config.variable.review_approved.default!==false||!config.resource?.terraform_data?.review_gate)throw Error('A delivery unit must preserve its default-deny review gate.');
  if(config.locals?.unfinished_work?.length)root.locals.unfinished_work.push(...config.locals.unfinished_work.map(gap=>name+':'+gap));
  const variableNames=Object.fromEntries(Object.keys(config.variable||{}).map(key=>[key,key==='review_approved'?'review_approved':name+'__'+key]));
  const args={source:'./'+path,providers:{},depends_on:['terraform_data.review_gate']};
  const inputs=JSON.parse(unit.files['deployment.tfvars.json.example']||'{}');
  for(const [key,value]of Object.entries(config.variable||{})){
   const target=variableNames[key];
   if(key!=='review_approved'){
    root.variable[target]=structuredClone(value);
    if(value.validation)root.variable[target].validation=relocateTerraformValues(value.validation,variableNames);
    if(Object.hasOwn(inputs,key))examples[target]=structuredClone(inputs[key]);
   }
   args[key]=expr('var.'+target);
  }
  const unitLocks=locks(unit.files['.terraform.lock.hcl']);
  for(const [local,required]of Object.entries(config.terraform?.required_providers||{})){
   if(!required.source||!required.version)throw Error('Each child provider needs its explicit reviewed source and version.');
   const old=root.terraform.required_providers[local];
   if(old&&old.source.toLowerCase()!==required.source.toLowerCase())throw Error('Conflicting provider source for '+local+'.');
   const source='registry.terraform.io/'+required.source.toLowerCase(),lock=unitLocks.get(source);
   if(!lock)throw Error('Missing reviewed provider lock for '+source+'.');
   if(providerLocks.has(source)&&providerLocks.get(source).version!==lock.version)throw Error('Conflicting reviewed provider versions for '+source+': '+providerLocks.get(source).version+' and '+lock.version+'. Qualify compatible adapters before composing.');
   providerLocks.set(source,lock);
   root.terraform.required_providers[local]={source:required.source,version:[...new Set([...(old?.version.split(', ')||[]),required.version])].join(', ')};
   const configurations=config.provider?.[local];
   if(!configurations||Array.isArray(configurations))throw Error('The child provider configuration requires a reviewed single-instance adapter.');
   if(configurations.alias||required.configuration_aliases)throw Error('Child provider aliases require an explicit reviewed mapping.');
   const alias=name;
   (root.provider[local]||=[]).push({...relocateTerraformValues(configurations,variableNames),alias});
   args.providers[local]=local+'.'+alias;
  }
  if(Object.keys(config.provider||{}).some(key=>!config.terraform?.required_providers?.[key]))throw Error('Undeclared child provider configuration.');
  delete config.provider;
  for(const [output,definition]of Object.entries(config.output||{}))root.output[name+'__'+output]={value:expr('module.'+name+'.'+output),...(definition.sensitive?{sensitive:true}:{})};
  root.module[name]=args;
  for(const [file,body]of Object.entries(unit.files)){
   if(!safePath(file)||typeof body!=='string')throw Error('Delivery-unit output contains an unsupported path or nontext file.');
   if(/(^|\/)backend\.(hcl|tf)$|\.tfstate(?:\.|$)|\.tfplan$/.test(file))throw Error('State, private backend inputs and plans do not belong in composed source.');
   if(file.endsWith('.tf')||file.endsWith('.tf.json')&&file!=='main.tf.json')throw Error('Additional Terraform configuration needs a reviewed module contract.');
   files[path+'/'+file]=file==='main.tf.json'?encode(config):body;
  }
  manifest.push({id:unit.id,module:name,path,implementation:unit.implementation,inputs:variableNames,outputs:Object.keys(config.output||{}),providerConfigurations:args.providers,files:Object.keys(unit.files).sort()});
 }
 root.locals.unfinished_work=[...new Set(root.locals.unfinished_work)].sort();
 files['main.tf.json']=encode(root);files['composition.json']=encode({version:1,units:manifest,boundary:'Generated module/input/provider/file links. Independent schema, runtime and destination checks remain required.'});
 files['deployment.tfvars.json.example']=encode(examples);
 files['.terraform.lock.hcl']='# Reviewed provider locks shared by all delivery units.\n\n'+[...providerLocks].sort(([a],[b])=>a.localeCompare(b)).map(([,lock])=>lock.text+'\n').join('\n');
 files['.gitignore']='.terraform/\n*.tfstate*\n*.tfplan\n*.tfvars\n*.tfvars.json\n!deployment.tfvars.json.example\nbackend.hcl\n';
 files['README.md']='# Composed delivery units\n\nRun Terraform from this root. Review composition.json and every unit README. Each unit retains its own application files, input validations, local tests, resource protections and review gate. Provider configurations and reviewed inputs are explicit at the root; source labels never choose a provider. Tests under a unit run independently from that unit directory with mock providers. Those tests are configuration checks, not application or cloud acceptance.\n\nReview all destination inputs and immutable images, then run terraform init -backend=false and terraform validate. Keep real values and credentials outside source. Do not apply this package without separate authorization and destination acceptance. Production remains blocked until whole-composition state custody and operating responsibilities are implemented and verified; a child cannot choose state for other units. Unsupported required integrations remain unfinished work.\n';
 return files;
}
