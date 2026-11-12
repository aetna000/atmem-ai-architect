import test from 'node:test';import assert from 'node:assert/strict';
import {compositionFixture} from '../scripts/engine-evaluation/composition-fixtures.mjs';
import {terraformSketch} from '../src/terraform.mjs';import {resourcePlan} from '../src/resources.mjs';import {generationQuality} from '../src/generation-quality.mjs';
for(const cloud of ['aws','azure','gcp','ibm'])test(cloud+': independent security inspection retains lifecycle, image and destination safeguards',()=>{
 const project=compositionFixture(cloud),plan=resourcePlan(project),files=terraformSketch(project),unit=plan.composition.units.find(u=>u.implementation==='container-service'),key=unit.path+'/main.tf.json',name=plan.rows.at(-1).address;
 assert.equal(JSON.parse(files['generation-quality.json']).infrastructureComplete,true);
 for(const mutation of ['destroy','ignore','image','instances','gate','provider']){
  const changed={...files},config=JSON.parse(files[key]),root=JSON.parse(files['main.tf.json']);
  const type=Object.keys(config.resource).find(t=>t!=='terraform_data'),body=Object.values(config.resource[type])[0];
  if(mutation==='destroy')body.lifecycle.prevent_destroy=false;
  if(mutation==='ignore')body.lifecycle.ignore_changes='all';
  if(mutation==='image')config.variable[name+'_image'].validation.condition='${true}';
  if(mutation==='instances')body.count=2;
  if(mutation==='gate')body.depends_on=[];
  if(mutation==='provider'){const local={aws:'aws',azure:'azurerm',gcp:'google',ibm:'ibm'}[cloud];root.provider[local].find(p=>p.alias===unit.module).endpoints={unreviewed:'https://foreign.invalid'};}
  changed[key]=JSON.stringify(config);changed['main.tf.json']=JSON.stringify(root);
  assert(generationQuality(project,plan,changed).fatalFindings.some(f=>f.code==='container-constraint-mismatch'),mutation);
 }
});
test('AWS role/resource identity is insufficient when the actual trust, grants or task has changed',()=>{
 const p=compositionFixture('aws'),plan=resourcePlan(p),files=terraformSketch(p),unit=plan.composition.units.find(u=>u.implementation==='container-service'),key=unit.path+'/main.tf.json',name=plan.rows.at(-1).address;
 for(const mutation of ['administrator','task-grant','trust-principal','source-account','source-arn','policy-role','repository','repository-guard','account-guard','task','cluster','execute','extra-container','image','log-group','privileged','subnet-vpc','group-vpc','lookup-region','lookup-id','subnet-binding']){
  const changed={...files},tf=JSON.parse(files[key]),root=JSON.parse(files['main.tf.json']),resources=tf.resource,service=resources.aws_ecs_service[name],task=resources.aws_ecs_task_definition[name];
  const policy=resources.aws_iam_role_policy[name],trust=JSON.parse(resources.aws_iam_role[name].assume_role_policy),permissions=JSON.parse(policy.policy),containers=JSON.parse(task.container_definitions);
  if(mutation==='administrator')permissions.Statement=[{Effect:'Allow',Action:'*',Resource:'*'}];
  if(mutation==='task-grant')resources.aws_iam_role[name+'_task'].inline_policy={name:'unowned',policy:JSON.stringify({Statement:[{Action:'*',Resource:'*',Effect:'Allow'}]})};
  if(mutation==='trust-principal')trust.Statement[0].Principal={AWS:'*'};
  if(mutation==='source-account')delete trust.Statement[0].Condition.StringEquals;
  if(mutation==='source-arn')trust.Statement[0].Condition.ArnLike['aws:SourceArn']='*';
  if(mutation==='policy-role')policy.role='${aws_iam_role.'+name+'_task.id}';
  if(mutation==='repository')permissions.Statement[1].Resource='*';
  if(mutation==='repository-guard')tf.variable[name+'_repository_arn'].validation.condition='${true}';
  if(mutation==='account-guard')delete root.provider.aws.find(p=>p.alias===unit.module).allowed_account_ids;
  if(mutation==='task')service.task_definition='foreign-task';if(mutation==='cluster')service.cluster='foreign-cluster';if(mutation==='execute')service.enable_execute_command=true;
  if(mutation==='extra-container')containers.push({name:'unowned',image:'unowned:latest'});
  if(mutation==='image')containers[0].image='unowned:latest';if(mutation==='log-group')containers[0].logConfiguration.options['awslogs-group']='unowned';if(mutation==='privileged')containers[0].privileged=true;
  if(mutation==='subnet-vpc'||mutation==='group-vpc')service.lifecycle.precondition.splice(mutation==='subnet-vpc'?0:1,1);
  if(mutation==='lookup-region')tf.data.aws_subnet[name].region='us-east-1';if(mutation==='lookup-id')tf.data.aws_security_group[name].id='sg-22222222222222222';if(mutation==='subnet-binding')service.network_configuration.subnets=['subnet-22222222222222222'];
  policy.policy=JSON.stringify(permissions);resources.aws_iam_role[name].assume_role_policy=JSON.stringify(trust);task.container_definitions=JSON.stringify(containers);
  changed[key]=JSON.stringify(tf);changed['main.tf.json']=JSON.stringify(root);
  assert(generationQuality(p,plan,changed).fatalFindings.some(f=>f.code==='container-constraint-mismatch'),mutation);
 }
});
test('independent policy comparison tolerates JSON ordering but preserves complete grant scope',()=>{
 const p=compositionFixture('aws'),plan=resourcePlan(p),files=terraformSketch(p),unit=plan.composition.units.find(u=>u.implementation==='container-service'),key=unit.path+'/main.tf.json',tf=JSON.parse(files[key]),policy=Object.values(tf.resource.aws_iam_role_policy)[0],body=JSON.parse(policy.policy);
 body.Statement.reverse();for(const statement of body.Statement)statement.Action.reverse();policy.policy=JSON.stringify({Statement:body.Statement,Version:body.Version});
 assert.deepEqual(generationQuality(p,plan,{...files,[key]:JSON.stringify(tf)}).fatalFindings,[]);
});
