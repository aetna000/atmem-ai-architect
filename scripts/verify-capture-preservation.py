#!/usr/bin/env python3
"""Compare explicit protected paths in immutable captures, without executing files.

The operator inventory pins the complete original ZIP and protected prefixes.
This is a byte/mode/scope check, not semantic or whole-repository acceptance.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import stat
import zipfile
import zlib

MAX_BYTES = 64_000_000
MAX_FILES = 2000


def sha(content):
    return hashlib.sha256(content).hexdigest()


def safe_path(name):
    return (isinstance(name, str) and 0 < len(name) <= 500
            and not any(char in name for char in ['\\', ':'])
            and not any(ord(char) < 32 or ord(char) == 127 for char in name)
            and all(part and part not in {'.', '..'} for part in name.split('/')))


def capture(path):
    if not 0 < path.stat().st_size <= MAX_BYTES:
        raise ValueError('Capture exceeds its byte bound.')
    content = path.read_bytes()
    files = {}
    seen = set()
    expanded = 0
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        if len(archive.infolist()) > MAX_FILES:
            raise ValueError('Capture exceeds its entry bound.')
        for entry in archive.infolist():
            name = entry.filename[:-1] if entry.is_dir() else entry.filename
            mode = entry.external_attr >> 16
            if not safe_path(name) or name.casefold() in seen:
                raise ValueError('Capture has an unsafe or ambiguous path.')
            seen.add(name.casefold())
            if stat.S_IFMT(mode) not in (0, stat.S_IFDIR if entry.is_dir() else stat.S_IFREG):
                raise ValueError('Capture has a non-regular entry.')
            if entry.is_dir():
                continue
            expanded += entry.file_size
            if entry.file_size < 0 or expanded > MAX_BYTES:
                raise ValueError('Capture exceeds its expanded byte bound.')
            body = archive.read(entry)
            if len(body) != entry.file_size:
                raise ValueError('Capture member length mismatch.')
            files[entry.filename] = {'sha256': sha(body), 'bytes': len(body), 'mode': stat.S_IMODE(mode)}
    return sha(content), files


def audit(before_path, after_path, inventory):
    if (not isinstance(inventory, dict) or inventory.get('version') != 1
            or not isinstance(inventory.get('beforeSha256'), str)
            or not re.fullmatch('[a-f0-9]{64}', inventory['beforeSha256'])):
        raise ValueError('A versioned inventory and exact original capture digest are required.')
    prefixes = inventory.get('protectedPrefixes')
    if (not isinstance(prefixes, list) or not 0 < len(prefixes) <= 100
            or any(not isinstance(prefix, str) or not prefix.endswith('/') or not safe_path(prefix[:-1]) for prefix in prefixes)
            or len(set(prefixes)) != len(prefixes)):
        raise ValueError('Protected prefixes must be explicit, distinct relative directories.')
    before_sha, before = capture(before_path)
    if before_sha != inventory['beforeSha256']:
        raise ValueError('Original capture does not match the inventory digest.')
    after_sha, after = capture(after_path)
    protected = lambda name: any(name.startswith(prefix) for prefix in prefixes)
    for prefix in prefixes:
        if not any(name.startswith(prefix) for name in before):
            raise ValueError('A protected prefix has no original files; an empty check cannot pass.')
    expected = {name: value for name, value in before.items() if protected(name)}
    actual = {name: value for name, value in after.items() if protected(name)}
    differences = []
    for name in sorted(expected.keys() | actual.keys()):
        if name not in actual:
            differences.append({'path': name, 'change': 'removed'})
        elif name not in expected:
            differences.append({'path': name, 'change': 'added'})
        elif actual[name] != expected[name]:
            differences.append({'path': name, 'change': 'modified', 'before': expected[name], 'after': actual[name]})
    return {'version': 1, 'status': 'failed' if differences else 'passed',
            'beforeSha256': before_sha, 'afterSha256': after_sha,
            'protectedPrefixes': prefixes, 'protectedFiles': expected,
            'differences': differences,
            'unprotectedAddedFiles': sorted(name for name in after if name not in before and not protected(name)),
            'boundary': 'Exact bytes, modes and path inventory within the operator-declared prefixes only. Other files, semantic correctness, execution and deployment are not qualified.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'inventory', 'out']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if args.out.resolve() in {args.before.resolve(), args.after.resolve(), args.inventory.resolve()}:
        parser.error('The report must not replace an input artifact.')
    try:
        report = audit(args.before, args.after, json.loads(args.inventory.read_text()))
    except (ValueError, OSError, TypeError, KeyError, zipfile.BadZipFile, zlib.error, EOFError, RuntimeError) as error:
        report = {'status': 'rejected', 'reason': str(error), 'executionPerformed': False}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ['status', 'reason'] if key in report}))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
