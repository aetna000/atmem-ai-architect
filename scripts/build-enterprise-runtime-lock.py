"""Resolve the private application core from exact already-reviewed metadata.

No resolver upgrades, network access or implicit version conflict selection.
Native model/secret adapters will require their own explicit dependency extension.
"""
import hashlib
import json
from pathlib import Path
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ['enterprise-auth-python-lock.json', 'web-python-lock.json', 'durable-python-lock.json']
ROOTS = ['msal==1.39.0', 'PyJWT[crypto]==2.15.1', 'requests==2.34.2',
         'psycopg[binary]==3.3.8', 'procrastinate==3.10.0', 'fastapi==0.162.0', 'uvicorn==0.54.0']


def build():
    records = {}
    for filename in INPUTS:
        for source in json.loads((ROOT / 'src/runtime' / filename).read_text())['sources']:
            name = canonicalize_name(source['name'])
            old = records.setdefault(name, {}).get(source['version'])
            if old is not None and old != source:
                raise ValueError('Conflicting metadata for the same reviewed version: ' + name)
            records[name][source['version']] = source
    environment = {**default_environment(), 'python_version': '3.13', 'python_full_version': '3.13.18',
                   'sys_platform': 'linux', 'os_name': 'posix', 'platform_machine': 'x86_64',
                   'platform_python_implementation': 'CPython', 'implementation_name': 'cpython'}
    selected, extras, processed = {}, {}, {}
    pending = [Requirement(value) for value in ROOTS]
    while pending:
        requirement = pending.pop(0)
        name = canonicalize_name(requirement.name)
        candidates = [s for version, s in records.get(name, {}).items() if version in requirement.specifier]
        if len(candidates) != 1:
            raise ValueError('Ambiguous/missing reviewed dependency: ' + str(requirement))
        source = candidates[0]
        if name in selected and selected[name]['version'] != source['version']:
            raise ValueError('Conflicting selected dependency: ' + name)
        selected[name] = source
        extras.setdefault(name, set()).update(requirement.extras)
        active = frozenset(extras[name])
        if processed.get(name) == active:
            continue
        processed[name] = active
        for value in source['requiresDist']:
            dependency = Requirement(value)
            if dependency.marker is None or any(dependency.marker.evaluate({**environment, 'extra': extra})
                                                for extra in {''} | set(active)):
                pending.append(dependency)
    sources = [selected[name] for name in sorted(selected)]
    requirements = '\n'.join(s['name'] + '==' + s['version'] + ' \\\n' + '\n'.join(
        '    --hash=sha256:' + digest + (' \\' if index < len(s['wheelHashes']) - 1 else '')
        for index, digest in enumerate(sorted(s['wheelHashes']))) for s in sources) + '\n'
    return {'requirements': requirements, 'sources': sources, 'roots': ROOTS,
            'target': 'CPython 3.13 Linux x86_64; binary wheels only',
            'derivedFrom': {str((Path('src/runtime') / name)): hashlib.sha256(
                (ROOT / 'src/runtime' / name).read_bytes()).hexdigest() for name in INPUTS},
            'scope': 'Private application core only. Native model/secret factories, operator provisioning and cloud isolation are not implemented by this lock.'}


if __name__ == '__main__':
    result = build()
    (ROOT / 'src/runtime/enterprise-runtime-python-lock.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Exact private runtime closure:', len(result['sources']), 'packages')
