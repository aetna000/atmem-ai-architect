// Select from explicit deployment ownership, never from a default cloud.
export function generationProviders(project){
 const deployed=project.nodes.filter(n=>n.data.kind!=='note'&&n.data.origin!=='existing'&&n.data.provider!=='tools').map(n=>n.data.provider);
 return [...new Set(deployed.length?deployed:project.provider&&project.provider!=='tools'?[project.provider]:[])].sort();
}
export function isAwsGeneration(project){const p=generationProviders(project);return p.length===1&&p[0]==='aws';}
