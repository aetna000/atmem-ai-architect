"""Opt-in installation of pinned local storage backends; no Docker or cloud keys."""
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'.local/cloud-emulators'

def main():
    DEST.mkdir(parents=True,exist_ok=True)
    for name in ['package.json','package-lock.json']:shutil.copyfile(ROOT/'scripts/cloud-emulators'/name,DEST/name)
    subprocess.run(['npm','ci','--prefix',str(DEST),'--ignore-scripts','--no-audit','--no-fund'],check=True)
    system=platform.system();arch={'arm64':'arm64','aarch64':'arm64','x86_64':'amd64'}.get(platform.machine())
    if system not in ('Darwin','Linux') or not arch:raise SystemExit('This local worker adapter currently supports macOS/Linux arm64/amd64.')
    version='1.56.1';name=f'fake-gcs-server_{version}_{system}_{arch}.tar.gz';base=f'https://github.com/fsouza/fake-gcs-server/releases/download/v{version}/'
    with urllib.request.urlopen(base+'checksums.txt',timeout=30) as response:checksums=response.read().decode()
    expected=next((line.split()[0] for line in checksums.splitlines() if line.split()[-1]==name),None)
    if not expected:raise SystemExit('Official release checksum missing')
    with urllib.request.urlopen(base+name,timeout=60) as response:data=response.read(40_000_000)
    actual=hashlib.sha256(data).hexdigest()
    if actual!=expected:raise SystemExit('Official release checksum mismatch')
    target=DEST/'fake-gcs';target.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        archive=Path(folder)/'download.tar.gz';archive.write_bytes(data)
        with tarfile.open(archive) as tar:
            for filename in ['fake-gcs-server','LICENSE','README.md']:
                member=tar.getmember(filename)
                if not member.isfile():raise SystemExit('Unexpected release member')
                (target/filename).write_bytes(tar.extractfile(member).read())
    (target/'fake-gcs-server').chmod(0o755)
    (target/'receipt.json').write_text(json.dumps({'version':version,'source':base+name,'sha256':actual,'binarySha256':hashlib.sha256((target/'fake-gcs-server').read_bytes()).hexdigest()},indent=2)+'\n')
    subprocess.run([str(ROOT/'.venv/bin/python'),'-m','pip','install','-r',str(ROOT/'server/cloud-emulation-requirements.txt')],check=True)
    print('Installed Azurite 3.37.0, fake-gcs-server 1.56.1 and pinned client SDK dependencies. No cloud operations.')
if __name__=='__main__':main()
