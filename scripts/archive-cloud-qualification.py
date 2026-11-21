"""Preserve real prompt/UI runs and native-provider fixture results without claiming deployment."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'examples/cloud-qualification'

def main():
    DEST.mkdir(parents=True,exist_ok=True)
    manifest_path=DEST/'manifest.json';manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'version':1,'cloudOperations':False,'runs':[]}
    for arg in sys.argv[1:]:
        source=Path(arg).resolve()
        if source.parent not in (ROOT/'.local/cloud-mentor',ROOT/'.local/cloud-storage',ROOT/'.local/emulation-browser'):raise SystemExit('Unexpected evidence source')
        if not (source/'results.json').is_file():raise SystemExit('Incomplete run; no aggregate results')
        aggregate=json.loads((source/'results.json').read_text())
        kind='real-model-browser-run' if source.parent.name=='cloud-mentor' else 'fixture-model-browser-regression' if source.parent.name=='emulation-browser' else aggregate.get('kind','synthetic-contract-fixture')
        target=DEST/'runs'/source.name;files=[]
        for folder in [source]+[p for p in source.iterdir() if p.is_dir() and p.name not in ('source','home')]:
            candidates=source.iterdir() if folder==source else folder.rglob('*')
            for file in candidates:
                relative=file.relative_to(source)
                if not file.is_file() or any(part in ('.terraform','__pycache__') for part in relative.parts) or file.suffix not in ('.json','.jsonl','.txt','.log','.hcl','.py','.md','.svg','.png'):continue
                if file.name in ('services.log','emulator.log'):continue
                dest=target/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,dest)
                files.append({'path':dest.relative_to(DEST).as_posix(),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
        entry={'id':source.name,'kind':kind,'files':files,'cloudOperations':False,'results':json.loads((source/'results.json').read_text())}
        if (source/'source').exists():
            digest=hashlib.sha256()
            for file in sorted((source/'source').rglob('*')):
                relative=file.relative_to(source/'source')
                if any(p in ('node_modules','.venv','.local','__pycache__') for p in relative.parts) or not file.is_file():continue
                digest.update(str(relative).encode());digest.update(file.read_bytes())
            entry['testedSourceDigest']=digest.hexdigest()
        manifest['runs']=[r for r in manifest['runs'] if r['id']!=entry['id']]+[entry]
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Archived {len(sys.argv)-1} runs, preserving prior failures and evidence kinds.')
if __name__=='__main__':main()
