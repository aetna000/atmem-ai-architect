import {resourcePlan} from './resources.mjs';
import {containerContract} from './container-contracts.mjs';

// These are next-step explanations, not evidence of implemented or tested behavior.
export function emulationGuidance(project,report,{beforeRun=false}={}){
 if(!report||(report.checks||[]).length)return null;
 let plan;try{if(project)plan=resourcePlan(project);}catch{}
 const base={title:'Testing couldn’t start',reason:'The local test setup is incomplete.',next:'Prepare a repair task so the missing implementation can be fixed.',owner:'engineering',needsModel:false,componentId:null};
 if(report.status==='unavailable')return {...base,reason:'The local test runner is not available.',next:'Enable the test runner, then try again.'};
 if(report.status==='failed')return {...base,reason:'The test runner stopped before it could check your application.',next:'Use the report to fix the test runner, then try again.'};
 if(plan&&!plan.rows.length)return {...base,reason:'There is no system drawn yet.',next:'Describe what you want to build so Architect can draw a first design.',owner:'user'};
 const browserIds=new Set((project?.nodes||[]).filter(n=>n.data.origin==='existing'&&n.data.provider==='tools'&&!n.data.binding&&/\bbrowser\b/i.test(n.data.label)).map(n=>n.id));
 const missing=plan?.rows.find(r=>!r.implemented&&!browserIds.has(r.id));
 if(missing)return {...base,title:'Application code is needed before testing',reason:`${missing.label} is in your design, but runnable application code is not available for this test.`,next:'Choose “Implement and check”. Architect will generate code and connections, attempt local tests, and show results in Implementation. Nothing is deployed to the cloud.',action:'build-and-test',componentId:missing.id};
 if(browserIds.size)return {...base,reason:'The browser needs to be marked as an external client.',next:'Architect can propose that small correction, then try the test again.',owner:'architect',needsModel:true,componentId:[...browserIds][0]};
 const access=plan?.gapDetails.find(g=>g.id.startsWith('access-'));
 if(access)return {...base,reason:'An access rule is missing.',next:'Confirm who should be allowed to use this block; Architect can add the rule.',owner:'user',needsModel:true,componentId:access.componentIds?.[0]};
 const connection=plan?.connections.find(e=>!e.generated);
 if(connection)return {...base,reason:'The connections between the application’s parts are not implemented yet.',next:'Choose “Implement and check” to generate its connections and run local checks.',action:'build-and-test',componentId:connection.source};
 const container=project?.nodes.find(containerContract);
 if(container&&!beforeRun)return {...base,reason:`${container.data.label} has infrastructure defined, but no supported local application test yet.`,next:'Choose “Implement and check” to use its supplied image and run local checks.',action:'build-and-test',componentId:container.id};
 return beforeRun?null:base;
}
export function guidanceMessage(guidance){
 return `**${guidance.title}.**\n\n${guidance.reason}\n\n**Next:** ${guidance.next}`;
}
export function emulationRepairTask(project,report){
 const guidance=report?emulationGuidance(project,report):emulationPreflight(project);
 report=report||{};
 return `# Architect repair task\n\n${guidance?.reason||'Investigate the test failure.'}\n\n## Next engineering step\n\n${guidance?.next||'Reproduce the failure and repair its cause.'}\n\n## Reproduce\n\n- Design: ${project.name}\n- Saved design version (internal): ${report.designRevision??project.revision}\n- Artifact: ${report.artifactDigest||'not available'}\n- Checks executed: ${(report.checks||[]).length}\n- Affected component: ${guidance?.componentId||'test runner / implementation pipeline'}\n\n## Preserve\n\nKeep all requested scope, existing systems, component IDs, connections and access boundaries. Fix the generator or test runner, not an exported copy. Do not clear gates or report success without executing the relevant checks.\n\n## Reported blockers\n\n${(report.blockers||[]).map(b=>'- '+String(b)).join('\n')||'- No structured blocker was returned; inspect the full report.'}\n\n## Acceptance\n\nRegenerate from this project, execute the affected tests and regression checks, and retain a fresh report tied to the generated files. Separate local checks from cloud plans and deployment. This task is a work request, not evidence of a completed fix.\n`;
}

// Readiness guidance is not a test report and must never be stored as evidence.
export function emulationPreflight(project){
 const guidance=emulationGuidance(project,{status:'blocked',checks:[]},{beforeRun:true});
 return guidance?.action==='build-and-test'?guidance:null;
}
