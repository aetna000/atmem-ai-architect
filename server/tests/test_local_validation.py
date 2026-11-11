import hashlib
import unittest
from unittest.mock import patch
from server.local_validation import DockerValidationWorker,ValidationSpec


class ValidationContractTests(unittest.TestCase):
    def test_operator_spec_requires_immutable_local_image_and_bounded_executable(self):
        image='sha256:'+'a'*64
        for values in [dict(image='python:latest'),dict(command=('python','test.py')),
                       dict(timeout_seconds=0),dict(timeout_seconds=301),dict(platform='linux/unknown')]:
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
