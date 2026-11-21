import {buildReview} from './build-review.mjs';
import {designDocumentFiles} from './design-documents.mjs';

const json = value => JSON.stringify(value,null,2) + '\n';
export function buildReviewFiles(project,model) {
  const review = buildReview(project,model);
  const open = review.decisions.filter(row=>row.status==='open');
  const lines = ['# '+project.name,'','## Build handoff','',
    review.counts.types+' of 28 diagram types contain project records. '+review.counts.covered+' of '+review.requirements.length+' requirements have a linked verification case.',
    '', '## Decisions requiring an owner','',
    ...open.flatMap(row=>['### '+row.id+' · '+(row.owner||'Unassigned'),'',row.question,'',...(row.requirementIds?.length?['Blocked requirements · '+row.requirementIds.join(', '),'']:[]),...(row.interfaceIds?.length?['Blocked interfaces · '+row.interfaceIds.join(', '),'']:[]),...(row.decisionBy?['Needed before · '+row.decisionBy,'']:[]),...(row.interim?['Interim · '+row.interim,'']:[]),...(row.blocks.length?['Affected components · '+row.blocks.join(', '),'']:[])]),
    ...(open.length?[]:['No open decisions recorded.','']),
    '## Implementation and verification','',
    '- Read the captured documents in design/ for the build sequence and source contracts when present.',
    '- qualification/interfaces.json records each directed interface and its proposed behaviour.',
    '- qualification/acceptance.json contains test setup, inputs, actions, expected results and requested evidence.',
    '- qualification/requirements.json links each requirement to its verification cases.',
    '- qualification/diagrams.json lists evidence gaps by diagram and record.',
    '- Run python3 qualification/check_handoff.py from the extracted archive to check the snapshot.',
    '', 'The cases are test specifications. Record observed partner and site results against the same revision before release.',''];
  const docs = designDocumentFiles(project.extensions?.architectureDocuments);
  return {'BUILD-HANDOFF.md':lines.join('\n'),
    ...Object.fromEntries(Object.entries(docs).map(([name,data])=>['design/'+name,data])),
    'qualification/decisions.json':json(review.decisions),'qualification/interfaces.json':json(review.interfaces),
    'qualification/acceptance.json':json(review.cases),'qualification/requirements.json':json(review.requirements),
    'qualification/diagrams.json':json(review.diagrams),
    'qualification/check_handoff.py':checkHandoff,
  };
}

