// Existing application source and an existing cloud deployment are separate facts.
export const existingDeployment=node=>{validateDeploymentOwnership(node.data);return ['existing','imported Pulumi state'].includes(node.data.origin)&&node.data.deploymentMode!=='create';};
export function validateDeploymentOwnership(data){
 if(data.deploymentMode==='reference'&&!['existing','imported Pulumi state'].includes(data.origin))throw Error('Reference handling must preserve an existing system; it cannot provision a proposed replacement.');
 if(data.binding&&(!['existing','imported Pulumi state'].includes(data.origin)||data.deploymentMode==='create'))throw Error('Reference bindings identify existing systems and cannot provision a replacement. Preserve existing ownership or correct the binding.');
 if(data.deploymentMode!=null&&!['reference','create'].includes(data.deploymentMode))throw Error('Choose reference or create for deployment ownership.');
 if(data.origin==='existing'&&data.deploymentMode==='create'&&(data.implementation!=='container-service'||data.binding))throw Error('Deploying existing application source requires an explicit container-service contract without an external reference binding.');
}
