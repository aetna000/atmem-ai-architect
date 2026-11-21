// Explicit capabilities only: diagram labels never grant access.
export const S3_ACCESS_MODES = ['s3-read', 's3-read-write'];
export const IAM_PRINCIPAL_BINDING = 'aws-iam-principal';
export function storageAccessPlan(project, rows) {
 const nodes=new Map(project.nodes.map(n=>[n.id,n]));
 const resources=new Map(rows.map(r=>[r.id,r]));
 const connections=project.edges.flatMap(edge=>{
  const source=nodes.get(edge.source),target=resources.get(edge.target);
  if(source?.data.binding!==IAM_PRINCIPAL_BINDING || source.data.provider!=='tools' || source.data.origin!=='existing' || !(target?.foundation&&S3_ACCESS_MODES.includes(edge.access) || (target?.compute||target?.summary)&&edge.access==='lambda-invoke' || target?.api&&edge.access==='api-invoke'))return [];
  return [{id:edge.id,source:edge.source,target:edge.target,access:edge.access,principalVariable:`principal_${resources.get(edge.source).address}_arn`}];
 });
 const bindings=[...new Set(connections.map(e=>e.source))].map(id=>({id,variable:`principal_${resources.get(id).address}_arn`}));
 return {connections,bindings};
}
