"""Convert verified provider archives into read-only image-local executable mirrors."""
import hashlib,json,stat,zipfile
from pathlib import Path,PurePosixPath
root=Path('/opt/architect/provider-mirror');total=0;files=[]
for archive in root.rglob('*.zip'):
 platform=archive.stem.rsplit('_',2)[-2:]
 if platform!=['linux','amd64']:raise RuntimeError('Unexpected provider platform')
 version=archive.stem[:-len('_linux_amd64')].split('_')[-1];target=archive.parent/version/'linux_amd64'
 with zipfile.ZipFile(archive) as bundle:
  for entry in bundle.infolist():
   name=PurePosixPath(entry.filename);total+=entry.file_size
   if name.is_absolute() or '..' in name.parts or '\\' in entry.filename or stat.S_ISLNK(entry.external_attr>>16) or total>8*1024**3:raise RuntimeError('Provider archive violates its build-time bounds')
   destination=target.joinpath(*name.parts)
   if entry.is_dir():destination.mkdir(parents=True,exist_ok=True);continue
   destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(bundle.read(entry))
   destination.chmod(0o555 if destination.name.startswith('terraform-provider-') else 0o444)
   files.append({'path':str(destination.relative_to(root)),'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()})
 archive.unlink()
Path('/opt/architect/provider-file-digests.json').write_text(json.dumps({'files':files,'bytes':total,'platform':'linux/amd64'},indent=2)+'\n')
