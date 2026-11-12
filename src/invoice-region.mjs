import {PROVIDER_REGION_PATTERNS,validProviderRegion} from './deployment-region.mjs';
export const INVOICE_REGION_PATTERNS={...PROVIDER_REGION_PATTERNS,aws:'^[a-z]{2}-[a-z]+-[0-9]{1,2}$'};
// This domain adapter still has commercial ARN/registry/model contracts. Do not
// inherit supplied-image partition support without implementing the whole policy.
export const invoicePartitionGap=(provider,region)=>provider==='aws'&&/^(cn-|us-gov-)/.test(region||'')?'Preserve the requested AWS partition and region. This invoice adapter still has commercial-partition ARN, registry and model contracts; implement partition support without substituting another destination.':null;
export const validInvoiceRegion=(provider,region)=>validProviderRegion(provider,region)&&!invoicePartitionGap(provider,region);
