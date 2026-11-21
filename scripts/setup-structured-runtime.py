"""Install an optional isolated worker, never alter server/provider SDK dependencies."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('provider',choices=['ibm']);parser.add_argument('--python',default='python3.13');args=parser.parse_args()
    interpreter=shutil.which(args.python)
    if not interpreter:raise SystemExit('Install Python 3.13 or supply --python /absolute/path/to/python3.13')
    version=subprocess.check_output([interpreter,'-I','-c','import sys;print("%s.%s"%sys.version_info[:2])'],text=True).strip()
    if version!='3.13':raise SystemExit('Generated runtime qualification requires Python 3.13')
    runtime=ROOT/'.local'/f'{args.provider}-structured-runtime'
    subprocess.run([interpreter,'-I','-m','venv',str(runtime)],check=True)
    with tempfile.TemporaryDirectory(prefix='atmem-runtime-locks-') as temporary:
        folder=Path(temporary)
        for emitted,source in [('requirements.lock',args.provider+'-python-lock.json'),('test-requirements.lock','azure-test-lock.json')]:
            (folder/emitted).write_text(json.loads((ROOT/'src/runtime'/source).read_text())['requirements'])
        subprocess.run([str(runtime/'bin/python'),'-I','-m','pip','--isolated','install','--only-binary=:all:','--require-hashes','-r',str(folder/'test-requirements.lock')],check=True)
        subprocess.run([str(runtime/'bin/python'),'-I','-m','pip','check'],check=True)
    print('Isolated worker ready:',runtime/'bin/python')
