// Sanitised provenance of externally managed resources. This is neither an
// executable import request nor a claim about their native physical IDs/behavior.
export function validateExternalReferences(project){
 const value=project.extensions?.externalReferences;if(value===undefined)return;
 const plain=v=>!!v&&typeof v==='object'&&!Array.isArray(v)&&[Object.prototype,null].includes(Object.getPrototypeOf(v));
 if(!plain(value)||value.version!==1||Object.keys(value).some(k=>!['version','references'].includes(k))||!Array.isArray(value.references)||value.references.length>200)throw Error('Invalid external reference provenance; preserve the original file.');
 const components=new Set(),identities=new Set();
 for(const entry of value.references){
  if(!plain(entry)||Object.keys(entry).some(k=>!['componentId','source','externalId','resourceType'].includes(k))||entry.source!=='pulumi-stack-export')throw Error('Unsupported external identity provenance; no source was substituted.');
  for(const [key,max]of [['componentId',100],['externalId',600],['resourceType',200]])if(typeof entry[key]!=='string'||!entry[key].trim()||entry[key].length>max)throw Error('Invalid external identity '+key+'; no value was clipped.');
  if(!entry.externalId.startsWith('urn:pulumi:')||components.has(entry.componentId)||identities.has(entry.externalId))throw Error('Duplicate or invalid external identity; resolve ownership without adopting another resource.');
  components.add(entry.componentId);identities.add(entry.externalId);
  const node=project.nodes.find(n=>n.id===entry.componentId);
  if(node&&(!['existing','imported Pulumi state'].includes(node.data.origin)||node.data.deploymentMode==='create'))throw Error('External state provenance identifies a preserved deployment. Keep its reference or model a separate proposed component; do not turn it into new infrastructure.');
 }
}
export const externalIdentity=(project,id)=>project.extensions?.externalReferences?.references.find(r=>r.componentId===id)||null;
