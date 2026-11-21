"""Versioned diagram catalogue used by authoring, review and local AtMem knowledge."""
import hashlib
import json
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / 'agent-skills/specialists/architecture-diagrams'
FILES = {name: (SKILL / name).read_bytes() for name in ('SKILL.md', 'catalog.json', 'notation-fields.json', 'skills.json')}
CATALOGUE_DIGEST = hashlib.sha256(b''.join(name.encode() + bytes(1) + data + bytes(1) for name, data in FILES.items())).hexdigest()
REVIEWED_DIGEST = '56460dad73e44cff0e350b5f6a645c43448b1a40223178def57bf785ad9dbdc8'
CATALOGUE = json.loads(FILES['catalog.json'])
FIELDS = json.loads(FILES['notation-fields.json'])
SKILLS = {row['id']: row for row in json.loads(FILES['skills.json'])}
TYPES = {row['id']: row for row in CATALOGUE}
SYSTEM = FILES['SKILL.md'].decode().split('---', 2)[-1].strip()
if TYPES.keys() != SKILLS.keys():
    raise RuntimeError('Every diagram type needs one versioned authoring skill.')


def publish_diagram_skills(memory, project):
    if not memory.enabled(project):
        return
    if CATALOGUE_DIGEST != REVIEWED_DIGEST:
        return
    for kind, template in TYPES.items():
        skill = SKILLS[kind]
        card = {**template, **skill}
        card['elementFields'] = {k: FIELDS['elementFields'][k] for k in template['elements'] if k in FIELDS['elementFields']}
        card['relationFields'] = {k: FIELDS['relationFields'][k] for k in template['relations'] if k in FIELDS['relationFields']}
        text = json.dumps(card, ensure_ascii=False, separators=(',', ':'))
        memory.enqueue(project, 'knowledge', 'skill.diagram.' + kind, text,
                       event_id=f'diagram-skill-{kind}-{CATALOGUE_DIGEST}',
                       source='AtMem Architect diagram catalogue v' + skill['version'] + ' · ' + CATALOGUE_DIGEST)
