import {structuredContract} from './structured-contract.mjs';
const ranges={containerMemoryBytes:[1,Number.MAX_SAFE_INTEGER],memoryMb:[128,10240],functionTimeoutSeconds:[1,900],concurrency:[1,1000],maxInputBytes:[1,1000000],maxOutputTokens:[1,4096],maxPdfBytes:[1,20000000],maxPdfPages:[1,1000],retentionDays:[1,3653]};
export const LOG_RETENTION_DAYS=[1,3,5,7,14,30,60,90,120,150,180,365,400,545,731,1096,1827,2192,2557,2922,3288,3653];
export function runtimeSettings(config={}){
 const result={};
 if(config?.outputContract!=null)result.outputContract=structuredContract(config.outputContract);
 for(const [name,[min,max]]of Object.entries(ranges)){
  const value=config?.[name];if(value==null)continue;
  if(!Number.isInteger(value)||value<min||value>max)throw Error(`Invalid ${name}: use an integer from ${min} to ${max}.`);
  result[name]=value;
 }
 if(config?.logRetentionDays!=null){if(!LOG_RETENTION_DAYS.includes(config.logRetentionDays))throw Error('Choose a supported finite CloudWatch retention period.');result.logRetentionDays=config.logRetentionDays;}
 if(config?.modelId!=null){if(typeof config.modelId!=="string"||config.modelId.length>150||!/^[a-z0-9][a-z0-9.-]*:[0-9]+$/.test(config.modelId))throw Error('Use a direct foundation-model ID including version.');result.modelId=config.modelId;}
 return result;
}
