"""Resolve an exact Linux auth dependency slice from reviewed pinned metadata.

No package download, version upgrade, unpinned resolver or dependency-conflict
fallback. Clean Linux install/runtime qualification is separate evidence.
"""
import hashlib
import json
from pathlib import Path
from packaging.requirements import Requirement
from packaging.markers import default_environment
from packaging.utils import canonicalize_name

ROOT=Path(__file__).resolve().parents[1]
paths=[ROOT/'src/runtime/azure-python-lock.json',ROOT/'src/runtime/durable-python-lock.json']
records={}
for path in paths:
    for source in json.loads(path.read_text())['sources']:
        key=canonicalize_name(source['name']);records.setdefault(key,{})[source['version']]=source
roots=['msal==1.39.0','PyJWT[crypto]==2.15.1','requests==2.34.2','psycopg[binary]==3.3.8']
env={**default_environment(),'python_version':'3.13','python_full_version':'3.13.14','sys_platform':'linux','os_name':'posix','platform_machine':'x86_64','platform_python_implementation':'CPython','implementation_name':'cpython'}
selected={};extras={};processed={};queue=[Requirement(value)for value in roots]
while queue:
    requirement=queue.pop(0);name=canonicalize_name(requirement.name)
    candidates=[source for version,source in records.get(name,{}).items()if version in requirement.specifier]
    if len(candidates)!=1:raise ValueError('Ambiguous or missing reviewed pin: '+str(requirement))
    source=candidates[0]
    if name in selected and selected[name]['version']!=source['version']:raise ValueError('Unreviewed dependency conflict: '+name)
    selected[name]=source;extras.setdefault(name,set()).update(requirement.extras)
    active=frozenset(extras[name])
    if processed.get(name)==active:continue
    processed[name]=active
    for raw in source['requiresDist']:
        dependency=Requirement(raw)
        if dependency.marker is None or any(dependency.marker.evaluate({**env,'extra':extra})for extra in {''}|set(active)):queue.append(dependency)
sources=[selected[name]for name in sorted(selected)]
requirements='\n'.join(source['name']+'=='+source['version']+' \\\n'+'\n'.join('    --hash=sha256:'+digest+(' \\'if index<len(source['wheelHashes'])-1 else'')for index,digest in enumerate(sorted(source['wheelHashes'])))for source in sources)+'\n'
result={'requirements':requirements,'sources':sources,'roots':roots,'target':'Python 3.13 Linux x86_64; binary wheels only','derivedFrom':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'scope':'Exact reviewed metadata dependency slice; clean installation/runtime/security qualification is separate.'}
(ROOT/'src/runtime/enterprise-auth-python-lock.json').write_text(json.dumps(result,indent=2)+'\n')
print('Reviewed auth closure:',len(sources),'exact dependencies')
