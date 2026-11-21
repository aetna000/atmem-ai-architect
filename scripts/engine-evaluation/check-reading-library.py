"""Independent contract oracle for the native orchard transfer fixture only."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker,ValidationSpec
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--artifact',type=Path,required=True);parser.add_argument('--unit',choices=['cm','m'],required=True)
parser.add_argument('--endpoint',required=True);parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();archive=args.artifact.read_bytes();digest=hashlib.sha256(archive).hexdigest()
oracle=r'''
const assert=require('node:assert/strict'),m=require('/work/source/readings.cjs');let n=0;
assert.equal(m.unit,UNIT);n++;
for(const value of [0,0.001,0.5,12.25,2000,Number.MAX_VALUE,-0]){
 const actual=m.normalize(value),expected=value*FACTOR;
 assert.equal(typeof actual,'number');assert.ok(Number.isFinite(actual));
 assert.ok(Math.abs(actual-expected)<=Math.max(1,Math.abs(expected))*1e-12);n++;
}
for(const value of [true,false,'1','',null,undefined,{},[],NaN,Infinity,-Infinity,-1]){assert.throws(()=>m.normalize(value),TypeError);n++;}
console.log('Independent assertions executed: '+n);
'''.replace('UNIT',json.dumps(args.unit)).replace('FACTOR','0.1' if args.unit=='cm' else '0.001')
spec=ValidationSpec('reading-contract-independent','sha256:df7f71a8588253403dfa833c5c4aacc95ca340204a88d5483edd58131c7f1128',
    ('/usr/bin/node','-e',oracle),platform='linux/arm64',bootstrap_python='/usr/bin/python3',timeout_seconds=60)
result=DockerValidationWorker(args.endpoint).run(archive,digest,spec)
result['independentAssertions']=20 if result['status']=='passed' and 'Independent assertions executed: 20\n' in result['output'] else None
result['oracleBoundary']='Evaluator-authored module API/units/finite-domain/denial assertions in a real isolated Linux Node runtime. Relative tolerance1e-12 accommodates floating point representation; no graph/service/cloud/system acceptance inferred.'
args.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'independentAssertions':result['independentAssertions']}))
