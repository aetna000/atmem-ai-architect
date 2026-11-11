"""Observe an operator-selected cached runtime without executing client source.

No pulls, installations, cloud clients or accounts. The receipt is operator-pinned
before registration; observed versions are distinct from application acceptance.
"""
import argparse,dataclasses,datetime,hashlib,io,json,re,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker
from server.validation_jobs import registered_validators
from server.runtime_evidence import runtime_binding,digest
PYTHON=r'''
import importlib.metadata,json,os,sys
packages,services=json.loads(sys.argv[1]);versions={}
for name in packages:
 try:versions[name]=importlib.metadata.version(name)
 except importlib.metadata.PackageNotFoundError:versions[name]=None
operations={}
if services:
 try:
  import botocore.session
 except ModuleNotFoundError:
  operations={name:None for name in services}
 else:
  session=botocore.session.get_session()
  for name in services:operations[name]=sorted(session.get_service_model(name).operation_names)
if 'ATMEM_TEST_POSTGRES_DSN' in os.environ:
 import psycopg
 with psycopg.connect(os.environ['ATMEM_TEST_POSTGRES_DSN']) as connection:
  versions['postgresql-server']=connection.execute('SHOW server_version').fetchone()[0].split()[0]
print(json.dumps({'kind':'python','executableVersion':sys.version.split()[0],'packages':versions,'serviceOperations':operations}))
'''
NODE=r'''
import fs from 'node:fs';import path from 'node:path';import {pathToFileURL} from 'node:url';
const result={kind:'node',executableVersion:process.versions.node,packages:{},serviceOperations:{},browserVersion:null};
if(process.env.ATMEM_PLAYWRIGHT_MODULE){
 const module=process.env.ATMEM_PLAYWRIGHT_MODULE;
 result.packages['playwright-core']=JSON.parse(fs.readFileSync(path.join(path.dirname(module),'package.json'),'utf8')).version;
 const {chromium}=await import(pathToFileURL(module).href),browser=await chromium.launch({headless:true,chromiumSandbox:true});
 try{result.browserVersion=browser.version();}finally{await browser.close();}
}
console.log(JSON.stringify(result));
'''
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--validators',type=Path,required=True);parser.add_argument('--validator',required=True);parser.add_argument('--kind',choices=['python','node'],required=True)
parser.add_argument('--python-package',action='append',default=[]);parser.add_argument('--python-service',action='append',default=[])
parser.add_argument('--profiles',type=Path);parser.add_argument('--endpoint',required=True);parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
if any(not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}',name) for name in [*args.python_package,*args.python_service]) or len(set(args.python_package))!=len(args.python_package) or len(set(args.python_service))!=len(args.python_service) or len(args.python_package)>32 or len(args.python_service)>16:parser.error('Use unique bounded installed package/service names')
entries=json.loads(args.validators.read_text());entry=next((item for item in entries if item['id']==args.validator),None)
if entry is None:parser.error('Choose an operator-registered validator')
entry={key:value for key,value in entry.items()if key!='runtimeReceipt'};registered=registered_validators([entry])[args.validator];spec=registered.spec
command=(spec.command[0],'-I','-c',PYTHON,json.dumps([args.python_package,args.python_service])) if args.kind=='python' else (spec.command[0],'--input-type=module','-e',NODE)
if spec.isolation_profile=='postgresql-local-v1':
 if args.kind!='python' or len(args.python_package)>31 or 'postgresql-server' in args.python_package:parser.error('SQL observation requires Python and room for the actual server version')
 command=(spec.command[0],'-I','/opt/atmem/sql_validation.py','-c',PYTHON,json.dumps([args.python_package,args.python_service]))
probe=dataclasses.replace(spec,name='runtime-observation',command=command,timeout_seconds=30)
worker=DockerValidationWorker(args.endpoint,isolation_profiles=json.loads(args.profiles.read_text())if args.profiles else None)
data=io.BytesIO()
with zipfile.ZipFile(data,'w'):pass
content=data.getvalue();result=worker.run(content,hashlib.sha256(content).hexdigest(),probe)
receipt={'format':'atmem.runtime-observation','version':1,'passed':False,'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runtime':runtime_binding(spec),'runtimeSha256':digest(runtime_binding(spec)),'workerPolicySha256':worker.policy_digest,'workerIdentitySha256':worker.identity_digest,'observerSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'probe':result,'cloudOperations':False,'scope':'Empty source archive in the registered immutable local image/profile. No application code, cloud client, account or network dependency is used. Null package versions mean distribution metadata unavailable; not proof that importing a module is impossible. Service operations describe the installed botocore model only, not account/API availability.'}
if result['status']=='passed':
 try:receipt['observed']=json.loads(result['output']);receipt['passed']=True
 except (ValueError,TypeError):pass
output=args.output.resolve();output.parent.mkdir(parents=True,exist_ok=True)
with output.open('x')as target:target.write(json.dumps(receipt,indent=2)+'\n')
if not receipt['passed']:raise SystemExit('Runtime observation failed; failed receipt retained')
print(json.dumps({'passed':True,'receiptSha256':hashlib.sha256(output.read_bytes()).hexdigest(),'observed':receipt['observed']},indent=2))
