import sources from './runtime/rag-sources.json' with {type:'json'};
import {compileSummaries} from './bedrock-summary.mjs';
import {RAG_HANDLER} from './rag-handler.mjs';
export function ragPlan(project,rows){
 const byId=new Map(rows.map(r=>[r.id,r])),nodes=new Map(project.nodes.map(n=>[n.id,n]));
 const typed=(r,impl,service)=>r&&!r.existing&&r.provider==='aws'&&r.service===service&&nodes.get(r.id)?.data.implementation===impl;
 const entries=[];
 for(const worker of rows){
  if(!typed(worker,'bounded-keyword-rag','AWS Lambda'))continue;
  const inputs=project.edges.filter(e=>e.target===worker.id&&e.integration==='http-api-lambda');
  const reads=project.edges.filter(e=>e.source===worker.id&&e.integration==='lambda-catalog-read');
  const models=project.edges.filter(e=>e.source===worker.id&&e.integration==='bedrock-converse');
  if(inputs.length!==1||reads.length!==1||models.length!==1)continue;
  const api=byId.get(inputs[0].source),table=byId.get(reads[0].target),model=byId.get(models[0].target);
  if(!typed(api,'iam-rag-api','Amazon API Gateway')||!typed(table,'bounded-rag-catalog','Amazon DynamoDB')||!model?.existing||model.provider!=='aws'||model.service!=='Amazon Bedrock'||nodes.get(model.id)?.data.binding!=='aws-bedrock-model')continue;
  entries.push({worker,api,table,model,edges:[inputs[0],reads[0],models[0]]});
 }
 const counts=new Map();for(const e of entries)for(const r of [e.worker,e.api,e.table])counts.set(r.id,(counts.get(r.id)||0)+1);
 const complete=entries.filter(e=>[e.worker,e.api,e.table].every(r=>counts.get(r.id)===1));
 return {entries:complete,componentIds:complete.flatMap(e=>[e.worker.id,e.api.id,e.table.id,e.model.id]),edgeIds:complete.flatMap(e=>e.edges.map(x=>x.id))};
}
export function compileRag(plan,environment){
 const resources={},variables={},outputs={},files={},builds=[];
 const add=(type,name,body)=>(resources[type]||={})[name]={...body,depends_on:[...(body.depends_on||[]),'terraform_data.review_gate']};
 const ref=(type,row,field)=>`\u0024{${type}.${row.address}.${field}}`;
 for(const {worker,api,table,model} of plan.ragPlan.entries){
  const n=worker.address,a=api.address,t=table.address,tags={ManagedBy:'AtMem AI Architect',Environment:environment,Component:n};
  const base=compileSummaries({...plan,summaryPlan:{entries:[{worker:{...worker,settings:{functionTimeoutSeconds:30,maxOutputTokens:1024,...worker.settings}},model}]}},environment);
  for(const [type,items]of Object.entries(base.resources))resources[type]={...(resources[type]||{}),...items};
  Object.assign(variables,base.variables);Object.assign(outputs,base.outputs);Object.assign(files,base.files);
  files[`handlers/${n}.py`]=RAG_HANDLER;
  files['manage-catalog.py']=sources['catalog_admin.py'];
  files['CATALOG.md']='# Bounded catalog operations\n\nThe catalog accepts at most 100 small UTF-8 documents. Every write supplies explicit subject and region ACLs; empty ACLs deny everyone. Use manage-catalog.py with a separate reviewed operator identity, the output table name, exact account/region and --confirm-write. End-user roles cannot write the catalog. New documents use a transactional capacity counter; updates and deletes require --expected-revision and fail on concurrent changes. Keep document files outside source control.\n\nInstall the hash-locked preflight dependencies first. Supply a JSON document containing exactly id, title, text, allowedSubjects and allowedRegions. Record the returned revision for subsequent updates/deletes. Do not put document contents in Terraform variables or state. Recovery, connector changes and source deletions must use the same conditional write contract.\n\nCallers assume their generated scoped API role and sign POST /live/ask with SigV4. Identity is the stable IAM principal ID; employee region is an authoritative directory field. The body contains only question. Existing broad IAM permissions must be reviewed separately; end users must not have direct Lambda invoke or catalog write access.\n';
  for(const [name,code]of Object.entries(sources).filter(([name])=>['bounded_rag.py','rag_aws_adapter.py'].includes(name)))files[`handlers/${n}/${name}`]=code;
  files[`app-tests/${n}_test.py`]=`import sys\nimport importlib\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).resolve().parents[1]/"build/${n}"))\napi=importlib.import_module("${n}")\n`+sources["rag_acceptance.py"];
  builds.push({address:n,sdk:true,modules:Object.keys(sources).filter(name=>['bounded_rag.py','rag_aws_adapter.py'].includes(name))});
  add('aws_dynamodb_table',t,{name:`atmem-catalog-${ref('aws_iam_role',worker,'name')}`,billing_mode:'PAY_PER_REQUEST',hash_key:'recordId',attribute:[{name:'recordId',type:'S'}],point_in_time_recovery:{enabled:true},server_side_encryption:{enabled:true},deletion_protection_enabled:environment==='production',lifecycle:{prevent_destroy:environment==='production'},tags});
  const policy=JSON.parse(resources.aws_iam_role_policy[n].policy);policy.Statement.push({Effect:'Allow',Action:['dynamodb:GetItem','dynamodb:Scan'],Resource:ref('aws_dynamodb_table',table,'arn')});resources.aws_iam_role_policy[n].policy=JSON.stringify(policy);
  add('aws_apigatewayv2_api',a,{name:`atmem-${a.slice(0,25)}`,protocol_type:'HTTP',tags});
  add('aws_apigatewayv2_integration',a,{api_id:ref('aws_apigatewayv2_api',api,'id'),integration_type:'AWS_PROXY',integration_uri:ref('aws_lambda_alias',worker,'invoke_arn'),payload_format_version:'2.0',timeout_milliseconds:29000});
  add('aws_apigatewayv2_route',a,{api_id:ref('aws_apigatewayv2_api',api,'id'),route_key:'POST /ask',authorization_type:'AWS_IAM',target:`integrations/${ref('aws_apigatewayv2_integration',api,'id')}`});
  add('aws_cloudwatch_log_group',a,{name:`/aws/apigateway/${ref('aws_apigatewayv2_api',api,'id')}`,retention_in_days:`\u0024{var.${n}_log_retention_days}`,tags});
  add('aws_apigatewayv2_stage',a,{api_id:ref('aws_apigatewayv2_api',api,'id'),name:'live',auto_deploy:true,default_route_settings:{throttling_burst_limit:2,throttling_rate_limit:1},access_log_settings:{destination_arn:ref('aws_cloudwatch_log_group',api,'arn'),format:JSON.stringify({requestId:'$context.requestId',status:'$context.status',routeKey:'$context.routeKey'})},tags});
  const invokeArn=`${ref('aws_apigatewayv2_api',api,'execution_arn')}/live/POST/ask`;
  add('aws_lambda_permission',a,{action:'lambda:InvokeFunction',function_name:ref('aws_lambda_function',worker,'function_name'),qualifier:ref('aws_lambda_alias',worker,'name'),principal:'apigateway.amazonaws.com',source_arn:invokeArn,source_account:'${var.aws_account_id}'});
  resources.aws_lambda_function[n].environment.variables={...resources.aws_lambda_function[n].environment.variables,CATALOG_TABLE:ref('aws_dynamodb_table',table,'name'),EXPECTED_ACCOUNT_ID:'${var.aws_account_id}',EXPECTED_API_ID:ref('aws_apigatewayv2_api',api,'id')};
  for(const edge of plan.accessPlan.connections.filter(e=>e.target===api.id&&e.access==='api-invoke')){
   const id=`caller_${n}_${Array.from(new TextEncoder().encode(edge.id),b=>b.toString(16).padStart(2,'0')).join('')}`;
   const subject=`${id}_subject`,region=`${id}_employee_region`;
   variables[subject]={type:'string',nullable:false,description:'Authoritative unique subject for this caller. Use the same stable ID in document ACLs.',validation:{condition:`\u0024{can(regex("^[A-Za-z0-9_-]{1,100}$", var.${subject}))}`,error_message:'Use a stable 1–100 character subject identifier.'}};
   variables[region]={type:'string',nullable:false,description:'Authoritative employee country/region code; never accepted from request body.',validation:{condition:`\u0024{can(regex("^[A-Z]{2}$", var.${region}))}`,error_message:'Use a reviewed two-letter uppercase country/region code.'}};
   add('aws_iam_role',id,{name_prefix:'atmem-rag-caller-',tags,assume_role_policy:JSON.stringify({Version:'2012-10-17',Statement:[{Effect:'Allow',Principal:{AWS:`\u0024{var.${edge.principalVariable}}`},Action:'sts:AssumeRole'}]})});
   add('aws_iam_role_policy',id,{role:`\u0024{aws_iam_role.${id}.id}`,policy:JSON.stringify({Version:'2012-10-17',Statement:[{Effect:'Allow',Action:['execute-api:Invoke'],Resource:invokeArn}]})});
   add('aws_dynamodb_table_item',id,{table_name:ref('aws_dynamodb_table',table,'name'),hash_key:'recordId',item:JSON.stringify({recordId:{S:`IDENTITY#\u0024{aws_iam_role.${id}.unique_id}`},kind:{S:'IDENTITY'},enabled:{BOOL:true},subject:{S:`\u0024{var.${subject}}`},employeeRegion:{S:`\u0024{var.${region}}`}})});
   outputs[id]={value:{role_arn:`\u0024{aws_iam_role.${id}.arn}`,subject:`\u0024{var.${subject}}`,employee_region:`\u0024{var.${region}}`}};
  }
  outputs[`${n}_catalog`]={value:{table_name:ref('aws_dynamodb_table',table,'name'),endpoint:`${ref('aws_apigatewayv2_api',api,'api_endpoint')}/live/ask`}};
 }
 return {resources,variables,outputs,files,builds};
}
