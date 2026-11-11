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
