// Visible configuration diagnostics, never production dispatch or held-out cases.
// Independent test files are added; generated implementation is never patched.
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';
import {compositionFixture} from './composition-fixtures.mjs';import {terraformSketch} from '../../src/terraform.mjs';import {resourcePlan} from '../../src/resources.mjs';
const folder=process.argv[2];if(!folder||fs.existsSync(folder))throw Error('Preserve earlier evidence; choose a fresh folder.');
const regions={aws:['eu-west-1','ap-southeast-2'],azure:['westeurope','australiaeast'],gcp:['europe-west1','australia-southeast1'],ibm:['eu-de','au-syd']},receipts=[];
const block=(name,body)=>name+' {\n'+body+'\n}\n';
const variables=values=>block('variables',Object.entries({...values,review_approved:true}).map(([key,value])=>key+' = '+JSON.stringify(value)).join('\n'));
function mocks(provider,region,values,alias){
 const vpc=Object.entries(values).find(([key])=>key.endsWith('_vpc_id'))?.[1];
 const data=provider==='aws'?['aws_subnet','aws_security_group'].map(type=>block('mock_data "'+type+'"','defaults = '+JSON.stringify({vpc_id:vpc}))).join('\n'):provider==='azure'?block('mock_data "azurerm_container_app_environment"','defaults = '+JSON.stringify({id:values.environment_id,location:region})):provider==='ibm'?block('mock_data "ibm_code_engine_project"','defaults = '+JSON.stringify({id:values.code_engine_project_id,region,account_id:values.account_id})):'';
 return block('mock_provider "'+({azure:'azurerm',gcp:'google'}[provider]||provider)+'"',(alias?'alias = '+JSON.stringify(alias)+'\n':'')+data);
}
function childOracle(provider,region,tf,values,address){
 let text=mocks(provider,region,values)+variables(values)+block('run "independent_accepted_placement"','command = plan\nassert {\n condition = var.region == '+JSON.stringify(region)+'\n error_message = "The accepted region was changed."\n}');
 if(provider==='gcp')text+=block('run "independent_cloud_run_location"','command = plan\nassert {\n condition = google_cloud_run_v2_service.'+address+'.location == '+JSON.stringify(region)+'\n error_message = "Cloud Run uses another region."\n}');
 if(['azure','ibm'].includes(provider)){
  const type=provider==='azure'?'azurerm_container_app_environment':'ibm_code_engine_project',resource=provider==='azure'?'azurerm_container_app':'ibm_code_engine_app',good=provider==='azure'?{id:values.environment_id,location:region}:{id:values.code_engine_project_id,region,account_id:values.account_id};
  for(const mutation of ['region','identity']){
   const bad={...good};if(mutation==='region')bad[provider==='azure'?'location':'region']=regions[provider][1];else if(provider==='azure')bad.id=values.environment_id.replace('11111111-1111-1111-1111-111111111111','22222222-2222-2222-2222-222222222222');else bad.account_id='22222222222222222222222222222222';
   text+=block('run "independent_reject_foreign_'+mutation+'"','command = plan\n'+block('override_data','target = data.'+type+'.'+address+'\nvalues = '+JSON.stringify(bad))+'expect_failures = ['+resource+'.'+address+']');
  }
 }
 return text;
}
function write(name,project,rootOracle=false){
 const files=terraformSketch(project),plan=resourcePlan(project),tf=JSON.parse(files['main.tf.json']);
 for(const [file,body]of Object.entries(files)){const target=path.join(folder,name,file);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,body);}
 const oracles=[];
 if(rootOracle){
  const values=JSON.parse(files['deployment.tfvars.json.example']);let test='';
  for(const unit of plan.composition.units){const childValues=JSON.parse(files[unit.path+'/deployment.tfvars.json.example']),node=project.nodes.find(n=>n.id===unit.id);test+=mocks(node.data.provider,node.data.config.region,childValues,unit.module);}
  test+=variables(values);const checks=plan.composition.units.map(unit=>'var.'+unit.module+'__region == '+JSON.stringify(project.nodes.find(n=>n.id===unit.id).data.config.region));
  test+=block('run "independent_distinct_regions_plan_together"','command = plan\nassert {\n condition = '+checks.join(' && ')+'\n error_message = "A unit lost its accepted placement."\n}');
  const first=plan.composition.units[0],provider=project.nodes.find(n=>n.id===first.id).data.provider;
  test+=block('run "independent_changed_accepted_region_blocked"','command = plan\n'+block('variables',first.module+'__region = '+JSON.stringify(regions[provider][1]))+'expect_failures = [var.'+first.module+'__region]');
  const relative='tests/independent-placement.tftest.hcl';fs.mkdirSync(path.join(folder,name,'tests'),{recursive:true});fs.writeFileSync(path.join(folder,name,relative),test);oracles.push({path:relative,sha256:createHash('sha256').update(test).digest('hex')});
 }else{
  const node=project.nodes.at(-1),unit=plan.composition?.units.find(u=>u.id===node.id),prefix=unit?unit.path+'/':'',child=JSON.parse(files[prefix+'main.tf.json']),values=JSON.parse(files[prefix+'deployment.tfvars.json.example']),address=plan.rows.find(r=>r.id===node.id).address;
  const test=childOracle(node.data.provider,node.data.config.region,child,values,address),relative=prefix+'tests/independent-placement.tftest.hcl';fs.writeFileSync(path.join(folder,name,relative),test);oracles.push({path:relative,sha256:createHash('sha256').update(test).digest('hex')});
 }
 fs.writeFileSync(path.join(folder,name+'-project.json'),JSON.stringify(project,null,2)+'\n');
 receipts.push({name,projectId:project.id,units:plan.composition?.units||[],rootOracle,oracles,generatedDigests:Object.fromEntries(Object.entries(files).map(([file,body])=>[file,createHash('sha256').update(body).digest('hex')]))});
}
for(const [provider,[first,second]]of Object.entries(regions)){
 const p=compositionFixture(provider),node=p.nodes.at(-1);node.data.config={region:first};write(provider+'-mixed',p);write(provider+'-standalone',{...p,nodes:[node],edges:[]});
 const other=structuredClone(node);other.id='separate-inventory';other.data.label='Independent inventory application';other.data.config.region=second;write(provider+'-two-regions',{...p,name:'Independent regional instruments',requirements:'Preserve two independent supplied-image responsibilities and their distinct accepted regions.',needs:[],nodes:[node,other],edges:[]},true);
}
fs.writeFileSync(path.join(folder,'receipt.json'),JSON.stringify({cases:receipts,boundary:'Visible accepted-placement/ownership diagnostics. Independent assertions are test harness only; implementation remains unmodified. Native schema/mock execution recorded separately.'},null,2)+'\n');console.log('Generated twelve standalone/mixed/two-region placement probes at '+folder);
