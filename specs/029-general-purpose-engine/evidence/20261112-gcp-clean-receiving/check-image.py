"""Independently check delivered image contents and frozen policy without a developer runtime."""
from pathlib import Path
import ast,hashlib,json,os,re,shlex,subprocess
ROOT=Path(__file__).resolve().parents[4];bulk=ROOT/'.local/external-artifacts/native-amd64-runtime/v1/receiving-build-v1';package=ROOT/'.local/external-artifacts/native-gcp-water/v1/native-run/unpacked';endpoint='unix:///Users/javadtaghia/.avm/c/amd64/validator.sock';image=(bulk/'image-id.txt').read_text().strip();assert re.fullmatch(r'sha256:[a-f0-9]{64}',image)
inspect=json.loads(subprocess.check_output(['docker','--host',endpoint,'image','inspect',image],text=True))[0];assert inspect['Architecture']=='amd64'and inspect['Os']=='linux'and inspect['Config']['User']=='10001:10001'
expected={}
for line in(package/'Dockerfile').read_text().splitlines():
 tokens=shlex.split(line)
 if tokens[:1]==['COPY']and tokens[-1]=='/app/':
  for source in tokens[1:-1]:
   name=Path(source).name;assert name not in expected;expected[name]=hashlib.sha256((package/source).read_bytes()).hexdigest()
assert expected
lock={re.sub(r'[-_.]+','-',name).lower():version for name,version in re.findall(r'^([A-Za-z0-9_.-]+)==([^\s]+)',(package/'application/test-requirements.lock').read_text(),re.M)};assert len(lock)==34
inventory=r'''
import hashlib,importlib.metadata,json,os,pathlib,platform,re,sys
expected,lock=json.loads(sys.stdin.buffer.read(1000000));assert os.getuid()==10001
files={str(p.relative_to('/app')):hashlib.sha256(p.read_bytes()).hexdigest()for p in pathlib.Path('/app').rglob('*')if p.is_file()}
assert files==expected,(set(files)-set(expected),set(expected)-set(files))
installed={re.sub(r'[-_.]+','-',d.metadata['Name']).lower():d.version for d in importlib.metadata.distributions()}
assert all(installed.get(name)==version for name,version in lock.items())
assert set(installed)==set(lock)|{'pip'},set(installed)-set(lock)
assert platform.python_version()=='3.13.18'and platform.machine()=='x86_64'
assert not pathlib.Path('/wheelhouse').exists()and not pathlib.Path('/var/run/docker.sock').exists()
assert {p.name for p in pathlib.Path('/sys/class/net').iterdir()}=={'lo'}
sys.path.insert(0,'/app');import sample_entry,sample_configuration
'''
# The child launcher is verified by hash and exercised through its executable entrypoint.
inventory+="\nprint(json.dumps({'passed':True,'files':files,'packages':installed,'uid':os.getuid(),'machine':platform.machine(),'python':platform.python_version(),'sourceEntryImports':True,'externalNetwork':False,'rootReadonly':bool(os.statvfs('/').f_flag&os.ST_RDONLY)}))\n"
base=['docker','--host',endpoint,'run','--pull','never','--rm','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','64','--memory','256m','--cpus','1','--entrypoint','/usr/local/bin/python3','-i',image,'-I','-c']
r=subprocess.run([*base,inventory],input=json.dumps([expected,lock]).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
(bulk/'image-inventory-output-v1.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,(r.stdout,r.stderr)
observed=json.loads(r.stdout);assert observed['rootReadonly'] is True
cases=ROOT/'specs/029-general-purpose-engine/evidence/20261112-native-gcp-water/requirements-cases-v1.json';tree=ast.parse((ROOT/'specs/029-general-purpose-engine/evidence/20261112-native-amd64-runtime/check-frozen-domain.py').read_text());code=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='code'for t in n.targets));code=code.replace("'/work/source/application'","'/app'").replace('cases=json.loads(sys.argv[1])','cases=json.loads(sys.stdin.buffer.read(1000000))')
r=subprocess.run([*base,code],input=cases.read_bytes(),stdout=subprocess.PIPE,stderr=subprocess.PIPE);(bulk/'image-frozen-policy-v1.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,(r.stdout,r.stderr)
receipt={'passed':True,'imageId':image,'platform':'linux/amd64','user':inspect['Config']['User'],'workdir':inspect['Config']['WorkingDir'],'defaultCommand':inspect['Config']['Cmd'],'expectedApplicationFiles':expected,'packageVersions':observed['packages'],'pinnedDependencyCount':len(lock),'inventoryCodeSha256':hashlib.sha256(inventory.encode()).hexdigest(),'policyCodeSha256':hashlib.sha256(code.encode()).hexdigest(),'frozenCasesSha256':hashlib.sha256(cases.read_bytes()).hexdigest(),'rootReadonly':True,'externalNetwork':False,'cloudOperations':False,'scope':'Clean delivered runtime image inventory/entry imports and pure frozen policy cases; not connected-system/native Google acceptance'}
with(bulk/'image-check-v1.json').open('x')as target:target.write(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'passed':True,'imageId':image,'applicationFiles':len(expected),'pinnedDependencies':len(lock),'uid':observed['uid'],'frozenPolicyPassed':True}))
