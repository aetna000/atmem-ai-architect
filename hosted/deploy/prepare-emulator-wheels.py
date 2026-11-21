"""Build-time download of the generator's exact hash-locked Linux ARM64 SDK wheels."""
import json,subprocess,sys,tempfile
from pathlib import Path
root=Path('/opt/architect')
requirements=json.loads((root/'src/runtime/aws-python-lock.json').read_text())['requirements']
with tempfile.TemporaryDirectory() as folder:
    lock=Path(folder)/'requirements.lock';lock.write_text(requirements)
    subprocess.run([sys.executable,'-I','-m','pip','--isolated','download','--only-binary=:all:','--require-hashes',
        '--python-version','3.13','--implementation','cp','--abi','cp313','--platform','manylinux2014_aarch64',
        '--index-url','https://pypi.org/simple','--dest',str(root/'emulator-wheels'),'-r',str(lock)],check=True)
