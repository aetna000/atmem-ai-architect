import {publicFaqFiles} from './public-faq.mjs';
import {existingReferenceFiles} from './existing-references.mjs';
export const v=n=>'${var.'+n+'}',ref=(type,n,key)=>'${'+type+'.'+n+'.'+key+'}';
export const UUID='^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$';
export function builder(project,plan,environment,provider){
 if(!plan.publicFaqPlan?.entries.length||plan.publicFaqPlan.entries.some(e=>e.provider!==provider))throw Error('A public FAQ adapter must match every proposed application provider; no cross-cloud substitution.');
 const variable={review_approved:{type:'bool',default:false}},examples={review_approved:false},resource={},output={},files={},data={},assertions=[];
 const gaps=[...plan.gapDetails.map(g=>g.id),...(environment==='production'?['production-state-backup-and-operating-review-required']:[])];
 resource.terraform_data={review_gate:{input:{design_revision:project.revision,environment},lifecycle:{precondition:[{condition:'${var.review_approved && length(local.unfinished_work) == 0}',error_message:'Review the source, public-only publication boundary, destination, native roles, model policy, costs and unresolved scope before deployment.'}]}}};
 const input=(name,description,example,pattern)=>{variable[name]={type:'string',nullable:false,description,validation:{condition:pattern?'${can(regex('+JSON.stringify(pattern)+', var.'+name+'))}':'${length(trimspace(var.'+name+')) > 0}',error_message:'Supply the reviewed '+name+' value.'}};examples[name]=example;return v(name);};
 const add=(type,name,body)=>((resource[type]||={})[name]={...body,depends_on:['terraform_data.review_gate',...(body.depends_on||[])]});
 const source=row=>Object.assign(files,publicFaqFiles(provider,row.address));
 function finish(config,lock,mock,guide){
  const values=Object.entries({...examples,review_approved:true}).map(([name,value])=>name+' = '+JSON.stringify(value)).join('\n');
  return {...files,...existingReferenceFiles(project),'.terraform.lock.hcl':lock,'main.tf.json':JSON.stringify({...config,variable,data,locals:{unfinished_work:gaps},resource,output},null,2),'resource-schedule.json':JSON.stringify(plan,null,2),'deployment.tfvars.json.example':JSON.stringify(examples,null,2),'.gitignore':'.terraform/\n*.tfstate*\n*.tfplan\n*.tfvars\n*.tfvars.json\n!deployment.tfvars.json.example\n.venv/\nbuild/\n*.zip\n__pycache__/\n','tests/public-faq.tftest.hcl':mock+'\nvariables {\n'+values+'\n}\n'+assertions.join('\n')+'\nrun "unapproved_blocked" {\n command = plan\n variables { review_approved = false }\n expect_failures = [terraform_data.review_gate]\n}\n','README.md':guide};
 }
 return {variable,examples,resource,output,files,data,assertions,input,add,source,finish};
}

