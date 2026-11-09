"""Small reviewed specialist registry; pinned upstream assets are references, never scripts."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDANCE = [
 ('architecture','AI architecture and discovery','all',['discover','design','review'], 'Clarify outcome, users, existing systems, data ownership and constraints. Evolve the diagram incrementally. Derive functional requirements and propose measurable quality targets as assumptions needing confirmation. Compare clouds against the actual requirements; do not assume an enterprise identity provider or a vendor. Keep proposed and accepted decisions distinct.'),
 ('security','Security and reliability','all',['design','review','deploy'], 'Check data classification, residency, access boundaries, encryption choices, approval of automated actions, reliability and recovery. A drawn control is not enforcement evidence. Explain missing controls and tests. Propose requirements from the components and paths; mark default targets as suggestions, never existing company policy.'),
 ('finops','FinOps and progressive estimation','all',['estimate','design'], 'Populate a bill of resources from the diagram. Separate monthly cloud charges from one-off build effort. Use pricing.lookup for supported current list pricing, and project.read for usage. Ask the largest missing usage/model/region question. Input and output tokens, storage, requests, duration, networking and observability can have separate charges. Never invent prices or effort. Options cost scores are qualitative judgements, not price quotes.'),
 ('devops','Infrastructure and DevOps handoff','all',['deploy','review'], 'Prepare a reviewable plan, IaC sketch, CI/CD checks, secrets handling, observability, acceptance tests, rollback and ownership. Existing systems require integration planning. Every wire needs implementation. Access does not equal permission to deploy; the current broker has no write/deploy tools. Report implementation and validation gaps.'),
 ('aws','AWS architecture guidance','aws',['design','review','estimate','deploy'], 'Apply AWS Well-Architected concerns to the drawn workload with evidence. Distinguish Bedrock on-demand model access, knowledge-base/vector storage, guardrails and IAM; they are separate concerns. S3 storage, requests and transfer are separate cost dimensions. A diagram is not a complete Well-Architected review. Native generation currently covers only S3 foundations.'),
 ('azure','Azure architecture guidance','azure',['design','review','estimate','deploy'], 'Check Microsoft 365/Entra integration only when relevant to the user. Match model, retrieval, data and runtime services to requirements. Evaluate redundancy, regional availability, identity and recovery separately. The pinned Azure reliability reference specifically covers Functions and App Service; do not extend its validation claims to other services.'),
 ('gcp','Google Cloud AI architecture guidance','gcp',['design','review','estimate','deploy'], 'Match model runtime, retrieval, storage, identity and network boundaries to the project. Distinguish architecture guidance from validated commands. Verify regional model availability, quotas and residency before estimating/deploying. The pinned platform architecture reference has additional companion manuals; those commands are not enabled in AtMem AI Architect.'),
 ('ibm','IBM Cloud architecture guidance','ibm',['design','review','estimate','deploy'], 'Match watsonx, data services, identity, application runtime and observability to the same requirements used for other clouds. Check region, data residency, model access and IBM plan before pricing. Use a sourced IBM quote; do not substitute an AWS/Azure rate or claim an unsupported deployment is ready.'),
 ('terraform','Terraform delivery guidance','all',['deploy','design'], 'Keep provider versions and configurable inputs explicit, use stable resource addresses, declare references and dependencies, and review state/import and destructive changes. Run validation before claiming a valid sketch. Current generated S3 foundations are partial; application resources and integrations remain engineering work.'),
 ('pulumi','Pulumi delivery guidance','all',['deploy','design'], 'Declare resources predictably and pass Outputs through dependencies; do not create resources inside apply callbacks. Plan aliases and protection before refactors. Keep secrets in supported secret/config stores. Explain import versus refresh limits. AtMem AI Architect Pulumi output remains a metadata scaffold, not deployed provider resources.'),
]


def generation_guidance():
    catalogue = json.loads((ROOT / 'agent-skills/generation-capabilities.json').read_text())
    return ('Compiler capability catalogue v' + str(catalogue['version']) + ': ' +
            json.dumps(catalogue['contracts'], separators=(',', ':')) + '. ' + catalogue['evidenceBoundary'] +
            ' Preserve required unsupported scope and identify missing compiler work; never substitute a different provider or present references as generated infrastructure.')


def registry():
    refs = json.loads((ROOT / 'agent-skills/upstream/manifest.json').read_text())
    by_id = {r['id']: r for r in refs}
    result = []
    for ident, name, provider, stages, content in GUIDANCE:
        path = ROOT / 'agent-skills/specialists' / ident / 'SKILL.md'
        expected = json.loads((ROOT / 'agent-skills/specialists/manifest.json').read_text())[ident]
        data = path.read_bytes()
        version_match = re.search(r'^version: ([0-9]+\.[0-9]+\.[0-9]+)$', data.decode(), re.MULTILINE)
        valid = hashlib.sha256(data).hexdigest() == expected and version_match is not None
        reference = by_id.get(ident)
        if reference:
            reference = {**reference, 'integrity': hashlib.sha256((ROOT / reference['file']).read_bytes()).hexdigest() == reference['sha256']}
            valid = valid and reference['integrity']
        result.append({'id': ident, 'name': name, 'provider': provider, 'stages': stages, 'version': version_match.group(1) if version_match else 'unknown', 'digest': expected,
            'instructions': data.decode(), 'source': reference['url'] if reference else 'AtMem AI Architect reviewed specialist guidance',
            'reference': reference, 'integrity': valid, 'coverage': 'guidance; no cloud execution', 'tools': ['memory.lookup','project.read','skills.lookup'] + (['pricing.lookup'] if ident in {'aws','finops'} else [])})
    return result


def catalogue(memory, project):
    skills = registry()
    with memory.db() as db:
        settings = dict(db.execute('SELECT id,enabled FROM skill_settings'))
    for skill in skills:
        skill['enabled'] = bool(settings.get(skill['id'], 1)) and skill['integrity']
    return skills


def select(memory, project, request, recalled):
    skills = catalogue(memory, project)
    text = request.message.lower()
    providers = {request.project.provider, *(n.data.provider for n in request.project.nodes)}
    if re.search(r'compar|versus|alternative|\bvs\b', text):
        providers.update({'aws','azure','gcp','ibm'})
    for provider, pattern in [('aws',r'\baws\b'),('azure',r'\bazure\b'),('gcp',r'google cloud|\bgcp\b'),('ibm',r'\bibm\b|watsonx')]:
        if re.search(pattern,text): providers.add(provider)
    selected = []
    for skill in skills:
        choose = skill['id'] == 'architecture' or ((request.stage in skill['stages'] or request.stage == 'discover') and skill['provider'] in providers)
        choose |= skill['id'] == 'security' and bool(request.project.nodes)
        choose |= skill['id'] == 'finops' and (request.stage == 'estimate' or bool(re.search(r'cost|pric|estimat|budget', text)))
        choose |= skill['id'] == 'devops' and (request.stage == 'deploy' or bool(re.search(r'deploy|devops|rollback|pipeline', text)))
        if skill['id'] in {'terraform','pulumi'}:
            choose = skill['id'] in text or request.stage == 'deploy' and skill['id'] in ' '.join(r['text'].lower() for r in recalled)
        if choose and skill['enabled']:
            selected.append(skill)
    return selected[:8]


def publish(memory, project):
    if not memory.enabled(project): return
    for skill in catalogue(memory, project):
        if not skill['integrity']: continue
        # Actual source-linked procedure guidance lives in the knowledge scope of AtMem.
        text = f'Skill {skill["id"]} v{skill["version"]}: {skill["instructions"]}\nSource: {skill["source"]}; artifact SHA256: {skill["digest"]}'
        memory.enqueue(project,'knowledge','skill.'+skill['id'],text,event_id='skill-'+skill['digest'],source=skill['source'])
    from .engineering_knowledge import publish as publish_practices
    publish_practices(memory,project)
    memory.flush()


def public(skills):
    return [{k:v for k,v in skill.items() if k != 'instructions'} for skill in skills]
