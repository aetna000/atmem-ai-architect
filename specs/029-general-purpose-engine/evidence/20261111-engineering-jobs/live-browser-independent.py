"""Independent behavior on downloaded immutable code, with no inference/host execution."""
import asyncio
import hashlib
import json
from pathlib import Path
import stat
import sys
import tempfile
import zipfile
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from server.codex_worker_policy import CodexWorkerClient,PROFILE
OUT=ROOT/'specs/029-general-purpose-engine/evidence/20261111-engineering-jobs/live-browser-work'
ORACLE='''const assert=require('node:assert/strict');
const {normalize,normalizeBatch}=require('./inventory-normalizer.cjs');
let checks=0;
for(const [value,unit,expected] of [[0,'g',0],[1,'g',1],[2,'kg',2000],[0.25,'kg',250]]){assert.equal(normalize(value,unit),expected);checks++;}
for(const [value,unit] of [[true,'g'],['2','g'],[-1,'g'],[NaN,'g'],[Infinity,'kg'],[1,'KG'],[1,'lb']]){assert.throws(()=>normalize(value,unit),TypeError);checks++;}
assert.deepEqual(normalizeBatch([]),[]);checks++;
assert.deepEqual(normalizeBatch([{value:1,unit:'kg'},{value:3,unit:'g'}]),[1000,3]);checks++;
assert.equal(normalizeBatch(Array.from({length:100},()=>({value:1,unit:'g'}))).length,100);checks++;
assert.throws(()=>normalizeBatch(Array.from({length:101},()=>({value:1,unit:'g'}))),RangeError);checks++;
console.log('INDEPENDENT_BROWSER_ARTIFACT_ORACLE_PASSED',checks);
'''


async def main():
    manifest=json.loads((OUT/'manifest.json').read_text())
    archive=OUT/'generated-package.zip'
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['sha256']
    config=json.loads((ROOT/'.local/engineering-preview/operator-toolchain.json').read_text())
    receipt={'passed':False,'artifactSha256':manifest['sha256'],'inferenceTurns':0,'cloudOperations':False,
        'boundary':'Independent post-generation Node behavioral oracle on copied digest-bound immutable download under the same qualified offline native command policy. No source repairs, cloud operations or whole-system claim.'}
    with tempfile.TemporaryDirectory(prefix='atm-browser-oracle-',dir='/tmp') as folder:
        workspace=Path(folder).resolve()
        with zipfile.ZipFile(archive) as package:
            for info in package.infolist():
                path=Path(info.filename)
                assert not path.is_absolute() and '..' not in path.parts
                assert not stat.S_ISLNK(info.external_attr>>16)
            assert sum(info.file_size for info in package.infolist())<=64_000_000
            package.extractall(workspace)
        worker=CodexWorkerClient(workspace,read_roots=config['readRoots'])
        try:
            await worker.start();await worker.verify_worker_tools()
            result=await worker.request('command/exec',{'command':[config['tools']['node'],'-e',ORACLE],
                'cwd':str(workspace),'permissionProfile':PROFILE,'env':{'TMPDIR':str(workspace/'.worker-tmp'),'OPENSSL_CONF':'/dev/null'},
                'timeoutMs':30000},timeout=40)
            receipt.update(result=result,passed=result['exitCode']==0 and 'INDEPENDENT_BROWSER_ARTIFACT_ORACLE_PASSED 15' in result['stdout'])
        finally:
            await worker.close()
            (OUT/'independent-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    assert receipt['passed'],receipt
    print(json.dumps(receipt,indent=2))

(OUT/'independent-oracle.cjs').write_text(ORACLE)
asyncio.run(main())
