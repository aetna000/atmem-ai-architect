"""Real command-worker read/copy/import transfer and denied-host-write canaries."""
import argparse,asyncio,hashlib,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.codex_worker_policy import CodexWorkerClient,PROFILE
from server.dependency_mirror import inspect_mirror
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--mirror',type=Path,required=True);parser.add_argument('--tools',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()


async def main():
 mirror=args.mirror.resolve();checked=inspect_mirror(mirror);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False);config=json.loads(args.tools.read_text());results=[]
 with tempfile.TemporaryDirectory(prefix='atd-',dir='/tmp')as temp,tempfile.TemporaryDirectory(prefix='atd-foreign-',dir='/tmp')as foreign:
  workspace=Path(temp).resolve()/'work';workspace.mkdir();(workspace/'.tools').mkdir();(workspace/'.tools/dependencyMirror').symlink_to(mirror,target_is_directory=True)
  canary=Path(foreign).resolve()/'synthetic-private.txt';canary.write_text('SYNTHETIC HOST-ONLY CANARY')
  worker=CodexWorkerClient(workspace,read_roots=[*config['readRoots'],str(mirror)])
  try:
   await worker.start();await worker.verify_worker_tools()
   code=r'''
import hashlib,json,pathlib,shutil,sys,zipfile
mirror=pathlib.Path('.tools/dependencyMirror');catalog=json.loads((mirror/'index.json').read_text())
assert hashlib.sha256((mirror/'index.json').read_bytes()).hexdigest()==sys.argv[1]
entry=next(item for item in catalog['artifacts']if item['name']=='jmespath');content=(mirror/entry['file']).read_bytes();assert hashlib.sha256(content).hexdigest()==entry['sha256']
copied=pathlib.Path('public-dependencies');copied.mkdir();(copied/entry['file']).write_bytes(content)
library=pathlib.Path('.worker-tmp/query-library');library.mkdir()
with zipfile.ZipFile(copied/entry['file'])as archive:
 assert all(not pathlib.PurePosixPath(item.filename).is_absolute() and '..' not in pathlib.PurePosixPath(item.filename).parts for item in archive.infolist());archive.extractall(library)
sys.path.insert(0,str(library.resolve()));import jmespath
assert jmespath.__version__=='1.0.1';assert jmespath.search('rooms[?celsius > `30`].name',{'rooms':[{'name':'North','celsius':21},{'name':'West','celsius':34}]})==['West']
try:pathlib.Path(sys.argv[2]).read_bytes()
except PermissionError:pass
else:raise AssertionError('Unregistered foreign host file became readable')
try:(mirror/'atmem-write-denial-canary').write_text('SYNTHETIC ONLY')
except PermissionError:pass
else:raise AssertionError('Approved mirror became writable')
print('STANDALONE_DEPENDENCY_TRANSFER_PASSED')
'''
   result=await worker.request('command/exec',{'command':[config['tools']['python'],'-I','-c',code,checked['sha256'],str(canary)],'cwd':str(workspace),'permissionProfile':PROFILE,'env':{'TMPDIR':str(workspace/'.worker-tmp'),'OPENSSL_CONF':'/dev/null'},'timeoutMs':30000,'outputBytesCap':20000},timeout=40);results.append(result)
  finally:
   await worker.close()
   # Only remove our named synthetic canary if an unexpected policy escape occurred.
   outside=mirror/'atmem-write-denial-canary'
   if outside.exists():outside.unlink()
 receipt={'passed':len(results)==1 and results[0]['exitCode']==0 and 'STANDALONE_DEPENDENCY_TRANSFER_PASSED' in results[0]['stdout'],'catalogSha256':checked['sha256'],'checks':results,'inferenceTurns':0,'cloudOperations':False,'scope':'Actual native command sandbox with one explicit public artifact read root: hash/read/copy and standalone climate-query library execution, blocked unregistered synthetic host file and blocked mirror write. Different non-cloud composition from SDK service use; not whole-project or hosted tenant isolation acceptance.'}
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');assert receipt['passed'],receipt;print('Passed registered artifact read/copy/non-cloud use and denial boundaries')


asyncio.run(main())
