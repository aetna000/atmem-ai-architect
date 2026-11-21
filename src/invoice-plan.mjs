import {resourceAddress} from './identifiers.mjs';
import{existingDeployment}from'./deployment-ownership.mjs';
import{existingReference}from'./existing-references.mjs';
import{validInvoiceRegion,invoicePartitionGap}from'./invoice-region.mjs';

export const INVOICE_SERVICES={aws:'Amazon ECS',azure:'Azure Container Apps',gcp:'Google Cloud Run',ibm:'IBM Code Engine'};
export const hasInvoice=project=>project.nodes.some(node=>node.data.kind!=='note'&&node.data.implementation==='invoice-workflow');
const address=resourceAddress;
const resourceTypes={aws:['aws_vpc','aws_db_instance','aws_s3_bucket','aws_ecs_cluster'],azure:['azurerm_resource_group','azurerm_postgresql_flexible_server','azurerm_storage_account','azurerm_container_app_environment'],gcp:['google_compute_network','google_sql_database_instance','google_storage_bucket','google_artifact_registry_repository'],ibm:['ibm_code_engine_project','ibm_database','ibm_cos_bucket','ibm_appid_application']};

// One composed delivery unit owns its API, worker, isolated parser, private SQL,
// original-document store, identities and operating tasks. Extra drawn systems
// remain in the plan with explicit gaps; they are never silently absorbed/deleted.
export function invoiceResourcePlan(project){
 const nodes=project.nodes.filter(node=>node.data.kind!=='note'),gapDetails=[];
 const add=(id,message,links={})=>gapDetails.push({id,message,...links});
 const candidates=nodes.filter(node=>node.data.implementation==='invoice-workflow'&&INVOICE_SERVICES[node.data.provider]===node.data.service&&!existingDeployment(node)&&node.data.origin!=='existing');
 const selected=candidates.length===1?candidates[0]:null;
 if(!selected)add('invoice-composition-scope','Select one proposed invoice-workflow delivery unit on its exact supported provider/service. Multiple independent workflows require separate compositions.');
 const browsers=nodes.filter(node=>existingDeployment(node)&&node.data.provider==='tools'&&node.data.binding==='web-browser');
 const references=nodes.map(node=>existingReference(node)).filter(Boolean);
 const browserEdges=selected?project.edges.filter(edge=>edge.target===selected.id&&edge.integration==='browser-https'&&browsers.some(node=>node.id===edge.source)):[];
 const accountingEdges=selected?project.edges.filter(edge=>edge.source===selected.id&&edge.integration==='approved-accounting-api'&&references.some(ref=>ref.id===edge.target)):[];
 if(selected){
  if(!browserEdges.length)add('invoice-browser-contract','Connect the existing staff browser to the workflow with browser-https.',{componentIds:[selected.id]});
  if(accountingEdges.length!==1)add('invoice-accounting-contract','Connect the workflow to exactly one explicitly existing accounting service with approved-accounting-api. Its endpoint, credential and normalized action/idempotency acceptance are destination inputs, not a replacement accounting system.',{componentIds:[selected.id]});
  const config=selected.data.config||{};
  if(config.region&&config.region!=='To be selected'&&!validInvoiceRegion(selected.data.provider,config.region))add('invoice-config-region',invoicePartitionGap(selected.data.provider,config.region)||'Preserve the selected placement and propose a canonical provider region within that accepted residency. Country names or expressions are not deployment-region identifiers; this is engineering work, not a request for the user to configure infrastructure.',{componentIds:[selected.id]});
  for(const[key,expected]of Object.entries({maxPdfBytes:10000000,maxPdfPages:100,retentionDays:90}))if(config[key]!==undefined&&config[key]!==expected)add('invoice-config-'+key,'The invoice implementation supplies '+key+'='+expected+'; preserve the explicit '+config[key]+' requirement and implement that change before claiming coverage.',{componentIds:[selected.id]});
  for(const key of ['outputContract','modelId','maxInputBytes','maxOutputTokens','memoryMb','containerMemoryBytes','functionTimeoutSeconds','concurrency','logRetentionDays'])if(config[key]!==undefined)add('invoice-config-'+key,'Explicit '+key+' is not mapped by this composed invoice contract; retain and implement that selection instead of substituting the recipe setting.',{componentIds:[selected.id]});
 }
 const generatedEdges=new Set([...browserEdges,...(accountingEdges.length===1?accountingEdges:[])].map(edge=>edge.id));
 const rows=nodes.map(node=>{
  const d=node.data,existing=existingDeployment(node),reference=references.find(ref=>ref.id===node.id),invoice=selected?.id===node.id;
  const externalBrowser=existing&&d.provider==='tools'&&d.binding==='web-browser';
  const row={id:node.id,address:address(node.id),label:d.label,provider:d.provider,service:d.service||d.label,sourceExisting:d.origin==='existing',existing,foundation:false,compute:false,reference:false,externalReference:externalBrowser,existingServiceReference:reference||null,invoice,implemented:invoice||externalBrowser||!!reference,resources:invoice?resourceTypes[d.provider]:[],region:d.config?.region||'To be selected',settings:{},dependencies:project.edges.filter(edge=>edge.target===node.id).map(edge=>edge.source),selection:'Explicit invoice composition or preserved existing reference',costDrivers:invoice?'API/worker/parser/operator compute, private database/backup/storage, NAT/private endpoints, identity, registry, model tokens, retained object versions, logging and notification delivery. Verify current regional rates and quotas; capacity limits are not spending caps.':'Existing system or actor; review its externally owned costs and access contract.',terraform:invoice?'Composed invoice API/worker/parser, durable SQL queue, private originals, review authorization, guarded accounting delivery and operating tasks generated; destination behavior remains unverified':reference?'Existing service reference — preserve without provisioning/import; actual connection acceptance required':externalBrowser?'External staff browser — authenticated workflow channel generated; no browser infrastructure to provision':'Additional required component is not implemented by this invoice composition'};
  if(!row.implemented)add('resource-'+row.address,d.label+': '+row.terraform+'.',{componentIds:[node.id]});
  return row;
 });
 const connections=project.edges.map(edge=>({id:edge.id,source:edge.source,target:edge.target,data:edge.label||'data',generated:generatedEdges.has(edge.id),status:generatedEdges.has(edge.id)?'Typed invoice contract/source generated; account, authorization and runtime acceptance required':'Additional required integration remains unimplemented'}));
 for(const edge of connections)if(!edge.generated)add('connection-'+address(edge.id),'Implement the preserved integration '+edge.source+' → '+edge.target+'.',{edgeIds:[edge.id]});
 const row=selected?rows.find(row=>row.id===selected.id):null;
 const invoicePlan={entries:row?[{row,provider:row.provider,browserIds:browserEdges.map(edge=>edge.source),accountingId:accountingEdges.length===1?accountingEdges[0].target:null}]:[],componentIds:row?[row.id]:[],edgeIds:[...generatedEdges]};
 return {revision:project.revision,rows,connections,invoicePlan,gaps:gapDetails.map(gap=>gap.message),gapDetails,accessPlan:{bindings:[],connections:[]},asyncPlan:{entries:[],pipelines:[],componentIds:[],edgeIds:[]},summaryPlan:{entries:[],modelIds:[]},ragPlan:{entries:[],componentIds:[]},sourceContractPlan:{sources:[],connections:[]},webPlan:{entries:[],componentIds:[]},structuredApiPlan:{entries:[]},publicFaqPlan:{entries:[],componentIds:[],editorIds:[],edgeIds:[]},azureStructuredPlan:{entries:[],componentIds:[]},gcpStructuredPlan:{entries:[],componentIds:[]},ibmStructuredPlan:{entries:[],componentIds:[]},scope:'Typed composed invoice implementation; extra required systems and flows remain visible. Source generation and local qualifications do not prove the destination deployment.',sources:[]};
}
