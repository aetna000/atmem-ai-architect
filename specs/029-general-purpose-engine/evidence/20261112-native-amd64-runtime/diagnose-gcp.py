"""Read failures immediately from two unchanged generated tests; not a full-suite qualification."""
from pathlib import Path
import argparse,dataclasses,hashlib,json,sys
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--full",action="store_true");args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker
from server.validation_jobs import registered_validators
code=r'''
import json,pathlib,sys,traceback,unittest
sys.path.insert(0,'/work/source')
def resources(label):
 values={}
 for name in ['memory.events','memory.current','memory.max','memory.stat','pids.events','pids.current','pids.max','cpu.stat','cpu.max']:
  try:values[name]=pathlib.Path('/sys/fs/cgroup',name).read_text()
  except OSError:values[name]='unobserved'
 print('RESOURCE_OBSERVATION',label,json.dumps(values),flush=True)
class Immediate(unittest.TextTestResult):
 def addError(self,test,err):
  super().addError(test,err);print('IMMEDIATE_ERROR',test.id(),flush=True);traceback.print_exception(*err);resources('error')
 def addFailure(self,test,err):
  super().addFailure(test,err);print('IMMEDIATE_FAILURE',test.id(),flush=True);traceback.print_exception(*err);resources('failure')
resources('before')
names=['tests.test_sample_routing.SampleJourneys.test_01_arithmetic_and_unicode_through_real_children','tests.test_sample_routing.SampleJourneys.test_02_strict_input_and_transport_boundaries']
if len(sys.argv)>1 and sys.argv[1]=='full':names=['tests.test_domain','tests.test_runtime_prerequisites','tests.test_sample_routing']
suite=unittest.defaultTestLoader.loadTestsFromNames(names)
assert suite.countTestCases()==(15 if len(names)==3 else 2)
result=unittest.TextTestRunner(verbosity=2,resultclass=Immediate).run(suite)
resources('after');sys.exit(0 if result.wasSuccessful() and not result.skipped else 1)
'''
entry=json.loads((ROOT/'.local/external-artifacts/native-gcp-water/v1/validators-observed.json').read_text())[0];entry.pop('runtimeReceipt');spec=registered_validators([entry])[entry['id']].spec
spec=dataclasses.replace(spec,name='full-gcp-diagnostic' if args.full else 'targeted-gcp-diagnostic',timeout_seconds=300,command=('/usr/local/bin/python3','-I','/opt/atmem/sql_validation.py','-c',code,'full' if args.full else 'targeted'))
content=(ROOT/'.local/external-artifacts/native-gcp-water/v1/native-run/artifact.zip').read_bytes();sha=hashlib.sha256(content).hexdigest();assert sha=='69bdacf7d6813bfdd977b007abe7c94d8c3308cb2e09f9fd09c6cb39cf61031d'
result=DockerValidationWorker('unix:///Users/javadtaghia/.avm/c/amd64/validator.sock').run(content,sha,spec)
with (ROOT/'.local/external-artifacts/native-amd64-runtime/v1'/('full-diagnostic-v1.json' if args.full else 'targeted-diagnostic-v1.json')).open('x') as target:target.write(json.dumps(result,indent=2)+'\n')
print(json.dumps({key:value for key,value in result.items()if key not in {'command','output'}}))
