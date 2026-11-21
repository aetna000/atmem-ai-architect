// A bounded implementation selected explicitly in the project, never inferred from labels.
export const TEXT_STATISTICS_HANDLER = `"""Authenticated direct invocation; no document text is logged."""
import os

MAX_INPUT_BYTES = int(os.environ.get("MAX_INPUT_BYTES", "65536"))

def handler(event, context):
    if not isinstance(event, dict) or set(event) != {"text"} or not isinstance(event["text"], str):
        raise ValueError("Expected an object containing only a text string")
    text = event["text"]
    try:
        size = len(text.encode("utf-8"))
    except UnicodeEncodeError:
        raise ValueError("Text must be valid Unicode") from None
    if size > MAX_INPUT_BYTES:
        raise ValueError("Text exceeds the configured byte limit")
    return {"wordCount": len(text.split()), "characterCount": len(text)}
`;
export function textStatisticsArtifacts(rows) {
 const files={};
 for(const row of rows.filter(r=>r.compute)){
  files[`handlers/${row.address}.py`]=TEXT_STATISTICS_HANDLER;
  files[`app-tests/${row.address}_test.py`]=`import importlib.util\nimport os\nimport unittest\nfrom pathlib import Path\nfrom contextlib import redirect_stdout\nfrom io import StringIO\nos.environ["MAX_INPUT_BYTES"]="${row.settings?.maxInputBytes??65536}"\nspec=importlib.util.spec_from_file_location("handler",Path(__file__).resolve().parents[1]/"build/${row.address}/${row.address}.py")\nmodule=importlib.util.module_from_spec(spec)\nspec.loader.exec_module(module)\nclass HandlerTests(unittest.TestCase):\n    def test_counts(self):\n        self.assertEqual(module.handler({"text":"one two\\nthree"},None),{"wordCount":3,"characterCount":13})\n        self.assertEqual(module.handler({"text":""},None),{"wordCount":0,"characterCount":0})\n        self.assertEqual(module.handler({"text":"café 世界"},None),{"wordCount":2,"characterCount":7})\n    def test_invalid_and_oversized(self):\n        for value in [None,[],{}, {"text":1}, {"text":"secret","unexpected":True}, {"text":"é"*(module.MAX_INPUT_BYTES//2+1)}]:\n            with self.assertRaises(ValueError):module.handler(value,None)\n    def test_document_not_logged(self):\n        output=StringIO()\n        with redirect_stdout(output):module.handler({"text":"private synthetic document"},None)\n        self.assertEqual(output.getvalue(),"")\n`;
 }
 return files;
}
export function compileTextStatistics(plan, environment="staging") {
 const resources={},data={},variables={},outputs={};
 const add=(type,name,body)=>(resources[type]||={})[name]={...body,depends_on:[...(body.depends_on||[]),'terraform_data.review_gate']};
 for(const row of plan.rows.filter(r=>r.compute)){
  const tags={ManagedBy:"AtMem AI Architect",Environment:environment,Component:row.address};
  const n=row.address,ref=(type,field)=>`\u0024{${type}.${n}.${field}}`;
  const number=(suffix,defaultValue,min,max)=>{const name=`${n}_${suffix}`;variables[name]={type:'number',default:defaultValue,description:`Reviewable ${suffix} for ${n}; confirm workload requirements.`,validation:{condition:`\u0024{var.${name} >= ${min} && var.${name} <= ${max} && floor(var.${name}) == var.${name}}`,error_message:`Use an integer from ${min} to ${max}.`}};return `\u0024{var.${name}}`;};
  const memory=number('memory_mb',row.settings?.memoryMb??128,128,10240),timeout=number('timeout_seconds',row.settings?.functionTimeoutSeconds??10,1,900),concurrency=number('concurrency',row.settings?.concurrency??1,1,1000),maxBytes=number('max_input_bytes',row.settings?.maxInputBytes??65536,1,1000000);
  const retentionName=`${n}_log_retention_days`;
  variables[retentionName]={type:'number',default:row.settings?.logRetentionDays??30,description:'Review log retention against policy; default is not a compliance claim.',validation:{condition:`\u0024{contains([1,3,5,7,14,30,60,90,120,150,180,365,400,545,731,1096,1827,2192,2557,2922,3288,3653], var.${retentionName})}`,error_message:'Choose a supported finite CloudWatch log retention period.'}};
  const versionName=`${n}_release_version`;variables[versionName]={type:'string',default:null,description:'Null deploys the newly published version. A prior numeric version explicitly rolls the live alias back.',validation:{condition:`\u0024{var.${versionName} == null ? true : can(regex("^[1-9][0-9]*$", var.${versionName}))}`,error_message:'Use a published numeric version, or null for the current release.'}};
  add('aws_iam_role',n,{tags,name_prefix:`atmem-${n.slice(0,24)}-`,assume_role_policy:JSON.stringify({Version:'2012-10-17',Statement:[{Effect:'Allow',Principal:{Service:'lambda.amazonaws.com'},Action:'sts:AssumeRole'}]})});
  add('aws_cloudwatch_log_group',n,{tags,name:`/aws/lambda/${ref('aws_iam_role','name')}`,retention_in_days:`\u0024{var.${retentionName}}`});
  add('aws_iam_role_policy',n,{role:ref('aws_iam_role','id'),policy:JSON.stringify({Version:'2012-10-17',Statement:[{Effect:'Allow',Action:['logs:CreateLogStream','logs:PutLogEvents'],Resource:`${ref('aws_cloudwatch_log_group','arn')}:*`}]})});

  add('aws_lambda_function',n,{tags,function_name:ref('aws_iam_role','name'),role:ref('aws_iam_role','arn'),runtime:'python3.13',architectures:['arm64'],handler:`${n}.handler`,filename:`\u0024{path.module}/build/${n}.zip`,source_code_hash:`\u0024{filebase64sha256(format("%s/build/${n}.zip", path.module))}`,memory_size:memory,timeout,reserved_concurrent_executions:concurrency,publish:true,environment:{variables:{MAX_INPUT_BYTES:`\u0024{tostring(var.${n}_max_input_bytes)}`}},depends_on:[`aws_iam_role_policy.${n}`,`aws_cloudwatch_log_group.${n}`]});
  add('aws_lambda_alias',n,{name:'live',function_name:ref('aws_lambda_function','function_name'),function_version:`\u0024{var.${versionName} == null ? aws_lambda_function.${n}.version : var.${versionName}}`});
  for(const edge of plan.accessPlan.connections.filter(e=>e.target===row.id&&e.access==='lambda-invoke')){
   const id=`invoke_${Array.from(new TextEncoder().encode(edge.id),b=>b.toString(16).padStart(2,'0')).join('')}`;
   add('aws_lambda_permission',id,{action:'lambda:InvokeFunction',function_name:ref('aws_lambda_function','function_name'),qualifier:ref('aws_lambda_alias','name'),principal:`\u0024{var.${edge.principalVariable}}`});
  }
  outputs[n]={value:{invoke_arn:ref('aws_lambda_alias','arn'),published_version:ref('aws_lambda_function','version'),log_group:ref('aws_cloudwatch_log_group','name')}};
 }
 return {resources,data,variables,outputs,files:textStatisticsArtifacts(plan.rows)};
}
