"""Versioned engine-owned modeling research, separate from vendor specifications.

Fixed local resources only. No caller paths, URLs, project data or execution.
Catalogue registration does not implement a notation or prove architectural quality.
"""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]/'agent-skills/specialists/enterprise-architecture/references'
MAX_BYTES=1_500_000
PAGE=5000


def _resource(name):
    path=ROOT/name
    if path.is_symlink() or not path.is_file():raise ValueError('Engine modeling research is unavailable.')
    with path.open('rb')as stream:raw=stream.read(MAX_BYTES+1)
    if not raw or len(raw)>MAX_BYTES:raise ValueError('Engine modeling research exceeds its bound.')
    return raw


def _catalogue():
    raw=_resource('diagram-catalog.json');data=json.loads(raw)
    if data.get('format')!='atmem.modeling-catalog' or type(data.get('version'))is not int or data['version']!=1:
        raise ValueError('Unsupported engine modeling catalogue.')
    return raw,data


def _rows(data):
    rows=[('modeling-catalog','Enterprise modeling catalogue - research in progress'),('modeling-depth','Language-neutral engineering-model depth'),('modeling-grammar','Implemented class, schema and logical system diagram contracts')]
    rows.extend(('modeling-family-'+family['id'],family['name']+' notation research')for family in data['families'])
    return [{'id':id,'title':title,'publisher':'AtMem engineering research','url':'atmem://research/'+id,
        'evidenceLevel':'engine_research_inventory','boundary':'Engine-owned synthesis and capability inventory, not a normative vendor specification or completed renderer.'}for id,title in rows]


def catalog():
    return _rows(_catalogue()[1])


def read(reference,offset=0,expected_digest=None):
    if not isinstance(reference,str)or len(reference)>100 or type(offset)is not int or offset<0:raise ValueError('Select an engine modeling reference and valid offset.')
    if expected_digest is not None and(not isinstance(expected_digest,str)or not re.fullmatch('[a-f0-9]{64}',expected_digest)):raise ValueError('Use the exact modeling reference digest.')
    if offset and not expected_digest:raise ValueError('A modeling reference digest is required for subsequent pages.')
    raw,data=_catalogue();rows={row['id']:row for row in _rows(data)}
    if reference not in rows:raise ValueError('Unknown engine modeling reference.')
    if reference in {'modeling-depth','modeling-grammar'}:
        raw=_resource('engineering-model-v1.md' if reference=='modeling-grammar' else 'modeling-depth.md');text=raw.decode('utf-8')
    else:
        family_id=reference.removeprefix('modeling-family-')
        families=data['families']if reference=='modeling-catalog'else[family for family in data['families']if family['id']==family_id]
        value={'format':data['format'],'version':data['version'],'researchStatus':data['researchStatus'],'researchedAt':data['researchedAt'],
            'scope':data['scope'],'languagePolicy':data['languagePolicy'],'families':families,'unfinished':data['unfinished']}
        if reference=='modeling-catalog':
            value['families']=[{key:family[key]for key in ['id','name','scope','researchStatus','engineStatus']}for family in families]
            value['familyReferences']=['modeling-family-'+family['id']for family in families]
            value['technologyPalette']=data['technologyPalette'];value['presentation']=data['presentation']
        else:
            value['views']=[view for view in data['views']if view['family']==family_id]
        text=json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)
    digest=sha256(raw).hexdigest()
    if expected_digest and expected_digest!=digest:raise ValueError('Engine modeling research changed. Read its first page again.')
    if offset>=len(text):raise ValueError('Modeling reference offset is past its end.')
    return {**rows[reference],'sha256':digest,'representationSha256':sha256(text.encode()).hexdigest(),'retrievedAt':datetime.now(timezone.utc).isoformat(),
        'characters':len(text),'offset':offset,'nextOffset':offset+PAGE if offset+PAGE<len(text)else None,'text':text[offset:offset+PAGE]}
