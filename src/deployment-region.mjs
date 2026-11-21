// Supported identifier shapes, not a region/service-availability catalogue.
// AWS supplied-image lowering supports commercial, China and GovCloud identifier
// families. Other partitions remain explicit implementation work, not a fallback.
export const PROVIDER_REGION_PATTERNS={aws:'^([a-z]{2}-[a-z]+|us-gov-[a-z]+)-[0-9]{1,2}$',azure:'^[a-z][a-z0-9]{1,39}$',gcp:'^[a-z]+-[a-z]+[0-9]{1,2}$',ibm:'^[a-z]{2}-[a-z]+$'};
export const validProviderRegion=(provider,value)=>typeof value==='string'&&Object.hasOwn(PROVIDER_REGION_PATTERNS,provider)&&new RegExp(PROVIDER_REGION_PATTERNS[provider]).test(value);
export function declaredRegion(node){
 const value=node.data.config?.region;
 if(value==null||value===''||value==='To be selected')return {region:null,gaps:[]};
 if(validProviderRegion(node.data.provider,value))return {region:value,gaps:[]};
 return {region:null,gaps:[{key:'region',value,reason:'is preserved but not a supported deployment-region identifier for this provider contract; implement its placement/partition requirements without choosing another destination'}]};
}
