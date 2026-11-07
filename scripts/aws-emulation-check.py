"""Run the product emulation backend for every archived example, without AWS credentials."""
import datetime
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from server.emulation_routes import EmulationRequest,emulate

def main():
    root=ROOT/'.local/emulation'/datetime.datetime.now(datetime.timezone.utc).isoformat().replace(':','-');root.mkdir(parents=True)
    manifest=json.loads((ROOT/'examples/aws/manifest.json').read_text());results=[]
    for example in manifest['scenarios']:
        # Load the same normalized project used by the real prompt run; no patched exports.
        source=ROOT/'examples/aws'/example['id']/'history'/example['sourceRun']/'round-2/workspace.json'
        result=emulate(EmulationRequest(project=json.loads(source.read_text())))
        (root/(example['id']+'.json')).write_text(json.dumps(result,indent=2)+'\n')
        results.append({'id':example['id'],'status':result['status'],'checks':len(result.get('checks',[]))})
        print(json.dumps(results[-1]),flush=True)
    (root/'results.json').write_text(json.dumps({'kind':'local-aws-emulation','cloudOperations':False,'results':results},indent=2)+'\n')
    print('Evidence:',root)
    return 0 if all(r['status']=='passed' for r in results) else 1
if __name__=='__main__':raise SystemExit(main())
