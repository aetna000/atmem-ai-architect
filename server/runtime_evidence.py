"""Pinned operator-observed runtime facts, separate from application acceptance."""
import hashlib,json,os,re
from datetime import datetime
from pathlib import Path
from server.process_control_observation import PYTHON_PROCESS_CONTROLS


def runtime_binding(spec):
    return {'imageId':spec.image,'platform':spec.platform,'executable':spec.command[0],
        'bootstrapPython':spec.bootstrap_python,'isolationProfile':spec.isolation_profile,
        'environment':dict(spec.runtime_environment),**({'executableScratch':True}if spec.executable_scratch else {})}


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


class RuntimeEvidence:
    def __init__(self,encoded):self._encoded=encoded

    def public(self):return json.loads(self._encoded)

    @classmethod
    def load(cls,reference,spec):
        if not isinstance(reference,dict) or set(reference)!={'path','sha256'} or not isinstance(reference['path'],str) or not Path(reference['path']).is_absolute() or not isinstance(reference.get('sha256'),str) or not re.fullmatch(r'[a-f0-9]{64}',reference['sha256']):
            raise ValueError('Register an absolute pinned operator runtime receipt')
        descriptor=os.open(reference['path'],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        try:
            import stat
            info=os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_size>64000:raise ValueError('Runtime evidence must be a bounded regular receipt')
            with os.fdopen(descriptor,'rb',closefd=False)as source:content=source.read(64001)
        finally:os.close(descriptor)
        if len(content)>64000 or hashlib.sha256(content).hexdigest()!=reference['sha256']:raise ValueError('Runtime receipt bytes differ from their operator pin')
        receipt=json.loads(content)
        binding=runtime_binding(spec)
        if not isinstance(receipt,dict) or receipt.get('format')!='atmem.runtime-observation' or type(receipt.get('version')) is not int or receipt['version'] not in {1,2} or receipt.get('passed') is not True or receipt.get('runtime')!=binding or receipt.get('runtimeSha256')!=digest(binding):
            raise ValueError('Runtime observation does not match the registered immutable runtime')
        if datetime.fromisoformat(receipt.get('observedAt','')).tzinfo is None or any(not isinstance(receipt.get(key),str) or not re.fullmatch(r'[a-f0-9]{64}',receipt[key]) for key in ['observerSha256','workerPolicySha256','workerIdentitySha256']):raise ValueError('Runtime observation requires dated observer/worker provenance')
        probe=receipt.get('probe')
        if not isinstance(probe,dict) or probe.get('status')!='passed' or type(probe.get('exitCode')) is not int or probe['exitCode']!=0 or probe.get('outputTruncated') is not False or probe.get('artifactSha256')!=hashlib.sha256(b'PK\x05\x06'+b'\0'*18).hexdigest() or any(probe.get(key)!=expected for key,expected in [('imageId',spec.image),('platform',spec.platform),('isolationProfile',spec.isolation_profile),('runtimeEnvironment',dict(spec.runtime_environment))]) or not isinstance(probe.get('command'),list) or probe['command'][:1]!=[spec.command[0]]:
            raise ValueError('Runtime evidence needs a successful empty-source probe of the same runtime')
        observed=receipt.get('observed')
        if probe.get('executableScratch',False)is not spec.executable_scratch:raise ValueError('Runtime observation does not match executable scratch capability')
        if not isinstance(probe.get('output'),str) or json.loads(probe['output'])!=observed:raise ValueError('Observed facts differ from the complete probe output')
        version=receipt['version']
        extra={'processControls','executionContext'} if version==2 else set()
        if not isinstance(observed,dict) or set(observed)-({'kind','executableVersion','packages','serviceOperations','browserVersion'}|extra) or observed.get('kind') not in {'python','node'}:
            raise ValueError('Unrecognized observed runtime shape')
        def text(value):return isinstance(value,str) and bool(value) and len(value)<=150 and not any(ord(c)<32 for c in value)
        if not text(observed.get('executableVersion')):raise ValueError('An observed executable version is required')
        packages=observed.get('packages',{})
        if not isinstance(packages,dict) or len(packages)>32 or any(not text(key) or (value is not None and not text(value)) for key,value in packages.items()):raise ValueError('Runtime package observations must be bounded versions or explicit unknowns')
        services=observed.get('serviceOperations',{})
        if not isinstance(services,dict) or len(services)>16:raise ValueError('Bound service capability observations')
        for name,operations in services.items():
            if not text(name) or (operations is not None and (not isinstance(operations,list) or len(operations)>2000 or any(not text(operation) for operation in operations) or len(set(operations))!=len(operations))):raise ValueError('Unrecognized service capability observations')
        if 'browserVersion' in observed and observed['browserVersion'] is not None and not text(observed['browserVersion']):raise ValueError('Invalid browser version observation')
        if version==2:validate_process_observation(receipt,observed,probe,text)
        result={'receiptSha256':reference['sha256'],'runtimeSha256':digest(binding),'observed':observed,
            'observedAt':receipt['observedAt'],'evidenceLevel':'operator_pinned_local_runtime_observation','scope':'Observed immutable image runtime only; artifact-vendored dependencies can differ. Null package versions mean unobserved distribution metadata, not proof an import is impossible. Null service operations are unknown; an actual operation list describes only the installed SDK model. Not application, account, cloud or requirement acceptance.'}
        if version==2:
            result.update(executionContextSha256=receipt['executionContextSha256'],processControlProbeSha256=receipt['processControlProbeSha256'])
            result['scope']=result['scope'].replace('Observed immutable image runtime only;', 'Observed immutable image metadata and the last recorded execution context;')
            result['scope']+=' Process controls describe only the last observed execution context, not an image-only capability or current availability guarantee. Reobserve after worker, kernel, boot or policy changes. Null process controls are unobserved, not unsupported. Observation never grants permissions or changes safeguards.'
        return cls(json.dumps(result,ensure_ascii=False,allow_nan=False))


def validate_process_observation(receipt,observed,probe,text):
    """Validate an opt-in context snapshot; do not turn it into authorization."""
    expected=hashlib.sha256(PYTHON_PROCESS_CONTROLS.encode()).hexdigest()
    if observed['kind']!='python' or receipt.get('processControlProbeSha256')!=expected or not any(isinstance(argument,str) and PYTHON_PROCESS_CONTROLS in argument for argument in probe['command']):
        raise ValueError('Process-control evidence requires the reviewed Python probe')
    controls=observed.get('processControls')
    if not isinstance(controls,dict) or set(controls)!={'noNewPrivileges','seccompFilter'}:
        raise ValueError('Unrecognized process-control observation')
    def outcome(value):
        if not isinstance(value,dict) or set(value)!={'supported','returnCode','errno'} or type(value['supported']) is not bool or type(value['returnCode']) is not int or type(value['errno']) is not int:
            raise ValueError('Process controls need explicit typed syscall outcomes')
        if (value['supported'] and (value['returnCode']!=0 or value['errno']!=0)) or (not value['supported'] and (value['returnCode']!=-1 or not 1<=value['errno']<=4095)):
            raise ValueError('Inconsistent process-control outcome')
    outcome(controls['noNewPrivileges'])
    if controls['noNewPrivileges']['supported']:outcome(controls['seccompFilter'])
    elif controls['seccompFilter'] is not None:
        raise ValueError('A dependent control without its prerequisite must remain unknown')
    context=observed.get('executionContext')
    if not isinstance(context,dict) or set(context)!={'processMachine','kernelRelease','kernelBootSha256','uid'} or not text(context['processMachine']) or not text(context['kernelRelease']) or type(context['uid']) is not int or not 0<=context['uid']<2**32 or not isinstance(context['kernelBootSha256'],str) or not re.fullmatch(r'[a-f0-9]{64}',context['kernelBootSha256']) or receipt.get('executionContextSha256')!=digest(context):
        raise ValueError('Process-control evidence requires a bound execution context')
