import {builder,v,ref} from './public-faq-builder.mjs';
import {CLOUD_PROVIDER_LOCKS} from './cloud-provider-locks.mjs';
import {faqLambdaBuild} from './faq-lambda-build.mjs';

// A small synchronous public FAQ does not need App Runner eligibility, an ECR
// repository or a continuously running load balancer/container. No service
// lifecycle exception is delegated to the visitor or hidden behind a mock pass.
export function awsPublicFaqTerraform(project,plan,environment='staging'){
 const b=builder(project,plan,environment,'aws'),{input,add}=b;
 const account=input('account_id','Reviewed destination AWS account; approved operator credential chain only.','123456789012','^[0-9]{12}$');
 const region=input('region','Reviewed commercial AWS region with Lambda, HTTP API and the direct regional Bedrock model; no cross-region inference fallback.','ap-southeast-2','^[a-z]{2}-[a-z]+-[0-9]$');
 const entries=plan.publicFaqPlan.entries;
 if(entries.every(e=>e.row.region===entries[0].row.region)&&/^[a-z]{2}-[a-z]+-[0-9]$/.test(entries[0].row.region)){b.variable.region.default=entries[0].row.region;b.examples.region=entries[0].row.region;}
 b.data.aws_caller_identity={destination:{}};
 b.resource.terraform_data.review_gate.lifecycle.precondition.push({condition:'${data.aws_caller_identity.destination.account_id == var.account_id}',error_message:'Approved operator must target the reviewed AWS account.'});
 for(const {row}of entries){
  const n=row.address,name=input(n+'_name','Unique application and IAM role name.','reviewed-public-help','^[a-z][a-z0-9-]{3,28}[a-z0-9]$');
  const model=input(n+'_model_id','Reviewed direct regional Converse foundation model ID; verify availability, quotas, context size, terms and retention-none compatibility.','anthropic.reviewed-model-v1:0','^[a-z0-9][a-z0-9.-]*:[0-9]+$');
  const editor=input(n+'_editor_principal_arn','Existing authorized same-account company editor role; it alone may assume the separate catalog editor role.','arn:aws:iam::123456789012:role/reviewed-company-editors','^arn:aws:iam::[0-9]{12}:role/[A-Za-z0-9_+=,.@/-]{1,512}$');
  b.resource.terraform_data.review_gate.lifecycle.precondition.push({condition:'${split(":", var.'+n+'_editor_principal_arn)[4] == var.account_id}',error_message:'Existing editor role must belong to the reviewed account.'});
  add('aws_s3_bucket',n,{bucket:account+'-'+name+'-catalog',force_destroy:false,lifecycle:{prevent_destroy:true}});
  const bucket=ref('aws_s3_bucket',n,'id'),bucketArn=ref('aws_s3_bucket',n,'arn'),objectArn=bucketArn+'/catalog.json';
  add('aws_s3_bucket_public_access_block',n,{bucket,block_public_acls:true,block_public_policy:true,ignore_public_acls:true,restrict_public_buckets:true});
  add('aws_s3_bucket_ownership_controls',n,{bucket,rule:{object_ownership:'BucketOwnerEnforced'}});
  add('aws_s3_bucket_server_side_encryption_configuration',n,{bucket,rule:{apply_server_side_encryption_by_default:{sse_algorithm:'AES256'},bucket_key_enabled:false}});
  add('aws_s3_bucket_versioning',n,{bucket,versioning_configuration:{status:'Enabled'}});
  add('aws_s3_bucket_lifecycle_configuration',n,{bucket,rule:{id:'expire-old-catalog-versions',status:'Enabled',filter:{prefix:''},noncurrent_version_expiration:{noncurrent_days:7},abort_incomplete_multipart_upload:{days_after_initiation:1}},depends_on:['aws_s3_bucket_versioning.'+n]});
  add('aws_s3_bucket_policy',n,{bucket,policy:JSON.stringify({Version:'2012-10-17',Statement:[{Sid:'RequireTLS',Effect:'Deny',Principal:'*',Action:'s3:*',Resource:[bucketArn,bucketArn+'/*'],Condition:{Bool:{'aws:SecureTransport':'false','aws:PrincipalIsAWSService':'false'}}}]}),depends_on:['aws_s3_bucket_public_access_block.'+n]});
  add('aws_iam_role',n,{name:name+'-runtime',assume_role_policy:JSON.stringify({Version:'2012-10-17',Statement:[{Effect:'Allow',Principal:{Service:'lambda.amazonaws.com'},Action:'sts:AssumeRole'}]})});
  add('aws_cloudwatch_log_group',n,{name:'/aws/lambda/'+name,retention_in_days:7});
  add('aws_iam_role_policy',n,{role:ref('aws_iam_role',n,'id'),policy:JSON.stringify({Version:'2012-10-17',Statement:[{Effect:'Allow',Action:['s3:GetObject'],Resource:objectArn},{Effect:'Allow',Action:['bedrock:InvokeModel'],Resource:'arn:aws:bedrock:'+region+'::foundation-model/'+model},{Effect:'Allow',Action:['bedrock:GetAccountDataRetention','bedrock:GetModelInvocationLoggingConfiguration'],Resource:'*',Condition:{StringEquals:{'aws:RequestedRegion':region}}},{Effect:'Allow',Action:['logs:CreateLogStream','logs:PutLogEvents'],Resource:ref('aws_cloudwatch_log_group',n,'arn')+':*'}]})});
  add('aws_iam_role',n+'_editor',{name:name+'-catalog-editor',assume_role_policy:JSON.stringify({Version:'2012-10-17',Statement:[{Effect:'Allow',Principal:{AWS:editor},Action:'sts:AssumeRole'}]})});
  add('aws_iam_role_policy',n+'_editor',{role:ref('aws_iam_role',n+'_editor','id'),policy:JSON.stringify({Version:'2012-10-17',Statement:[{Effect:'Allow',Action:['s3:GetObject','s3:PutObject'],Resource:objectArn}]})});
  add('aws_apigatewayv2_api',n,{name,protocol_type:'HTTP',disable_execute_api_endpoint:false});
  const origin=ref('aws_apigatewayv2_api',n,'api_endpoint'),settings={REGION:region,ACCOUNT_ID:account,MODEL_ID:model,MAX_OUTPUT_TOKENS:'1024',CATALOG_BUCKET:bucket,PUBLIC_ORIGIN:origin};
  add('aws_lambda_function',n,{function_name:name,role:ref('aws_iam_role',n,'arn'),runtime:'python3.13',handler:'lambda_faq.handler',architectures:['x86_64'],filename:'${path.module}/build/'+n+'.zip',source_code_hash:'${filebase64sha256("${path.module}/build/'+n+'.zip")}',timeout:29,memory_size:512,reserved_concurrent_executions:5,publish:true,environment:{variables:settings},logging_config:{log_format:'JSON',application_log_level:'WARN',system_log_level:'WARN'},depends_on:['aws_iam_role_policy.'+n,'aws_s3_bucket_policy.'+n,'aws_s3_bucket_server_side_encryption_configuration.'+n,'aws_s3_bucket_versioning.'+n,'aws_cloudwatch_log_group.'+n]});
  add('aws_lambda_alias',n,{name:'live',function_name:ref('aws_lambda_function',n,'function_name'),function_version:ref('aws_lambda_function',n,'version')});
  add('aws_apigatewayv2_integration',n,{api_id:ref('aws_apigatewayv2_api',n,'id'),integration_type:'AWS_PROXY',integration_uri:ref('aws_lambda_alias',n,'invoke_arn'),payload_format_version:'2.0',timeout_milliseconds:29000});
  add('aws_apigatewayv2_route',n,{api_id:ref('aws_apigatewayv2_api',n,'id'),route_key:'$default',authorization_type:'NONE',target:'integrations/'+ref('aws_apigatewayv2_integration',n,'id')});
  add('aws_apigatewayv2_stage',n,{api_id:ref('aws_apigatewayv2_api',n,'id'),name:'$default',auto_deploy:true,default_route_settings:{throttling_burst_limit:10,throttling_rate_limit:10},depends_on:['aws_apigatewayv2_route.'+n]});
  add('aws_lambda_permission',n,{statement_id:'OnlyOwnedHttpApi',action:'lambda:InvokeFunction',function_name:ref('aws_lambda_function',n,'function_name'),qualifier:ref('aws_lambda_alias',n,'name'),principal:'apigateway.amazonaws.com',source_account:account,source_arn:ref('aws_apigatewayv2_api',n,'execution_arn')+'/*/*'});
  b.output[n+'_url']={value:origin+'/'};b.output[n+'_catalog']={value:{bucket,region}};b.output[n+'_editor_role_arn']={value:ref('aws_iam_role',n+'_editor','arn')};b.source(row);
  b.assertions.push(`run "${n}_public_boundary" {\n command = plan\n assert {\n condition = aws_s3_bucket_public_access_block.${n}.block_public_policy && aws_s3_bucket_public_access_block.${n}.restrict_public_buckets && !aws_s3_bucket.${n}.force_destroy\n error_message = "Only the app is public; catalog storage remains private and protected."\n }\n assert {\n condition = jsondecode(aws_iam_role_policy.${n}.policy).Statement[0].Action == ["s3:GetObject"] && toset(jsondecode(aws_iam_role_policy.${n}_editor.policy).Statement[0].Action) == toset(["s3:GetObject", "s3:PutObject"])\n error_message = "Workload read and separate conditional editor write authority must stay distinct."\n }\n assert {\n condition = aws_lambda_function.${n}.reserved_concurrent_executions == 5 && aws_lambda_function.${n}.timeout == 29 && aws_apigatewayv2_integration.${n}.payload_format_version == "2.0" && aws_apigatewayv2_route.${n}.authorization_type == "NONE"\n error_message = "This explicit public-only synchronous module uses bounded Lambda concurrency and the implemented HTTP API v2 event contract."\n }\n assert {\n condition = aws_lambda_permission.${n}.source_account == var.account_id && aws_lambda_permission.${n}.qualifier == "live"\n error_message = "Only the owned account/API may invoke the published live alias."\n }\n}`);
 }
 Object.assign(b.files,faqLambdaBuild(entries.map(e=>e.row.address)));
 const config={terraform:{required_version:'>= 1.17.1, < 2.0.0',required_providers:{aws:{source:'hashicorp/aws',version:'6.72.0'}}},provider:{aws:{region,allowed_account_ids:[account],default_tags:{tags:{ManagedBy:'AtMem AI Architect',Environment:environment}}}}};
 const mocks=`mock_provider "aws" {\n override_during = plan\n mock_data "aws_caller_identity" { defaults = { account_id = "${b.examples.account_id}" } }\n mock_resource "aws_iam_role" { defaults = { arn = "arn:aws:iam::${b.examples.account_id}:role/mock-role" } }\n mock_resource "aws_s3_bucket" { defaults = { id = "mock-catalog", arn = "arn:aws:s3:::mock-catalog" } }\n mock_resource "aws_cloudwatch_log_group" { defaults = { arn = "arn:aws:logs:${b.examples.region}:${b.examples.account_id}:log-group:/aws/lambda/mock" } }\n mock_resource "aws_lambda_function" { defaults = { arn = "arn:aws:lambda:${b.examples.region}:${b.examples.account_id}:function:mock", version = "1" } }\n mock_resource "aws_lambda_alias" { defaults = { arn = "arn:aws:lambda:${b.examples.region}:${b.examples.account_id}:function:mock:live", invoke_arn = "arn:aws:apigateway:${b.examples.region}:lambda:path/2015-03-31/functions/arn:aws:lambda:${b.examples.region}:${b.examples.account_id}:function:mock:live/invocations" } }\n mock_resource "aws_apigatewayv2_api" { defaults = { id = "mockapi1234", api_endpoint = "https://mockapi1234.execute-api.${b.examples.region}.amazonaws.com", execution_arn = "arn:aws:execute-api:${b.examples.region}:${b.examples.account_id}:mockapi1234" } }\n}\n`;
 b.assertions.push(`run "wrong_account_blocked" {\n command = plan\n variables { account_id = "999999999999" }\n expect_failures = [terraform_data.review_gate]\n}`);
 return b.finish(config,CLOUD_PROVIDER_LOCKS.aws,mocks,AWS_PUBLIC_FAQ_GUIDE);
}

