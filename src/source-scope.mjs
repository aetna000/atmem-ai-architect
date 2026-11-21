// Source interpretation is review work, not automatic user agreement or execution.
export function sourceDerivedRequirement(project,requirement){
 const sources=project.extensions?.designSources;
 return Array.isArray(sources)&&sources.some(source=>typeof source?.name==='string'&&/^[a-f0-9]{64}$/.test(source?.sha256||'')&&requirement.basis?.startsWith(source.name+' · ')&&requirement.basis?.endsWith('SHA-256 '+source.sha256));
}
export function recordedOutcome(project){
 return [project.brief?.application,project.requirements,project.extensions?.systemSpec?.decomposition].find(text=>typeof text==='string'&&text.trim())||'';
}
