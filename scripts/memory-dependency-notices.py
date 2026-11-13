"""Run with the locked memory interpreter; preserve installed wheels' legal files."""
from importlib.metadata import distribution
from pathlib import Path
import json
import re
ROOT = Path(__file__).resolve().parents[1]
inventory, notices = [], []
for line in (ROOT/'server/memory-requirements.txt').read_text().splitlines():
    match = re.fullmatch(r'([\w-]+)==([\w.]+)', line)
    if not match:
        continue
    name, expected = match.groups()
    package = distribution(name)
    if package.version != expected:
        raise RuntimeError(f'Install the exact memory lock before generating notices: {name}')
    files = [file for file in package.files or [] if '.dist-info/licenses/' in str(file) or ('.dist-info/' in str(file) and re.search(r'/(LICENSE|NOTICE|COPYING)(\.|$)', str(file), re.I))]
    if not files:
        raise RuntimeError(f'No wheel legal files found: {name}')
    inventory.append({'name': name, 'version': package.version,
                      'declaredLicense': package.metadata.get('License-Expression') or package.metadata.get('License') or 'UNKNOWN',
                      'wheelLegalFiles': [str(file) for file in files]})
    for file in files:
        notices.append('\n'+'='*72+f'\n{name}=={package.version}\n{file}\n\n'+package.locate_file(file).read_text())
(ROOT/'docs/memory-dependency-inventory.json').write_text(json.dumps(sorted(inventory,key=lambda row:row['name']),indent=2)+'\n')
(ROOT/'public/licenses/memory-dependency-notices.txt').write_text(re.sub(r'[ \t]+$', '', '\n'.join(notices), flags=re.M).rstrip()+'\n')
print(f'Preserved legal files from {len(inventory)} locked memory distributions.')
