"""Exercise delivered processing children and same-UID credential/supervisor denials."""
from pathlib import Path
import argparse,hashlib,json,subprocess,uuid
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--attempt",choices=["v1","v2"],default="v2");args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[4];bulk=ROOT/'.local/external-artifacts/native-amd64-runtime/v1/receiving-build-v1';image=(bulk/'image-id.txt').read_text().strip();cases=ROOT/'specs/029-general-purpose-engine/evidence/20261112-native-gcp-water/requirements-cases-v1.json'
code=r'''
import json,os,pathlib,secrets,sys,time
sys.path.insert(0,'/app')
from workflow_process_stage import ProcessStage
from workflow_errors import PermanentWork,TemporaryWork,ExternalOutcomeUnknown
from sample_isolation import supervisor
cases=json.loads(sys.stdin.buffer.read(1000000));supervisor();assert os.getuid()==10001
root=pathlib.Path('/runtime');secret=root/'publication-secret';sql=root/'database-secret';secret.write_text(secrets.token_hex(32));sql.write_text(secrets.token_hex(32));secret.chmod(0o600);sql.chmod(0o600)
os.environ['SQL_PRIVATE_MARKER']=sql.read_text();os.environ['PUBLISH_PRIVATE_MARKER']=secret.read_text()
with secret.open('rb')as held:
 probes={'publication':str(secret),'sql':str(sql),'supervisorEnvironment':f'/proc/{os.getpid()}/environ','supervisorMemory':f'/proc/{os.getpid()}/mem','supervisorDescriptor':f'/proc/{os.getpid()}/fd/{held.fileno()}'}
 assert pathlib.Path(probes['supervisorDescriptor']).read_bytes()==secret.read_bytes()
 stage=ProcessStage([sys.executable,'-I','/app/sample_child.py','probe'],kind='extract',timeout_seconds=10,environment={})
 observed=stage({'source_ref':cases['validSourceCases'][0]['source']},probes=probes)
 assert observed['uid']==10001 and all(observed['blocked'].values()),observed
 assert set(observed['environment'])<={'LC_CTYPE'} and observed['environment'].get('LC_CTYPE','C.UTF-8')=='C.UTF-8'
 assert not any(value in observed['environment'].values()for value in [secret.read_text(),sql.read_text()])
process=ProcessStage([sys.executable,'-I','/app/sample_child.py','process'],kind='extract',timeout_seconds=10,environment={})
for case in cases['validSourceCases']:assert process({'source_ref':case['source']})==case['expectedResult']
for case in cases['invalidSourceCases']:
 try:process({'source_ref':case['source']})
 except PermanentWork:pass
 else:raise AssertionError('Invalid source accepted')
deadlines=[]
for kind,error in [('extract',TemporaryWork),('dispatch',ExternalOutcomeUnknown)]:
 stage=ProcessStage([sys.executable,'-I','-c','import time;time.sleep(30)'],kind=kind,timeout_seconds=.2,environment={})
 started=time.monotonic()
 try:stage({'source_ref':cases['validSourceCases'][0]['source']})
 except error:elapsed=time.monotonic()-started;assert elapsed<3;deadlines.append({'kind':kind,'elapsedSeconds':elapsed})
 else:raise AssertionError('Stage deadline not enforced')
print(json.dumps({'passed':True,'uid':os.getuid(),'sameUidDenials':observed['blocked'],'childEnvironmentCredentialsAbsent':True,'interpreterLocale':observed['environment'].get('LC_CTYPE'),'validProcessingCases':len(cases['validSourceCases']),'invalidProcessingCases':len(cases['invalidSourceCases']),'deadlines':deadlines,'cloudOperations':False}))
'''
assert not (bulk/('child-check-'+args.attempt+'.json')).exists() and not (bulk/('child-check-output-'+args.attempt+'.log')).exists()
name='atmem-receiving-child-'+uuid.uuid4().hex;endpoint='unix:///Users/javadtaghia/.avm/c/amd64/validator.sock'
command=['docker','--host',endpoint,'run','--pull','never','--rm','--name',name,'--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','64','--memory','256m','--cpus','1','--tmpfs','/runtime:rw,noexec,nosuid,nodev,size=2m,uid=10001,gid=10001,mode=0700','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=8m,uid=10001,gid=10001,mode=0700','--entrypoint','/usr/local/bin/python3','-i',image,'-I','-c',code]
try:
 result=subprocess.run(command,input=cases.read_bytes(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 (bulk/('child-check-output-'+args.attempt+'.log')).write_bytes(result.stdout+result.stderr);assert result.returncode==0,(result.stdout,result.stderr)
 receipt={'passed':True,'imageId':image,'codeSha256':hashlib.sha256(code.encode()).hexdigest(),'frozenCasesSha256':hashlib.sha256(cases.read_bytes()).hexdigest(),'observed':json.loads(result.stdout),'boundary':'Actual processing child IPC/isolation in clean delivered image; not HTTP/SQL/queue/TLS full-system or native account acceptance'}
 with(bulk/('child-check-'+args.attempt+'.json')).open('x')as target:target.write(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(receipt))
finally:
 subprocess.run(['docker','--host',endpoint,'rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
