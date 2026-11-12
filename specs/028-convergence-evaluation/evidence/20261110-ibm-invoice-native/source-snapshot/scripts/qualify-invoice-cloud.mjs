// Independent native Terraform schema/mock checks; never contacts a cloud account.
import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import {StringDecoder} from 'node:string_decoder';
import {awsInvoiceTerraform} from '../src/invoice-aws.mjs';
import {azureInvoiceTerraform}from'../src/invoice-azure.mjs';
import {gcpInvoiceTerraform}from'../src/invoice-gcp.mjs';
import {ibmInvoiceTerraform}from'../src/invoice-ibm.mjs';

const provider=process.argv[2],adapters={aws:awsInvoiceTerraform,azure:azureInvoiceTerraform,gcp:gcpInvoiceTerraform,ibm:ibmInvoiceTerraform};
if(!adapters[provider])throw Error('Invoice adapter not implemented: '+provider);
const root=path.resolve('.'),out=path.resolve(process.argv[3]||'.local/invoice-cloud-'+provider);
if(fs.existsSync(out))throw Error('Preserve previous qualification; use a fresh output directory');
const scratch=fs.mkdtempSync('/tmp/invoice-cloud-'),checks=[];
const project={id:'11111111-1111-4111-8111-111111111111',version:1,revision:1,name:'Invoice adapter qualification',provider,nodes:[],edges:[]};
const row={id:'invoice',address:'block_696e766f696365',provider,region:{aws:'ap-southeast-2',azure:'australiaeast',gcp:'australia-southeast1',ibm:'au-syd'}[provider]};
const embedded=JSON.parse(fs.readFileSync(path.join(root,'src/runtime/invoice-sources.json'),'utf8'));
for(const[name,body]of Object.entries(embedded))if(fs.readFileSync(path.join(root,'src/runtime',name),'utf8')!==body)throw Error('Embedded runtime is stale; run node scripts/embed-runtimes.mjs before qualification');
const compilerFiles=['scripts/qualify-invoice-cloud.mjs','src/invoice-aws.mjs','src/invoice-azure.mjs','src/invoice-gcp.mjs','src/invoice-ibm.mjs','src/ibm-registry.mjs','src/runtime/invoice-ibm-provider-lock.json','src/runtime/cloud-sql-proxy-lock.json','src/runtime/cloud-sql-proxy-security-review.json','src/runtime/invoice-azapi-provider-lock.json','src/invoice-builder.mjs','src/invoice-application.mjs','src/invoice-dependencies.mjs','src/invoice-operations.mjs','src/python-container.mjs','src/runtime/invoice-sources.json'];
const compilerHashes=()=>Object.fromEntries(compilerFiles.map(name=>[name,createHash('sha256').update(fs.readFileSync(path.join(root,name))).digest('hex')]));const compilerBefore=compilerHashes();
const files=adapters[provider](project,row);
fs.mkdirSync(out,{recursive:true});
for(const [name,body]of Object.entries(files)){const target=path.join(out,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,body);}
const env={PATH:process.env.PATH,HOME:scratch,TMPDIR:scratch,TF_PLUGIN_CACHE_DIR:path.join(root,'.local/provider-cache'),CHECKPOINT_DISABLE:'1',AWS_EC2_METADATA_DISABLED:'true',TF_IN_AUTOMATION:'1'};
async function run(name,args){
 const target=path.join(out,name+'.log'),stream=fs.createWriteStream(target),rawHash=createHash('sha256');let pending='',tail='',filterError=null;
 const stripSchemas=value=>{if(Array.isArray(value))return value.map(stripSchemas);if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([key,child])=>[key,key==='provider_schemas'?{omittedFromLog:true,sha256:createHash('sha256').update(JSON.stringify(child)).digest('hex'),reason:'Provider schemas are pinned separately; retain complete native plans without repeating the entire provider catalogue per run.'}:stripSchemas(child)]));return value;};
 function line(value){let actual=value;if(name==='provider-mocks'&&value.trim()){try{actual=JSON.stringify(stripSchemas(JSON.parse(value)));}catch(error){filterError=error.message;}}stream.write(actual+'\n');tail=(tail+actual+'\n').slice(-4000);}
 const child=spawn(path.join(root,'.venv/bin/terraform'),args,{cwd:out,env});let failure=null;child.on('error',error=>{failure=error.message;});
 const decoder=new StringDecoder('utf8');
 const stdout=(async()=>{for await(const chunk of child.stdout){rawHash.update(chunk);pending+=decoder.write(chunk);let newline;while((newline=pending.indexOf('\n'))!==-1){line(pending.slice(0,newline));pending=pending.slice(newline+1);}}pending+=decoder.end();if(pending)line(pending);})();
 const stderr=(async()=>{for await(const chunk of child.stderr){rawHash.update(chunk);stream.write(chunk);tail=(tail+chunk.toString('utf8')).slice(-4000);}})();
 const timer=setTimeout(()=>child.kill('SIGTERM'),180000);const code=await new Promise(resolve=>child.on('close',resolve));clearTimeout(timer);await Promise.all([stdout,stderr]);await new Promise(resolve=>stream.end(resolve));
 checks.push({name,passed:code===0&&!failure&&!filterError,exitCode:code,error:failure||filterError,logSha256:createHash('sha256').update(fs.readFileSync(target)).digest('hex'),nativeOutputSha256:rawHash.digest('hex'),providerSchemasOmittedFromVerboseLog:name==='provider-mocks'});
 if(code!==0||failure||filterError)throw Error(name+' failed: '+tail);
}
try{await run('provider-init',['init','-backend=false','-input=false','-lockfile=readonly','-no-color']);await run('provider-schema',['validate','-json']);await run('provider-mocks',['test','-json','-verbose']);}
catch(error){checks.push({name:'native-adapter-qualification',passed:false,error:error.message});process.exitCode=1;}
finally{const receipt={kind:'invoice-native-adapter-qualification',provider,checks,passed:checks.length===3&&checks.every(check=>check.passed)&&JSON.stringify(compilerBefore)===JSON.stringify(compilerHashes()),compilerHashes:compilerBefore,compilerUnchanged:JSON.stringify(compilerBefore)===JSON.stringify(compilerHashes()),sourceHashes:Object.fromEntries(Object.entries(files).map(([name,body])=>[name,createHash('sha256').update(body).digest('hex')])),cloudOperations:false,nearDeploymentQualified:false,boundary:'Isolated compiler fixture, native provider schemas and mock plans. No cloud account, model, IAM, restore, complete conversation or deployment evidence.'};fs.writeFileSync(path.join(out,'qualification.json'),JSON.stringify(receipt,null,2)+'\n');fs.rmSync(scratch,{recursive:true,force:true});console.log(JSON.stringify({provider,passed:receipt.passed,checks:checks.map(check=>({name:check.name,passed:check.passed})),receipt:path.join(out,'qualification.json')}));}
