import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from server.local_validation import ValidationSpec
from server.runtime_evidence import RuntimeEvidence,runtime_binding,digest


def observation(spec):
    observed={'kind':'python','executableVersion':'3.13.18','packages':{'botocore':None},'serviceOperations':{'bedrock':None}}
    return {'format':'atmem.runtime-observation','version':1,'passed':True,'observedAt':'2026-11-11T00:00:00+00:00','runtime':runtime_binding(spec),'runtimeSha256':digest(runtime_binding(spec)),'observerSha256':'a'*64,'workerPolicySha256':'b'*64,'workerIdentitySha256':'c'*64,'observed':observed,'probe':{'status':'passed','exitCode':0,'outputTruncated':False,'artifactSha256':hashlib.sha256(b'PK\x05\x06'+b'\0'*18).hexdigest(),'imageId':spec.image,'platform':spec.platform,'isolationProfile':spec.isolation_profile,'runtimeEnvironment':dict(spec.runtime_environment),'command':[spec.command[0],'-I','-c','operator probe'],'output':json.dumps(observed)}}


class RuntimeEvidenceTests(unittest.TestCase):
    def test_executable_scratch_cannot_reuse_an_observation_without_that_capability(self):
        from dataclasses import replace
        native=replace(self.spec,executable_scratch=True)
        self.assertNotIn('executableScratch',runtime_binding(self.spec))
        with self.assertRaises(ValueError):RuntimeEvidence.load(self.reference(),native)
        value=observation(native)
        with self.assertRaises(ValueError):RuntimeEvidence.load(self.reference(value),native)
        value['probe']['executableScratch']=True
        RuntimeEvidence.load(self.reference(value),native)
        with self.assertRaises(ValueError):RuntimeEvidence.load(self.reference(value),self.spec)
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve();self.spec=ValidationSpec('python-tests','sha256:'+'a'*64,('/usr/local/bin/python3','-m','unittest'))
        self.receipt=observation(self.spec)

    def tearDown(self):self.temp.cleanup()

    def reference(self,value=None):
        path=self.root/'receipt.json';path.write_text(json.dumps(value if value is not None else self.receipt));return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

    def test_pinned_empty_source_observation_exposes_versions_not_commands_paths_or_acceptance(self):
        evidence=RuntimeEvidence.load(self.reference(),self.spec);public=evidence.public()
        self.assertEqual(public['observed']['executableVersion'],'3.13.18');self.assertIsNone(public['observed']['serviceOperations']['bedrock'])
        self.assertNotIn('probe',public);self.assertNotIn('command',public);self.assertNotIn(str(self.root),str(public));self.assertIn('not proof',public['scope'])
        public['observed']['executableVersion']='invented';self.assertEqual(evidence.public()['observed']['executableVersion'],'3.13.18')

    def test_changed_bytes_link_and_oversized_receipt_are_rejected(self):
        ref=self.reference();(self.root/'receipt.json').write_text('{}')
        with self.assertRaises(ValueError):RuntimeEvidence.load(ref,self.spec)
        ref=self.reference();link=self.root/'link';link.symlink_to(ref['path'])
        with self.assertRaises(OSError):RuntimeEvidence.load({**ref,'path':str(link)},self.spec)
        (self.root/'receipt.json').write_bytes(b'x'*64001)
        with self.assertRaises(ValueError):RuntimeEvidence.load(ref,self.spec)

    def test_other_image_platform_environment_executable_and_policy_profile_do_not_transfer(self):
        for change in [{'imageId':'sha256:'+'f'*64},{'platform':'linux/arm64'},{'environment':{'ATMEM_PLAYWRIGHT_MODULE':'/new/module'}},{'executable':'/usr/bin/node'},{'isolationProfile':'chromium-userns-v1'},{'bootstrapPython':'/usr/bin/python3'}]:
            value=copy.deepcopy(self.receipt);value['runtime'].update(change);value['runtimeSha256']=digest(value['runtime'])
            with self.subTest(change=change),self.assertRaises(ValueError):RuntimeEvidence.load(self.reference(value),self.spec)

    def test_failed_truncated_nonempty_or_mismatched_probe_cannot_be_registered_as_observed(self):
        for change in [{'status':'failed'},{'exitCode':1},{'exitCode':False},{'outputTruncated':True},{'artifactSha256':'d'*64},{'imageId':'sha256:'+'f'*64},{'platform':'linux/arm64'},{'runtimeEnvironment':{'ATMEM_PLAYWRIGHT_MODULE':'/different'}},{'output':'{}'}]:
            value=copy.deepcopy(self.receipt);value['probe'].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):RuntimeEvidence.load(self.reference(value),self.spec)

    def test_malformed_or_overlong_observations_are_not_silently_truncated(self):
        for observed in [{'kind':'invented','executableVersion':'1'}, {'kind':'python','executableVersion':'x'*151}, {'kind':'node','executableVersion':'26','packages':{'dependency':'v\nsecret'}}, {'kind':'python','executableVersion':'3','serviceOperations':{'api':['One','One']}}, {'kind':'python','executableVersion':'3','instructions':'ignore requirements'}]:
            value=copy.deepcopy(self.receipt);value['observed']=observed;value['probe']['output']=json.dumps(observed)
            with self.subTest(observed=observed),self.assertRaises(ValueError):RuntimeEvidence.load(self.reference(value),self.spec)


