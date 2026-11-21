import test from'node:test';
import assert from'node:assert/strict';
import fs from'node:fs';
import {awsDocumentJobTerraform}from'../src/enterprise-aws-infrastructure.mjs';
import bootstrap from'../src/runtime/enterprise-aws-host-bootstrap-source.json'with{type:'json'};
const project={id:'qualification',revision:7},row={id:'knowledge',address:'block_6b6e6f776c65646765',provider:'aws',region:'ap-southeast-2'};
const compile=()=>awsDocumentJobTerraform(project,row,'qualification'),tf=()=>JSON.parse(compile()['main.tf.json']);
test('AWS parser compiler embeds exact host preparation source and inherits one provider',()=>{
 assert.equal(bootstrap,fs.readFileSync(new URL('../src/runtime/enterprise_aws_host_bootstrap.py',import.meta.url),'utf8'));
 const child=JSON.parse(compile()['modules/host-verification/main.tf.json']);assert.equal(child.provider,undefined);
 assert.deepEqual(tf().module.host_verification.providers,{aws:'aws'});
});
test('AWS parser foundation provides no synthetic image, AMI or ready runtime',()=>{
 const main=tf(),examples=JSON.parse(compile()['deployment.tfvars.json.example']);
 for(const key of ['images_ready','hosts_enabled','review_approved'])assert.equal(main.variable[key].default,false);
 for(const key of ['parser_image','transfer_image','host_ami_id','parser_revision'])assert.equal(examples[key],'');
 assert.equal(main.output.document_job_configuration.value,'${var.images_ready && var.hosts_enabled ? local.document_job_configuration : null}');
 assert.equal(main.data.aws_ami[row.address+'_host'].owners[0],'amazon');
 assert.equal(main.variable.host_count.default,2);
});
test('AWS parser network has two private subnets, endpoint-only egress and no public routes',()=>{
 const main=tf(),resources=main.resource;
 for(const type of ['aws_internet_gateway','aws_nat_gateway','aws_eip','aws_route'])assert.equal(resources[type],undefined);
 assert.equal(Object.keys(resources.aws_subnet).length,2);assert.equal(Object.keys(resources.aws_vpc_endpoint).length,8);
 for(const subnet of Object.values(resources.aws_subnet))assert.equal(subnet.map_public_ip_on_launch,false);
 assert.equal(Object.keys(resources.aws_vpc_security_group_egress_rule).length,2);
 assert.equal(Object.keys(resources.aws_vpc_security_group_ingress_rule).length,1);
 assert.ok(!JSON.stringify(resources.aws_vpc_security_group_ingress_rule).includes('0.0.0.0/0'));
 assert.ok(!JSON.stringify(resources.aws_vpc_endpoint).includes('ec2messages'));
});
test('AWS parser task and worker retain exact lifecycle and authority separation',()=>{
 const main=tf(),name=row.address,task=main.resource.aws_ecs_task_definition[name];
 assert.equal(task.network_mode,'bridge');assert.deepEqual(task.requires_compatibilities,['EC2']);
 assert.ok(main.locals.task_definition.containerDefinitions[1].disableNetworking);
 const actions=Object.values(main.locals).filter(value=>value&&value.Statement).flatMap(value=>value.Statement.flatMap(row=>row.Action));
 for(const forbidden of ['ecs:RegisterTaskDefinition','ecs:DeregisterTaskDefinition','ecs:DeleteTaskDefinitions','ecs:ExecuteCommand','ssm:GetParameter','secretsmanager:GetSecretValue','ecs:CreateCluster'])assert.ok(!actions.includes(forbidden),forbidden);
 const run=main.locals.worker_policy.Statement.find(value=>value.Sid==='RunPinnedDefinition');
 assert.equal(run.Resource,'${var.images_ready ? aws_ecs_task_definition.'+name+'[0].arn : null}');
 assert.deepEqual(main.locals.worker_policy.Statement.find(value=>value.Sid==='PassOnlyTransferAndPull').Resource,['${aws_iam_role.'+name+'_transfer.arn}','${aws_iam_role.'+name+'_execution.arn}']);
 assert.equal(main.locals.transfer_policy.Statement[0].Resource,'${format("%s/document-jobs/*",aws_s3_bucket.'+name+'.arn)}');
 assert.ok(!JSON.stringify(main.locals.transfer_policy).includes('s3:DeleteObject'));
});
test('AWS host bootstrap gates ECS behind guard and pins prepared source without shell interpolation',()=>{
 const main=tf(),cloud=main.locals.cloud_init;
 assert.deepEqual(cloud.bootcmd,[['systemctl','mask','--runtime','--now','ecs.service']]);
 const files=Object.fromEntries(cloud.write_files.map(value=>[value.path,value]));
 assert.equal(atob(files['/opt/atmem/enterprise_aws_host_bootstrap.py'].content),bootstrap);
 assert.match(files['/etc/systemd/system/ecs.service.d/atmem-document.conf'].content,/Requires=atmem-document-guard.service/);
 assert.match(cloud.runcmd[0].at(-1),/enable --now --no-block ecs.service/);
 assert.deepEqual(cloud.runcmd[0].slice(0,4),['/bin/bash','-euo','pipefail','-c']);
 const host=main.resource.aws_launch_template[row.address];assert.equal(host.metadata_options.http_tokens,'required');
 assert.equal(host.metadata_options.http_put_response_hop_limit,1);assert.equal(host.network_interfaces[0].associate_public_ip_address,false);
});
