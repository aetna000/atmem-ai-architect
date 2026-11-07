"""Append reviewed synthetic emulation reports; preserve earlier proof and failures."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('runs',nargs='+',type=Path);args=parser.parse_args()
    archive=ROOT/'examples/aws';manifest=json.loads((archive/'manifest.json').read_text())
    for supplied in args.runs:
        source=supplied.resolve()
        if not source.is_relative_to(ROOT/'.local/emulation'):raise SystemExit('Only local emulation evidence directories are accepted')
        report=json.loads((source/'results.json').read_text())
        if report.get('kind')!='local-aws-emulation' or report.get('cloudOperations') is not False:raise SystemExit('Not an emulation report')
        files=[]
        for name in ['results.json']+[r['id']+'.json' for r in report['results']]:
            if Path(name).name!=name:raise SystemExit('Unsafe evidence name')
            data=(source/name).read_bytes();value=json.loads(data)
            if value.get('cloudOperations') is not False:raise SystemExit('Unexpected cloud evidence in emulator archive')
            relative=Path('evidence/emulation')/source.name/name;target=archive/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            files.append({'path':relative.as_posix(),'sha256':hashlib.sha256(data).hexdigest(),'sourceSha256':hashlib.sha256(data).hexdigest(),'sanitized':False})
        entry={'kind':'emulation','sourceRun':source.name,'status':'passed' if all(r['status']=='passed' for r in report['results']) else 'failed','files':files}
        manifest['reproductions']=[r for r in manifest.get('reproductions',[]) if not(r['kind']=='emulation' and r['sourceRun']==source.name)]+[entry]
    (archive/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Archived emulation histories:',len(args.runs))
if __name__=='__main__':main()