export const AWS_PUBLIC_FAQ_GUIDE=`# AWS public-only FAQ: Lambda and HTTP API

This small synchronous public assistant uses generated Python 3.13 source with the
hash-pinned Mangum ASGI adapter, a published Lambda version/live alias and HTTP API
v2. It has no App Runner eligibility requirement, ECR dependency, always-on task or
load balancer. AWS closed App Runner to new customers; do not silently substitute
it or ask a basic visitor to resolve that restriction.

Run python3 build-runtime.py first. It builds the exact Linux x86_64 wheel closure
and deterministic ZIP from applications/* source, metadata and web assets. Retain
build/artifact-hashes.json. Run emitted faq_acceptance.py and the real Mangum HTTP
API event tests in a matching isolated Python environment; qualify the exact ZIP
inside the reviewed AWS Python 3.13 Linux runtime. Schema/mock/local tests never
establish real Lambda, IAM or model behavior. There is no Terraform execution hook.

The private S3 catalog has public-access blocks, TLS-only policy, AES256 encryption,
owner-enforced ownership, versioning and seven-day noncurrent expiry. Runtime has
GetObject only on catalog.json, direct selected regional Bedrock InvokeModel and
read-only regional retention/logging checks. A separate role assumed by the
existing reviewed company editor has Get/Put only on catalog.json. Article removal
conditionally rewrites the manifest; no object DELETE or bucket administration
is granted. Review inherited IAM and recovery/version-erasure requirements.

Seed genuinely public articles via the separate operator CLI before traffic. No
private source, arbitrary URL fetch, editing HTTP endpoint, end-user sign-in,
question/answer persistence or content-bearing application log is implemented.
Only the owned account/API receives permission to invoke the published live alias.
Same-origin checks are browser hygiene, not visitor authentication. Runtime logs
are WARN-only with seven-day retention; review all platform/audit logging separately.

Converse requests JSON with independently checked schema, source IDs and exact
quotes. It does not claim constrained Bedrock grammar, whose first compilation
can exceed this 29-second boundary. The app fails closed on invalid output, stale
or inaccessible source, unknown retention or enabled model text logging. It never
changes account-wide model policy. Verify actual model availability, retention-none
eligibility, region/context/quota/terms and real answer/citation/abstention/latency.
Long-running work requires the separate durable workflow contract, not a longer
synchronous timeout or a falsely successful response.

Reserved Lambda concurrency is five, with bounded HTTP API throttles. These are
capacity controls, not an invoice cap, anonymous abuse protection or SLA. Verify
destination concurrency quota, cold starts, current prices, budgets and abuse policy.
No prices are invented. Protect state and variable files. Review account/region,
native Terraform schemas/tests and a separately authorized real plan before apply.
No export proves deployment; production state/backup/operations remain gated.

References:
- https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html
- https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html
- https://mangum.fastapiexpert.com/adapter/
`;
