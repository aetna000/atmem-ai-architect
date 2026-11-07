// Optional schema and mock-provider checks. No real AWS plan or apply is executed.
// Needs Terraform 1.7+ for mock_provider; init downloads the official AWS provider.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { terraformSketch } from '../src/terraform.mjs';
const binary=(process.env.ATMEM_ARCHITECT_TERRAFORM_BIN || process.env.ATFORMA_TERRAFORM_BIN) || 'terraform';
const folder=fs.mkdtempSync(path.join(os.tmpdir(),'atforma-terraform-check-'));
const command=(...args)=>{
 const r=spawnSync(binary,[`-chdir=${folder}`,...args],{stdio:'inherit',env:{PATH:process.env.PATH,HOME:folder,TMPDIR:folder,TF_IN_AUTOMATION:'1',CHECKPOINT_DISABLE:'1',...(process.env.ATMEM_ARCHITECT_TERRAFORM_TEST_CACHE?{TF_PLUGIN_CACHE_DIR:process.env.ATMEM_ARCHITECT_TERRAFORM_TEST_CACHE}:{})}});
 if(r.error)throw Error(`Terraform could not start. Install Terraform 1.7+ or set ATFORMA_TERRAFORM_BIN. ${r.error.message}`);
 if(r.status!==0)throw Error(`Terraform ${args[0]} failed (${r.status}); fixture: ${folder}`);
};
const node=(id,label,kind)=>({id,data:{label,kind,provider:'aws',origin:'proposed',description:label,config:{region:'ap-southeast-2',classification:'Internal'}}});
const project={version:1,revision:1,name:'QA storage foundation',provider:'aws',requirements:'Private object storage',nodes:[node('files','Amazon S3','source')],edges:[]};
project.nodes.push({...node('operator','Existing operator','tool'),data:{kind:'tool',label:'Existing operator',provider:'tools',origin:'existing',binding:'aws-iam-principal'}});project.edges.push({id:'access',source:'operator',target:'files',access:'s3-read-write'});
const write=()=>{for(const [name,content]of Object.entries(terraformSketch(project))){const dest=path.join(folder,name);fs.mkdirSync(path.dirname(dest),{recursive:true});fs.writeFileSync(dest,content);}fs.rmSync(path.join(folder,'tests/storage-access.tftest.hcl'),{force:true});};
try {
write();fs.mkdirSync(path.join(folder,'tests'),{recursive:true});
const testFile=path.join(folder,'tests','review.tftest.hcl');
const prefix=`mock_provider "aws" {}\nvariables {\n  aws_region = "ap-southeast-2"\n  aws_account_id = "123456789012"\n  principal_block_6f70657261746f72_arn = "arn:aws:iam::123456789012:role/test"\n}\n`;
fs.writeFileSync(testFile,prefix+`run "unapproved_plan_is_blocked" {\n  command = plan\n  expect_failures = [terraform_data.review_gate]\n}\nrun "reviewed_foundation_can_be_planned" {\n  command = plan\n  variables {\n    review_approved = true\n  }\n}\n`);
command('init','-backend=false','-input=false','-no-color');command('validate','-no-color');command('test','-no-color');
project.nodes.push(node('model','Amazon Bedrock','agent'));project.edges.push({id:'context',source:'files',target:'model'});write();
fs.writeFileSync(testFile,prefix+`run "unfinished_application_stays_blocked_even_when_approved" {\n  command = plan\n  variables {\n    review_approved = true\n  }\n  expect_failures = [terraform_data.review_gate]\n}\n`);
command('validate','-no-color');command('test','-no-color');
console.log(`Terraform validation and all three mock-plan scenarios passed. No AWS operations performed. Fixture: ${folder}`);

} finally { fs.rmSync(path.join(folder,'.terraform'),{recursive:true,force:true}); }