const checkHandoff = `"""Check the exported files against the project snapshot. Runs offline with Python 3."""
import hashlib
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
def read(path):
    return json.loads((root / path).read_text(encoding='utf-8'))
def require(value, message):
    if not value:
        raise SystemExit('Handoff check failed: ' + message)

source = next((root / name for name in ('project.atmem-ai-architect.json', 'source-context.json') if (root / name).is_file()), None)
require(source, 'project snapshot missing')
project = json.loads(source.read_text(encoding='utf-8'))
nodes = project['design']['nodes']
board = {n['id'] for n in nodes}
interfaces = read('qualification/interfaces.json')
edges = {r['id']: r for r in project['design']['edges']}
contract_fields = {'transport':'Transport and version','input':'Request or event','output':'Response or result','authorization':'Identity and authority','failure':'Failure and retry','verification':'Contract tests'}
def explicitly_unqualified(text):
    lower = text.lower()
    words = set(re.findall('[a-z]+', lower))
    return bool(words & {'tbd','tbc','placeholder','unconfirmed','provisional'}) or '/proposed/' in lower or any(phrase in lower for phrase in ('transport pending','schema pending','wire pending','contract pending','interface pending','pending confirmation','pending qualification','pending approval','to be confirmed','requires owner approval','requires customer approval','requires vendor approval'))
require(len(interfaces) == len(edges) and {r['id'] for r in interfaces} == set(edges), 'interface inventory')
for row in interfaces:
    edge = edges[row['id']]
    require(row['source'] == edge['source'] and row['target'] == edge['target'] and row['source'] in board and row['target'] in board, row['id'] + ' endpoints')
    require(row['contract'] == edge.get('interfaceSpec', {}), row['id'] + ' contract')
    missing = {label for key,label in contract_fields.items() if not row['contract'].get(key,'').strip()}
    pending = {label for key,label in contract_fields.items() if explicitly_unqualified(row['contract'].get(key,''))}
    require(set(row['missing']) == missing, row['id'] + ' missing contract fields')
    require(pending <= set(row['pending']), row['id'] + ' provisional contract marked qualified')
cases = read('qualification/acceptance.json')
original = {(n['id'], c['id']): c for n in nodes for c in (n['data'].get('buildSpec') or {}).get('verificationCases', [])}
require(len(cases) == len(original) and {(r['blockId'], r['id']) for r in cases} == set(original), 'verification case inventory')
for row in cases:
    require({k:v for k,v in row.items() if k not in ('blockId','blockName')} == original[(row['blockId'],row['id'])], 'verification case changed')
requirements = read('qualification/requirements.json')
expected = {r['id']:r for r in project.get('requirements', [])}
if project.get('extensions', {}).get('diagramCatalogueRequired'):
    dedicated = {c['requirementIds'][0] for c in original.values() if len(c['requirementIds']) == 1}
    require(set(expected) <= dedicated, 'dedicated cases missing for ' + ', '.join(sorted(set(expected) - dedicated)))
    fixture_groups = {}
    for (block, case_id), case in original.items():
        if len(case['requirementIds']) != 1: continue
        signature = (block, *( ' '.join(case[k].split()) for k in ('setup', 'input', 'action', 'expected')))
        fixture_groups.setdefault(signature, set()).add(case['requirementIds'][0])
    require(all(len(ids) <= 1 for ids in fixture_groups.values()), 'dedicated fixtures duplicate across requirements')
require(len(requirements) == len(expected) and {r['id'] for r in requirements} == set(expected), 'requirements inventory')
for row in requirements:
    require({k:v for k,v in row.items() if k not in ('cases','interfaceIds')} == expected[row['id']], row['id'] + ' requirement changed')
    scenario_interfaces = {step['interfaceId'] for n in nodes for scenario in (n['data'].get('buildSpec') or {}).get('scenarios', []) for step in scenario.get('steps', []) if row['id'] in step.get('requirementIds', []) and step.get('interfaceId')}
    require(set(row.get('interfaceIds', [])) == scenario_interfaces and scenario_interfaces <= set(edges), row['id'] + ' interface links')
    require({(r['blockId'],r['id']) for r in row['cases']} == {key for key,c in original.items() if row['id'] in c['requirementIds']}, row['id'] + ' case links')
ext = project.get('extensions', {})
for doc in (ext.get('architectureDocuments') or {}).get('files', []):
    path = doc['path'] if doc['path'] != 'README.md' else 'NATIVE_DESIGN.md'
    dest = (root / 'design' / path).resolve()
    require((root / 'design').resolve() in dest.parents, 'document path outside design folder')
    require(hashlib.sha256(dest.read_bytes()).hexdigest() == doc['sha256'], path + ' digest')
diagrams = read('qualification/diagrams.json')
actual = {(t['id'],p['id']): p for t in diagrams for p in t['pages']}
views = (ext.get('architectureDiagrams') or {}).get('views', [])
require(len(actual) == len(views) and set(actual) == {(v['kind'],v['id']) for v in views}, 'diagram inventory')
for v in views:
    p = actual[(v['kind'],v['id'])]
    require(p['name'] == v['name'] and p['populated'] == bool(v['elementIds']), 'diagram changed')
decisions = read('qualification/decisions.json')
questions = project.get('openQuestions', [])
require(len(decisions)==len(questions), 'decisions inventory')
for recorded, source in zip(decisions,questions):
    require(all(recorded.get(k)==v for k,v in source.items() if k!='status'), source['id']+' decision changed')
    require(recorded['status']==('answered' if source.get('status')=='answered' and source.get('answer','').strip() else 'open'), source['id']+' status')
print(f"Snapshot check passed: {len(interfaces)} interfaces, {len(cases)} case definitions, {len(views)} typed pages.")
print("Owner decisions open:", sum(r['status']=='open' for r in decisions))
print("This check verifies the handoff files. Site operation and test execution require separate evidence.")
`;
