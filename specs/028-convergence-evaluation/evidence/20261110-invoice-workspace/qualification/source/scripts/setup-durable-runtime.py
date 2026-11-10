"""Install the optional isolated queue worker from reviewed wheel hashes."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--python',default='python3.13');args=parser.parse_args()
    interpreter=shutil.which(args.python)
    if not interpreter:raise SystemExit('Supply an installed Python 3.13 interpreter')
    version=subprocess.check_output([interpreter,'-I','-c','import sys;print("%s.%s"%sys.version_info[:2])'],text=True).strip()
    if version!='3.13':raise SystemExit('This reviewed runtime targets Python 3.13')
    folder=ROOT/'.local/durable-runtime';subprocess.run([interpreter,'-I','-m','venv',str(folder)],check=True)
    with tempfile.TemporaryDirectory(prefix='atmem-durable-lock-')as temporary:
        lock=Path(temporary)/'requirements.lock';lock.write_text(json.loads((ROOT/'src/runtime/durable-python-lock.json').read_text())['requirements'])
        subprocess.run([str(folder/'bin/python'),'-I','-m','pip','--isolated','install','--only-binary=:all:','--require-hashes','-r',str(lock)],check=True)
    subprocess.run([str(folder/'bin/python'),'-I','-m','pip','check'],check=True)
    print('Isolated durable worker ready:',folder/'bin/python')
