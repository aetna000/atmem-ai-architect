"""Regenerate an unchanged evaluated project through the corrected generator.
Never edits the original export or attributes a compiler-only rerun to new conversation.
"""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['src','agent-skills'] for p in (ROOT/folder).rglob('*') if p.is_file()}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('original_case');p.add_argument('destination');args=p.parse_args()
    original=Path(args.original_case).resolve();destination=Path(args.destination).resolve()
    if destination.exists():raise SystemExit('Destination already exists; retain previous evidence and choose a new run directory')
    source=(original/'project.json').read_bytes();project=json.loads(source);before=hashes();destination.mkdir(parents=True)
    request={'action':'export','project':project,'output':str(destination/'handoff')}
    done=subprocess.run(['node',str(ROOT/'scripts/convergence-bridge.mjs')],input=json.dumps(request),capture_output=True,text=True,cwd=ROOT,timeout=60)
    if done.returncode:raise SystemExit(done.stderr)
    after=hashes()
    if before!=after:raise SystemExit('Generator changed during export; package not qualified')
    (destination/'project.json').write_bytes(source)
    (destination/'export-assessment.json').write_text(json.dumps(json.loads(done.stdout),indent=2)+'\n')
    record={'kind':'compiler-only-regeneration','newUserExchanges':0,'newModelCalls':0,'nativeConversationSource':str(original),'originalProjectSha256':hashlib.sha256(source).hexdigest(),'baseCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'generatorSourceHashes':before,'originalExportPreserved':True,'cloudOperations':False}
    (destination/'regeneration.json').write_text(json.dumps(record,indent=2)+'\n')
    print(destination)
