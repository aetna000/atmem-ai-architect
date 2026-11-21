"""Trusted empty-source probe fragment; observations never grant capabilities.

Only libc prctl is used, not ISA-specific syscall numbers. RET_ALLOW stacks onto
the existing outer policy; it cannot remove that policy or restore privileges.
"""
PYTHON_PROCESS_CONTROLS = r'''
import ctypes,hashlib,platform,uuid
from pathlib import Path
class Filter(ctypes.Structure):
 _fields_=[('code',ctypes.c_ushort),('jt',ctypes.c_ubyte),('jf',ctypes.c_ubyte),('k',ctypes.c_uint32)]
class Program(ctypes.Structure):
 _fields_=[('len',ctypes.c_ushort),('filter',ctypes.POINTER(Filter))]
libc=ctypes.CDLL(None,use_errno=True)
libc.prctl.argtypes=[ctypes.c_int,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong]
libc.prctl.restype=ctypes.c_int
def observe_prctl(option,value):
 ctypes.set_errno(0);code=libc.prctl(option,value,0,0,0);error=ctypes.get_errno()
 return {'supported':code==0 and error==0,'returnCode':code,'errno':error}
controls={'noNewPrivileges':observe_prctl(38,1)}
filters=(Filter*1)(Filter(6,0,0,0x7fff0000));program=Program(1,filters)
# Do not try the dependent operation without its prerequisite. Null is unknown.
controls['seccompFilter']=None
if controls['noNewPrivileges']['supported']:
 ctypes.set_errno(0);code=libc.prctl(22,2,ctypes.addressof(program),0,0);error=ctypes.get_errno()
 controls['seccompFilter']={'supported':code==0 and error==0,'returnCode':code,'errno':error}
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
if str(uuid.UUID(boot))!=boot:raise ValueError('Unrecognized kernel boot identity')
result['processControls']=controls
result['executionContext']={'processMachine':platform.machine(),'kernelRelease':platform.release(),
 'kernelBootSha256':hashlib.sha256(boot.encode()).hexdigest(),'uid':os.getuid()}
'''
