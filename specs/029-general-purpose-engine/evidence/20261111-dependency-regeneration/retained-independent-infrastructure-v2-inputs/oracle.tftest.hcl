mock_provider "aws" {
 mock_data "aws_caller_identity" { defaults = { account_id = "123456789012" } }
 mock_data "aws_partition" { defaults = { partition = "aws" } }
 mock_resource "aws_iam_role" { defaults = { arn = "arn:aws:iam::123456789012:role/evaluator-runtime" } }
 mock_resource "aws_apigatewayv2_api" { defaults = { api_endpoint = "https://example.execute-api.ap-southeast-2.amazonaws.com" } }
}
variables { cognito_domain_prefix = "independent-evaluator" }
run "independent_boundaries" {
 command = plan
 assert {
  condition = aws_lambda_function.app.runtime == "python3.12" && aws_lambda_function.app.architectures == tolist(["arm64"])
  error_message = "Declared and locally checked production runtime"
 }
 assert {
  condition = aws_lambda_function.app.reserved_concurrent_executions >= 5 && aws_lambda_function.app.memory_size == 256
  error_message = "Capacity supports five and matches documented256MB footprint"
 }
 assert {
  condition = aws_lambda_function.app.timeout > 0 && aws_apigatewayv2_integration.app.timeout_milliseconds >= 1000 * aws_lambda_function.app.timeout && aws_apigatewayv2_integration.app.timeout_milliseconds <= 30000
  error_message = "Finite coherent integration timeout, no invented customer SLA"
 }
 assert {
  condition = aws_lambda_function.app.environment[0].variables.CLIENT_ID == aws_cognito_user_pool_client.browser.id && aws_lambda_function.app.environment[0].variables.REDIRECT_URI == "${aws_apigatewayv2_api.app.api_endpoint}/"
  error_message = "Client/config callback wiring"
 }
 assert {
  condition = aws_apigatewayv2_route.suggest.authorization_type == "JWT" && aws_apigatewayv2_route.suggest.route_key == "POST /suggest" && aws_apigatewayv2_route.suggest.authorization_scopes == toset(["review/suggest"])
  error_message = "JWT-protected API and implementation scope"
 }
 assert {
  condition = sort(keys(aws_apigatewayv2_route.public)) == tolist(["GET /", "GET /app.js", "GET /config", "GET /style.css"])
  error_message = "Only intended public asset/config routes"
 }
 assert {
  condition = aws_cognito_user_pool.staff.admin_create_user_config[0].allow_admin_create_user_only && aws_cognito_user_pool.staff.mfa_configuration == "ON" && aws_cognito_user_pool.staff.software_token_mfa_configuration[0].enabled
  error_message = "Invited staff and declared TOTP policy"
 }
 assert {
  condition = !aws_cognito_user_pool_client.browser.generate_secret && aws_cognito_user_pool_client.browser.allowed_oauth_flows == toset(["code"]) && contains(aws_cognito_user_pool_client.browser.allowed_oauth_scopes,"review/suggest")
  error_message = "Public authorization-code client and scope"
 }
 assert {
  condition = aws_cognito_user_group.reviewers.name == "reviewers" && aws_cognito_user_group.reviewers.user_pool_id == aws_cognito_user_pool.staff.id
  error_message = "Staff group agrees with handler authorization"
 }
 assert {
  condition = jsondecode(aws_iam_role_policy.runtime.policy).Statement[0].Action == ["bedrock:InvokeModel"] && jsondecode(aws_iam_role_policy.runtime.policy).Statement[0].Resource == "arn:aws:bedrock:ap-southeast-2::foundation-model/amazon.nova-lite-v1:0"
  error_message = "Direct Sydney model grant only"
 }
 assert {
  condition = length(jsondecode(aws_iam_role_policy.runtime.policy).Statement) == 3 && jsondecode(aws_iam_role_policy.runtime.policy).Statement[1].Action == ["bedrock:GetAccountDataRetention", "bedrock:GetModelInvocationLoggingConfiguration"] && jsondecode(aws_iam_role_policy.runtime.policy).Statement[1].Condition.StringEquals["aws:RequestedRegion"] == "ap-southeast-2"
  error_message = "Read-only regional safety checks; no account-policy mutation"
 }
 assert {
  condition = aws_lambda_permission.gateway.principal == "apigateway.amazonaws.com" && aws_lambda_permission.gateway.action == "lambda:InvokeFunction"
  error_message = "API Gateway invocation boundary"
 }
}
