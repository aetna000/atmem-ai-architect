// Progress records acknowledge a working draft, never cloud validation or deployment permission.
// Navigation is independent of completion: opening a section must not accept a
// decision, advance a checkpoint or send a model request.
export const DESIGN_SECTIONS=Object.freeze([
 {id:'board',label:'Board',mode:'design',view:'board'},
 {id:'scope',label:'Requirements',mode:'design',view:'requirements'},
 {id:'cloud',label:'Choices',mode:'design',view:'options'},
 {id:'location',label:'Country & region',mode:'design',view:'location'},
 {id:'architecture',label:'Infrastructure',mode:'design',view:'terraform'},
 {id:'review',label:'Review',mode:'review',view:'board'},
 {id:'estimate',label:'Costs',mode:'estimate',view:'board'},
 {id:'delivery',label:'Delivery',mode:'design',view:'outputs'},
].map(Object.freeze));
export function designSection(mode,view){
 if(mode==='deploy')return DESIGN_SECTIONS.find(s=>s.id==='delivery');
 if(mode==='design'&&view==='decisions')view='options';
 return DESIGN_SECTIONS.find(s=>s.mode===mode&&s.view===view)||DESIGN_SECTIONS[0];
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
 return {scope,architecture,estimate:snapshot([architecture,p.estimate||{}])};
}
export function cloudMapping(p){
 const provider=choice(p,'platform.cloud');
 const nodes=p.nodes.filter(n=>n.data.kind!=='note'&&n.data.origin!=='existing');
 const services=CLOUD_SERVICES[provider]||[];
 const gaps=nodes.flatMap(n=>{
  const errors=[];
  if(n.data.provider!==provider || !services.some(s=>[n.data.service,n.data.label].some(value=>s.toLowerCase()===String(value||'').toLowerCase())))errors.push(`${n.data.label}: choose a named ${clouds[provider]||'cloud'} service`);
  if(!n.data.config?.region||/select|unknown|tbd/i.test(n.data.config.region))errors.push(`${n.data.label}: clarify regional or global placement`);
  return errors;
 });
 if(nodes.length>1&&!p.edges.length)gaps.push('Connect the cloud services and describe the interactions');
 for(const edge of p.edges)if(!edge.label || /^(data|flow|connection)$/i.test(edge.label))gaps.push('Describe what each service connection carries');
 if(!nodes.length)gaps.push('No proposed cloud services are drawn yet');
 return {provider,ready:!!provider&&nodes.length>0&&!gaps.length,gaps};
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
 return step('delivery','Prepare the delivery draft','Bring together the architecture, requirements, estimates and infrastructure sketch. Engineering gaps and access checks remain before any deployment.','Prepare the handoff','deploy','board','Walk me through the delivery draft, resource inventory and Terraform sketch. Explain the next engineering task and missing access/validation. Current native IaC covers S3 foundations only and no deployment tool exists. Do not claim this is deployable or deployed.');
}
export function advanceJourney(p,checkpoint){
 const state=journey(p);
 if(state.checkpoint!==checkpoint)return p;
 const key=checkpoint==='review'?'architecture':checkpoint;
 return {...p,extensions:{...p.extensions,journey:{...p.extensions?.journey,[checkpoint]:state.keys[key]}}};
}