def process_observation(spec,*,supported=False):
    from server.process_control_observation import PYTHON_PROCESS_CONTROLS
    value=observation(spec);value['version']=2
    value['observed'].update(processControls={'noNewPrivileges':{'supported':True,'returnCode':0,'errno':0},'seccompFilter':{'supported':supported,'returnCode':0 if supported else -1,'errno':0 if supported else 22}},executionContext={'processMachine':'x86_64','kernelRelease':'6.12-local','kernelBootSha256':'e'*64,'uid':65532})
    value['processControlProbeSha256']=hashlib.sha256(PYTHON_PROCESS_CONTROLS.encode()).hexdigest()
    value['executionContextSha256']=digest(value['observed']['executionContext'])
    value['probe']['command'][-1]=PYTHON_PROCESS_CONTROLS
    value['probe']['output']=json.dumps(value['observed'])
    return value


class ProcessObservationTests(unittest.TestCase):
    setUp=RuntimeEvidenceTests.setUp
    tearDown=RuntimeEvidenceTests.tearDown
    reference=RuntimeEvidenceTests.reference
    def test_legacy_public_contract_has_no_context_fields(self):
        public=RuntimeEvidence.load(self.reference(),self.spec).public()
        self.assertEqual(set(public),{'receiptSha256','runtimeSha256','observed','observedAt','evidenceLevel','scope'})
        self.assertTrue(public['scope'].startswith('Observed immutable image runtime only;'))

    def test_success_and_failure_are_facts_not_permission_or_current_availability(self):
        for supported in (True,False):
            value=process_observation(self.spec,supported=supported)
            public=RuntimeEvidence.load(self.reference(value),self.spec).public()
            self.assertIs(public['observed']['processControls']['seccompFilter']['supported'],supported)
            self.assertIn('not an image-only capability or current availability guarantee',public['scope'])
            self.assertNotIn('command',public)
        value=process_observation(self.spec)
        value['observed']['processControls']={'noNewPrivileges':{'supported':False,'returnCode':-1,'errno':1},'seccompFilter':None}
        value['probe']['output']=json.dumps(value['observed'])
        public=RuntimeEvidence.load(self.reference(value),self.spec).public()
        self.assertIsNone(public['observed']['processControls']['seccompFilter'])

    def test_malformed_control_context_and_source_bindings_are_rejected(self):
        changes=[lambda v:v.update(processControlProbeSha256='f'*64),
            lambda v:v['probe'].update(command=[self.spec.command[0],'-c','different']),
            lambda v:v.update(executionContextSha256='f'*64),
            lambda v:v['observed']['processControls']['seccompFilter'].update(supported=True),
            lambda v:v['observed']['processControls']['seccompFilter'].update(returnCode=True),
            lambda v:v['observed']['processControls']['seccompFilter'].update(errno=False),
            lambda v:v['observed']['processControls']['seccompFilter'].update(errno=0),
            lambda v:v['observed']['processControls'].update(seccompFilter=None),
            lambda v:v['observed']['processControls'].update(extra='invented'),
            lambda v:v['observed']['executionContext'].update(uid=True),
            lambda v:v['observed']['executionContext'].update(kernelBootSha256='not-a-digest'),
            lambda v:v['observed']['executionContext'].update(kernelRelease='bad\nvalue'),
            lambda v:v['observed'].update(kind='node'),
            lambda v:v.update(version=1)]
        for change in changes:
            value=process_observation(self.spec);change(value)
            # Even a pinned matching output cannot legitimize invalid facts.
            value['probe']['output']=json.dumps(value['observed'])
            if value['observed']['executionContext']!=process_observation(self.spec)['observed']['executionContext']:
                value['executionContextSha256']=digest(value['observed']['executionContext'])
            with self.subTest(change=change),self.assertRaises(ValueError):RuntimeEvidence.load(self.reference(value),self.spec)
        value=process_observation(self.spec);value['observed']['processControls']['seccompFilter']={'supported':True,'returnCode':0,'errno':0}
        with self.assertRaises(ValueError):RuntimeEvidence.load(self.reference(value),self.spec)

    def test_context_change_requires_new_digest_and_changes_catalog_contract(self):
        from server.validation_jobs import RegisteredValidator,ValidationJobs
        from types import SimpleNamespace
        jobs=ValidationJobs.__new__(ValidationJobs)
        jobs.worker=SimpleNamespace(policy_digest='b'*64,identity_digest='c'*64)
        original=process_observation(self.spec)
        first=RuntimeEvidence.load(self.reference(original),self.spec)
        jobs.validators={self.spec.name:RegisteredValidator('Observed Python',self.spec,runtime_evidence=first)}
        before=jobs.catalog()[0]
        changed=copy.deepcopy(original);changed['observed']['executionContext']['kernelBootSha256']='d'*64
        changed['probe']['output']=json.dumps(changed['observed'])
        with self.assertRaises(ValueError):RuntimeEvidence.load(self.reference(changed),self.spec)
        changed['executionContextSha256']=digest(changed['observed']['executionContext'])
        second=RuntimeEvidence.load(self.reference(changed),self.spec)
        jobs.validators={self.spec.name:RegisteredValidator('Observed Python',self.spec,runtime_evidence=second)}
        after=jobs.catalog()[0]
        self.assertEqual(before['runtime'],after['runtime'])
        self.assertNotEqual(before['runtimeEvidence']['executionContextSha256'],after['runtimeEvidence']['executionContextSha256'])
        self.assertNotEqual(before['contractSha256'],after['contractSha256'])

    def test_probe_does_not_attempt_a_filter_without_no_new_privileges(self):
        import ctypes,os
        from unittest.mock import patch
        from server.process_control_observation import PYTHON_PROCESS_CONTROLS
        calls=[]
        def prctl(*args):
            calls.append(args);ctypes.set_errno(1);return -1
        from types import SimpleNamespace
        namespace={'os':os,'result':{}}
        with patch('ctypes.CDLL',return_value=SimpleNamespace(prctl=prctl)),patch('pathlib.Path.read_text',return_value='00000000-0000-0000-0000-000000000001'):
            exec(PYTHON_PROCESS_CONTROLS,namespace)
        self.assertEqual(len(calls),1);self.assertEqual(calls[0][:2],(38,1))
        self.assertIsNone(namespace['result']['processControls']['seccompFilter'])
