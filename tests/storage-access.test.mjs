import test from 'node:test';
import assert from 'node:assert/strict';
import {terraformSketch} from '../src/terraform.mjs';
import {resourcePlan} from '../src/resources.mjs';
import {validateImport} from '../src/core.mjs';
import {toAgentProject} from '../src/local-agent.mjs';
import {toProjectFile,fromProjectFile} from '../src/project-file.mjs';
const node=(id,provider,service,origin='proposed')=>({id,type:'resource',position:{x:0,y:0},data:{kind:'resource',label:id,provider,service,origin,config:{region:'ap-southeast-2',classification:'Internal',timeout:5000}}});
function fixture(access='s3-read-write'){
 const actor=node('operator','tools','Existing IAM principal','existing');actor.data.binding='aws-iam-principal';
 return {version:1,revision:1,name:'Private storage',provider:'aws',nodes:[actor,node('docs','aws','Amazon S3')],edges:[{id:'access',source:'operator',target:'docs',label:'Upload and read documents',access}]};
}
const tf=p=>JSON.parse(terraformSketch(p)['main.tf.json']);
test('typed operator contract emits bucket-only grants and resolves only implemented gaps',()=>{
 const p=fixture(),t=tf(p),plan=resourcePlan(p);
 assert.deepEqual(t.locals.unfinished_work,[]);assert.deepEqual(plan.gaps,[]);
 const variable=plan.accessPlan.bindings[0].variable;
 assert.equal(t.variable[variable].default,undefined);assert.equal(t.variable[variable].nullable,false);
 assert.match(t.variable[variable].validation.condition,/role\|user/);
 assert.match(JSON.stringify(t.resource.terraform_data.review_gate),/var.aws_account_id/);
 const policy=JSON.parse(Object.values(t.resource.aws_s3_bucket_policy)[0].policy);
 const grants=policy.Statement.filter(s=>s.Effect==='Allow');assert.equal(grants.length,2);
 for(const grant of grants){assert.equal(grant.Principal.AWS,`\u0024{var.${variable}}`);assert.notEqual(grant.Resource,'*');assert.ok(grant.Action.every(a=>!a.includes('*')&&!a.includes('Delete')&&!a.includes('Policy')));}
 assert.deepEqual(grants[0].Action,['s3:ListBucket','s3:GetBucketLocation']);
 assert.deepEqual(grants[1].Action,['s3:GetObject','s3:GetObjectVersion','s3:PutObject']);
 assert.equal(policy.Statement[0].Effect,'Deny');
 assert.equal(Object.values(t.resource.aws_s3_bucket)[0].lifecycle.prevent_destroy,true);
 assert.equal(t.resource.aws_iam_user,undefined);assert.equal(t.resource.aws_iam_role,undefined);
});
test('read-only bindings never grant writes; a second bucket receives no implicit grant',()=>{
 const p=fixture('s3-read');p.nodes.push(node('other','aws','Amazon S3'));
 const policies=Object.values(tf(p).resource.aws_s3_bucket_policy).map(r=>JSON.parse(r.policy));
 assert.equal(policies.length,2);assert.equal(policies[1].Statement.filter(s=>s.Effect==='Allow').length,0);
 assert.ok(!JSON.stringify(policies).includes('s3:PutObject'));
});
test('free text, wrong ownership, wrong target and reversed edges cannot grant access',()=>{
 const invalidOwner=fixture();invalidOwner.nodes[0].data.origin='proposed';assert.throws(()=>tf(invalidOwner),/Reference bindings/);
 for(const mutate of [p=>delete p.nodes[0].data.binding,p=>delete p.edges[0].access,p=>p.edges[0].access='s3:*',p=>p.nodes[1].data.service='AWS Lambda',p=>[p.edges[0].source,p.edges[0].target]=[p.edges[0].target,p.edges[0].source]]){
  const p=fixture();mutate(p);const t=tf(p);
  assert.ok(t.locals.unfinished_work.length);assert.ok(!JSON.stringify(t.resource.aws_s3_bucket_policy||{}).includes('OperatorObjects'));
 }
});
test('an unsupported adjacent integration stays blocked alongside implemented storage access',()=>{
 const p=fixture();p.nodes.push(node('llm','aws','Amazon Bedrock'));p.edges.push({id:'unsupported',source:'docs',target:'llm'});
 const t=tf(p);assert.equal(resourcePlan(p).accessPlan.connections.length,1);assert.ok(t.locals.unfinished_work.some(g=>g.startsWith('connection-')));
});
test('typed binding and access survive project round trip and model request serialization',()=>{
 const p=fixture();const reopened=fromProjectFile(toProjectFile(p));
 const project=reopened.project||reopened;
 for(const candidate of [validateImport(p),project,toAgentProject(p)]){
  assert.equal(candidate.nodes[0].data.binding,'aws-iam-principal');assert.equal(candidate.edges[0].access,'s3-read-write');
 }
});
test('the export carries executable mock tests and a deliberately incomplete deployment input example',()=>{
 const files=terraformSketch(fixture());
 assert.match(files['tests/storage-access.tftest.hcl'],/mock_provider "aws"/);
 assert.match(files['tests/storage-access.tftest.hcl'],/cross_account_binding_rejected/);
 const inputs=JSON.parse(files['deployment.tfvars.json.example']);assert.equal(inputs.review_approved,false);
 assert.match(inputs.aws_account_id,/REPLACE/);
 assert.match(files['VALIDATION.md'],/do not call AWS/);
});
test('an isolated S3 bucket cannot qualify as usable storage without an access contract',()=>{
 const p=fixture();p.nodes=p.nodes.filter(n=>n.id==='docs');p.edges=[];
 const t=tf(p);assert.ok(t.locals.unfinished_work.includes('access-block_646f6373'));
});
test('untrusted component IDs cannot inject Terraform template expressions',()=>{
 const p=fixture(),old=p.nodes[0].id;p.nodes[0].id='${file("/etc/passwd")}';p.edges[0].source=p.nodes[0].id;
 const output=terraformSketch(p)['main.tf.json'];assert.ok(!output.includes('/etc/passwd'));assert.ok(!output.includes('${file('));
});
test('production exports require a remote state backend and exclude local state artifacts from source control',()=>{
 const files=terraformSketch(fixture(),'production'),tf=JSON.parse(files['main.tf.json']);
 assert.deepEqual(tf.terraform.backend,{s3:{encrypt:true,use_lockfile:true}});assert.match(tf.terraform.required_version,/1.10/);
 assert.match(files['backend.hcl.example'],/use_lockfile = true/);assert.match(files['.gitignore'],/tfstate/);
 assert.equal(JSON.parse(terraformSketch(fixture(),'staging')['main.tf.json']).terraform.backend,undefined);
});
test('explicit temporary qualification permits cleanup without weakening staging or production protection',()=>{
 const p=fixture();
 for(const environment of ['staging','production'])assert.equal(Object.values(JSON.parse(terraformSketch(p,environment)['main.tf.json']).resource.aws_s3_bucket)[0].lifecycle.prevent_destroy,true);
 assert.equal(Object.values(JSON.parse(terraformSketch(p,'qualification')['main.tf.json']).resource.aws_s3_bucket)[0].lifecycle.prevent_destroy,false);
});
