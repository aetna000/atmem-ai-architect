import {invoiceApplicationFiles}from'./invoice-application.mjs';
import {existingReferenceFiles}from'./existing-references.mjs';
import {INVOICE_OPERATIONS}from'./invoice-operations.mjs';
import{INVOICE_REGION_PATTERNS,validInvoiceRegion}from'./invoice-region.mjs';

export const v=name=>'${var.'+name+'}';
export const r=(type,name,attribute)=>'${'+type+'.'+name+'.'+attribute+'}';
export const l=name=>'${local.'+name+'}';
export const UUID='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';

export function invoiceBuilder(project,row,environment='staging'){
 if(!project||typeof project.id!=='string'||!project.id||!row||!/^block_[0-9a-f]+$/.test(row.address)||!['aws','azure','gcp','ibm'].includes(row.provider))throw Error('Use a stable owned invoice project, address and provider');
 if(!['staging','production','qualification'].includes(environment))throw Error('Use an explicit supported invoice environment');
 const seed='https://atmem.ai/workspaces/'+encodeURIComponent(project.id)+'/'+row.address+'/'+environment;
 const variable={review_approved:{type:'bool',default:false},applications_enabled:{type:'bool',default:false,description:'Enable only after native SQL identity/schema/membership bootstrap, secret population and immutable image publication are reviewed.'}};
 const examples={review_approved:false,applications_enabled:false},resource={},data={},output={},assertions=[],testExpressions={},files=invoiceApplicationFiles(row.provider,row.address);
 files['OPERATIONS.md']=INVOICE_OPERATIONS;
 const locals={name:'${format("invoice-%s",substr(sha256('+JSON.stringify(seed)+'),0,12))}',account_uuid:new RegExp(UUID).test(project.id)?project.id:'${uuidv5("url",'+JSON.stringify(seed)+')}',api_db_user:'${format("invoice_api_%s",substr(sha256('+JSON.stringify(seed)+'),0,12))}',worker_db_user:'${format("invoice_worker_%s",substr(sha256('+JSON.stringify(seed)+'),0,12))}'};
 const input=(name,description,example,pattern)=>{
  if(variable[name])throw Error('Duplicate invoice input '+name);
  variable[name]={type:'string',nullable:false,description,validation:{condition:pattern?'${can(regex('+JSON.stringify(pattern)+',var.'+name+'))}':'${length(trimspace(var.'+name+')) > 0}',error_message:'Supply the reviewed '+name+' input.'}};examples[name]=example;return v(name);
 };
 if(row.region&&!validInvoiceRegion(row.provider,row.region))throw Error('Preserve and resolve the explicit invoice region as a canonical provider region before compilation.');
 const region=input('region','Reviewed single deployment/data region; verify current service/model availability and quotas.',row.region||{aws:'ap-southeast-2',azure:'australiaeast',gcp:'australia-southeast1',ibm:'au-syd'}[row.provider],INVOICE_REGION_PATTERNS[row.provider]);
 if(row.provider==='aws')variable.region.validation.condition=variable.region.validation.condition.slice(0,-1)+' && !startswith(var.region,"cn-")}';
 if(row.region){variable.region.default=row.region;variable.region.validation={condition:'${var.region == '+JSON.stringify(row.region)+'}',error_message:'Placement is bound to this design. Update and regenerate the design before changing region.'};}
 resource.terraform_data={review_gate:{input:{design_revision:project.revision,environment,provider:row.provider},lifecycle:{precondition:[{condition:'${var.review_approved}',error_message:'Review the actual source, placement, identities, existing accounting contract, costs, operations and destination account before any apply.'}]}}};
 const add=(type,name,body)=>((resource[type]||={})[name]={...body,depends_on:['terraform_data.review_gate',...(body.depends_on||[])]});
 function finish(providerConfig,requiredProviders,lock,mock,guide){
  const values=Object.entries({...examples,review_approved:true,applications_enabled:true}).map(([key,value])=>key+' = '+(testExpressions[key]||JSON.stringify(value))).join('\n');
  const config={terraform:{required_version:'>= 1.17.1, < 2.0.0',required_providers:requiredProviders},provider:providerConfig,variable,locals,data,resource,output};
  return{...files,...existingReferenceFiles(project),'.terraform.lock.hcl':lock,'main.tf.json':JSON.stringify(config,null,2)+'\n','deployment.tfvars.json.example':JSON.stringify(examples,null,2)+'\n','.gitignore':'.terraform/\n*.tfstate*\n*.tfplan\n*.tfvars\n*.tfvars.json\n!deployment.tfvars.json.example\n.local/\n.venv/\nbuild/\n__pycache__/\n','tests/invoice.tftest.hcl':mock+'\nvariables {\n'+values+'\n}\n'+assertions.join('\n')+'\nrun "review_required" {\n command = plan\n variables { review_approved = false }\n expect_failures = [terraform_data.review_gate]\n}\n','README.md':guide,'invoice-deployment-boundary.json':JSON.stringify({provider:row.provider,sourceComponent:row.id,namespace:'invoice',accountIdentity:'local.account_uuid',applicationRelease:'Explicit foundation/bootstrap/application phases; no automatic cloud operations.',externalAccounting:'Preserved external dependency with a normalized, independently testable action/receipt contract; actual endpoint/credentials/idempotency acceptance remain destination inputs.',qualification:'Compiler emission alone is not full project acceptance or deployment evidence.'},null,2)+'\n'};
 }
 return{variable,examples,resource,data,locals,output,assertions,testExpressions,files,input,add,finish,region,seed};
}
