// Evaluation-only native assertions; never alter generated implementation bytes.
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';
const folder=process.argv[2],manifest=JSON.parse(fs.readFileSync(path.join(folder,'receipt.json'),'utf8'));
for(const entry of manifest.cases){
 if(entry.rootOracle)continue;
 const provider=entry.name.split('-')[0],unit=entry.units.find(u=>u.implementation==='container-service'),prefix=unit?unit.path+'/':'',root=path.join(folder,entry.name),tf=JSON.parse(fs.readFileSync(path.join(root,prefix+'main.tf.json'),'utf8')),values=JSON.parse(fs.readFileSync(path.join(root,prefix+'deployment.tfvars.json.example'),'utf8'));
 const name=Object.keys(tf.variable).find(k=>k.endsWith('_image')).slice(0,-6),local={azure:'azurerm',gcp:'google'}[provider]||provider;
 let text='mock_provider "'+local+'" {\n override_during = plan\n';
 if(provider==='aws')text+='mock_data "aws_partition" { defaults = {partition = "aws"} }\n';
 if(provider==='aws')text+='mock_resource "aws_cloudwatch_log_group" {\n override_during = plan\n defaults = {arn = "arn:aws:logs:'+values.region+':123456789012:log-group:/fixture/owned"}\n}\n';
 if(provider==='gcp')text+='mock_resource "google_service_account" {\n override_during = plan\n defaults = {email = "fixture@reviewed-project.iam.gserviceaccount.com"}\n}\n';
 if(provider==='aws')for(const type of ['aws_subnet','aws_security_group'])text+='mock_data "'+type+'" { defaults = '+JSON.stringify({vpc_id:values[name+'_vpc_id']})+' }\n';
 if(provider==='azure')text+='mock_data "azurerm_container_app_environment" { defaults = '+JSON.stringify({id:values.environment_id,location:values.region})+' }\n';
 if(provider==='ibm')text+='mock_data "ibm_code_engine_project" { defaults = '+JSON.stringify({id:values.code_engine_project_id,region:values.region,account_id:values.account_id})+' }\n';
 text+='}\nvariables {\n'+Object.entries({...values,review_approved:true}).map(([key,value])=>key+' = '+JSON.stringify(value)).join('\n')+'\n}\n';
 const assertion=(label,condition)=>'run "independent_'+label+'" {\n command = plan\n assert {\n condition = '+condition+'\n error_message = "The native supplied-image safeguard changed."\n }\n}\n';
 const identity={azure:'azurerm_container_app.'+name+'.identity[0].type == "SystemAssigned"',gcp:'google_cloud_run_v2_service.'+name+'.template[0].service_account == google_service_account.'+name+'.email && google_cloud_run_v2_service.'+name+'.deletion_protection == true',ibm:'ibm_code_engine_app.'+name+'.run_service_account == "none"'};
 if(provider!=='aws')text+=assertion('native_runtime_identity',identity[provider]);
 else{
  const policy='jsondecode(aws_iam_role_policy.'+name+'.policy)',trust='jsondecode(aws_iam_role.'+name+'_task.assume_role_policy)';
  text+=assertion('native_execution_scope','length('+policy+'.Statement[0].Action) == 1 && '+policy+'.Statement[0].Action[0] == "ecr:GetAuthorizationToken" && '+policy+'.Statement[1].Resource == var.'+name+'_repository_arn && length('+policy+'.Statement) == 3');
  text+=assertion('native_trust_scope',trust+'.Statement[0].Principal.Service == "ecs-tasks.amazonaws.com" && '+trust+'.Statement[0].Condition.StringEquals["aws:SourceAccount"] == var.account_id && '+trust+'.Statement[0].Condition.ArnLike["aws:SourceArn"] == "arn:aws:ecs:${var.region}:${var.account_id}:*"');
  text+='run "independent_wildcard_repository_denied" {\n command = plan\n variables { '+name+'_repository_arn = "*" }\n expect_failures = [var.'+name+'_repository_arn]\n}\n';
  for(const [type,key]of [['aws_subnet','subnets'],['aws_security_group','security_groups']])text+='run "independent_foreign_'+type+'_vpc_denied" {\n command = plan\n override_data {\n target = data.'+type+'.'+name+'['+JSON.stringify(values[name+'_'+key][0])+']\n values = {vpc_id = "vpc-33333333333333333"}\n }\n expect_failures = [aws_ecs_service.'+name+']\n}\n';
 }
 const relative=prefix+'tests/independent-safeguards.tftest.hcl',file=path.join(root,relative);if(fs.existsSync(file))throw Error('Preserve existing oracle files.');fs.writeFileSync(file,text);entry.oracles.push({path:relative,sha256:createHash('sha256').update(text).digest('hex')});
}
fs.writeFileSync(path.join(folder,'receipt.json'),JSON.stringify(manifest,null,2)+'\n');console.log('Added independent native safeguards to eight unit packages.');
