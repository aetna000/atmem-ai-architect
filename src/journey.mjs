// Progress records acknowledge a working draft, never cloud validation or deployment permission.
// Navigation is independent of completion: opening a section must not accept a
// decision, advance a checkpoint or send a model request.
export const DESIGN_SECTIONS=Object.freeze([
 {id:'board',label:'Board',mode:'design',view:'board'},
 {id:'scope',label:'Requirements',mode:'design',view:'requirements'},
 {id:'cloud',label:'Choices',mode:'design',view:'options'},
 {id:'review',label:'Review',mode:'review',view:'board'},
 {id:'delivery',label:'Delivery',mode:'design',view:'outputs'},
].map(Object.freeze));
export function journeySectionId(id){return ({location:'cloud',architecture:'cloud',estimate:'review'})[id]||id;}
export function designSection(mode,view){
 if(mode==='deploy')return DESIGN_SECTIONS[4];
 if(mode==='estimate'||mode==='review'||view==='terraform')return DESIGN_SECTIONS[3];
 if(view==='location'||view==='decisions')view='options';
 return DESIGN_SECTIONS.find(s=>s.mode===mode&&s.view===view)||DESIGN_SECTIONS[0];
}
export function completedStages(p){
 const keys=journeyKeys(p),saved=p.extensions?.journey||{};
 return {board:p.nodes.some(n=>n.data.kind!=='note'),scope:saved.scope===keys.scope,
 cloud:cloudMapping(p).ready&&saved.architecture===keys.architecture,
 review:saved.review===keys.architecture&&saved.estimate===keys.estimate,
 delivery:saved.delivery===keys.delivery}; // Delivery means the exact package was downloaded, not deployed.
}
export function journeyAction(guidance,section='board'){
 if(section===journeySectionId(guidance.id)&&guidance.checkpoint&&section!=='board')return {kind:'continue',label:guidance.continueLabel};
 if(section!=='board')return null;
 const destination={scope:['scope','Review requirements'],location:['cloud','Choose country & region'],review:['review','Review design'],estimate:['review','Review costs'],delivery:['delivery','Review delivery']}[guidance.id];
 if(destination)return {kind:'navigate',section:destination[0],label:destination[1]};
 return {kind:guidance.checkpoint?'continue':'assist',label:guidance.checkpoint?guidance.continueLabel:guidance.action};
}
const clouds={aws:'AWS',azure:'Azure',gcp:'Google Cloud',ibm:'IBM Cloud'};
export const CLOUD_SERVICES={
 aws:['Amazon S3','Amazon Bedrock','Bedrock Guardrails','AWS Lambda','Amazon API Gateway','Amazon Cognito','Amazon OpenSearch Serverless','Amazon OpenSearch Service','Amazon DynamoDB','Amazon RDS','Amazon ECS','AWS Fargate','Amazon CloudWatch','AWS IAM','IAM policy','Amazon VPC','AWS KMS','Amazon SageMaker AI','SageMaker AI','Amazon EventBridge','Amazon SQS'],
 azure:['Azure Blob Storage','Azure AI Search','Azure OpenAI','Azure OpenAI Service','Microsoft Foundry','Azure AI Foundry','Azure Functions','Azure Container Apps','Azure API Management','Microsoft Entra ID','Azure Key Vault','Azure Monitor','Azure Cosmos DB','Azure SQL','Azure SQL Database','Azure Virtual Network','Azure App Service','Azure Service Bus'],
 gcp:['Cloud Storage','Google Cloud Storage','Vertex AI','Vertex AI Search','Cloud Run','Cloud Functions','API Gateway','Identity Platform','Cloud IAM','Cloud Logging','Cloud Monitoring','Secret Manager','Cloud SQL','Firestore','BigQuery','Pub/Sub','Google Kubernetes Engine','VPC'],
 ibm:['IBM Cloud Object Storage','watsonx.ai','watsonx.ai Runtime','watsonx model deployment','watsonx Orchestrate','IBM Cloud Code Engine','IBM Cloud IAM','IBM Cloud Databases for PostgreSQL','IBM Db2','IBM Cloud Kubernetes Service','IBM Cloud Secrets Manager','IBM Cloud Logs','IBM Cloud Monitoring','IBM Cloud VPC','IBM Event Streams']
};
const choice=(p,subject)=>[...(p.decisions||[])].reverse().find(d=>d.subject===subject&&d.status==='Accepted')?.decision;
// Compact change fingerprints, not security/authentication tokens or copies of project text.
const snapshot=value=>{const text=JSON.stringify(value);let a=2166136261,b=5381;for(let i=0;i<text.length;i++){a=Math.imul(a^text.charCodeAt(i),16777619);b=Math.imul(b,33)^text.charCodeAt(i);}return `${text.length}-${(a>>>0).toString(16)}-${(b>>>0).toString(16)}`;};
export function journeyKeys(p){
 const scope=snapshot([p.brief?.application||p.requirements||'',(p.needs||[]).filter(r=>r.source==='user').map(r=>[r.id,r.statement,r.measure]).sort()]);
 const architecture=snapshot([scope,p.nodes.filter(n=>n.data.kind!=='note').map(n=>[n.id,n.data.label,n.data.service,n.data.provider,n.data.config,n.data.description]).sort(),p.edges.map(e=>[e.source,e.target,e.label]).sort(),choice(p,'platform.cloud'),choice(p,'cloud.region'),choice(p,'data.country')]);
 const estimate=snapshot([architecture,p.estimate||{}]);return {scope,architecture,estimate,delivery:snapshot([architecture,estimate,p.revision])};
}
export function cloudMapping(p){
 const provider=choice(p,'platform.cloud');
 const nodes=p.nodes.filter(n=>n.data.kind!=='note'&&n.data.origin!=='existing');
 const services=CLOUD_SERVICES[provider]||[];
 const gaps=nodes.flatMap(n=>{
  const errors=[];
  // This acknowledges a named working draft, never service availability or
  // implementation support. Examples are a legacy label fallback, not a registry.
  const explicit=typeof n.data.service==='string'&&n.data.service.trim()&&!/^(?:storage|compute|database|service|api|ai|unknown|tbd|to be .*|select.*)$/i.test(n.data.service.trim());
  if(n.data.provider!==provider || !(explicit||services.some(s=>s.toLowerCase()===String(n.data.label||'').toLowerCase())))errors.push(`${n.data.label}: choose a named ${clouds[provider]||'cloud'} service`);
  if(!n.data.config?.region||/select|unknown|tbd/i.test(n.data.config.region))errors.push(`${n.data.label}: clarify regional or global placement`);
  return errors;
 });
 if(nodes.length>1&&!p.edges.length)gaps.push('Connect the cloud services and describe the interactions');
 for(const edge of p.edges)if(!edge.label || /^(data|flow|connection)$/i.test(edge.label))gaps.push('Describe what each service connection carries');
 if(!nodes.length)gaps.push('No proposed cloud services are drawn yet');
 if(provider&&!Object.hasOwn(CLOUD_SERVICES,provider))gaps.push('The selected cloud has no reviewed journey mapping; preserve the target and clarify its support.');
 return {provider,ready:Object.hasOwn(CLOUD_SERVICES,provider)&&nodes.length>0&&!gaps.length,gaps,boundary:'named_working_draft_only'};
}
export function journey(p){
 const keys=journeyKeys(p),saved=p.extensions?.journey||{},mapping=cloudMapping(p);
 const base={keys,mapping,availableModes:['design']};
 const step=(id,title,reason,action,mode,view,prompt,extra={})=>({...base,id,title,reason,action,mode,view,prompt,...extra});
 if(!p.nodes.some(n=>n.data.kind!=='note'))return step('idea','Sketch your idea','Tell me the outcome you want. We’ll draw it and clarify the requirements together.','Help me shape the idea','design','board','Help me shape my idea. Ask one useful question about the desired outcome; draw only from what I tell you.');
 if(saved.scope!==keys.scope)return step('scope','Sketch and document','We have a first design. Let’s check that the document captures what you want before choosing cloud services.','Work through this design','design','requirements','Review the board and requirements together. Briefly summarise the intended outcome and ask the most important unresolved scope question. Update the document from the discussion. Do not jump to costs or deployment.',{checkpoint:'scope',continueLabel:'Continue to cloud options'});
 if(!mapping.provider)return step('cloud','Explore cloud solutions','We’ll compare how AWS, Azure, Google Cloud and IBM would implement this scope, then choose together.','Explore cloud options','design','options','Compare AWS, Azure, Google Cloud and IBM for our agreed working scope. Populate optionAssessment with actual service combinations for each option, integration tradeoffs and unknowns. Ask one question about existing systems or cloud preference. Do not assume a choice.');
 if(!choice(p,'data.country')&&!choice(p,'cloud.region'))return step('location','Choose where it will run',`We’re exploring ${clouds[mapping.provider]}. Country and data residency determine which services and regions fit.`,'Discuss country and residency','design','board',`We have chosen ${clouds[mapping.provider]}. Ask which country the users and data should be in, and whether data must stay there. Offer regional choices after the answer; do not silently select a country.`);
 if(!mapping.ready || saved.architecture!==keys.architecture)return step('architecture',`Build the ${clouds[mapping.provider]} architecture`,mapping.ready?'The board now names cloud services. Let’s check how they connect and what still needs validating.':'Translate the concept into named cloud services, their responsibilities, connections and regional placement.','Develop the cloud architecture','design','board',`Create or refine a concrete ${clouds[mapping.provider]} architecture for our scope and chosen country/region. Return a complete graph proposal using real named services in data.service and data.label, explicit responsibilities in descriptions, meaningful connection labels and region placement. Preserve existing systems and comments. Explain the mapping and ask one useful refinement question. Identify unverified regional availability and integration assumptions. Service candidates: ${CLOUD_SERVICES[mapping.provider].join(', ')}. Current mapping gaps: ${mapping.gaps.join('; ')||'none; discuss the integrations and remaining assumptions'}.`,{checkpoint:mapping.ready?'architecture':null,continueLabel:'Review this cloud design'});
 base.availableModes=['design','review'];
 if(saved.review!==keys.architecture)return step('review','Check the design together','We have a concrete service design. Let’s examine security, resilience, integration gaps and the assumptions that need validation.','Walk through the design risks','review','board','Review the concrete cloud architecture against our requirements. Explain the highest-impact risk or integration assumption, identify verification needed, and ask one question. A diagram is not evidence that services work together.',{checkpoint:'review',continueLabel:'Estimate with the remaining risks recorded'});
 base.availableModes=['design','review','estimate'];
 if(saved.estimate!==keys.estimate)return step('estimate','Build the cost estimate','We’ll use the actual services and ask about usage, then model sourced running costs and implementation effort.','Work through the costs','estimate','board','Estimate the concrete cloud architecture progressively. Use sourced prices where supported. Ask the single missing usage/model/scale question with the biggest effect. Separate cloud running cost and delivery effort, and keep missing rates explicit.',{checkpoint:'estimate',continueLabel:'Prepare a delivery draft with cost gaps noted'});
 base.availableModes=['design','review','estimate','deploy'];
 return step('delivery','Review the handoff','Inspect the captured implementation, requirements and exact check evidence. Missing implementation or validation remains visible.','Review delivery','design','outputs','Review the actual delivery package and its requirements, implementation, infrastructure and recorded checks. Explain the next engineering task from that evidence. Treat design-only output, missing or stale implementation and unexecuted checks explicitly. Do not claim cloud availability, deployment or full project acceptance from a diagram or local check.');
}
export function advanceJourney(p,checkpoint){
 const state=journey(p);
 if(state.checkpoint!==checkpoint)return p;
 const key=checkpoint==='review'?'architecture':checkpoint;
 return {...p,extensions:{...p.extensions,journey:{...p.extensions?.journey,[checkpoint]:state.keys[key]}}};
}

// Explicit completion actions acknowledge a working draft; navigation never does.
export function acknowledgeStage(p,stage){
 const keys=journeyKeys(p),previous=p.extensions?.journey||{},saved={...previous};
 if(stage==='scope'&&(p.needs?.length||p.brief?.application?.trim()))saved.scope=keys.scope;
 if(stage==='cloud'&&cloudMapping(p).ready)saved.architecture=keys.architecture;
 if(stage==='review')saved.review=keys.architecture;
 if(stage==='delivery')saved.delivery=keys.delivery;
 return {...p,extensions:{...p.extensions,journey:saved}};
}
