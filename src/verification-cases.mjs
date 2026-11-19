// Executable intent, not execution evidence. No case can assert a pass here.
const object=v=>v&&typeof v==='object'&&!Array.isArray(v);
const text=(v,max=4000)=>typeof v==='string'&&v.trim()&&Array.from(v).length<=max;
const fields=['id','name','category','requirementIds','environment','setup','input','action','expected','evidence','interfaceId','operationId'];
export const verificationCategories=['unit','contract','integration','security','recovery','load','acceptance'];
export function validateVerificationCases(cases){
 if(cases===undefined)return;
 if(!Array.isArray(cases)||!cases.length||cases.length>100)throw Error('Verification cases need 1–100 cases.');
 const ids=new Set();
 for(const row of cases){
  if(!object(row)||Object.keys(row).some(key=>!fields.includes(key))||!text(row.id,100)||ids.has(row.id)||!text(row.name,150)||!verificationCategories.includes(row.category))throw Error('Verification case identity or fields are invalid.');
  ids.add(row.id);
  for(const key of ['environment','setup','input','action','expected','evidence'])if(!text(row[key]))throw Error('Verification case needs concrete '+key+'.');
  if(!Array.isArray(row.requirementIds)||!row.requirementIds.length||row.requirementIds.length>50||new Set(row.requirementIds).size!==row.requirementIds.length||row.requirementIds.some(id=>!text(id,100)))throw Error('Verification case needs 1–50 unique requirement IDs.');
  for(const key of ['interfaceId','operationId'])if(row[key]!==undefined&&!text(row[key],100))throw Error('Verification case reference is invalid.');
 }
}
export function verificationReferenceIssues(project){
 const issues=[];
 const requirements=new Set((project.needs||[]).map(r=>r.id)),interfaces=new Map(project.edges.map(e=>[e.id,e]));
 const operations=new Map((project.extensions?.engineeringModel?.elements||[]).flatMap(e=>(e.operations||[]).map(op=>[op.id,e.blockId])));
 for(const node of project.nodes){
  const cases=node.data.buildSpec?.verificationCases;validateVerificationCases(cases);
  for(const row of cases||[]){
   const issue=(code,message,ref)=>issues.push({code,severity:'error',blockId:node.id,caseId:row.id,message,ref});
   for(const id of row.requirementIds)if(!requirements.has(id))issue('verification_requirement_missing','Verification case refers to an unknown requirement.',id);
   if(row.interfaceId!==undefined){const edge=interfaces.get(row.interfaceId);if(!edge||![edge.source,edge.target].includes(node.id))issue('verification_interface_missing','Verification case needs an incident interface.',row.interfaceId);}
   if(row.operationId!==undefined&&operations.get(row.operationId)!==node.id)issue('verification_operation_missing','Verification case needs an operation owned by its module.',row.operationId);
  }
 }
 return issues;
}
export function validateVerificationReferences(project){
 const [first]=verificationReferenceIssues(project);
 if(first)throw Error(first.message);
}
export function verificationCaseMarkdown(row){
 return `## ${row.id} · ${row.name}\n\nCategory: ${row.category} · Execution: not run\n\nRequirements: ${row.requirementIds.join(', ')}${row.interfaceId?'\n\nInterface: '+row.interfaceId:''}${row.operationId?'\n\nOperation: '+row.operationId:''}\n\n`+['environment','setup','input','action','expected','evidence'].map(key=>`### ${key[0].toUpperCase()+key.slice(1)}\n\n${row[key]}`).join('\n\n');
}
