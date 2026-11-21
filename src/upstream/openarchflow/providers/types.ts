export interface ServiceItem { name:string; description:string; service:string; type?:string; subtype?:string }
export interface ServiceCategory { category:string; items:ServiceItem[] }
