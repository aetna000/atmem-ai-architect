// Local mock-provider execution only. Never reads AWS credentials or calls AWS.
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {terraformSketch} from '../src/terraform.mjs';
const root=path.resolve('.local/storage-access-validation',new Date().toISOString().replaceAll(':','-'));
fs.mkdirSync(root,{recursive:true});
const binary=process.env.ATMEM_ARCHITECT_TERRAFORM_BIN||path.resolve('.venv/bin/terraform');
const mirror=process.env.ATMEM_ARCHITECT_PROVIDER_MIRROR;
const env={PATH:process.env.PATH,HOME:root,CHECKPOINT_DISABLE:'1',TF_IN_AUTOMATION:'1',AWS_EC2_METADATA_DISABLED:'true'};
const evidence=[];
function command(...args){const r=spawnSync(binary,[`-chdir=${root}`,...args],{env,encoding:'utf8',timeout:120000});evidence.push({args,exitCode:r.status,stdout:r.stdout,stderr:r.stderr});fs.writeFileSync(path.join(root,'validation.json'),JSON.stringify({scope:'mock-provider-only; no cloud operations',evidence},null,2));if(r.status!==0)throw Error(`${args[0]} failed: ${r.stdout}\n${r.stderr}`);console.log(r.stdout);}
const p={version:1,revision:1,name:'Storage binding qualification',provider:'aws',nodes:[{id:'operator',data:{kind:'resource',label:'Operator',provider:'tools',origin:'existing',binding:'aws-iam-principal'}},{id:'docs',data:{kind:'source',label:'Documents',service:'Amazon S3',provider:'aws',origin:'proposed'}}],edges:[{id:'access',source:'operator',target:'docs',access:'s3-read-write'}]};
const write=()=>{for(const [name,content]of Object.entries(terraformSketch(p))){const dest=path.join(root,name);fs.mkdirSync(path.dirname(dest),{recursive:true});fs.writeFileSync(dest,content);}};
write();fs.mkdirSync(path.join(root,'tests'),{recursive:true});fs.rmSync(path.join(root,'tests/storage-access.tftest.hcl'));
const variable='principal_block_6f70657261746f72_arn';
const prefix=`mock_provider "aws" {}\nvariables {\n aws_region = "ap-southeast-2"\n aws_account_id = "123456789012"\n ${variable} = "arn:aws:iam::123456789012:role/qualification/operator"\n review_approved = true\n}\n`;
const invalid=['arn:aws:iam::123456789012:root','arn:aws:sts::123456789012:assumed-role/test/session','arn:aws:iam::123456789012:role/*','*'];
fs.writeFileSync(path.join(root,'tests/access.tftest.hcl'),prefix+`
run "bound_storage_plan" {
 command = plan
 assert {
 condition = length(local.unfinished_work) == 0
 error_message = "Implemented access must not leave placeholder gaps."
 }
}
run "wrong_account" {
 command = plan
 variables { ${variable} = "arn:aws:iam::999999999999:role/other" }
 expect_failures = [terraform_data.review_gate]
}
run "review_not_approved" {
 command = plan
 variables { review_approved = false }
 expect_failures = [terraform_data.review_gate]
}
`+invalid.map((arn,i)=>`run "invalid_principal_${i}" {
 command = plan
 variables { ${variable} = "${arn}" }
 expect_failures = [var.${variable}]
}`).join('\n'));
command('init','-backend=false','-input=false','-no-color',...(mirror?[`-plugin-dir=${path.resolve(mirror)}`]:[]));
command('validate','-no-color');command('test','-no-color');
p.edges[0].access='s3-read';write();fs.rmSync(path.join(root,'tests/storage-access.tftest.hcl'));
fs.writeFileSync(path.join(root,'tests/access.tftest.hcl'),prefix+`run "read_only_plan" { command = plan }`);
command('test','-no-color');
p.edges.push({id:'untyped',source:'operator',target:'docs'});write();fs.rmSync(path.join(root,'tests/storage-access.tftest.hcl'));
fs.writeFileSync(path.join(root,'tests/access.tftest.hcl'),prefix+`run "untyped_edge_stays_blocked" {\n command = plan\n expect_failures = [terraform_data.review_gate]\n}`);
command('test','-no-color');
console.log(`Storage access qualification evidence: ${root}`);
