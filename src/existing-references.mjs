// External ownership is not evidence that an application or integration works.
// These references never create/import resources or make requests to the endpoint.
export function existingReference(node) {
 const d=node.data;
 if(!['existing','imported Pulumi state'].includes(d.origin)||d.implementation)return null;
 const explicit=d.binding==='existing-service'||d.origin==='imported Pulumi state';
 const firebase=!d.binding&&d.provider==='gcp'&&/^(?:Google )?Firebase (?:App )?Hosting$/i.test(String(d.service||'').trim());
 if(!explicit&&!firebase)return null;
 return {id:node.id,label:d.label,provider:d.provider,service:d.service||d.label,ownership:'external',provision:false,import:false,behaviorValidated:false};
}
export function existingReferenceFiles(project){
 const references=project.nodes.filter(n=>n.data.kind!=='note').map(existingReference).filter(Boolean);
 if(!references.length)return {};
 return {'existing-references.json':JSON.stringify({version:1,references},null,2),'EXISTING-SYSTEMS.md':'# Existing systems\n\nThese components remain externally managed. This export does not create, import, replace or modify them. Their presence in the diagram is not proof of availability, authentication, permissions or integration behavior. Connection implementations and runtime tests remain separate requirements.\n\n'+references.map(r=>`- ${JSON.stringify(r.label)} (${JSON.stringify(r.id)}): reference only, preserve existing system.`).join('\n')+'\n'};
}
