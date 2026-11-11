import {protectedState} from './protected-state.mjs';
// Compatibility adapter: the established invoice default is an explicit policy.
export function invoiceState(provider){
 const backend={aws:'s3',azure:'azurerm',gcp:'gcs',ibm:'http'}[provider];
 if(!backend)throw Error('Invoice state must preserve the selected provider');
 return protectedState(backend,{title:'Invoice state and environment ownership'});
}
