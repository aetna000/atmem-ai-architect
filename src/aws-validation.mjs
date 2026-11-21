// Mechanical architecture checks. These do not establish deployed behavior or model quality.
export function assessAwsArchitecture(project,scenario){
 const nodes=project.nodes.filter(n=>n.data.kind!=='note');
 const text=n=>String(n.data.service||n.data.label||'').toLowerCase();
 const has=re=>nodes.some(n=>n.data.provider==='aws'&&re.test(text(n)));
 const ids=new Set(nodes.map(n=>n.id));
 const edges=project.edges.filter(e=>ids.has(e.source)&&ids.has(e.target));
 const visited=new Set(nodes.length?[nodes[0].id]:[]);
 for(let changed=true;changed;){changed=false;for(const e of edges)if(visited.has(e.source)!==visited.has(e.target)){visited.add(e.source);visited.add(e.target);changed=true;}}
 const checks=[{id:'nonempty',passed:nodes.length>0},{id:'unique-component-ids',passed:ids.size===nodes.length},{id:'valid-edge-endpoints',passed:project.edges.every(e=>project.nodes.some(n=>n.id===e.source)&&project.nodes.some(n=>n.id===e.target))},{id:'connected-graph',passed:nodes.length>0&&visited.size===nodes.length},{id:'aws-proposed-components',passed:nodes.filter(n=>n.data.origin!=='existing'&&n.data.role!=='human').every(n=>n.data.provider==='aws')},...scenario.expected.map(name=>({id:`service-${name}`,passed:has(new RegExp(name,'i'))}))];
 if(scenario.id==='01-private-storage')checks.push({id:'storage-only-scope',passed:!has(/bedrock|lambda|opensearch|dynamodb|ecs|app\s*runner/)},{id:'operator-access-contract',passed:nodes.some(n=>n.data.binding==='aws-iam-principal'&&n.data.provider==='tools'&&n.data.origin==='existing'&&edges.some(e=>e.source===n.id&&e.access==='s3-read-write'&&nodes.some(t=>t.id===e.target&&t.data.provider==='aws'&&/\bs3\b/.test(text(t)))))});
 if(['03-async-documents','04-model-summary','05-cited-rag','06-permission-rag','07-enterprise-connectors'].includes(scenario.id))checks.push({id:'connected-components',passed:project.edges.length>0&&nodes.every(n=>project.edges.some(e=>e.source===n.id||e.target===n.id))});
 if(scenario.id==='03-async-documents'){
  const queues=nodes.filter(n=>/sqs/.test(text(n)));
  checks.push({id:'queue-connected-to-worker',passed:queues.some(q=>project.edges.some(e=>e.source===q.id&&nodes.some(n=>n.id===e.target&&/lambda/.test(text(n)))))});
 }
 if(['05-cited-rag','06-permission-rag','07-enterprise-connectors'].includes(scenario.id))checks.push({id:'retrieval-component',passed:has(/opensearch|knowledge\s*base|retriev|search|vector/)||nodes.some(n=>n.data.role==='index'||n.data.implementation==='bounded-rag-catalog')});
 if(scenario.id==='06-permission-rag')checks.push({id:'identity-or-access-component',passed:has(/identity|cognito|single.sign|authoriz|permission|access/)||nodes.some(n=>n.data.provider==='aws'&&n.data.implementation==='iam-rag-api')});
 if(scenario.id==='07-enterprise-connectors')checks.push({id:'web-application-component',passed:nodes.some(n=>n.data.implementation==='rag-web-app')});
 if(scenario.id==='07-enterprise-connectors')for(const source of ['sharepoint','confluence'])checks.push({id:`existing-${source}`,passed:nodes.some(n=>text(n).includes(source)&&n.data.origin==='existing')});
 return {passed:checks.every(c=>c.passed),checks,limitations:'Structural checks only. Application correctness, security, service availability and deployment require independent evidence.'};
}

// A conservative decision about the next validation stage, never a probability of success.
// Only the local test runner supplies evidence; model prose is not execution evidence.
export function assessAwsDeploymentCandidate(project, scenario, terraform, evidence = {}) {
 const architecture=assessAwsArchitecture(project,scenario);
 const blockers=architecture.checks.filter(c=>!c.passed).map(c=>({id:`architecture-${c.id}`,owner:'architecture',message:`Architecture check failed: ${c.id}`}));
 const add=(id,owner,message)=>blockers.push({id,owner,message});
 const resources=terraform?.resource||{};
 const count=Object.entries(resources).filter(([type])=>type.startsWith('aws_')).reduce((sum,[,items])=>sum+Object.keys(items||{}).length,0);
 if(!count)add('no-cloud-resources','generator','No AWS resources are emitted; a valid review gate is not a deployment.');
 const expected={s3:'aws_s3_bucket',lambda:'aws_lambda_function',sqs:'aws_sqs_queue'};
 for(const family of scenario.expected)if(expected[family]&&!Object.keys(resources[expected[family]]||{}).length)add(`missing-${family}`,'generator',`Required ${expected[family]} is absent from the export.`);
 const unfinished=terraform?.locals?.unfinished_work;
 if(!Array.isArray(unfinished))add('missing-coverage-evidence','generator','Export does not declare unresolved implementation coverage.');
 else for(const gap of unfinished)add(`unfinished-${gap}`,'implementation',`Unresolved generated work: ${gap}`);
 if(scenario.id!=='01-private-storage'&&evidence.applicationTests!=='passed')add('application-not-qualified','application','No executable application acceptance evidence for this artifact.');
 if(evidence.providerSchema!=='passed')add('provider-schema-unverified','validation','Run provider-schema validation against this exact export.');
 if(evidence.requirementsReview!=='passed')add('requirements-review-unverified','review','Review requirements against emitted configuration, including identity, limits, region, costs and cleanup.');
 return {status:blockers.length?'blocked':'ready_for_account_plan',awsResourceCount:count,blockers,
  cloudPlan:evidence.cloudPlan||'not_run',deployment:evidence.deployment||'not_run',
  limitations:'No numerical success probability is justified. Schema validity does not prove complete coverage, runtime behavior or deployability. A ready-for-plan result is not permission to deploy.'};
}

export function awsRefinementPrompt(assessment) {
 return `Review this same architecture and its generated Terraform. Keep the original scenario scope and preserve valid component IDs and existing systems. Validation findings: ${JSON.stringify(assessment.blockers)}. Correct architecture defects through a proposal where supported. For missing native resources, application code or integrations, explain the product implementation gap and next concrete engineering action; do not claim a diagram edit implemented it. Do not remove required components, weaken acceptance checks or clear unfinished-work gates to obtain a pass. Do not claim tests ran or request deployment. Identify what remains unverified.`;
}
