import hashlib
import unittest
from unittest.mock import patch
from server.local_validation import DockerValidationWorker,ValidationSpec


class ValidationContractTests(unittest.TestCase):
    def test_executable_scratch_is_explicit_operator_capability_with_reviewed_combinations(self):
        from server.validation_jobs import registered_validators
        entry={'id':'dependency-tests','label':'Native dependencies','image':'sha256:'+'a'*64,'command':['/usr/local/bin/python3','-m','unittest']}
        self.assertFalse(registered_validators([entry])['dependency-tests'].spec.executable_scratch)
        self.assertTrue(registered_validators([{**entry,'executableScratch':True}])['dependency-tests'].spec.executable_scratch)
        for value in [None,1,'true',{},[]]:
            with self.subTest(value=value),self.assertRaises(ValueError):registered_validators([{**entry,'executableScratch':value}])
        with self.assertRaises(ValueError):registered_validators([{**entry,'executableScratch':True,'isolationProfile':'chromium-userns-v1'}])
    def test_operator_spec_requires_immutable_local_image_and_bounded_executable(self):
        image='sha256:'+'a'*64
        for values in [dict(image='python:latest'),dict(command=('python','test.py')),
                       dict(timeout_seconds=0),dict(timeout_seconds=301),dict(platform='linux/unknown'),dict(bootstrap_python='python'),dict(isolation_profile='unconfined'),dict(runtime_environment=(('AWS_SECRET_ACCESS_KEY','/secret'),)),dict(runtime_environment=(('ATMEM_PLAYWRIGHT_MODULE','relative'),)),dict(runtime_environment=(({},'/path'),))]:
            args={'name':'local-tests','image':image,'command':('/usr/local/bin/python3','test.py'),**values}
            with self.subTest(values=values),self.assertRaises(ValueError):ValidationSpec(**args)

    def test_remote_or_missing_daemons_never_receive_an_artifact(self):
        for endpoint in ['tcp://remote:2375','ssh://remote','unix:///does/not/exist']:
            with self.assertRaises(ValueError):DockerValidationWorker(endpoint)

    def test_digest_and_output_budget_rejected_before_starting_docker(self):
        with patch('server.local_validation.Path.is_socket',return_value=True):
            with self.assertRaises(ValueError):DockerValidationWorker('unix:///safe/local.sock',max_output_bytes=1)
            worker=DockerValidationWorker('unix:///safe/local.sock')
        spec=ValidationSpec('local-tests','sha256:'+'a'*64,('/usr/local/bin/python3','test.py'))
        with patch('server.local_validation.subprocess.run') as command:
            with self.assertRaises(ValueError):worker.run(b'archive','incorrect',spec)
            command.assert_not_called()

    def test_cached_config_platform_and_identity_must_both_match_before_execution(self):
        from types import SimpleNamespace
        image='sha256:'+'a'*64;raw=b'fixture archive'
        with patch('server.local_validation.Path.is_socket',return_value=True):worker=DockerValidationWorker('unix:///safe/local.sock')
        spec=ValidationSpec('local-tests',image,('/usr/local/bin/python3','test.py'))
        for observed in ['linux/arm64 '+image,'linux/amd64 sha256:'+'b'*64]:
            with self.subTest(observed=observed),patch('server.local_validation.subprocess.run',side_effect=[SimpleNamespace(returncode=0,stdout=image),SimpleNamespace(returncode=0,stdout=observed)]) as inspect,patch('server.local_validation.subprocess.Popen') as execute:
                with self.assertRaises(RuntimeError):worker.run(raw,hashlib.sha256(raw).hexdigest(),spec)
                self.assertNotIn('--platform',inspect.call_args.args[0])
                execute.assert_not_called()

    def test_unregistered_or_modified_isolation_policy_cannot_launch_a_container(self):
        import json,tempfile
        from pathlib import Path
        with patch('server.local_validation.Path.is_socket',return_value=True):
            for profiles in [[],{'unconfined':{}},{'chromium-userns-v1':{'path':'relative','sha256':'a'*64}}]:
                with self.assertRaises(ValueError):DockerValidationWorker('unix:///safe/local.sock',isolation_profiles=profiles)
            worker=DockerValidationWorker('unix:///safe/local.sock')
            spec=ValidationSpec('browser-tests','sha256:'+'a'*64,('/usr/bin/node','--test'),isolation_profile='chromium-userns-v1')
            with patch('server.local_validation.subprocess.run') as command:
                with self.assertRaises(RuntimeError):worker.run(b'archive',hashlib.sha256(b'archive').hexdigest(),spec)
                command.assert_not_called()
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'policy.json';path.write_text(json.dumps({'defaultAction':'SCMP_ACT_ALLOW'}))
                with self.assertRaises(ValueError):DockerValidationWorker('unix:///safe/local.sock',isolation_profiles={'chromium-userns-v1':{'path':str(path),'sha256':worker.REVIEWED_PROFILES['chromium-userns-v1']}})


class SqlValidatorContractTests(unittest.TestCase):
    def test_isolated_unittest_driver_keeps_test_count_and_skip_interpretation(self):
        from server.local_validation import validation_test_runner
        spec=ValidationSpec('isolated-oracle','sha256:'+'a'*64,('/usr/bin/python3','-I','-m','unittest','discover','-s','/opt/atmem','-v'))
        self.assertEqual(validation_test_runner(spec),'unittest')
        unrelated=ValidationSpec('isolated-script','sha256:'+'a'*64,('/usr/bin/python3','-I','/opt/atmem/check.py'))
        self.assertEqual(validation_test_runner(unrelated),'operator_registered')

    def test_sql_wrapper_is_reported_as_unittest_and_keeps_secret_environment_denial(self):
        from server.local_validation import validation_test_runner
        spec=ValidationSpec('sql-tests','sha256:'+'a'*64,('/usr/local/bin/python3','-I','/opt/atmem/sql_validation.py','-m','unittest','discover','-v'),isolation_profile='postgresql-local-v1')
        self.assertEqual(validation_test_runner(spec),'unittest')
        with patch('server.local_validation.Path.is_socket',return_value=True):self.assertTrue(DockerValidationWorker('unix:///safe/local.sock').supports(spec))
        with self.assertRaises(ValueError):ValidationSpec('sql-tests','sha256:'+'a'*64,spec.command,isolation_profile='postgresql-local-v1',runtime_environment=(('PGPASSWORD','/secret'),))
