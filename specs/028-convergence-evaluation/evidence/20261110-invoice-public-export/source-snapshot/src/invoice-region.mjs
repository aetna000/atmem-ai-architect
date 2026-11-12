export const INVOICE_REGION_PATTERNS={aws:'^[a-z]{2}-[a-z]+-[0-9]{1,2}$',azure:'^[a-z][a-z0-9]{1,39}$',gcp:'^[a-z]+-[a-z]+[0-9]{1,2}$',ibm:'^[a-z]{2}-[a-z]+$'};
export const validInvoiceRegion=(provider,value)=>typeof value==='string'&&Object.hasOwn(INVOICE_REGION_PATTERNS,provider)&&new RegExp(INVOICE_REGION_PATTERNS[provider]).test(value);
