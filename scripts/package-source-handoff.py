"""Wrap an unchanged, digest-checked handoff with its exact original sources.

Custody only: this does not approve a design, implement it, or execute its cases.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile


def digest(content):
    return hashlib.sha256(content).hexdigest()


def bounded_file(path, limit):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError('Delivery input must be a bounded regular file.')
    with path.open('rb') as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise ValueError('Delivery input grew beyond its byte bound.')
    return content


def assemble(handoff, sources, audit=None):
    if len(handoff) > 64_000_000:
        raise ValueError('Handoff exceeds the delivery bound; no files were changed.')
    with zipfile.ZipFile(io.BytesIO(handoff)) as package:
        entries = package.infolist()
        names = [row.filename for row in entries]
        if len(names) > 2000 or len(set(names)) != len(names) or sum(row.file_size for row in entries) > 128_000_000:
            raise ValueError('Handoff inventory exceeds its custody bound.')
        if any(name.startswith('/') or '\\' in name or ':' in name or any(part in ('', '.', '..') for part in name.split('/')) for name in names):
            raise ValueError('Handoff has an unsafe member name.')
        manifest = json.loads(package.read('manifest.json'))
        expected = manifest['fileDigests']
        if set(expected) != set(names) - {'manifest.json'}:
            raise ValueError('Handoff manifest inventory differs from its files.')
        for name, receipt in expected.items():
            content = package.read(name)
            if receipt['bytes'] != len(content) or receipt['sha256'] != digest(content):
                raise ValueError('Handoff payload integrity failed: ' + name)
        snapshot = package.read('project.atmem-ai-architect.json')
        project = json.loads(snapshot)
    declared = project.get('extensions', {}).get('designSources', [])
    wanted = {(row['name'], row['sha256']) for row in declared}
    if len(wanted) != len(declared) or len(sources) != len(wanted) or len({name.casefold() for name, _ in wanted}) != len(wanted):
        raise ValueError('Supply every original source exactly once.')
    files = {'architecture-handoff.zip': handoff, 'reviewed-project.json': snapshot}
    received = set()
    for path in sources:
        content = bounded_file(path, 32_000_000)
        identity = (path.name, digest(content))
        if identity not in wanted or identity in received:
            raise ValueError('Original source name or digest does not match the captured specification: ' + path.name)
        received.add(identity)
        files['original-specifications/' + path.name] = content
    if received != wanted:
        raise ValueError('An original specification is missing.')
    if audit is not None:
        files['audit.html'] = audit
    files['READ_FIRST.md'] = (
        '# Developer delivery — ' + project['meta']['name'] + '\n\n'
        '1. Extract architecture-handoff.zip and read START_HERE.md, BUILD-HANDOFF.md and the work orders.\n'
        '2. Keep original-specifications beside the handoff. Their exact bytes match the uploaded source digests.\n'
        '3. Run python3 qualification/check_handoff.py inside the extracted handoff.\n\n'
        'reviewed-project.json reopens this design in Architect. audit.html records the review when supplied.\n\n'
        'The original handoff is unchanged. Test definitions are not executed results. Owner qualifications, implementation and deployment remain separate.\n'
    ).encode()
    if sum(map(len, files.values())) > 128_000_000:
        raise ValueError('Developer delivery exceeds its explicit bound.')
    files['delivery-manifest.json'] = json.dumps({
        'format': 'atmem.developer-delivery', 'version': 1,
        'projectId': project['meta']['id'], 'designRevision': project['meta']['revision'],
        'files': {name: {'sha256': digest(body), 'bytes': len(body)} for name, body in files.items()},
        'boundary': 'Unchanged architecture handoff and exact original specifications; no implementation, case execution or deployment.'
    }, indent=2).encode()
    return files


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--handoff', required=True, type=Path)
    parser.add_argument('--source', required=True, action='append', type=Path)
    parser.add_argument('--audit', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    files = assemble(bounded_file(args.handoff, 64_000_000), args.source, bounded_file(args.audit, 16_000_000) if args.audit else None)
    temporary = args.output.with_suffix(args.output.suffix + '.next')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as package:
        for name, content in files.items():
            package.writestr(name, content)
    temporary.replace(args.output)
    print(json.dumps({'output': str(args.output), 'files': len(files), 'sha256': digest(args.output.read_bytes())}))
