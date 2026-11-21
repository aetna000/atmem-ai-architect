mock_provider "aws" {}
override_data {
 target = data.aws_iam_role.block_6b6e6f776c65646765_worker
 values = {arn="arn:aws:iam::123456789012:role/question-worker",name="question-worker"}
}
override_data {
 target = module.host_verification.data.aws_iam_role.block_6b6e6f776c65646765_worker
 values = {arn="arn:aws:iam::123456789012:role/question-worker",name="question-worker"}
}
override_data {
 target = data.aws_ssm_parameter.block_6b6e6f776c65646765_recommended_ami
 values = {value="ami-0123456789abcdef0"}
}
override_data {
 target = data.aws_ami.block_6b6e6f776c65646765_host
 values = {id="ami-0123456789abcdef0",root_device_name="/dev/xvda"}
}
override_resource {
 override_during = plan
 target = aws_ecs_cluster.block_6b6e6f776c65646765
 values = {arn=format("arn:aws:ecs:ap-southeast-2:123456789012:cluster/%s",format("doc-%s",substr(sha256("https://atmem.ai/workspaces/private-knowledge-qualification/block_6b6e6f776c65646765/qualification"),0,12)))}
}
override_resource {
 override_during = plan
 target = aws_s3_bucket.block_6b6e6f776c65646765
 values = {id=format("atmem-doc-%s",substr(sha256(format("%s:%s","123456789012",format("doc-%s",substr(sha256("https://atmem.ai/workspaces/private-knowledge-qualification/block_6b6e6f776c65646765/qualification"),0,12)))),0,20)),arn=format("arn:aws:s3:::%s",format("atmem-doc-%s",substr(sha256(format("%s:%s","123456789012",format("doc-%s",substr(sha256("https://atmem.ai/workspaces/private-knowledge-qualification/block_6b6e6f776c65646765/qualification"),0,12)))),0,20)))}
}
override_resource {
 override_during = plan
 target = aws_ecr_repository.block_6b6e6f776c65646765_parser
 values = {arn=format("arn:aws:ecr:ap-southeast-2:123456789012:repository/%s/parser",format("doc-%s",substr(sha256("https://atmem.ai/workspaces/private-knowledge-qualification/block_6b6e6f776c65646765/qualification"),0,12))),repository_url=format("123456789012.dkr.ecr.ap-southeast-2.amazonaws.com/%s/parser",format("doc-%s",substr(sha256("https://atmem.ai/workspaces/private-knowledge-qualification/block_6b6e6f776c65646765/qualification"),0,12)))}
}
override_resource {
 override_during = plan
 target = aws_ecr_repository.block_6b6e6f776c65646765_transfer
 values = {arn=format("arn:aws:ecr:ap-southeast-2:123456789012:repository/%s/transfer",format("doc-%s",substr(sha256("https://atmem.ai/workspaces/private-knowledge-qualification/block_6b6e6f776c65646765/qualification"),0,12))),repository_url=format("123456789012.dkr.ecr.ap-southeast-2.amazonaws.com/%s/transfer",format("doc-%s",substr(sha256("https://atmem.ai/workspaces/private-knowledge-qualification/block_6b6e6f776c65646765/qualification"),0,12)))}
}
override_resource {
 override_during = plan
 target = aws_iam_role.block_6b6e6f776c65646765_host
 values = {arn=format("arn:aws:iam::123456789012:role/%s-host",format("doc-%s",substr(sha256("https://atmem.ai/workspaces/private-knowledge-qualification/block_6b6e6f776c65646765/qualification"),0,12)))}
}
override_resource {
 override_during = plan
 target = aws_iam_role.block_6b6e6f776c65646765_execution
 values = {arn=format("arn:aws:iam::123456789012:role/%s-execution",format("doc-%s",substr(sha256("https://atmem.ai/workspaces/private-knowledge-qualification/block_6b6e6f776c65646765/qualification"),0,12)))}
}
override_resource {
 override_during = plan
 target = aws_iam_role.block_6b6e6f776c65646765_transfer
 values = {arn=format("arn:aws:iam::123456789012:role/%s-transfer",format("doc-%s",substr(sha256("https://atmem.ai/workspaces/private-knowledge-qualification/block_6b6e6f776c65646765/qualification"),0,12)))}
}
override_resource {
 override_during = plan
 target = aws_ecs_task_definition.block_6b6e6f776c65646765
 values = {arn=format("arn:aws:ecs:ap-southeast-2:123456789012:task-definition/document-%s-parser:1",format("doc-%s",substr(sha256("https://atmem.ai/workspaces/private-knowledge-qualification/block_6b6e6f776c65646765/qualification"),0,12))),revision=1}
}
override_resource {
 override_during = plan
 target = aws_iam_instance_profile.block_6b6e6f776c65646765
 values = {arn=format("arn:aws:iam::123456789012:instance-profile/%s-host",format("doc-%s",substr(sha256("https://atmem.ai/workspaces/private-knowledge-qualification/block_6b6e6f776c65646765/qualification"),0,12)))}
}
override_resource {
 override_during = plan
 target = aws_vpc.block_6b6e6f776c65646765
 values = {id="vpc-aaaaaaaaaaaaaaaaa"}
}
override_resource {
 override_during = plan
 target = aws_security_group.block_6b6e6f776c65646765_host
 values = {id="sg-bbbbbbbbbbbbbbbbb"}
}
override_resource {
 override_during = plan
 target = aws_security_group.block_6b6e6f776c65646765_endpoint
 values = {id="sg-ccccccccccccccccc"}
}
override_resource {
 override_during = plan
 target = aws_subnet.block_6b6e6f776c65646765_0
 values = {id="subnet-11111111111111111"}
}
override_resource {
 override_during = plan
 target = aws_route_table.block_6b6e6f776c65646765_0
 values = {id="rtb-33333333333333333"}
}
override_resource {
 override_during = plan
 target = aws_subnet.block_6b6e6f776c65646765_1
 values = {id="subnet-22222222222222222"}
}
override_resource {
 override_during = plan
 target = aws_route_table.block_6b6e6f776c65646765_1
 values = {id="rtb-44444444444444444"}
}
override_resource {
 override_during = plan
 target = aws_vpc_endpoint.block_6b6e6f776c65646765_ecs
 values = {id="vpce-11111111111111111"}
}
override_resource {
 override_during = plan
 target = aws_vpc_endpoint.block_6b6e6f776c65646765_ecs_agent
 values = {id="vpce-22222222222222222"}
}
override_resource {
 override_during = plan
 target = aws_vpc_endpoint.block_6b6e6f776c65646765_ecs_telemetry
 values = {id="vpce-33333333333333333"}
}
override_resource {
 override_during = plan
 target = aws_vpc_endpoint.block_6b6e6f776c65646765_ecr_api
 values = {id="vpce-44444444444444444"}
}
override_resource {
 override_during = plan
 target = aws_vpc_endpoint.block_6b6e6f776c65646765_ecr_dkr
 values = {id="vpce-55555555555555555"}
}
override_resource {
 override_during = plan
 target = aws_vpc_endpoint.block_6b6e6f776c65646765_ssm
 values = {id="vpce-66666666666666666"}
}
override_resource {
 override_during = plan
 target = aws_vpc_endpoint.block_6b6e6f776c65646765_ssmmessages
 values = {id="vpce-77777777777777777"}
}
override_resource {
 override_during = plan
 target = aws_vpc_endpoint.block_6b6e6f776c65646765_s3
 values = {id="vpce-88888888888888888",prefix_list_id="pl-aaaaaaaaaaaaaaaaa"}
}
override_resource {
 override_during = plan
 target = aws_launch_template.block_6b6e6f776c65646765
 values = {id="lt-aaaaaaaaaaaaaaaaa",latest_version=1}
}
override_resource {
 override_during = plan
 target = module.host_verification.aws_ssm_document.block_6b6e6f776c65646765
 values = {arn=format("arn:aws:ssm:ap-southeast-2:123456789012:document/%s",format("doc-host-%s",substr(sha256("https://atmem.ai/workspaces/private-knowledge-qualification/block_6b6e6f776c65646765/qualification"),0,12))),hash="ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",hash_type="Sha256",latest_version=1}
}
variables {
 review_approved=true
 account_id="123456789012"
 worker_role_arn="arn:aws:iam::123456789012:role/question-worker"
 availability_zones=["ap-southeast-2a","ap-southeast-2b"]
}
run "foundation_has_no_ready_runtime" {
 command = plan
 assert {
 condition = output.document_job_configuration == null && length(aws_ecs_task_definition.block_6b6e6f776c65646765) == 0 && length(aws_launch_template.block_6b6e6f776c65646765) == 0 && length(aws_autoscaling_group.block_6b6e6f776c65646765) == 0
 error_message = "No synthetic task, AMI or ready worker during foundation."
}
}
run "private_document_substrate" {
 command = plan
 variables {
 images_ready=true
 hosts_enabled=true
 host_ami_id="ami-0123456789abcdef0"
 parser_revision="cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
 parser_image=format("123456789012.dkr.ecr.ap-southeast-2.amazonaws.com/%s/parser@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",format("doc-%s",substr(sha256("https://atmem.ai/workspaces/private-knowledge-qualification/block_6b6e6f776c65646765/qualification"),0,12)))
 transfer_image=format("123456789012.dkr.ecr.ap-southeast-2.amazonaws.com/%s/transfer@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",format("doc-%s",substr(sha256("https://atmem.ai/workspaces/private-knowledge-qualification/block_6b6e6f776c65646765/qualification"),0,12)))
}
assert {
 condition = output.document_job_configuration.format == "enterprise-aws-document-job-v2" && output.document_job_configuration.taskDefinitionArn == aws_ecs_task_definition.block_6b6e6f776c65646765[0].arn && output.document_job_configuration.workerRoleArn == var.worker_role_arn
 error_message = "Bind the exact static revision and existing worker."
}
assert {
 condition = aws_ecs_task_definition.block_6b6e6f776c65646765[0].network_mode == "bridge" && jsondecode(aws_ecs_task_definition.block_6b6e6f776c65646765[0].container_definitions)[1].disableNetworking && length(jsondecode(aws_ecs_task_definition.block_6b6e6f776c65646765[0].container_definitions)) == 3
 error_message = "Keep isolated parser and sequential transfer stages."
}
}
run "private_host_bootstrap" {
 command = plan
 variables {
 images_ready=true
 hosts_enabled=true
 host_ami_id="ami-0123456789abcdef0"
 parser_revision="cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
 parser_image=format("123456789012.dkr.ecr.ap-southeast-2.amazonaws.com/%s/parser@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",format("doc-%s",substr(sha256("https://atmem.ai/workspaces/private-knowledge-qualification/block_6b6e6f776c65646765/qualification"),0,12)))
 transfer_image=format("123456789012.dkr.ecr.ap-southeast-2.amazonaws.com/%s/transfer@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",format("doc-%s",substr(sha256("https://atmem.ai/workspaces/private-knowledge-qualification/block_6b6e6f776c65646765/qualification"),0,12)))
}
assert {
 condition = aws_launch_template.block_6b6e6f776c65646765[0].metadata_options[0].http_tokens == "required" && aws_launch_template.block_6b6e6f776c65646765[0].metadata_options[0].http_put_response_hop_limit == 1 && !one(aws_launch_template.block_6b6e6f776c65646765[0].network_interfaces).associate_public_ip_address && one(aws_launch_template.block_6b6e6f776c65646765[0].block_device_mappings).ebs[0].encrypted
 error_message = "Private host identity and encrypted disposable root volume."
}
assert {
 condition = aws_autoscaling_group.block_6b6e6f776c65646765[0].desired_capacity == var.host_count && aws_autoscaling_group.block_6b6e6f776c65646765[0].max_size == var.host_count
 error_message = "Standing bounded pool; do not claim automatic scaling."
}
}
run "storage_has_no_history" {
 command = plan
 assert {
 condition = aws_s3_bucket_versioning.block_6b6e6f776c65646765.versioning_configuration[0].status == "Disabled" && aws_s3_bucket_public_access_block.block_6b6e6f776c65646765.block_public_policy && !aws_s3_bucket.block_6b6e6f776c65646765.force_destroy
 error_message = "No retained history/public access or destructive populated-store deletion."
}
}
run "review_required" {
 command = plan
 variables {review_approved=false}
 expect_failures=[terraform_data.block_6b6e6f776c65646765_review]
}
run "worker_path_cannot_redirect" {
 command = plan
 variables {worker_role_arn="arn:aws:iam::123456789012:role/wrong/question-worker"}
 expect_failures=[terraform_data.block_6b6e6f776c65646765_review]
}
run "region_drift_rejected" {
 command = plan
 variables {region="us-east-1"}
 expect_failures=[var.region]
}
run "same_zone_rejected" {
 command = plan
 variables {availability_zones=["ap-southeast-2a","ap-southeast-2a"]}
 expect_failures=[var.availability_zones]
}
run "missing_ami_rejected" {
 command = plan
 variables {hosts_enabled=true}
 expect_failures=[var.host_ami_id]
}
run "missing_image_revision_rejected" {
 command = plan
 variables {images_ready=true}
 expect_failures=[var.parser_image,var.transfer_image,var.parser_revision]
}
