// Visible evaluation-only expected values, authored separately from lowering.
// Adds assertion files; generated implementation/configuration is never patched.
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';
import {compositionFixture} from './composition-fixtures.mjs';import {terraformSketch} from '../../src/terraform.mjs';import {resourcePlan} from '../../src/resources.mjs';
const folder=process.argv[2];if(!folder||fs.existsSync(folder))throw Error('Choose a fresh output directory.');
const cases={aws:{bytes:2147483648,memory:'2048',cpu:'256'},azure:{bytes:1610612736,memory:'1.5Gi',cpu:0.75},gcp:{bytes:6442450944,memory:'6144Mi',cpu:'2'},ibm:{bytes:2000000000,memory:'2G',cpu:'0.5'},'aws-upper':{provider:'aws',bytes:261993005056,memory:'249856',cpu:'32768'},'azure-upper':{provider:'azure',bytes:4294967296,memory:'4Gi',cpu:2},'gcp-upper':{provider:'gcp',bytes:34359738368,memory:'32768Mi',cpu:'8'},'ibm-upper':{provider:'ibm',bytes:48000000000,memory:'48G',cpu:'12'}};
const receipts=[];
for(const [name,expected]of Object.entries(cases)){
 const provider=expected.provider||name;
 const project=compositionFixture(provider),node=project.nodes.at(-1);node.data.config={containerMemoryBytes:expected.bytes,...(provider==='aws'?{logRetentionDays:90}:{})};
 const files=terraformSketch(project),plan=resourcePlan(project),unit=plan.composition.units.find(u=>u.id===node.id),address=plan.rows.find(r=>r.id===node.id).address;
 const paths={aws:[`aws_ecs_task_definition.${address}.memory`,`aws_ecs_task_definition.${address}.cpu`],azure:[`azurerm_container_app.${address}.template[0].container[0].memory`,`azurerm_container_app.${address}.template[0].container[0].cpu`],gcp:[`google_cloud_run_v2_service.${address}.template[0].containers[0].resources[0].limits["memory"]`,`google_cloud_run_v2_service.${address}.template[0].containers[0].resources[0].limits["cpu"]`],ibm:[`ibm_code_engine_app.${address}.scale_memory_limit`,`ibm_code_engine_app.${address}.scale_cpu_limit`]}[provider];
 const assertions=[`${paths[0]} == ${JSON.stringify(expected.memory)}`,`${paths[1]} == ${JSON.stringify(expected.cpu)}`,...(provider==='aws'?[`aws_cloudwatch_log_group.${address}.retention_in_days == 90`]:[])];
 const child=JSON.parse(files[unit.path+'/main.tf.json']),inputs={...JSON.parse(files[unit.path+'/deployment.tfvars.json.example']),review_approved:true};
 const oracle=Object.keys(child.terraform.required_providers).map(name=>`mock_provider "${name}" {}`).join('\n')+'\nvariables {\n'+Object.entries(inputs).map(([key,value])=>key+' = '+JSON.stringify(value)).join('\n')+'\n}\n'+`run "independent_exact_memory_and_compatible_cpu" {\n command = plan\n${assertions.map(condition=>' assert {\n condition = '+condition+'\n error_message = "Independent exact provider allocation mismatch."\n }').join('\n')}\n}\n`;
 for(const [file,body]of Object.entries(files)){const target=path.join(folder,name,file);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,body);}
 fs.writeFileSync(path.join(folder,name,unit.path,'tests/independent-lowering.tftest.hcl'),oracle);
 fs.writeFileSync(path.join(folder,name+'-project.json'),JSON.stringify(project,null,2)+'\n');
 receipts.push({name,provider,expected,unitPath:unit.path,generatedDigests:Object.fromEntries(Object.entries(files).map(([name,body])=>[name,createHash('sha256').update(body).digest('hex')])),independentOracleSha256:createHash('sha256').update(oracle).digest('hex')});
}
fs.writeFileSync(path.join(folder,'receipt.json'),JSON.stringify({cases:receipts,boundary:'Visible exact memory lowering diagnostics. Independent assertions added only as test harness; generated implementation unchanged. Native execution recorded separately.'},null,2)+'\n');
console.log('Provider-aware mixed allocation probes generated at '+folder);
