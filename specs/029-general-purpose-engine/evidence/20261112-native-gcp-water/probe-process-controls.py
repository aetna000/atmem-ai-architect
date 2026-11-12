"""Observe process controls independently of client source and ISA syscall numbers.

An additional RET_ALLOW filter can only intersect existing outer controls. It
does not disable them. No native syscall-number fallback or policy bypass runs.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
code='''import ctypes,json,os,platform
class Filter(ctypes.Structure):_fields_=[('code',ctypes.c_ushort),('jt',ctypes.c_ubyte),('jf',ctypes.c_ubyte),('k',ctypes.c_uint32)]
class Program(ctypes.Structure):_fields_=[('len',ctypes.c_ushort),('filter',ctypes.POINTER(Filter))]
libc=ctypes.CDLL(None,use_errno=True);libc.prctl.argtypes=[ctypes.c_int,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong];libc.prctl.restype=ctypes.c_int
ctypes.set_errno(0);nnp=libc.prctl(38,1,0,0,0);nnp_errno=ctypes.get_errno()
filters=(Filter*1)(Filter(6,0,0,0x7fff0000));program=Program(1,filters)
ctypes.set_errno(0);status=libc.prctl(22,2,ctypes.addressof(program),0,0);error=ctypes.get_errno()
print(json.dumps({'machine':platform.machine(),'python':platform.python_version(),'uid':os.getuid(),'layout':{'instructionBytes':ctypes.sizeof(Filter),'programBytes':ctypes.sizeof(Program),'pointerOffset':Program.filter.offset},'noNewPrivileges':{'return':nnp,'errno':nnp_errno},'allowOnlyAdditionalFilter':{'return':status,'errno':error},'cloudOperations':False}))
'''
endpoint='unix:///Users/javadtaghia/.avm/c/engine/docker.sock';rows=[]
for name,image,arch,python in [('gcp-amd64','sha256:bafc5723ac59b025d42337e4c965e6d7b89a07da3d18b49a9384cfa70274f8e2','linux/amd64','/usr/local/bin/python3'),('native-arm64','sha256:df7f71a8588253403dfa833c5c4aacc95ca340204a88d5483edd58131c7f1128','linux/arm64','/usr/bin/python3')]:
    result=subprocess.run(['docker','--host',endpoint,'run','--rm','--pull','never','--platform',arch,'--user','65532:65532','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','32','--memory','128m','--cpus','1','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777','--entrypoint',python,image,'-I','-c',code],capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
    rows.append({'name':name,'image':image,'platform':arch,'observed':json.loads(result.stdout)})
assert rows[0]['observed']['allowOnlyAdditionalFilter']=={'return':-1,'errno':22}
assert rows[1]['observed']['allowOnlyAdditionalFilter']=={'return':0,'errno':0}
daemon_arch=subprocess.check_output(['docker','--host',endpoint,'info','--format','{{.Architecture}}'],text=True).strip()
receipt={'rows':rows,'daemonArchitecture':daemon_arch,'sameProbeAndOuterPolicy':True,'probeSha256':hashlib.sha256(code.encode()).hexdigest(),'clientSourceExecuted':False,
    'comparisonLimit':'Different Python/image builds, identical measured64-bit ctypes layout and allow-only libc prctl program. Current context capability only; no full native-AMD64-kernel test or universal emulator diagnosis.','cloudOperations':False}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
