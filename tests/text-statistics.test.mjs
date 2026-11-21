import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {spawnSync} from 'node:child_process';
import {terraformSketch} from '../src/terraform.mjs';
import {validateImport} from '../src/core.mjs';
import {toAgentProject} from '../src/local-agent.mjs';
const fixture=()=>({version:1,revision:1,name:'Text statistics',provider:'aws',nodes:[{id:'caller',position:{x:0,y:0},data:{kind:'resource',label:'Caller',provider:'tools',origin:'existing',binding:'aws-iam-principal'}},{id:'counter',position:{x:100,y:0},data:{kind:'resource',label:'Counter',service:'AWS Lambda',provider:'aws',implementation:'text-statistics'}}],edges:[{id:'invoke',source:'caller',target:'counter',access:'lambda-invoke'}]});
test('explicit compute contract generates executable Lambda, least-privilege logs, alias and caller grant',()=>{
 const p=fixture(),files=terraformSketch(p),tf=JSON.parse(files['main.tf.json']);
 assert.deepEqual(tf.locals.unfinished_work,[]);
 for(const type of ['aws_lambda_function','aws_iam_role','aws_iam_role_policy','aws_cloudwatch_log_group','aws_lambda_alias','aws_lambda_permission'])assert.equal(Object.keys(tf.resource[type]).length,1,type);
 const fn=Object.values(tf.resource.aws_lambda_function)[0];assert.equal(fn.publish,true);assert.equal(fn.runtime,'python3.13');assert.ok(fn.depends_on.some(x=>x.startsWith('aws_iam_role_policy.')));
 const logPolicy=JSON.parse(Object.values(tf.resource.aws_iam_role_policy)[0].policy);
 assert.deepEqual(logPolicy.Statement[0].Action,['logs:CreateLogStream','logs:PutLogEvents']);assert.notEqual(logPolicy.Statement[0].Resource,'*');
 const permission=Object.values(tf.resource.aws_lambda_permission)[0];assert.equal(permission.action,'lambda:InvokeFunction');assert.match(permission.qualifier,/aws_lambda_alias/);assert.match(permission.principal,/var.principal_/);
 assert.equal(tf.resource.aws_lambda_function_url,undefined);
 assert.ok(Object.keys(files).some(n=>n.startsWith('handlers/')));assert.ok(Object.keys(files).some(n=>n.startsWith('app-tests/')));
 for(const copy of [validateImport(p),toAgentProject(p)]){assert.equal(copy.nodes[1].data.implementation,'text-statistics');assert.equal(copy.edges[0].access,'lambda-invoke');}
});
test('a Lambda label alone never manufactures an application implementation',()=>{
 const p=fixture();delete p.nodes[1].data.implementation;const tf=JSON.parse(terraformSketch(p)['main.tf.json']);
 assert.equal(tf.resource.aws_lambda_function,undefined);assert.ok(tf.locals.unfinished_work.length);
});
test('the generated Python application passes its shipped acceptance tests',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'atmem-handler-'));
 try{
  for(const [name,content]of Object.entries(terraformSketch(fixture()))){const dest=path.join(root,name);fs.mkdirSync(path.dirname(dest),{recursive:true});fs.writeFileSync(dest,content);}
  const built=spawnSync(path.resolve('.venv/bin/python'),['build-runtime.py'],{cwd:root,encoding:'utf8',env:{PATH:process.env.PATH}});assert.equal(built.status,0,built.stdout+built.stderr);
  const hash=fs.readFileSync(path.join(root,'build/artifact-hashes.json'),'utf8');
  const rebuilt=spawnSync(path.resolve('.venv/bin/python'),['build-runtime.py'],{cwd:root,encoding:'utf8',env:{PATH:process.env.PATH}});assert.equal(rebuilt.status,0);assert.equal(fs.readFileSync(path.join(root,'build/artifact-hashes.json'),'utf8'),hash);
  const r=spawnSync(path.resolve('.venv/bin/python'),['-m','unittest','discover','-s','app-tests','-p','*_test.py','-v'],{cwd:root,encoding:'utf8',env:{PATH:process.env.PATH}});
  assert.equal(r.status,0,r.stdout+r.stderr);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
test('requested runtime settings survive model/project round trips and change generated Terraform defaults',()=>{
 const p=fixture();p.nodes[1].data.config={memoryMb:512,functionTimeoutSeconds:25,concurrency:3,maxInputBytes:20000,logRetentionDays:90};
 for(const copy of [p,validateImport(p),toAgentProject(p)]){
  const vars=JSON.parse(terraformSketch(copy)['main.tf.json']).variable;
  for(const [suffix,value]of [['memory_mb',512],['timeout_seconds',25],['concurrency',3],['max_input_bytes',20000],['log_retention_days',90]])assert.equal(Object.entries(vars).find(([name])=>name.endsWith(suffix))[1].default,value);
 }
 p.nodes[1].data.config.concurrency=0;assert.throws(()=>terraformSketch(p),/Invalid concurrency/);
 p.nodes[1].data.config.concurrency=3;p.nodes[1].data.config.logRetentionDays=2;assert.throws(()=>validateImport(p),/retention/);
});
