import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {AI_QUALIFICATION_SCENARIOS,AI_QUALIFICATION_FAMILIES,assessAiArchitecture} from '../src/ai-qualification-scenarios.mjs';
const root=path.resolve(import.meta.dirname,'..'),archive=path.join(root,'examples/cloud-qualification');
const manifest=JSON.parse(fs.readFileSync(path.join(archive,'manifest.json'))),results=[];
for(const scenario of AI_QUALIFICATION_SCENARIOS){
 const runs=manifest.runs.filter(r=>r.kind==='real-model-browser-run'&&Array.isArray(r.results)&&r.results.some(x=>x.provider===scenario.id)).sort((a,b)=>b.id.localeCompare(a.id));
 const latestAttempt=runs[0];const run=runs.find(r=>fs.existsSync(path.join(archive,'runs',r.id,scenario.id,'workspace.json')))||latestAttempt;if(!run){results.push({id:scenario.id,status:'not_run'});continue;}
 const folder=path.join('runs',run.id,scenario.id),file=path.join(archive,folder,'workspace.json'),record=run.results.find(x=>x.provider===scenario.id);
 if(!fs.existsSync(file)){results.push({id:scenario.id,status:'journey_failed',sourceRun:run.id,error:record.error});continue;}
 const data=fs.readFileSync(file),project=JSON.parse(data),assessment=assessAiArchitecture(project,scenario);
 const runtime=JSON.parse(fs.readFileSync(path.join(archive,folder,'emulation.json')));
 results.push({id:scenario.id,sourceRun:run.id,latestAttempt:{sourceRun:latestAttempt.id,record:latestAttempt.results.find(x=>x.provider===scenario.id)},workspaceSha256:createHash('sha256').update(data).digest('hex'),project:path.join(folder,'project.atmem-ai-architect.json'),promptHistory:path.join(folder,'prompt-history.json'),status:runtime.status==='passed'?'bounded_runtime_pass':'implementation_incomplete',runtimeStatus:runtime.status,runtimeChecks:runtime.checks?.length||0,staticAssessment:assessment,cloudPlan:'not_run',deployment:'not_run'});
}
fs.writeFileSync(path.join(archive,'ai-assessment.json'),JSON.stringify({kind:'retrospective-static-assessment-with-linked-runtime-evidence',assessorSha256:createHash('sha256').update(fs.readFileSync(path.join(root,'src/ai-qualification-scenarios.mjs'))).digest('hex'),results},null,2)+'\n');
const table=['# AI scenario evidence matrix','','Links open loadable project files from actual model/UI runs. **Local checks passed** means only the recorded bounded runtime checks. **Implementation incomplete** is not deployable. Static graph checks do not prove semantic completeness. When a later provider request failed, the link retains the most recent available project; ai-assessment.json records the later failed attempt separately. Prompts, raw model responses, screenshots and Terraform sit beside each project.','','| Workload | AWS | Azure | Google Cloud | IBM |','|---|---|---|---|---|'];
for(const family of AI_QUALIFICATION_FAMILIES)table.push('| '+family.name+' | '+['aws','azure','gcp','ibm'].map(provider=>{const r=results.find(x=>x.id===provider+'-'+family.id);return r.project?`[${r.status==='bounded_runtime_pass'?'Local checks passed':'Implementation incomplete'}](${r.project})`:r.status;}).join(' | ')+' |');
fs.writeFileSync(path.join(archive,'MATRIX.md'),table.join('\n')+'\n');console.log(JSON.stringify({cases:results.length,runtimePassed:results.filter(r=>r.runtimeStatus==='passed').length,staticGraphPassed:results.filter(r=>r.staticAssessment?.passed).length,journeyFailed:results.filter(r=>r.status==='journey_failed').length}));
