// Existing application source and an existing cloud deployment are separate facts.
export const existingDeployment=node=>['existing','imported Pulumi state'].includes(node.data.origin)&&node.data.deploymentMode!=='create';
export function validateDeploymentOwnership(data){
 if(data.deploymentMode!=null&&!['reference','create'].includes(data.deploymentMode))throw Error('Choose reference or create for deployment ownership.');
 if(data.origin==='existing'&&data.deploymentMode==='create'&&(data.implementation!=='container-service'||data.binding))throw Error('Deploying existing application source requires an explicit container-service contract without an external reference binding.');
}
