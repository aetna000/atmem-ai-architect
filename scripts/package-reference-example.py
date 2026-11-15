"""Package the public reference without host sessions, worker inputs or private paths."""
import hashlib,json,sys,zipfile,io
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=Path(sys.argv[1]);receipt=json.loads(Path(sys.argv[2]).read_text());data=source.read_bytes()
if hashlib.sha256(data).hexdigest()!=receipt['sha256']:raise ValueError('Source artifact digest mismatch')
with zipfile.ZipFile(io.BytesIO(data)) as original:
    files={n:original.read(n) for n in original.namelist() if not n.endswith('/') and not n.startswith(('.agents/','atmem-tools/')) and n not in {'project-context.json','ATMEM_DELIVERY.md','evidence/build.log'}}
qualification=json.loads(files['evidence/qualification.json'])
qualification['files']=[f for f in qualification['files'] if f['path'] in files]
for f in qualification['files']:
    if hashlib.sha256(files[f['path']]).hexdigest()!=f['sha256']:raise ValueError('Stale check evidence: '+f['path'])
qualification['sourceArtifactSha256']=receipt['sha256']
qualification['packagingNote']='Portable reference retains checked implementation bytes. Backend worker inputs and host-specific build log are excluded.'
files['evidence/qualification.json']=(json.dumps(qualification,indent=2)+'\n').encode()
out=root/'public/reference-example.zip';out.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for name,content in sorted(files.items()):
        info=zipfile.ZipInfo(name,date_time=(2026,11,15,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,content)
project=json.loads(files['project.atmem-ai-architect.json'])
(root/'src/reference-example/project.json').write_text(json.dumps(project,indent=2)+'\n')
meta={k:v for k,v in receipt.items() if k not in {'sessionId','artifactId','sha256','bytes'}}
meta.update({'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'bytes':out.stat().st_size,'url':'/reference-example.zip','price':{'monthly':7.56,'currency':'USD','region':'ap-southeast-2','kind':'illustrative usage'},'sourceArtifactSha256':receipt['sha256']})
(root/'src/reference-example/receipt.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps({'files':len(files),'bytes':meta['bytes'],'sha256':meta['sha256']}))
