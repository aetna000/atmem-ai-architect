"""Inventory installed optional emulator dependencies without executing their code."""
import json
from importlib.metadata import distribution
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
records=[];texts=[]
for line in (ROOT/'server/cloud-emulation-requirements.txt').read_text().splitlines():
    if not line or line.startswith('#'):continue
    name=line.split('==')[0];d=distribution(name);files=[f for f in d.files or [] if any(part.lower() in ('license','licenses','notice','license.txt','license.md') for part in f.parts)]
    license=d.metadata.get('License-Expression') or d.metadata.get('License') or 'UNKNOWN'
    records.append({'name':d.metadata['Name'],'version':d.version,'license':license,'ecosystem':'python','scope':'optional cloud emulation clients','licenseFiles':[str(f) for f in files]})
    texts.append(f'\n{name}@{d.version}\nDeclared license: {license}\n')
    for file in files:
        target=Path(d.locate_file(file))
        if target.is_file():texts.append(target.read_text(errors='replace'))
lock=json.loads((ROOT/'scripts/cloud-emulators/package-lock.json').read_text())
for location,entry in lock['packages'].items():
    if not location:continue
    target=ROOT/'.local/cloud-emulators'/location
    if not (target/'package.json').is_file():continue
    package=json.loads((target/'package.json').read_text());files=[p for p in target.iterdir() if p.is_file() and p.name.lower().split('.')[0] in ('license','licence','copying','notice')]
    records.append({'name':package['name'],'version':package['version'],'license':package.get('license','UNKNOWN'),'ecosystem':'npm','scope':'optional Azurite service','licenseFiles':[p.name for p in files]})
    texts.append(f'\n{package["name"]}@{package["version"]}\nDeclared license: {package.get("license","UNKNOWN")}\n')
    texts.extend(p.read_text(errors='replace') for p in files)
folder=ROOT/'.local/cloud-emulators/fake-gcs';receipt=json.loads((folder/'receipt.json').read_text());records.append({'name':'fake-gcs-server','version':receipt['version'],'source':receipt['source'],'license':'BSD-2-Clause','ecosystem':'standalone binary','scope':'optional GCS API service'});texts.append((folder/'LICENSE').read_text())
(ROOT/'docs/cloud-emulation-dependency-inventory.json').write_text(json.dumps(records,indent=2)+'\n')
(ROOT/'public/licenses/cloud-emulation-notices.txt').write_text('\n'.join(texts).replace('\r\n','\n').rstrip()+'\n')
print(json.dumps({'installedDependencies':len(records),'unknownLicense':[r['name'] for r in records if r['license']=='UNKNOWN']}))
