import probeSource from './runtime/enterprise-aws-host-probe-source.json' with{type:'json'};
import {CLOUD_PROVIDER_LOCKS}from'./cloud-provider-locks.mjs';
import {awsHostVerificationTests}from'./enterprise-aws-host-tests.mjs';

// Owned host-verification building block. This does not provision the EC2 pool,
// document store, native execution permissions, application or complete export.
export function awsHostVerificationTerraform(project,row,environment='staging'){
 if(!project||typeof project.id!=='string'||!project.id||project.id.length>255||!Number.isSafeInteger(project.revision)||project.revision<1)throw Error('Use the owned project/revision');
 if(!row||row.provider!=='aws'||typeof row.id!=='string'||!row.id||typeof row.region!=='string'||!(/^(af|ap|ca|eu|il|me|mx|sa|us)-(east|west|south|north|central|southeast|southwest|northeast|northwest)-[1-9]$/).test(row.region))throw Error('Preserve the explicit AWS provider and selected region');
 encodeURIComponent(row.id);
 const address='block_'+Array.from(new TextEncoder().encode(row.id),value=>value.toString(16).padStart(2,'0')).join('');
 if(row.address!==address||!['staging','production','qualification'].includes(environment))throw Error('Use canonical component ownership and environment');
 const n=address,v=name=>'${var.'+name+'}',r=(type,name,attribute)=>'${'+type+'.'+name+'.'+attribute+'}',l=name=>'${local.'+name+'}';
 const literal=value=>value.replace(/\$\{/g,()=>'$${').replace(/%\{/g,()=>'%%{');
 const variable={review_approved:{type:'bool',default:false,nullable:false,description:'Review the exact SSM command, existing worker IAM and host ownership before apply.'}},examples={review_approved:false};
 function input(name,description,example,pattern,defaultValue){
  variable[name]={type:'string',nullable:false,description,validation:{condition:'${can(regex('+JSON.stringify(pattern)+',var.'+name+'))}',error_message:'Supply the reviewed '+name+' input.'}};
  if(defaultValue!==undefined)variable[name].default=defaultValue;examples[name]=example;return v(name);
 }
 const account=input('account_id','Existing destination account, never inferred from a source node.','123456789012','^[0-9]{12}$');
 const region=input('region','Keep the selected architecture region; regenerate to change.',row.region,'^'+row.region+'$',row.region);
 const cluster=input('cluster_arn','Existing owned parser ECS cluster. This module does not create/adopt a compute pool.','arn:aws:ecs:'+row.region+':123456789012:cluster/document-parser','^arn:aws:ecs:[a-z]{2}-[a-z]+-[1-9]:[0-9]{12}:cluster/[A-Za-z0-9_-]{1,255}$');
 const worker=input('worker_role_arn','Existing question-worker IAM role; append one named policy without replacing its other policies.','arn:aws:iam::123456789012:role/question-worker','^arn:aws:iam::[0-9]{12}:role/[A-Za-z0-9_+=,.@/-]{1,128}$');
 const seed='https://atmem.ai/workspaces/'+encodeURIComponent(project.id)+'/'+n+'/'+environment;
 const locals={name:'${format("doc-host-%s",substr(sha256('+JSON.stringify(seed)+'),0,12))}',
  policy_sha256:'${sha256(jsonencode({format="enterprise-aws-host-policy-v1",clusterArn=var.cluster_arn,probeSha256=sha256('+JSON.stringify(literal(probeSource))+')}))}',
  expected:{format:'enterprise-aws-host-policy-v1',clusterArn:cluster,policySha256:l('policy_sha256')}};
 const b64=btoa(Array.from(new TextEncoder().encode(probeSource),value=>String.fromCharCode(value)).join(''));
 const launcher='import base64;exec(compile(base64.b64decode(\''+b64+'\'),"owned-host-probe","exec"))';
 const quoted="'"+launcher.replace(/'/g,"'\"'\"'")+"'";
 const prefix='exec /usr/bin/python3 -I -c '+quoted+' ';
 locals.document={schemaVersion:'2.2',description:'Fixed read-only parser host inspection; no caller command or secret parameters.',parameters:{},
  mainSteps:[{action:'aws:runShellScript',name:'verifyHost',precondition:{StringEquals:['platformType','Linux']},
   inputs:{timeoutSeconds:'30',runCommand:['${format("%s%s",'+JSON.stringify(prefix)+',base64encode(jsonencode(local.expected)))}']}}]};
 const resource={terraform_data:{[n+'_review']:{input:{design_revision:project.revision,source_component:literal(row.id),environment,
  requested_worker_arn:worker,resolved_worker_arn:'${data.aws_iam_role.'+n+'_worker.arn}'},lifecycle:{precondition:[
  {condition:v('review_approved'),error_message:'Review the selected host policy and existing worker before apply.'},
  {condition:'${startswith(var.cluster_arn,format("arn:aws:ecs:%s:%s:cluster/",var.region,var.account_id))}',error_message:'Keep the parser cluster in the selected account/region.'},
  {condition:'${startswith(var.worker_role_arn,format("arn:aws:iam::%s:role/",var.account_id))}',error_message:'Keep the referenced worker in the selected account.'},
  {condition:'${data.aws_iam_role.'+n+'_worker.arn == var.worker_role_arn}',error_message:'The existing worker role must match the full accepted ARN, including its path.'}]}}}};
 const data={aws_iam_role:{[n+'_worker']:{name:'${basename(var.worker_role_arn)}'}}};
 const add=(type,name,body)=>((resource[type]??={})[name]={...body,depends_on:['terraform_data.'+n+'_review',...(body.depends_on||[])]});
 add('aws_ssm_document',n,{name:l('name'),document_type:'Command',document_format:'JSON',target_type:'/AWS::EC2::Instance',content:'${jsonencode(local.document)}',
  tags:{'atmem-document-policy':l('policy_sha256')},lifecycle:{prevent_destroy:true,postcondition:[{condition:'${self.hash_type == "Sha256" && can(regex("^[0-9a-f]{64}$",self.hash))}',error_message:'Require the native SHA256 document hash before exposing verification configuration.'}]}});
 const doc=r('aws_ssm_document',n,'arn'),container='${format("arn:aws:ecs:%s:%s:container-instance/%s/*",var.region,var.account_id,basename(var.cluster_arn))}';
 locals.worker_policy={Version:'2012-10-17',Statement:[
  {Sid:'InspectOwnedCluster',Effect:'Allow',Action:['ecs:ListContainerInstances'],Resource:cluster},
  {Sid:'InspectOwnedInstances',Effect:'Allow',Action:['ecs:DescribeContainerInstances'],Resource:container,Condition:{ArnEquals:{'ecs:cluster':cluster}}},
  {Sid:'FixedProbeDocumentOnly',Effect:'Allow',Action:['ssm:GetDocument','ssm:SendCommand'],Resource:doc},
  {Sid:'TaggedParserHostsOnly',Effect:'Allow',Action:['ssm:SendCommand'],Resource:'${format("arn:aws:ec2:%s:%s:instance/*",var.region,var.account_id)}',Condition:{StringEquals:{'ssm:resourceTag/atmem-document-policy':l('policy_sha256')}}},
  {Sid:'ReadProbeInvocation',Effect:'Allow',Action:['ssm:GetCommandInvocation'],Resource:'*'}]};
 add('aws_iam_role_policy',n,{name:l('name'),role:'${data.aws_iam_role.'+n+'_worker.name}',policy:'${jsonencode(local.worker_policy)}'});
 const output={host_verification:{value:{clusterArn:cluster,hostPolicySha256:l('policy_sha256'),hostDocumentArn:doc,hostDocumentHash:r('aws_ssm_document',n,'hash'),hostDocumentVersion:'${tostring(aws_ssm_document.'+n+'.latest_version)}'},
  depends_on:['aws_ssm_document.'+n,'aws_iam_role_policy.'+n],description:'Fixed command/worker policy only. Compute pool and complete private application are not provided by this module.'}};
 const main={terraform:{required_version:'>= 1.17.1, < 2.0.0',required_providers:{aws:{source:'hashicorp/aws',version:'6.72.0'}}},provider:{aws:{region,allowed_account_ids:[account]}},variable,locals,data,resource,output};
 return {'main.tf.json':JSON.stringify(main,null,2)+'\n','.terraform.lock.hcl':CLOUD_PROVIDER_LOCKS.aws,
  'deployment.tfvars.json.example':JSON.stringify(examples,null,2)+'\n',
  'tests/host-verification.tftest.hcl':awsHostVerificationTests(n,seed,row.region),
  'host-policy-boundary.json':JSON.stringify({component:row.id,address:n,provider:'aws',region:row.region,scope:'Fixed SSM verifier and additive existing-worker policy; not a compute pool or complete private export.',wholeProjectQualified:false,cloudOperations:false},null,2)+'\n',
  'README.md':'# Owned AWS parser-host verification\n\nThis module creates one fixed, parameterless SSM command and appends one named policy to the existing question worker. It references the selected existing parser cluster. It does not create a compute pool, replace a worker role, deploy an application or register a complete private capability.\n\nOnly this SSM document may be submitted, and only instances tagged with the exact policy fingerprint may be targeted. The worker pins native document version/hash, independently checks command content and restricts task placement to the instances it just verified. GetCommandInvocation requires resource wildcard in the native IAM contract; no command discovery, document mutation or Parameter Store read is granted. Account inherited permissions still require inspection.\n\nProvision the dedicated private host pool with matching ECS/daemon/IMDS settings and tags before use. This module deliberately emits no ready parser configuration or invented image/AMI. Runtime/identity, host drift, IAM and eventual native behavior remain subject to independent destination qualification. No account plan or deployment has run.\n'};
}
