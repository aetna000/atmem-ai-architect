// Raw conversation is retained as provenance, never presented as a finished brief.
export function implementationOutcome(project){
 if(project.brief?.application?.trim())return project.brief.application.trim();
 const needs=(project.needs||[]).map(r=>r.statement).filter(Boolean);
 return `System: ${project.name||'Unnamed system'}. Structured outcome requires confirmation.${needs.length?'\n\nRecorded requirements:\n'+needs.map(s=>'- '+s).join('\n'):''}`;
}
