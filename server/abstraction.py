"""Server-owned progressive detail policy; priorities are not architecture validation."""
import re

def consultation_focus(request):
    text=request.message.lower()
    technical=bool(re.search(r'\b(?:what|which) port\b|\blisten on\b|\b(?:write|show|build|create)\b.{0,35}\b(?:dockerfile|container|application code|terraform code)\b|\bimplementation details\b|\bentrypoint\b',text))
    overview=bool(re.search(r'\b(?:high.level|big picture|topology|overview|step back|too much detail)\b',text))
    level='topology' if overview else 'implementation' if technical else 'component_contracts' if request.origin=='block-review' else 'system_design'
    return {
        'level':level,
        'purpose':'Converge from outcomes and major responsibilities to detailed, tested implementation without a configuration questionnaire.',
        'engineeringOwner':'Architect proposes the required components, connections and routine settings, reuses accepted facts, validates the composition and prepares an agent-executable handoff. Users provide goals, consequential business constraints and approvals; missing generator features are engineering work, never a user questionnaire.',
        'convergencePolicy':'Aim for a coherent standard-system design in about ten meaningful user exchanges, with more for genuine complexity. This is a pacing target, not a limit or a quality claim. Recommend first; ask one small high-impact question only when an answer changes the next design decision. Carry routine details internally using sourced best practices and visible proposals. Reuse previous answers and evaluate connected moving parts together.',
        'priorityOrder':['outcome and current scope','existing systems and deployment ownership','user journeys and responsibility boundaries','data ownership, access, privacy and money','interfaces, state and failure behavior','implementation configuration'],
        'questionPolicy':'Ask at most one material user decision, only when it changes the next design choice. Explain the decision it unlocks. If enough is known, improve the diagram and summarise the change without another question. Recommend routine engineering choices as explicit proposals; do not invent accepted business decisions.',
        'deferUnlessRelevant':['runtime port','Dockerfile or startup command','SDK versions','instance sizes','provider-specific toggles'],
        'implementationBoundary':'A supplied-image contract may propose port 8080, but that is not evidence an application exists or implements the business requirements. Packaging questions do not take priority over unresolved system boundaries.',
        'topologyPolicy':'Keep topology reasoning internal. Show understandable components, with plain names and short descriptions, in the component canvas. Add the components and connections needed by the known requirements as a proposal; do not ask the user to design a topology or choose a topology view. Preserve IDs, ownership, requirements and existing systems. Explain technical details only when requested or needed for a material decision.',
        'evaluationPolicy':'Judge each iteration against preserved requirements, ownership and evidence. A smaller question backlog or a prettier diagram alone is not improvement; reject regressions and distinguish design advice, static checks, emulation and runtime proof.'
    }


def response_budget_seconds(request):
    """Bound complex connected designs without giving a larger prompt budget to greetings."""
    text=(request.message+' '+request.project.requirements).lower()
    themes=[r'\b(?:tenant|sign.in|authentication|identity)\b',r'\b(?:credit|payment|billing)\b',r'\b(?:queue|workflow|retrieval|retry|retries)\b',r'\b(?:sharepoint|confluence|crm|connector)\b',r'\b(?:regulated|compliance|recovery|enterprise)\b',r'\bexisting (?:website|site|application)\b']
    connected=sum(bool(re.search(pattern,text)) for pattern in themes)
    return 240 if len(request.project.nodes)>10 or connected>=2 else 150
