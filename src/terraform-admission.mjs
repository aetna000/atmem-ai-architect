import catalogue from '../agent-skills/generation-capabilities.json' with {type:'json'};
import {existingDeployment} from './deployment-ownership.mjs';
import {deliveryUnitName} from './terraform-composition.mjs';
import {relocateTerraformValues} from './terraform-expressions.mjs';
const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const reference=name=>'${var.'+name+'}';
const gated=config=>config.variable?.review_approved?.type==='bool'&&config.variable.review_approved.default===false&&Array.isArray(config.resource?.terraform_data?.review_gate?.lifecycle?.precondition)&&config.resource.terraform_data.review_gate.lifecycle.precondition.some(p=>typeof p?.condition==='string'&&p.condition.includes('var.review_approved'));
// Admission derives ownership/paths from the project and reviewed catalogue, never
// from a module's self-reported manifest. It inspects only the emitted file map.
export function inspectTerraformModules(project,plan,files,root,add){
 const configs=[{path:'',prefix:'',config:root}],scopes=new Map();
 const eligible=project.nodes.filter(n=>n.data.kind!=='note'&&!existingDeployment(n)&&catalogue.contracts.some(c=>c.deliveryUnit&&(!c.deliveryUnit.proposedOnly||n.data.origin==='proposed')&&c.provider===n.data.provider&&c.service===n.data.service&&c.implementation===n.data.implementation));
 const expected=eligible.length>=2?eligible.map(n=>({id:n.id,implementation:n.data.implementation,module:deliveryUnitName(n.id),path:'units/'+deliveryUnitName(n.id)})).sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0):[];
 const active=plan.composition?.version===1&&expected.length>=2;
 const allowedFiles=new Set(['main.tf.json']),allowedAliases=new Set(),expectedOutputs=new Set();
 const fail=(text,id)=>add('unreviewed-module',text,id);
 if(!active){if(Object.keys(root.module||{}).length)fail('Module dependencies require a reviewed project-owned capability; arbitrary module sources are not admitted.');}
 else{
  if(!equal(plan.composition.units,expected))fail('The claimed composition units do not match the current project and reviewed capability catalogue.');
  if(!gated(root)||!root.resource.terraform_data.review_gate.lifecycle.precondition.some(p=>p.condition?.replace(/\s/g,'')==='${var.review_approved&&length(local.unfinished_work)==0}'))add('missing-work-gate','The composition must retain its default-deny approval and unfinished-scope gate.');
  if(Object.keys(root.resource||{}).some(type=>type!=='terraform_data')||Object.keys(root.resource?.terraform_data||{}).some(name=>name!=='review_gate')||Object.keys(root.data||{}).length)fail('Root resources/data outside the composition gate require a separately reviewed adapter.');
  for(const name of Object.keys(root.module||{}))if(!expected.some(u=>u.module===name))fail('An undeclared module was added to the composition: '+name+'.');
  let manifest;try{manifest=JSON.parse(files['composition.json']);}catch{fail('The composition manifest is missing or malformed.');}
  if(manifest&&(manifest.version!==1||!Array.isArray(manifest.units)||manifest.units.length!==expected.length))fail('The composition manifest has unexpected unit identities.');
  for(const unit of expected){
   const args=root.module?.[unit.module],path=unit.path+'/main.tf.json';allowedFiles.add(path);
   const node=project.nodes.find(n=>n.id===unit.id),contract=catalogue.contracts.find(c=>c.deliveryUnit&&c.provider===node.data.provider&&c.service===node.data.service&&c.implementation===node.data.implementation);
   for(const required of contract.deliveryUnit.requiredFiles||[])if(typeof files[unit.path+'/'+required]!=='string'||!files[unit.path+'/'+required].trim())fail('A required unit artifact or native test is missing: '+required+'.',unit.id);
   if(!args||args.source!=='./'+unit.path){fail('The delivery unit must use its exact owned local source: '+unit.path+'.',unit.id);continue;}
   let config;try{config=JSON.parse(files[path]);if(!config||Array.isArray(config)||typeof config!=='object')throw Error();}catch{fail('Missing or invalid owned module configuration: '+path+'.',unit.id);continue;}
   configs.push({path:unit.path,prefix:'module.'+unit.module+'.',config,provider:project.nodes.find(n=>n.id===unit.id).data.provider});scopes.set(unit.id,{path:unit.path,prefix:'module.'+unit.module+'.',config,module:unit.module});
   if(Object.keys(config.module||{}).length||Object.keys(config.provider||{}).length||config.terraform?.backend||config.terraform?.cloud)fail('A child cannot import another module, configure providers or select whole-composition state.',unit.id);
   if(!gated(config))add('missing-work-gate','The delivery unit lost its default-deny approval gate.',unit.id);
   if(!equal(args.depends_on,['terraform_data.review_gate']))add('missing-work-gate','Every delivery unit must depend on the complete composition gate.',unit.id);
   const variables=config.variable||{},names=Object.fromEntries(Object.keys(variables).map(key=>[key,key==='review_approved'?'review_approved':unit.module+'__'+key]));
   const allowedArgs=new Set(['source','providers','depends_on',...Object.keys(variables)]);
   if(Object.keys(args).some(key=>!allowedArgs.has(key)))fail('A module has unreviewed arguments or instance expansion.',unit.id);
   for(const [key,body]of Object.entries(variables)){
    if(args[key]!==reference(names[key])||!root.variable?.[names[key]]){fail('A module input is absent or bound outside its owned current-context namespace: '+key+'.',unit.id);continue;}
    if(key!=='review_approved'){
     const expectedVariable=structuredClone(body);try{if(body.validation)expectedVariable.validation=relocateTerraformValues(body.validation,names);}catch{fail('A child input has an invalid variable-validation closure: '+key+'.',unit.id);continue;}
     if(!equal(root.variable[names[key]],expectedVariable))fail('A root input changed its child type/default/sensitivity/validation contract: '+key+'.',unit.id);
    }
   }
   const required=config.terraform?.required_providers||{};
   if(Object.keys(args.providers||{}).some(key=>!Object.hasOwn(required,key)))fail('A provider binding is not declared by the unit.',unit.id);
   for(const [local,definition]of Object.entries(required)){
    const alias=local+'.'+unit.module,providers=root.provider?.[local],matches=(Array.isArray(providers)?providers:[providers]).filter(p=>p?.alias===unit.module);allowedAliases.add(alias);
    if(args.providers?.[local]!==alias||matches.length!==1)fail('A unit is not bound to its exact declared provider configuration: '+local+'.',unit.id);
    const rootDefinition=root.terraform?.required_providers?.[local];
    if(!rootDefinition||String(rootDefinition.source).toLowerCase()!==String(definition.source).toLowerCase()||!String(rootDefinition.version||'').split(', ').includes(definition.version))fail('Root provider source/version does not retain the child requirement: '+local+'.',unit.id);
   }
   for(const [name,body]of Object.entries(config.output||{})){
    const key=unit.module+'__'+name;expectedOutputs.add(key);const actual=root.output?.[key];
    if(actual?.value!=='${module.'+unit.module+'.'+name+'}'||!!actual?.sensitive!==!!body.sensitive)fail('A published module output changed its unit identity or sensitivity: '+name+'.',unit.id);
   }
   for(const gap of Array.isArray(config.locals?.unfinished_work)?config.locals.unfinished_work:[])if(!Array.isArray(root.locals?.unfinished_work)||!root.locals.unfinished_work.includes(unit.module+':'+gap))add('missing-work-gate','Root unfinished scope omits a child blocker: '+gap+'.',unit.id);
   const record=(Array.isArray(manifest?.units)?manifest.units:[]).find(r=>r?.id===unit.id);
   if(!record||record.module!==unit.module||record.path!==unit.path||record.implementation!==unit.implementation||!equal(record.inputs,names)||!equal(record.providerConfigurations,args.providers)||!equal(record.outputs,Object.keys(config.output||{})))fail('Module metadata does not match the actual project-owned input/provider/output closure.',unit.id);
  }
  for(const [local,values]of Object.entries(root.provider||{}))for(const body of Array.isArray(values)?values:[values])if(!allowedAliases.has(local+'.'+body?.alias))fail('A root provider configuration is not owned by a declared delivery unit.');
  for(const output of Object.keys(root.output||{}))if(!expectedOutputs.has(output))fail('An output outside the declared module closure was added.');
 }
 for(const path of Object.keys(files))if(/\.tf(?:\.json)?$/.test(path)&&!allowedFiles.has(path))fail('Additional Terraform configuration is outside the inspected module closure: '+path+'.');
 return {configs,scopes,composed:active};
}
