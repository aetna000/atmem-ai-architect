import { setPrice, usage } from './estimate.mjs';
const patterns = {aws:/\bs3\b/i,azure:/blob|data lake|azure storage/i,gcp:/cloud storage|storage bucket/i,ibm:/object storage|\bcos\b/i};
export const storageNodes = p => p.nodes.filter(n=>patterns[n.data.provider]?.test(`${n.data.label} ${n.data.service || ''}`));
const sources = {'AWS public Price List':'https://pricing.us-east-1.amazonaws.com/','Azure Retail Prices API':'https://prices.azure.com/','Google Cloud Billing Catalog':'https://cloud.google.com/'};
export function applyPriceQuotes(project, quotes) {
 let p=project;
 for(const quote of quotes||[]){
  if(!sources[quote.source] || !quote.url?.startsWith(sources[quote.source]) || !['GB-month','GiB-month'].includes(quote.unit))continue;
  for(const n of storageNodes(p)){
   const existing=p.estimate?.prices?.[n.id];
   if(n.data.provider!==quote.provider || n.data.config?.region!==quote.region || existing?.source && !sources[existing.source])continue;
   // Shared usage is decimal GB; preserve the conversion in the quote note.
   const factor=quote.unit==='GiB-month'?1e9/(1024**3):1;
   p=setPrice(p,n.id,{price:quote.price*factor,currency:quote.currency,source:quote.source,url:quote.url,date:quote.date,region:quote.region,service:quote.service,tierLimit:quote.tierLimit,coverageIncomplete:true,note:quote.coverage+(factor!==1?`; provider GiB converted from decimal GB using ${factor}`:'')});
  }
 }
 return p;
}
export async function fetchStoragePrices(session,project){
 const quotes=[],errors=[];
 const selections=[...new Map(storageNodes(project).filter(n=>n.data.config?.region && !/select|unknown/i.test(n.data.config.region)).map(n=>[`${n.data.provider}:${n.data.config.region}`,{provider:n.data.provider,region:n.data.config.region}])).values()];
 for(const selection of selections){
  try{
   const response=await fetch('/api/pricing/storage',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.token}`},body:JSON.stringify({projectId:project.id,...selection}),signal:AbortSignal.timeout(20000)});
   const value=await response.json();
   if(!response.ok || value.available===false){errors.push({provider:selection.provider,reason:value.reason||value.detail,sourceUrl:value.sourceUrl});continue;}
   quotes.push(value);
  }catch(e){errors.push({provider:selection.provider,reason:e.message});}
 }
 return {quotes,errors};
}

export const lambdaNodes=p=>p.nodes.filter(n=>n.data.provider==='aws'&&/\blambda\b/i.test(`${n.data.service||''} ${n.data.implementation||''} ${n.data.label}`));
export function applyLambdaQuote(project,node,quote){
 if(quote.available!==true||quote.provider!=='aws'||quote.region!==node.data.config?.region||quote.source!=='AWS public Price List'||!quote.url?.startsWith('https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSLambda/'))return project;
 const chosen=project.estimate?.projectSize;
 if(!chosen)return project;
 const requests=usage(project).requests_per_month.value;if(requests==null)return project;
 const configured=node.data.config||{},memory=Number.isFinite(configured.memoryMb)?configured.memoryMb:128,duration=Number.isFinite(configured.estimatedDurationMs)?configured.estimatedDurationMs:200;
 if(memory<128||memory>10240||duration<=0||duration>900000)return project;
 const quantities={requests,compute:requests*memory/1024*duration/1000};
 const current=project.estimate?.details||[],prefix=`auto-lambda-${node.id}-`;
 if(current.some(line=>line.componentId===node.id&&!line.id.startsWith(prefix)))return project;
 const generated=[];
 for(const kind of ['requests','compute']){
  const meter=quote.meters?.[kind];if(!meter||!Number.isFinite(meter.price)||meter.price<=0||meter.tierLimit!=null&&quantities[kind]>meter.tierLimit)return project;
  generated.push({id:prefix+kind,componentId:node.id,description:kind==='requests'?'Lambda requests':'Lambda compute',quantity:quantities[kind],unit:kind==='requests'?'requests':'GB-seconds',price:meter.price,currency:quote.currency,service:meter.service,region:quote.region,source:quote.source,date:quote.date,url:quote.url,coverageIncomplete:kind==='compute',note:`${chosen} planning usage; ${memory} MB; ${duration} ms per request; ${quote.architecture}. ${quote.coverage}`});
 }
 return {...project,estimate:{...project.estimate,details:[...current.filter(line=>!line.id.startsWith(prefix)),...generated]}};
}
export async function fetchPlanningPrices(session,project){
 const storage=await fetchStoragePrices(session,project);let next=applyPriceQuotes(project,storage.quotes);const errors=[...storage.errors];
 for(const node of lambdaNodes(project)){
  const region=node.data.config?.region;if(!region||!/^[a-z]{2}-(?:gov-)?[a-z]+-\d$/.test(region)){errors.push({component:node.data.label,reason:'Choose the AWS region in Choices to price this component.'});continue;}
  try{
   const architecture=node.data.config?.architecture==='arm64'?'arm64':'x86_64';
   const response=await fetch('/api/pricing/lambda',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.token}`},body:JSON.stringify({projectId:project.id,region,architecture}),signal:AbortSignal.timeout(20000)}),quote=await response.json();
   if(!response.ok)throw Error(quote.detail||'Regional Lambda pricing is unavailable.');
   next=applyLambdaQuote(next,node,quote);
  }catch(error){errors.push({component:node.data.label,reason:error.message});}
 }
 return {project:next,errors};
}
