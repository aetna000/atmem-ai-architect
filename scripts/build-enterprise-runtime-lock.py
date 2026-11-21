"""Resolve the private application core from exact already-reviewed metadata.

No resolver upgrades, network access or implicit version conflict selection.
Native model/secret adapters will require their own explicit dependency extension.
"""
import hashlib
import json
import argparse
from pathlib import Path
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ['enterprise-auth-python-lock.json', 'web-python-lock.json', 'durable-python-lock.json']
ROOTS = ['msal==1.39.0', 'PyJWT[crypto]==2.15.1', 'requests==2.34.2',
         'psycopg[binary]==3.3.8', 'procrastinate==3.10.0', 'fastapi==0.162.0', 'uvicorn==0.54.0']


def build(provider=None):
    if provider not in {None, 'aws', 'azure', 'gcp', 'ibm'}:
        raise ValueError('Supply the owned native model provider')
    additions = {'aws': ('aws-web-python-lock.json', ['boto3==1.43.123']),
                 'azure': ('azure-python-lock.json', ['azure-identity==1.27.0']),
                 'gcp': (None, []), 'ibm': ('ibm-python-lock.json', ['ibm-cloud-sdk-core==3.28.2'])}
    filename, extra_roots = additions.get(provider, (None, []))
    inputs = [*INPUTS, *([filename] if filename else [])]
    # IBM's SDK requires >=3.0.0; the queue admits that reviewed version. Other
    # providers retain the queue's existing 2.9 pin. Never hide incompatible SDK
    # constraints by forcing one supposedly common transitive version.
    dateutil = '3.0.0' if provider == 'ibm' else '2.9.0.post0'
    roots = [*ROOTS, *extra_roots, *(['python-dateutil==' + dateutil] if provider else [])]
    pins = {canonicalize_name(r.name): str(next(iter(r.specifier))).removeprefix('==')
            for r in map(Requirement, roots) if len(list(r.specifier)) == 1 and next(iter(r.specifier)).operator == '=='}
    records = {}
    for filename in inputs:
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
    pending = [Requirement(value) for value in roots]
    while pending:
        requirement = pending.pop(0)
        name = canonicalize_name(requirement.name)
        candidates = [s for version, s in records.get(name, {}).items() if version in requirement.specifier
                      and (name not in pins or version == pins[name])]
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
    result = {'requirements': requirements, 'sources': sources, 'roots': roots,
            'target': 'CPython 3.13 Linux x86_64; binary wheels only',
            'derivedFrom': {str((Path('src/runtime') / name)): hashlib.sha256(
                (ROOT / 'src/runtime' / name).read_bytes()).hexdigest() for name in inputs},
            'scope': 'Private application dependency closure. Native model/secret factories, operator provisioning and cloud isolation require their own implementation/qualification.'}
    if provider is not None: result['provider'] = provider
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--provider', choices=['core', 'aws', 'azure', 'gcp', 'ibm', 'all'], default='core')
    argument = parser.parse_args().provider
    for provider in ([None, 'aws', 'azure', 'gcp', 'ibm'] if argument == 'all' else [None if argument == 'core' else argument]):
        result = build(provider)
        name = 'enterprise-runtime' + ('-' + provider if provider else '') + '-python-lock.json'
        (ROOT / 'src/runtime' / name).write_text(json.dumps(result, indent=2) + '\n')
        print('Exact private', provider or 'core', 'closure:', len(result['sources']), 'packages')
