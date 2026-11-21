mock_provider "aws" {}
override_resource {
 override_during = plan
 target = aws_ssm_document.block_6b6e6f776c65646765
 values = {
 arn = format("arn:aws:ssm:ap-southeast-2:123456789012:document/%s",format("doc-host-%s",substr(sha256("https://atmem.ai/workspaces/private-knowledge-qualification/block_6b6e6f776c65646765/qualification"),0,12)))
 hash = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
 hash_type = "Sha256"
 latest_version = 1
 }
}
variables {
 review_approved = true
 account_id = "123456789012"
 cluster_arn = "arn:aws:ecs:ap-southeast-2:123456789012:cluster/document-parser"
 worker_role_arn = "arn:aws:iam::123456789012:role/question-worker"
}
override_data {
 target = data.aws_iam_role.block_6b6e6f776c65646765_worker
 values = {
 arn = "arn:aws:iam::123456789012:role/question-worker"
 name = "question-worker"
 }
}
run "fixed_host_verification" {
 command = plan
 assert {
 condition = length(keys(jsondecode(aws_ssm_document.block_6b6e6f776c65646765.content).parameters)) == 0 && length(jsondecode(aws_ssm_document.block_6b6e6f776c65646765.content).mainSteps) == 1 && jsondecode(aws_ssm_document.block_6b6e6f776c65646765.content).mainSteps[0].action == "aws:runShellScript"
 error_message = "Only the fixed parameterless probe is allowed."
 }
 assert {
 condition = output.host_verification.hostDocumentVersion == "1" && output.host_verification.hostDocumentHash == "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff" && output.host_verification.clusterArn == var.cluster_arn && length(output.host_verification.hostPolicySha256) == 64
 error_message = "Runtime must receive exact native document identity and selected host policy."
 }
}
run "worker_permission_boundary" {
 command = plan
 assert {
 condition = aws_iam_role_policy.block_6b6e6f776c65646765.role == "question-worker" && length(jsondecode(aws_iam_role_policy.block_6b6e6f776c65646765.policy).Statement) == 5 && jsondecode(aws_iam_role_policy.block_6b6e6f776c65646765.policy).Statement[2].Resource == aws_ssm_document.block_6b6e6f776c65646765.arn && toset(jsondecode(aws_iam_role_policy.block_6b6e6f776c65646765.policy).Statement[2].Action) == toset(["ssm:GetDocument","ssm:SendCommand"])
 error_message = "Preserve the existing worker and grant only this probe document."
 }
 assert {
 condition = jsondecode(aws_iam_role_policy.block_6b6e6f776c65646765.policy).Statement[3].Condition.StringEquals["ssm:resourceTag/atmem-document-policy"] == output.host_verification.hostPolicySha256 && toset(jsondecode(aws_iam_role_policy.block_6b6e6f776c65646765.policy).Statement[4].Action) == toset(["ssm:GetCommandInvocation"])
 error_message = "Only tagged hosts and invocation reads; no caller-selected commands or Parameter Store authority."
 }
}
run "review_required" {
 command = plan
 variables { review_approved = false }
 expect_failures = [terraform_data.block_6b6e6f776c65646765_review]
}
run "foreign_cluster_rejected" {
 command = plan
 variables { cluster_arn = "arn:aws:ecs:ap-southeast-2:000000000000:cluster/foreign" }
 expect_failures = [terraform_data.block_6b6e6f776c65646765_review]
}
run "foreign_worker_rejected" {
 command = plan
 variables { worker_role_arn = "arn:aws:iam::000000000000:role/foreign" }
 expect_failures = [terraform_data.block_6b6e6f776c65646765_review]
}
run "wrong_worker_path_rejected" {
 command = plan
 variables { worker_role_arn = "arn:aws:iam::123456789012:role/incorrect-path/question-worker" }
 expect_failures = [terraform_data.block_6b6e6f776c65646765_review]
}
run "region_drift_rejected" {
 command = plan
 variables { region = "us-east-1" }
 expect_failures = [var.region]
}
