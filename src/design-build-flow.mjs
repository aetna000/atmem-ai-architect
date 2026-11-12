// Architecture is the entry point. Implementation is an explicit outcome action.
export const BUILD_AND_TEST_REQUEST='Implement the current saved design and run its local checks. Preserve every requirement, existing system, provider, placement and ownership boundary. Include a coherent Spec Kit with requirements, a plan, dependent tasks and acceptance evidence, plus implementation, infrastructure and receiving run instructions. Generate the application and its connections, run the applicable block and full-system tests, and retain artifact-bound evidence. Clarify only material unresolved choices; never substitute a smaller demonstration or report an unexecuted check as passed. No cloud deployment or account access.';
export const BUILD_DESIGN_REQUEST=BUILD_AND_TEST_REQUEST;
export function hasArchitectureDesign(project){
 return !!(project?.nodes?.some(n=>n.data?.kind!=='note')||project?.extensions?.architectureWork?.records?.some(r=>['responsibility','delivery-unit','interface'].includes(r.kind)));
}
export function buildIntent(project,draft){
 if(typeof draft==='string'&&draft.trim())return draft;
 return hasArchitectureDesign(project)?BUILD_DESIGN_REQUEST:'';
}
