// Independent visible partition probes. SOURCE may be a frozen before checkout.
import fs from 'node:fs';import path from 'node:path';import {pathToFileURL} from 'node:url';import {createHash} from 'node:crypto';
import {compositionFixture} from './composition-fixtures.mjs';
const folder=process.argv[2],source=process.argv[3]||path.resolve('.'),before=process.argv[4]==='before';
if(!folder||fs.existsSync(folder))throw Error('Preserve earlier output; choose a fresh folder.');
const {terraformSketch}=await import(pathToFileURL(path.join(source,'src/terraform.mjs'))),{resourcePlan}=await import(pathToFileURL(path.join(source,'src/resources.mjs')));
const cases=[],regions=[['eu-west-1','aws'],['cn-north-1','aws-cn'],['cn-northwest-1','aws-cn'],['us-gov-west-1','aws-us-gov'],['us-gov-east-1','aws-us-gov']];
function mocks(partition,region,values,alias){
 const name=Object.keys(values).find(k=>k.endsWith('_image')).slice(0,-6);
 return 'mock_provider "aws" {\n'+(alias?'alias = '+JSON.stringify(alias)+'\n':'')+'override_during = plan\nmock_data "aws_partition" { defaults = {partition = '+JSON.stringify(partition)+'} }\n'+['aws_subnet','aws_security_group'].map(type=>'mock_data "'+type+'" {defaults = '+JSON.stringify({vpc_id:values[name+'_vpc_id']})+'}').join('\n')+'\nmock_resource "aws_cloudwatch_log_group" {\n override_during = plan\n defaults = {arn = "arn:'+partition+':logs:'+region+':123456789012:log-group:/fixture/owned"}\n}\n}\n';
}
function write(name,project,expected,rootOracle=false){
 const files=terraformSketch(project),plan=resourcePlan(project),root=JSON.parse(files['main.tf.json']),oracles=[];
 for(const [file,body]of Object.entries(files)){const target=path.join(folder,name,file);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,body);}
 let test='',prefix='',values;
 if(rootOracle){
  values=JSON.parse(files['deployment.tfvars.json.example']);
  for(const unit of plan.composition.units){const node=project.nodes.find(n=>n.id===unit.id),[region,partition]=expected.find(([r])=>r===node.data.config.region),inputs=JSON.parse(files[unit.path+'/deployment.tfvars.json.example']);test+=mocks(partition,region,inputs,unit.module);}
 }else{
  const unit=plan.composition?.units.find(u=>u.implementation==='container-service');prefix=unit?unit.path+'/':'';values=JSON.parse(files[prefix+'deployment.tfvars.json.example']);test+=mocks(expected[0][1],expected[0][0],values);
 }
 test+='variables {\n'+Object.entries({...values,review_approved:true}).map(([key,value])=>key+' = '+JSON.stringify(value)).join('\n')+'\n}\n';
 if(rootOracle){
  const conditions=plan.composition.units.map(unit=>'var.'+unit.module+'__region == '+JSON.stringify(project.nodes.find(n=>n.id===unit.id).data.config.region));
  test+='run "independent_partition_units_plan_together" {\n command = plan\n assert {\n condition = '+conditions.join(' && ')+'\n error_message = "Partition units lost their selected regions."\n}\n}\n';
 }else{
  const [region,partition]=expected[0],name=Object.keys(values).find(k=>k.endsWith('_image')).slice(0,-6);
  test+='run "independent_exact_partition_trust" {\n command = plan\n assert {\n condition = jsondecode(aws_iam_role.'+name+'_task.assume_role_policy).Statement[0].Condition.ArnLike["aws:SourceArn"] == '+JSON.stringify('arn:'+partition+':ecs:'+region+':123456789012:*')+'\n error_message = "Native role trust uses the wrong requested partition or region."\n}\n}\n';
  if(!before){
   test+='run "independent_native_partition_value" {\n command = plan\n assert {\n condition = data.aws_partition.'+name+'.partition == '+JSON.stringify(partition)+' && var.region == '+JSON.stringify(region)+'\n error_message = "Native partition/region was changed."\n}\n}\n';
   const foreign=partition==='aws'?'aws-cn':'aws',bad=values[name+'_repository_arn'].replace('arn:'+partition+':','arn:'+foreign+':');
   test+='run "independent_cross_partition_repository_denied" {\n command = plan\n variables { '+name+'_repository_arn = '+JSON.stringify(bad)+' }\n expect_failures = [aws_iam_role_policy.'+name+']\n}\n';
   const wrongRegion=values[name+'_repository_arn'].replace(':ecr:'+region+':',':ecr:'+(partition==='aws'?'cn-north-1':'eu-west-1')+':');
   test+='run "independent_repository_region_family_denied" {\n command = plan\n variables { '+name+'_repository_arn = '+JSON.stringify(wrongRegion)+' }\n expect_failures = [aws_iam_role_policy.'+name+']\n}\n';
   const coherentForeign='arn:'+foreign+':ecr:'+(foreign==='aws-cn'?'cn-northwest-1':'us-east-1')+':123456789012:repository/independent';
   test+='run "independent_provider_region_partition_denied" {\n command = plan\n variables { '+name+'_repository_arn = '+JSON.stringify(coherentForeign)+' }\n override_data {\n target = data.aws_partition.'+name+'\n values = {partition = '+JSON.stringify(foreign)+'}\n }\n expect_failures = [aws_ecs_service.'+name+']\n}\n';
  }
 }
 const relative=prefix+'tests/independent-partition.tftest.hcl';fs.mkdirSync(path.join(folder,name,prefix+'tests'),{recursive:true});fs.writeFileSync(path.join(folder,name,relative),test);oracles.push({path:relative,sha256:createHash('sha256').update(test).digest('hex')});
 fs.writeFileSync(path.join(folder,name+'-project.json'),JSON.stringify(project,null,2)+'\n');cases.push({name,rootOracle,units:plan.composition?.units||[],oracles,expected,generatedDigests:Object.fromEntries(Object.entries(files).map(([file,body])=>[file,createHash('sha256').update(body).digest('hex')]))});
}
for(const [region,partition]of before?[regions[1]]:regions){const p=compositionFixture('aws'),node=p.nodes.at(-1);node.data.config={region};write(region,{...p,nodes:[node],edges:[]},[[region,partition]]);}
if(!before){
 const p=compositionFixture('aws');p.nodes.at(-1).data.config={region:'cn-north-1'};write('commercial-invoice-china-container',p,[regions[1]]);
 const all=compositionFixture('aws'),prototype=all.nodes.at(-1);all.nodes=[regions[0],regions[1],regions[3]].map(([region],i)=>({...structuredClone(prototype),id:'independent-partition-'+i,data:{...prototype.data,config:{region}}}));all.edges=[];all.needs=[];all.requirements='Keep three independent supplied-image responsibilities in their explicitly chosen AWS partitions; do not infer a cross-partition connection.';write('three-independent-partitions',all,[regions[0],regions[1],regions[3]],true);
}
fs.writeFileSync(path.join(folder,'receipt.json'),JSON.stringify({cases,boundary:'Generated implementation unchanged; separate independent mock plan oracles. ARN/region contract only, not service availability or account behavior.'},null,2)+'\n');console.log('Generated '+cases.length+' partition packages.');
