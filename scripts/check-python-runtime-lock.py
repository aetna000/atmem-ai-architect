"""Check emitted pins against installed wheel METADATA without importing SDK code."""
from email.parser import BytesParser
from pathlib import Path
import json
import sys
from packaging.utils import canonicalize_name

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from server.runtime_dependency_locks import dependency_gaps

def check(application,sdk):
    metadata={}
    for path in sdk.glob('*.dist-info/METADATA'):
        message=BytesParser().parsebytes(path.read_bytes())
        key=canonicalize_name(message['Name'])
        if key in metadata:raise ValueError('Duplicate installed distribution: '+key)
        metadata[key]={'version':message['Version'],'requiresDist':message.get_all('Requires-Dist',[])}
    records=[];requirements=''
    for source,lock in [('dependency-sources.json','requirements.lock'),('test-dependency-sources.json','test-requirements.lock')]:
        if not (application/source).exists():continue
        requirements+=(application/lock).read_text()+'\n'
        for row in json.loads((application/source).read_text()):
            installed=metadata.get(canonicalize_name(row['name']))
            if not installed or installed['version']!=row['version']:raise ValueError('Missing/mismatched pinned distribution: '+row['name'])
            records.append({**row,'requiresDist':installed['requiresDist']})
    if not records:raise ValueError('No runtime dependency provenance')
    gaps=dependency_gaps({'sources':records,'requirements':requirements})
    return {'passed':not gaps,'dependencyGaps':sorted(gaps),'distributions':len(records),'target':'CPython 3.13 / Linux x86_64','boundary':'Read installed wheel METADATA and emitted pins; this does not execute a Linux image or verify cloud behavior.'}

if __name__=='__main__':
    try:result=check(Path(sys.argv[1]),Path(sys.argv[2]))
    except Exception as error:result={'passed':False,'error':str(error)}
    print(json.dumps(result));raise SystemExit(0 if result['passed'] else 1)
