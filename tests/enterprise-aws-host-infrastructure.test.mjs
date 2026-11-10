import test from'node:test';
import assert from'node:assert/strict';
import fs from'node:fs';
import {awsHostVerificationTerraform}from'../src/enterprise-aws-host-infrastructure.mjs';
import source from'../src/runtime/enterprise-aws-host-probe-source.json'with{type:'json'};
const project={id:'qualification',revision:7},row={id:'knowledge',address:'block_6b6e6f776c65646765',provider:'aws',region:'ap-southeast-2'};
const compile=(selected=row)=>awsHostVerificationTerraform(project,selected,'qualification');
test('AWS host probe source embedding is byte-identical to the owned inspected program',()=>{
 assert.equal(source,fs.readFileSync(new URL('../src/runtime/enterprise_aws_host_probe.py',import.meta.url),'utf8'));
});
test('AWS host verifier module preserves project ownership and rejects location/provider substitution',()=>{
 const before=JSON.stringify({project,row});
 for(const selected of [{...row,provider:'gcp'},{...row,region:'${file("private")}'},{...row,address:'block_616e6f74686572'},{...row,id:'\ud800'}])assert.throws(()=>compile(selected));
 assert.equal(JSON.stringify({project,row}),before);assert.equal(JSON.parse(compile()['main.tf.json']).variable.region.default,row.region);
});
test('AWS host verifier provisions only a fixed document and additive worker policy',()=>{
 const tf=JSON.parse(compile()['main.tf.json']);
 assert.deepEqual(Object.keys(tf.resource).sort(),['aws_iam_role_policy','aws_ssm_document','terraform_data']);
 assert.deepEqual(tf.locals.document.parameters,{});assert.equal(tf.locals.document.mainSteps[0].name,'verifyHost');
 assert.equal(tf.locals.worker_policy.Statement.length,5);assert.equal(tf.locals.worker_policy.Statement[2].Resource,'${aws_ssm_document.'+row.address+'.arn}');
 assert.deepEqual(tf.locals.worker_policy.Statement[4].Action,['ssm:GetCommandInvocation']);
 assert.equal(tf.data.aws_iam_role[row.address+'_worker'].name,'${basename(var.worker_role_arn)}');
 assert.ok(tf.resource.terraform_data[row.address+'_review'].lifecycle.precondition.some(item=>item.condition==='${data.aws_iam_role.'+row.address+'_worker.arn == var.worker_role_arn}'));
 assert.equal(tf.resource.terraform_data[row.address+'_review'].input.resolved_worker_arn,'${data.aws_iam_role.'+row.address+'_worker.arn}');
 assert.ok(!JSON.stringify(tf.locals.worker_policy).includes('ssm:GetParameter'));
 assert.ok(!JSON.stringify(tf.resource).includes('aws_iam_role_policy_attachments_exclusive'));
});
test('AWS host verification config uses native document version/hash and retains complete-project boundary',()=>{
 const files=compile(),tf=JSON.parse(files['main.tf.json']),config=tf.output.host_verification.value;
 assert.equal(config.hostDocumentHash,'${aws_ssm_document.'+row.address+'.hash}');
 assert.equal(config.hostDocumentVersion,'${tostring(aws_ssm_document.'+row.address+'.latest_version)}');
 assert.equal(JSON.parse(files['host-policy-boundary.json']).wholeProjectQualified,false);
 assert.equal((files['tests/host-verification.tftest.hcl'].match(/run "/g)||[]).length,7);
 assert.match(files['README.md'],/does not create a compute pool/);
});
test('AWS host verifier preserves hostile source IDs as literal evidence',()=>{
 const id='${file("owned-marker.txt")} %{if true}marker%{endif}',address='block_'+Buffer.from(id).toString('hex');
 const tf=JSON.parse(compile({...row,id,address})['main.tf.json']);
 assert.equal(tf.resource.terraform_data[address+'_review'].input.source_component,id.replace(/\$\{/g,()=>'$${').replace(/%\{/g,()=>'%%{'));
});
