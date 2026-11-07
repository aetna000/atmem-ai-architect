// Summarize observed rounds. No model verdict or schema pass becomes cloud evidence.
import fs from 'node:fs';
import path from 'node:path';
import {AWS_SCENARIOS} from '../src/aws-validation-scenarios.mjs';
const root=path.resolve(process.argv[2]||'');
if(!process.argv[2])throw Error('Pass a completed live run directory');
const run=JSON.parse(fs.readFileSync(path.join(root,'validation.json'),'utf8'));
const results=AWS_SCENARIOS.map(scenario=>{
 const rounds=run.results.filter(r=>r.id===scenario.id).sort((a,b)=>(a.round||1)-(b.round||1));
 const first=rounds[0],last=rounds.at(-1);
 const gaps=r=>new Set(r?.unfinishedWork||[]),before=gaps(first),after=gaps(last);
 return {id:scenario.id,rounds:rounds.length,status:last?.deploymentAssessment?.status||'not_evaluated',
  architecture:last?.stages.architecture||'not_run',providerSchema:last?.stages.localValidation||'not_run',
  implementationProgress:rounds.length<2?'not_compared':[...before].every(x=>after.has(x))&&[...after].every(x=>before.has(x))?'unchanged':'changed_requires_review',
  remainingGaps:[...after],blockers:last?.deploymentAssessment?.blockers||[],
  evidence:rounds.map(r=>({round:r.round||1,directory:r.evidenceDirectory||r.id,artifactSha256:r.artifactSha256,stages:r.stages})),
  deployment:last?.stages.deployment||'not_run'};
});
const report={scope:'Product qualification loop; no cloud execution',sourceRun:path.relative(process.cwd(),root),
 interpretation:'A changed gap count is not proof of improvement. Inspect requirements, component identities and implementation evidence. Unchanged implementation gaps need product code work, not more prompt retries.',results};
fs.writeFileSync(path.join(root,'loop-report.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(results.map(({id,rounds,status,architecture,providerSchema,implementationProgress})=>({id,rounds,status,architecture,providerSchema,implementationProgress})),null,2));
