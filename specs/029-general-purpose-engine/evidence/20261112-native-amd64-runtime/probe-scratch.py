"""Counterfactual native extension loading with unchanged default isolation."""
import hashlib,io,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker,ValidationSpec
out=ROOT/'.local/external-artifacts/native-amd64-runtime/v1/scratch-probe-v1';out.mkdir(parents=True,exist_ok=False)
entry=next(x for x in json.loads((ROOT/'.local/external-artifacts/native-gcp-water/v1/validators-observed.json').read_text())if x['id']=='python-sql-gcp-tests')
code=r'''
import errno,importlib,importlib.util,json,os,pathlib,shutil,socket,sys,tempfile
enabled=json.loads(sys.argv[1]);assert os.getuid()==65532
assert os.statvfs('/tmp').f_flag&os.ST_NOEXEC
assert os.statvfs('/work/source').f_flag&os.ST_NOEXEC
assert not pathlib.Path('/var/run/docker.sock').exists()
assert {p.name for p in pathlib.Path('/sys/class/net').iterdir()}=={'lo'}
try:os.setuid(0)
except PermissionError:pass
else:raise AssertionError('Regained root')
try:pathlib.Path('/etc/scratch-probe').write_text('MUTATED')
except OSError as error:assert error.errno in {errno.EACCES,errno.EROFS}
else:raise AssertionError('Image root writable')
status=pathlib.Path('/proc/self/status').read_text();assert 'CapEff:\t0000000000000000'in status and 'NoNewPrivs:\t1'in status
rows=[]
for domain,name in [('museum','_csv'),('weather','_json')]:
 module=importlib.import_module(name);original=pathlib.Path(module.__file__)
 with tempfile.TemporaryDirectory(prefix=domain+'-')as folder:
  target=pathlib.Path(folder)/original.name;shutil.copyfile(original,target)
  assert bool(os.statvfs(folder).f_flag&os.ST_NOEXEC)==(not enabled)
  try:
   spec=importlib.util.spec_from_file_location(name,target);loaded=importlib.util.module_from_spec(spec);spec.loader.exec_module(loaded)
  except ImportError:
   assert not enabled;rows.append({'domain':domain,'extension':name,'loaded':False})
  else:
   assert enabled and pathlib.Path(loaded.__file__).resolve()==target.resolve()
   if name=='_csv':assert list(loaded.reader(['station,reading']))==[['station','reading']]
   else:assert loaded.scanstring('"clear"',1)[0]=='clear'
   rows.append({'domain':domain,'extension':name,'loaded':True})
assert len(rows)==2
if enabled:assert os.environ['ATMEM_TEST_DEPENDENCY_ROOT']=='/dependencies'
print(json.dumps({'passed':True,'executableScratch':enabled,'cases':rows,'sourceAndOrdinaryTmpNoexec':True,'rootReadonlyUidCapabilitiesAndNetworkDenials':True}))
'''
stream=io.BytesIO()
with zipfile.ZipFile(stream,'w'):pass
archive=stream.getvalue();worker=DockerValidationWorker('unix:///Users/javadtaghia/.avm/c/amd64/validator.sock')
for enabled in [False,True]:
    spec=ValidationSpec('native-extension-probe',entry['image'],('/usr/local/bin/python3','-I','-c',code,json.dumps(enabled)),platform='linux/amd64',timeout_seconds=30,executable_scratch=enabled)
    result=worker.run(archive,hashlib.sha256(archive).hexdigest(),spec);(out/('enabled.json'if enabled else'default.json')).write_text(json.dumps(result,indent=2)+'\n');assert result['status']=='passed',result
    print('Verified extension loading and denials; executable scratch',enabled,flush=True)
