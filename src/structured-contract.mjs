// Deliberately bounded flat output contracts. Nested objects require a separate reviewed capability.
export function structuredContract(value){
 if(value==null)return undefined;
 if(!value||typeof value!=="object"||Array.isArray(value)||Object.keys(value).some(k=>!['instruction','fields'].includes(k)))throw Error('Invalid structured-output contract.');
 if(typeof value.instruction!=='string'||!value.instruction.trim()||value.instruction.length>2000)throw Error('Structured output needs an instruction of 1–2000 characters.');
 if(!Array.isArray(value.fields)||!value.fields.length||value.fields.length>24)throw Error('Structured output needs 1–24 fields.');
 const names=new Set();
 const fields=value.fields.map(f=>{
  if(!f||Object.keys(f).some(k=>!['name','type','description','values','maxLength'].includes(k))||typeof f.name!=='string'||!/^[a-z][a-zA-Z0-9_]{0,39}$/.test(f.name)||names.has(f.name))throw Error('Structured-output field names must be unique identifiers.');
  names.add(f.name);
  if(!['string','boolean','number'].includes(f.type))throw Error('Unsupported structured-output field type.');
  if(typeof f.description!=='string'||!f.description.trim()||f.description.length>300)throw Error('Each output field needs a short meaning.');
  if(f.values!=null&&(f.type!=='string'||!Array.isArray(f.values)||!f.values.length||f.values.length>30||new Set(f.values).size!==f.values.length||f.values.some(v=>typeof v!=='string'||!v||v.length>100)))throw Error('Use a bounded, unique string enumeration.');
  if(f.maxLength!=null&&(f.type!=='string'||!Number.isInteger(f.maxLength)||f.maxLength<1||f.maxLength>4096))throw Error('Use a string length from 1 to 4096.');
  if(f.values&&f.values.some(v=>v.length>(f.maxLength??4096)))throw Error('Enumeration values exceed the field length limit.');
  return {name:f.name,type:f.type,description:f.description,...(f.values!=null?{values:[...f.values]}:{}),...(f.maxLength!=null?{maxLength:f.maxLength}:{})};
 });
 return {instruction:value.instruction,fields};
}
