export function awsDocumentInfrastructureTests(n,seed,region){
 const name=`format("doc-%s",substr(sha256(${JSON.stringify(seed)}),0,12))`,host=`format("doc-host-%s",substr(sha256(${JSON.stringify(seed)}),0,12))`;
 const block=(kind,target,values)=>`${kind} {\n ${kind==='override_resource'?'override_during = plan\n ':''}target = ${target}\n values = ${values}\n}\n`;
 const run=(name,body)=>`run "${name}" {\n command = plan\n ${body}\n}\n`,assert=(condition,message)=>`assert {\n condition = ${condition}\n error_message = ${JSON.stringify(message)}\n}`;
 let text='mock_provider "aws" {}\n';
 for(const target of [`data.aws_iam_role.${n}_worker`,`module.host_verification.data.aws_iam_role.${n}_worker`])text+=block('override_data',target,'{arn="arn:aws:iam::123456789012:role/question-worker",name="question-worker"}');
 text+=block('override_data',`data.aws_ssm_parameter.${n}_recommended_ami`,'{value="ami-0123456789abcdef0"}');
 text+=block('override_data',`data.aws_ami.${n}_host`,'{id="ami-0123456789abcdef0",root_device_name="/dev/xvda"}');
 text+=block('override_resource',`aws_ecs_cluster.${n}`,`{arn=format("arn:aws:ecs:${region}:123456789012:cluster/%s",${name})}`);
 const bucket=`format("atmem-doc-%s",substr(sha256(format("%s:%s","123456789012",${name})),0,20))`;
 text+=block('override_resource',`aws_s3_bucket.${n}`,`{id=${bucket},arn=format("arn:aws:s3:::%s",${bucket})}`);
 for(const purpose of ['parser','transfer'])text+=block('override_resource',`aws_ecr_repository.${n}_${purpose}`,`{arn=format("arn:aws:ecr:${region}:123456789012:repository/%s/${purpose}",${name}),repository_url=format("123456789012.dkr.ecr.${region}.amazonaws.com/%s/${purpose}",${name})}`);
 for(const purpose of ['host','execution','transfer'])text+=block('override_resource',`aws_iam_role.${n}_${purpose}`,`{arn=format("arn:aws:iam::123456789012:role/%s-${purpose}",${name})}`);
 text+=block('override_resource',`aws_ecs_task_definition.${n}`,`{arn=format("arn:aws:ecs:${region}:123456789012:task-definition/document-%s-parser:1",${name}),revision=1}`);
 text+=block('override_resource',`aws_iam_instance_profile.${n}`,`{arn=format("arn:aws:iam::123456789012:instance-profile/%s-host",${name})}`);
 text+=block('override_resource',`aws_vpc.${n}`,'{id="vpc-aaaaaaaaaaaaaaaaa"}');
 for(const [suffix,id]of [['_host','bbbbbbbbbbbbbbbbb'],['_endpoint','ccccccccccccccccc']])text+=block('override_resource',`aws_security_group.${n}${suffix}`,`{id="sg-${id}"}`);
 for(let i=0;i<2;i++){
  text+=block('override_resource',`aws_subnet.${n}_${i}`,`{id="subnet-${String(i+1).repeat(17)}"}`);
  text+=block('override_resource',`aws_route_table.${n}_${i}`,`{id="rtb-${String(i+3).repeat(17)}"}`);
 }
 for(const [index,service]of ['ecs','ecs_agent','ecs_telemetry','ecr_api','ecr_dkr','ssm','ssmmessages','s3'].entries())text+=block('override_resource',`aws_vpc_endpoint.${n}_${service}`,`{id="vpce-${String(index+1).repeat(17)}"${service==='s3'?',prefix_list_id="pl-aaaaaaaaaaaaaaaaa"':''}}`);
 text+=block('override_resource',`aws_launch_template.${n}`,'{id="lt-aaaaaaaaaaaaaaaaa",latest_version=1}');
 text+=block('override_resource',`module.host_verification.aws_ssm_document.${n}`,`{arn=format("arn:aws:ssm:${region}:123456789012:document/%s",${host}),hash="${'f'.repeat(64)}",hash_type="Sha256",latest_version=1}`);
 text+=`variables {\n review_approved=true\n account_id="123456789012"\n worker_role_arn="arn:aws:iam::123456789012:role/question-worker"\n availability_zones=["${region}a","${region}b"]\n}\n`;
 const ready=`variables {\n images_ready=true\n hosts_enabled=true\n host_ami_id="ami-0123456789abcdef0"\n parser_revision="${'c'.repeat(64)}"\n parser_image=format("123456789012.dkr.ecr.${region}.amazonaws.com/%s/parser@sha256:${'a'.repeat(64)}",${name})\n transfer_image=format("123456789012.dkr.ecr.${region}.amazonaws.com/%s/transfer@sha256:${'b'.repeat(64)}",${name})\n}\n`;
 text+=run('foundation_has_no_ready_runtime',assert(`output.document_job_configuration == null && length(aws_ecs_task_definition.${n}) == 0 && length(aws_launch_template.${n}) == 0 && length(aws_autoscaling_group.${n}) == 0`,'No synthetic task, AMI or ready worker during foundation.'));
 text+=run('private_document_substrate',ready+assert(`output.document_job_configuration.format == "enterprise-aws-document-job-v2" && output.document_job_configuration.taskDefinitionArn == aws_ecs_task_definition.${n}[0].arn && output.document_job_configuration.workerRoleArn == var.worker_role_arn`,'Bind the exact static revision and existing worker.')+'\n'+assert(`aws_ecs_task_definition.${n}[0].network_mode == "bridge" && jsondecode(aws_ecs_task_definition.${n}[0].container_definitions)[1].disableNetworking && length(jsondecode(aws_ecs_task_definition.${n}[0].container_definitions)) == 3`,'Keep isolated parser and sequential transfer stages.'));
 text+=run('private_host_bootstrap',ready+assert(`aws_launch_template.${n}[0].metadata_options[0].http_tokens == "required" && aws_launch_template.${n}[0].metadata_options[0].http_put_response_hop_limit == 1 && !one(aws_launch_template.${n}[0].network_interfaces).associate_public_ip_address && one(aws_launch_template.${n}[0].block_device_mappings).ebs[0].encrypted`,'Private host identity and encrypted disposable root volume.')+'\n'+assert(`aws_autoscaling_group.${n}[0].desired_capacity == var.host_count && aws_autoscaling_group.${n}[0].max_size == var.host_count`,'Standing bounded pool; do not claim automatic scaling.'));
 text+=run('storage_has_no_history',assert(`aws_s3_bucket_versioning.${n}.versioning_configuration[0].status == "Disabled" && aws_s3_bucket_public_access_block.${n}.block_public_policy && !aws_s3_bucket.${n}.force_destroy`,'No retained history/public access or destructive populated-store deletion.'));
 text+=run('review_required',`variables {review_approved=false}\n expect_failures=[terraform_data.${n}_review]`);
 text+=run('worker_path_cannot_redirect',`variables {worker_role_arn="arn:aws:iam::123456789012:role/wrong/question-worker"}\n expect_failures=[terraform_data.${n}_review]`);
 text+=run('region_drift_rejected',`variables {region="us-east-1"}\n expect_failures=[var.region]`);
 text+=run('same_zone_rejected',`variables {availability_zones=["${region}a","${region}a"]}\n expect_failures=[var.availability_zones]`);
 text+=run('missing_ami_rejected',`variables {hosts_enabled=true}\n expect_failures=[var.host_ami_id]`);
 text+=run('missing_image_revision_rejected',`variables {images_ready=true}\n expect_failures=[var.parser_image,var.transfer_image,var.parser_revision]`);
 return text;
}
