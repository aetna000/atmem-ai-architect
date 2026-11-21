import subprocess,json,re,hashlib,shlex
from pathlib import Path
subprocess.run(['apt-get','update','-qq'],check=True)
args=['apt-get','--no-install-recommends','--yes','--download-only','install','g++','cmake','make','pkg-config','libleptonica-dev']
uris=subprocess.check_output(args[:1]+['--print-uris']+args[1:],text=True)
subprocess.run(args,check=True)
Path('/review').mkdir(exist_ok=True);Path('/review/apt-print-uris.txt').write_text(uris)
entries=[]
for line in uris.splitlines():
 if not line.startswith("'"):continue
 url,name,size=shlex.split(line)[:3];p=Path('/var/cache/apt/archives')/name
 if not p.is_file():raise RuntimeError('Missing downloaded reviewed package')
 raw=p.read_bytes();metadata=subprocess.check_output(['dpkg-deb','-f',str(p),'Package','Version','Architecture','Source'],text=True)
 entries.append({'url':url.replace('http://','https://'),'filename':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'metadata':metadata})
indexes={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in Path('/var/lib/apt/lists').iterdir()if p.is_file()and('InRelease'in p.name or'Packages'in p.name)}
assert {p.name for p in Path('/var/cache/apt/archives').glob('*.deb')}=={p['filename']for p in entries}
Path('/review/manifest.json').write_text(json.dumps({'platform':'linux/amd64','base':'python:3.13-slim-trixie@sha256:48d884813cf44e927cf64c5529dd630dd3b18338c6dc727991eef9b71e934a20','method':'APT default signature/hash verification, exact downloaded package SHA256 and signed-index hashes','packages':entries,'indexHashes':indexes},indent=2)+'\n')
print(json.dumps({'reviewedPackages':len(entries),'bytes':sum(p['bytes']for p in entries)}))
