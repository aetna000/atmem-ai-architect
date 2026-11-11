import {runtimeSettings} from './runtime-settings.mjs';
const MiB=2**20,GiB=2**30;
// Exact quantities: never round client memory to a provider's size tier. CPU is
// a proposed compatible allocation, not an inferred CPU/performance requirement.
export function containerRuntime(node){
 const provider=node.data.provider,settings=runtimeSettings(node.data.config),gaps=[];
 const defaults={aws:512*MiB,azure:GiB,gcp:512*MiB,ibm:1e9};
 const explicit=settings.containerMemoryBytes??(settings.memoryMb==null?null:settings.memoryMb*MiB);
 const conflict=settings.containerMemoryBytes!=null&&settings.memoryMb!=null&&settings.containerMemoryBytes!==settings.memoryMb*MiB;
 const bytes=explicit??defaults[provider];let memory,cpu,executionEnvironment;
 if(provider==='aws'){
  const gib=bytes/GiB;
  const tier=bytes===512*MiB?256:Number.isInteger(gib)&&gib>=1?(gib<=2?256:gib<=4?512:gib<=8?1024:gib<=16?2048:gib<=30?4096:gib<=60&&gib%4===0?8192:gib<=120&&gib%8===0?16384:gib===244?32768:null):null;
  if(tier){memory=String(bytes/MiB);cpu=String(tier);}
 }else if(provider==='azure'){
  // Existing environment has no declared workload-profile contract yet. Use the
  // combinations valid for Consumption-only environments, rather than assume it.
  if(bytes>=512*MiB&&bytes<=4*GiB&&bytes%(512*MiB)===0){memory=String(bytes/GiB)+'Gi';cpu=bytes/GiB/2;}
 }else if(provider==='gcp'){
  if(bytes>=128*MiB&&bytes<=32*GiB&&bytes%MiB===0){memory=String(bytes/MiB)+'Mi';cpu=String(bytes<=4*GiB?1:bytes<=8*GiB?2:bytes<=16*GiB?4:bytes<=24*GiB?6:8);executionEnvironment=bytes<512*MiB?'EXECUTION_ENVIRONMENT_GEN1':'EXECUTION_ENVIRONMENT_GEN2';}
 }else if(provider==='ibm'){
  const sizes=new Map([[250e6,'0.125'],[500e6,'0.25'],[1e9,'0.5'],[2e9,'0.5'],[4e9,'1'],[8e9,'2'],[12e9,'6'],[16e9,'4'],[20e9,'10'],[24e9,'6'],[32e9,'8'],[40e9,'10'],[48e9,'12']]);
  if(sizes.has(bytes)){memory=String(bytes/1e9)+'G';cpu=sizes.get(bytes);}
 }
 if(conflict)gaps.push({key:'containerMemoryBytes',value:settings.containerMemoryBytes,reason:'conflicts with the preserved memoryMb requirement (MiB); resolve the conflicting quantities without discarding either'});
 if(memory==null&&!conflict)gaps.push({key:settings.containerMemoryBytes==null?'memoryMb':'containerMemoryBytes',value:explicit,reason:'has no exact supported memory/CPU mapping in the selected provider/environment contract; no rounding or provider substitution was performed'});
 // The old finite log-retention field is explicitly a CloudWatch contract.
 for(const [key,value]of Object.entries(settings))if(!['memoryMb','containerMemoryBytes'].includes(key)&&!(key==='logRetentionDays'&&provider==='aws'))gaps.push({key,value,reason:'is not implemented by this supplied-image footprint; implement and validate the required behavior before applying'});
 return {requestedMemoryBytes:explicit,memoryBytes:memory==null?defaults[provider]:bytes,memory:memory??({aws:'512',azure:'1Gi',gcp:'512Mi',ibm:'1G'}[provider]),cpu:cpu??({aws:'256',azure:0.5,gcp:'1',ibm:'0.5'}[provider]),executionEnvironment:executionEnvironment||'EXECUTION_ENVIRONMENT_GEN2',logRetentionDays:settings.logRetentionDays??30,gaps};
}
