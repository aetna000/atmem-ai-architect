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
        'priorityOrder':['outcome and current scope','existing systems and deployment ownership','user journeys and responsibility boundaries','data ownership, access, privacy and money','interfaces, state and failure behavior','implementation configuration'],
        'questionPolicy':'Ask at most one material user decision, only when it changes the next design choice. Explain the decision it unlocks. If enough is known, improve the diagram and summarise the change without another question. Recommend routine engineering choices as explicit proposals; do not invent accepted business decisions.',
        'deferUnlessRelevant':['runtime port','Dockerfile or startup command','SDK versions','instance sizes','provider-specific toggles'],
        'implementationBoundary':'A supplied-image contract may propose port 8080, but that is not evidence an application exists or implements the business requirements. Packaging questions do not take priority over unresolved system boundaries.',
        'topologyPolicy':'Show major responsibilities and named flows first. Use topologyGroup to relate components to responsibilities; it is a view grouping, not a new deployment. Preserve the detailed graph and drill into the relevant responsibility when needed.',
        'evaluationPolicy':'Judge each iteration against preserved requirements, ownership and evidence. A smaller question backlog or a prettier diagram alone is not improvement; reject regressions and distinguish design advice, static checks, emulation and runtime proof.'
    }
