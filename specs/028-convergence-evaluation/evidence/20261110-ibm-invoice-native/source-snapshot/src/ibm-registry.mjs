// Reviewed 2026-11-10: IBM's registry hostname is not its Code Engine region.
// https://cloud.ibm.com/docs/Registry?topic=Registry-registry_overview
export const IBM_REGISTRY_HOSTS=Object.freeze({'au-syd':'au.icr.io','br-sao':'br.icr.io','ca-mon':'ca2.icr.io','ca-tor':'ca.icr.io','eu-de':'de.icr.io','eu-es':'es.icr.io','eu-gb':'uk.icr.io','in-che':'in.icr.io','in-mum':'in2.icr.io','jp-osa':'jp2.icr.io','jp-tok':'jp.icr.io','us-south':'us.icr.io'});
export function ibmRegistryHost(region){
 if(!Object.hasOwn(IBM_REGISTRY_HOSTS,region))throw Error('Select an explicitly supported regional IBM registry; no global fallback is inferred');
 return IBM_REGISTRY_HOSTS[region];
}
export function ibmRegistryHostExpression(variable='var.region'){
 if(!/^var\.[a-z][a-z0-9_]*$/.test(variable))throw Error('Use a compiler-owned registry region variable');
 return'${lookup('+JSON.stringify(IBM_REGISTRY_HOSTS)+','+variable+')}';
}
export function ibmRegistryRegionValidation(){return{condition:'${contains('+JSON.stringify(Object.keys(IBM_REGISTRY_HOSTS))+',var.region)}',error_message:'Use a reviewed regional Container Registry location; an invented region hostname or implicit global fallback is not supported.'};}
