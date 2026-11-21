"""Inventory installed sidecar packages and preserve wheel-provided legal text."""
from importlib import metadata
from pathlib import Path
import json
import argparse
parser=argparse.ArgumentParser()
parser.add_argument("--environment",choices=["sidecar","memory"],default="sidecar")
options=parser.parse_args()
prefix="memory-" if options.environment=="memory" else "python-"
inventory=[];notices=[]
for dist in sorted(metadata.distributions(),key=lambda d:d.metadata['Name'].lower()):
    name=dist.metadata['Name'];version=dist.version
    licence=dist.metadata.get('License-Expression') or dist.metadata.get('License') or 'UNKNOWN'
    if len(licence)>300:licence='See bundled licence text and upstream metadata'
    files=[]
    for file in dist.files or []:
        lower=str(file).lower()
        if '.dist-info/' not in lower:continue
        if '/licenses/' in lower or Path(lower).name.startswith(('license','licence','notice','copying')):
            path=dist.locate_file(file)
            if path.is_file():
                try:notices.append(f'\n{name}=={version}\n{file}\n'+path.read_text())
                except UnicodeError:continue
                files.append(str(file))
    inventory.append({'name':name,'version':version,'declaredLicense':licence,'wheelLegalFiles':files})
Path(f'docs/{prefix}dependency-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
Path(f'public/licenses/{prefix}dependency-notices.txt').write_text('\n'.join(notices))
print(json.dumps({'installedPackages':len(inventory),'missingDeclaredLicense':[x['name'] for x in inventory if x['declaredLicense']=='UNKNOWN'],'noWheelLegalFiles':[x['name'] for x in inventory if not x['wheelLegalFiles']]}))
