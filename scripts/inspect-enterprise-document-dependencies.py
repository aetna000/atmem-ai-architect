"""Inventory the exact pinned shaded jar's embedded Maven descriptors.

This SBOM describes declared embedded coordinates, not a complete bytecode audit.
It is useful when an image scanner omits the shaded Java artifact. Scan it with
the independent vulnerability tool and retain that tool's database metadata.
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def inspect(jar, destination):
    lock = json.loads((ROOT / 'src/runtime/enterprise-document-lock.json').read_text())
    if hashlib.sha256(jar.read_bytes()).hexdigest() != lock['sha256']:
        raise ValueError('Supply the exact reviewed Tika artifact')
    if destination.exists() or not destination.resolve().is_relative_to(ROOT / '.local'):
        raise ValueError('Use a fresh local inventory file')
    components = []
    with zipfile.ZipFile(jar) as archive:
        for name in archive.namelist():
            if not name.endswith('/pom.properties'):
                continue
            raw = archive.read(name)
            fields = {}
            for line in raw.decode('utf-8').splitlines():
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    fields[key.strip()] = value.strip()
            group, artifact, version = [fields.get(key) for key in ['groupId', 'artifactId', 'version']]
            if not all([group, artifact, version]):
                raise ValueError('Review incomplete embedded Maven descriptor')
            purl = 'pkg:maven/' + quote(group, safe='.') + '/' + quote(artifact, safe='.-') + '@' + quote(version, safe='.-')
            components.append({'type': 'library', 'group': group, 'name': artifact, 'version': version,
                'purl': purl, 'bom-ref': purl, 'properties': [
                    {'name': 'atmem:embeddedDescriptor', 'value': name},
                    {'name': 'atmem:descriptorSha256', 'value': hashlib.sha256(raw).hexdigest()}]})
    if not components or len({item['bom-ref'] for item in components}) != len(components):
        raise ValueError('Review missing or ambiguous dependency identities')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({'bomFormat': 'CycloneDX', 'specVersion': '1.5', 'version': 1,
        'components': components}, indent=2) + '\n')
    print(json.dumps({'components': len(components), 'jarSha256': lock['sha256'],
        'sbomSha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
        'scope': 'embedded Maven descriptors; not complete shaded bytecode coverage'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--jar', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    inspect(args.jar, args.out)
