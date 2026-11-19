// Architecture is the entry point. Implementation is an explicit outcome action.
export const BUILD_AND_TEST_REQUEST='Implement the current saved design and run its local checks. Preserve every requirement, existing system, provider, placement and ownership boundary. Include a coherent Spec Kit with requirements, a plan, dependent tasks and acceptance evidence, plus implementation, infrastructure and receiving run instructions. Generate the application and its connections, run the applicable block and full-system tests, and retain artifact-bound evidence. Choose reversible implementation defaults with rationale. Record material unresolved choices without asking questions in this build turn, and continue independent tasks while affected work stays blocked. Never substitute a smaller demonstration or report an unexecuted check as passed. No cloud deployment or account access.';
export const BUILD_DESIGN_REQUEST=BUILD_AND_TEST_REQUEST;
export function hasArchitectureDesign(project){
 return !!(project?.nodes?.some(n=>n.data?.kind!=='note')||project?.extensions?.architectureWork?.records?.some(r=>['responsibility','delivery-unit','interface'].includes(r.kind)));
}
export function buildIntent(project,draft){
 if(typeof draft==='string'&&draft.trim())return draft;
 return hasArchitectureDesign(project)?BUILD_DESIGN_REQUEST:'';
}

export function blockBuildIntent(project, id) {
 const node=project.nodes.find(block=>block.id===id&&block.data.kind!=='note');
 if(!node?.data.buildSpec)return '';
 return `Build and test only block ${JSON.stringify(id)} in the saved design. Treat the Block Spec Kit and linked requirements as the design basis. Preserve other blocks and existing systems. Use local in-process fixtures or contract doubles for adjacent dependencies and report what those doubles cannot prove. Implement this block, run its unit and producer/consumer contract tests, and capture exact commands, exit status, test counts, output and artifact file links for block ${JSON.stringify(id)}. Emit architecture-work-proposal.json linking the captured implementation and test files to this exact block and its requirements. Keep unfinished requirements and missing evidence visible. Choose reversible implementation defaults with rationale. Record material unanswered choices without asking questions in this build turn; keep only affected work blocked and continue independent work. Preserve the complete block scope and distinguish partial implementation from acceptance of shared requirements. Recommend CI, packaging, rollback and operational checks. No cloud or site access, publishing or deployment.`;
}
