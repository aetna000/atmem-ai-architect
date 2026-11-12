mock_provider "aws" {
 mock_data "aws_caller_identity" { defaults = { account_id = "123456789012" } }
 mock_data "aws_partition" { defaults = { partition = "aws" } }
 mock_resource "aws_iam_role" { defaults = { arn = "arn:aws:iam::123456789012:role/evaluator-runtime" } }
 mock_resource "aws_apigatewayv2_api" { defaults = { api_endpoint = "https://example.execute-api.ap-southeast-2.amazonaws.com" } }
}
run "independent_boundaries" {
 command = plan
 assert {
  condition = aws_lambda_function.web.runtime == "python3.12" && aws_lambda_function.web.architectures == tolist(["arm64"])
  error_message = "Declared production runtime and architecture"
 }
 assert {
  condition = aws_lambda_function.web.reserved_concurrent_executions == 5 && aws_lambda_function.web.memory_size == 256
  error_message = "Five-request starting footprint"
 }
 assert {
  condition = aws_lambda_function.web.timeout == 28 && aws_apigatewayv2_integration.web.timeout_milliseconds == 29000
  error_message = "Concrete bounded integration timeouts"
 }
 assert {
  condition = aws_lambda_function.web.environment[0].variables.INFERENCE_ENABLED == "false" && aws_lambda_function.web.environment[0].variables.RETENTION_VERIFIED_UNTIL == "0" && aws_lambda_function.web.environment[0].variables.ALLOWED_SUBS == "[]"
  error_message = "Unknown safety/access configuration disables inference"
 }
 assert {
  condition = aws_apigatewayv2_route.suggest.authorization_type == "JWT" && aws_apigatewayv2_route.suggest.route_key == "POST /suggest" && aws_apigatewayv2_route.suggest.authorization_scopes == toset(["ticket-review/suggest"])
  error_message = "Protected application route and exact custom scope"
 }
 assert {
  condition = sort(keys(aws_apigatewayv2_route.assets)) == tolist(["GET /", "GET /app.js", "GET /config.json", "GET /style.css"])
  error_message = "Only intended public static/config routes"
 }
 assert {
  condition = aws_cognito_user_pool.staff.admin_create_user_config[0].allow_admin_create_user_only && aws_cognito_user_pool.staff.mfa_configuration == "ON" && aws_cognito_user_pool.staff.software_token_mfa_configuration[0].enabled
  error_message = "Invited staff and mandatory TOTP"
 }
 assert {
  condition = !aws_cognito_user_pool_client.web.generate_secret && aws_cognito_user_pool_client.web.allowed_oauth_flows == toset(["code"]) && contains(aws_cognito_user_pool_client.web.allowed_oauth_scopes,"ticket-review/suggest")
  error_message = "Public authorization-code client and scope"
 }
 assert {
  condition = jsondecode(aws_iam_role_policy.model_only.policy).Statement[0].Action == "bedrock:InvokeModel" && jsondecode(aws_iam_role_policy.model_only.policy).Statement[0].Resource == "arn:aws:bedrock:ap-southeast-2::foundation-model/amazon.nova-lite-v1:0"
  error_message = "Exact direct Sydney model permission"
 }
 assert {
  condition = length(jsondecode(aws_iam_role_policy.model_only.policy).Statement) == 3 && jsondecode(aws_iam_role_policy.model_only.policy).Statement[1].Action == "bedrock:GetModelInvocationLoggingConfiguration" && jsondecode(aws_iam_role_policy.model_only.policy).Statement[2].Effect == "Deny" && jsondecode(aws_iam_role_policy.model_only.policy).Statement[2].Condition.StringNotEquals["aws:RequestedRegion"] == "ap-southeast-2"
  error_message = "Bounded logging read and no foreign-region Bedrock fallback"
 }
 assert {
  condition = aws_lambda_permission.gateway.principal == "apigateway.amazonaws.com" && aws_lambda_permission.gateway.action == "lambda:InvokeFunction"
  error_message = "API Gateway service invocation boundary"
 }
}
run "staff_count_is_not_a_business_quota" {
 command = plan
 variables { allowed_subs = ["00000000-0000-0000-0000-000000000001", "00000000-0000-0000-0000-000000000002", "00000000-0000-0000-0000-000000000003", "00000000-0000-0000-0000-000000000004", "00000000-0000-0000-0000-000000000005", "00000000-0000-0000-0000-000000000006", "00000000-0000-0000-0000-000000000007", "00000000-0000-0000-0000-000000000008", "00000000-0000-0000-0000-000000000009", "00000000-0000-0000-0000-000000000010", "00000000-0000-0000-0000-000000000011"] }
 assert {
 condition = length(jsondecode(aws_lambda_function.web.environment[0].variables.ALLOWED_SUBS)) == 11
 error_message = "Ten staff was a planning input; do not invent a hard roster quota"
 }
}
