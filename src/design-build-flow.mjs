// Architecture is the entry point. Implementation is an explicit outcome action.
export const BUILD_DESIGN_REQUEST='Build the current saved design.';
export function hasArchitectureDesign(project){
 return !!(project?.nodes?.some(n=>n.data?.kind!=='note')||project?.extensions?.architectureWork?.records?.some(r=>['responsibility','delivery-unit','interface'].includes(r.kind)));
}
export function buildIntent(project,draft){
 if(typeof draft==='string'&&draft.trim())return draft;
 return hasArchitectureDesign(project)?BUILD_DESIGN_REQUEST:'';
}
