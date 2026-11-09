import {STRUCTURED_OPERATION_POLICY} from './structured-operation-policy.mjs';
import {STRUCTURED_WEB_HTML,STRUCTURED_WEB_CSS,STRUCTURED_WEB_JS,STRUCTURED_WEB_GUIDE} from './structured-web.mjs';
import sources from './runtime/rag-sources.json' with {type:'json'};
import {RAG_WEB_HTML,RAG_WEB_CSS,RAG_WEB_JS} from './rag-web-assets.mjs';
export function webPlan(project,rows,retrievalPlan){
 const nodes=new Map(project.nodes.map(n=>[n.id,n])),byId=new Map(rows.map(r=>[r.id,r]));
 const entries=[];
 for(const rag of retrievalPlan.entries){
  const links=project.edges.filter(e=>e.target===rag.api.id&&e.integration==='web-rag-api');
  if(links.length!==1)continue;
  const web=byId.get(links[0].source);
  if(!web||web.existing||web.provider!=='aws'||web.service!=='Amazon CloudFront'||nodes.get(web.id)?.data.implementation!==(rag.structured?'structured-web-app':'rag-web-app'))continue;
  const signins=project.edges.filter(e=>e.source===web.id&&e.integration==='oauth-pkce');if(signins.length!==1)continue;
  const identity=byId.get(signins[0].target);
  if(!identity||identity.existing||identity.provider!=='aws'||identity.service!=='Amazon Cognito'||nodes.get(identity.id)?.data.implementation!==(rag.structured?'structured-user-pool':'rag-user-pool'))continue;
  const auth=project.edges.filter(e=>e.source===identity.id&&e.target===rag.api.id&&e.integration==='jwt-authorizer');if(auth.length!==1)continue;
  entries.push({...rag,web,identity,edges:[links[0],signins[0],auth[0]]});
 }
 const webIds=new Set(entries.map(e=>e.web.id));
 const browsers=project.nodes.filter(n=>n.data.origin==='existing'&&n.data.provider==='tools'&&n.data.binding==='web-browser');
 const browserEdges=project.edges.filter(e=>e.integration==='browser-https'&&webIds.has(e.target)&&browsers.some(n=>n.id===e.source));
 return {entries,componentIds:[...entries.flatMap(e=>[e.web.id,e.identity.id]),...browserEdges.map(e=>e.source)],edgeIds:[...entries.flatMap(e=>e.edges.map(x=>x.id)),...browserEdges.map(e=>e.id)]};
}
export function compileWeb(plan,environment,resources){
 const data={},outputs={},files={};
 const add=(type,name,body)=>(resources[type]||={})[name]={...body,depends_on:[...(body.depends_on||[]),'terraform_data.review_gate']};
 const ref=(type,row,field)=>`\u0024{${type}.${row.address}.${field}}`;
 for(const {web,identity,api,worker,table,structured} of plan.webPlan.entries){
  if(!structured)files['manage-web-users.py']=sources['web_user_admin.py'];
  if(structured)files['STRUCTURED-WEB.md']=STRUCTURED_WEB_GUIDE;
  else files['WEB.md']='# Authenticated knowledge web application\n\nCloudFront serves private S3 assets and proxies /api/* to the authenticated API. Cognito uses authorization-code flow with S256 PKCE, required software-token MFA and administrator-created users. The API requires the atmem/ask access-token scope; identity and employee region come from the authoritative catalog mapping, never request-body fields or editable profile claims.\n\nRun manage-web-users.py using a separate reviewed operator identity, the output user pool/catalog, exact account and region, an authoritative subject/employee-region mapping and --confirm-change. It prompts for a temporary password, suppresses invitation email and journals the new user before adding the directory mapping. Deliver credentials through your approved secure process; the user sets a permanent password and enrolls MFA at first sign-in. A partial onboarding failure remains denied until its directory mapping is completed. Never add passwords to Terraform or source control.\n\nDisable a user with the same tool and --disable: the authoritative directory is disabled before Cognito, so already-issued tokens lose application access. Review the receipt if either step fails. Existing administrator IAM permissions can bypass application controls; end users must not hold those permissions.\n\nVerify sign-in/MFA, logout, expired/incorrect-scope tokens, Alice/Bob isolation, source citations, document changes and user revocation through the actual web application. Local browser fixtures are not live Cognito acceptance. Frontend tokens stay in memory; transient PKCE state is removed after callback. No external scripts or HTML rendering of model answers are used.\n';
  const w=web.address,i=identity.address,a=api.address,n=worker.address,tags={ManagedBy:'AtMem AI Architect',Environment:environment,Component:w};
  add('aws_s3_bucket',w,{bucket_prefix:'atmem-web-',force_destroy:false,lifecycle:{prevent_destroy:environment==='production'},tags});
  const bucket=ref('aws_s3_bucket',web,'id');
  add('aws_s3_bucket_public_access_block',w,{bucket,block_public_acls:true,block_public_policy:true,ignore_public_acls:true,restrict_public_buckets:true});
  add('aws_s3_bucket_server_side_encryption_configuration',w,{bucket,rule:{apply_server_side_encryption_by_default:{sse_algorithm:'AES256'}}});
  add('aws_s3_bucket_versioning',w,{bucket,versioning_configuration:{status:'Enabled'}});
  add('aws_s3_bucket_ownership_controls',w,{bucket,rule:{object_ownership:'BucketOwnerEnforced'}});
  add('aws_cloudfront_origin_access_control',w,{name:`atmem-${w.slice(0,35)}`,origin_access_control_origin_type:'s3',signing_behavior:'always',signing_protocol:'sigv4'});
  add('aws_cognito_user_pool',i,{name:`atmem-${i.slice(0,35)}`,deletion_protection:environment==='production'?'ACTIVE':'INACTIVE',mfa_configuration:'ON',software_token_mfa_configuration:{enabled:true},admin_create_user_config:{allow_admin_create_user_only:true},username_configuration:{case_sensitive:false},password_policy:{minimum_length:14,require_lowercase:true,require_uppercase:true,require_numbers:true,require_symbols:true,temporary_password_validity_days:1},tags});
  add('aws_cognito_user_pool_domain',i,{user_pool_id:ref('aws_cognito_user_pool',identity,'id'),domain:`\u0024{lower(replace(aws_cognito_user_pool.${i}.id, "_", "-"))}`});
  const authOrigin=`https://${ref('aws_cognito_user_pool_domain',identity,'domain')}.auth.\u0024{var.aws_region}.amazoncognito.com`;
  const issuer=`https://cognito-idp.\u0024{var.aws_region}.amazonaws.com/${ref('aws_cognito_user_pool',identity,'id')}`;
  add('aws_cognito_resource_server',i,{identifier:'atmem',name:structured?'AI workspace':'Knowledge assistant',user_pool_id:ref('aws_cognito_user_pool',identity,'id'),scope:[{scope_name:'ask',scope_description:structured?'Submit input for a human-reviewed AI result':'Ask questions from authorized documents'}]});
  const callback=`https://${ref('aws_cloudfront_distribution',web,'domain_name')}/`;
  add('aws_cognito_user_pool_client',i,{name:structured?'structured-web':'knowledge-web',user_pool_id:ref('aws_cognito_user_pool',identity,'id'),generate_secret:false,allowed_oauth_flows_user_pool_client:true,allowed_oauth_flows:['code'],allowed_oauth_scopes:['openid','atmem/ask'],supported_identity_providers:['COGNITO'],callback_urls:[callback],logout_urls:[callback],prevent_user_existence_errors:'ENABLED',enable_token_revocation:true,access_token_validity:15,id_token_validity:15,refresh_token_validity:1,token_validity_units:{access_token:'minutes',id_token:'minutes',refresh_token:'days'},depends_on:[`aws_cognito_resource_server.${i}`]});
  add('aws_apigatewayv2_authorizer',w,{api_id:ref('aws_apigatewayv2_api',api,'id'),name:'verified-web-users',authorizer_type:'JWT',identity_sources:['$request.header.Authorization'],jwt_configuration:{audience:[ref('aws_cognito_user_pool_client',identity,'id')],issuer}});
  add('aws_apigatewayv2_route',w,{api_id:ref('aws_apigatewayv2_api',api,'id'),route_key:'POST /api/ask',authorization_type:'JWT',authorizer_id:ref('aws_apigatewayv2_authorizer',web,'id'),authorization_scopes:['atmem/ask'],target:`integrations/${ref('aws_apigatewayv2_integration',api,'id')}`});
  add('aws_lambda_permission',w,{action:'lambda:InvokeFunction',function_name:ref('aws_lambda_function',worker,'function_name'),qualifier:ref('aws_lambda_alias',worker,'name'),principal:'apigateway.amazonaws.com',source_arn:`${ref('aws_apigatewayv2_api',api,'execution_arn')}/live/POST/api/ask`,source_account:'${var.aws_account_id}'});
  Object.assign(resources.aws_lambda_function[n].environment.variables,{COGNITO_ISSUER:issuer,COGNITO_CLIENT_ID:ref('aws_cognito_user_pool_client',identity,'id'),...(structured?{COGNITO_USER_POOL_ID:ref('aws_cognito_user_pool',identity,'id'),EXPECTED_API_ID:ref('aws_apigatewayv2_api',api,'id')}:{})});
  if(structured){const policy=JSON.parse(resources.aws_iam_role_policy[n].policy);policy.Statement.push({Effect:'Allow',Action:['cognito-idp:AdminGetUser'],Resource:ref('aws_cognito_user_pool',identity,'arn')});resources.aws_iam_role_policy[n].policy=JSON.stringify(policy);}
  // The distribution does not depend on client-specific assets or API routes;
  // this avoids an OAuth callback/domain dependency cycle.
  data.aws_cloudfront_cache_policy={...(data.aws_cloudfront_cache_policy||{}),[w]:{name:'Managed-CachingDisabled'}};
  data.aws_cloudfront_origin_request_policy={...(data.aws_cloudfront_origin_request_policy||{}),[w]:{name:'Managed-AllViewerExceptHostHeader'}};
  add('aws_cloudfront_response_headers_policy',w,{name:`atmem-${w.slice(0,35)}`,security_headers_config:{content_security_policy:{content_security_policy:`default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self' ${authOrigin}; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self' ${authOrigin}`,override:true},content_type_options:{override:true},frame_options:{frame_option:'DENY',override:true},referrer_policy:{referrer_policy:'no-referrer',override:true},strict_transport_security:{access_control_max_age_sec:31536000,include_subdomains:true,override:true}}});
  add('aws_cloudfront_distribution',w,{enabled:true,is_ipv6_enabled:true,default_root_object:'index.html',price_class:'PriceClass_All',origin:[{domain_name:ref('aws_s3_bucket',web,'bucket_regional_domain_name'),origin_id:'private-web',origin_access_control_id:ref('aws_cloudfront_origin_access_control',web,'id')},{domain_name:`\u0024{replace(aws_apigatewayv2_api.${a}.api_endpoint, "https://", "")}`,origin_id:'authenticated-api',origin_path:'/live',custom_origin_config:{http_port:80,https_port:443,origin_protocol_policy:'https-only',origin_ssl_protocols:['TLSv1.2']}}],default_cache_behavior:{target_origin_id:'private-web',viewer_protocol_policy:'redirect-to-https',allowed_methods:['GET','HEAD'],cached_methods:['GET','HEAD'],cache_policy_id:`\u0024{data.aws_cloudfront_cache_policy.${w}.id}`,response_headers_policy_id:ref('aws_cloudfront_response_headers_policy',web,'id'),compress:true},ordered_cache_behavior:[{path_pattern:'/api/*',target_origin_id:'authenticated-api',viewer_protocol_policy:'https-only',allowed_methods:['GET','HEAD','OPTIONS','PUT','PATCH','POST','DELETE'],cached_methods:['GET','HEAD'],cache_policy_id:`\u0024{data.aws_cloudfront_cache_policy.${w}.id}`,origin_request_policy_id:`\u0024{data.aws_cloudfront_origin_request_policy.${w}.id}`,response_headers_policy_id:ref('aws_cloudfront_response_headers_policy',web,'id')}],restrictions:{geo_restriction:{restriction_type:'none'}},viewer_certificate:{cloudfront_default_certificate:true},tags});
  add('aws_s3_bucket_policy',w,{bucket,policy:JSON.stringify({Version:'2012-10-17',Statement:[{Effect:'Allow',Principal:{Service:'cloudfront.amazonaws.com'},Action:'s3:GetObject',Resource:`${ref('aws_s3_bucket',web,'arn')}/*`,Condition:{StringEquals:{'AWS:SourceArn':ref('aws_cloudfront_distribution',web,'arn')}}},{Effect:'Deny',Principal:'*',Action:'s3:*',Resource:[ref('aws_s3_bucket',web,'arn'),`${ref('aws_s3_bucket',web,'arn')}/*`],Condition:{Bool:{'aws:SecureTransport':'false','aws:PrincipalIsAWSService':'false'}}}]})});
  const safeTitle=String(web.label).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;').replaceAll('$','&#36;').replaceAll('%','&#37;');
  const fieldsBase64=structured?btoa(String.fromCharCode(...new TextEncoder().encode(JSON.stringify(worker.settings.outputContract.fields)))):undefined;
  const assets={'index.html':[structured?STRUCTURED_WEB_HTML.replaceAll('AI workspace',safeTitle).replace('maxlength="20000"','maxlength="'+(worker.settings.maxInputBytes??16000)+'"'):RAG_WEB_HTML,'text/html; charset=utf-8'],'app.css':[structured?STRUCTURED_WEB_CSS:RAG_WEB_CSS,'text/css; charset=utf-8'],'app.js':[structured?STRUCTURED_WEB_JS:RAG_WEB_JS,'application/javascript; charset=utf-8'],'config.json':[JSON.stringify({authOrigin,clientId:ref('aws_cognito_user_pool_client',identity,'id'),...(structured?{fieldsBase64,maxInputBytes:worker.settings.maxInputBytes??16000,requestDeadlineMs:STRUCTURED_OPERATION_POLICY.browserDeadlineMs}:{})}),'application/json']};
  for(const [name,[content,type]]of Object.entries(assets)){
   const address=`${w}_${name.replaceAll('.','_')}`;add('aws_s3_object',address,{bucket,key:name,content,content_type:type,cache_control:'no-store',source_hash:`\u0024{sha256(${JSON.stringify(content)})}`,depends_on:[`aws_s3_bucket_versioning.${w}`,`aws_s3_bucket_server_side_encryption_configuration.${w}`]});files[`web/${w}/${name}`]=content;
  }
  outputs[`${w}_web`]={value:{url:callback,user_pool_id:ref('aws_cognito_user_pool',identity,'id'),...(table?{catalog_table:ref('aws_dynamodb_table',table,'name')}:{})}};
 }
 return {data,outputs,files};
}
