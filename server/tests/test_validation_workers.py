import json
from pathlib import Path
import socket
import tempfile
import unittest
from server.validation_workers import registered_workers


class WorkerRegistrationTests(unittest.TestCase):
    def test_definitions_are_detached_and_missing_socket_is_unavailable_without_fallback(self):
        data={'approved-worker':{'endpoint':'unix:///nonexistent/owned-validator.sock'}}
        definitions=registered_workers(data);data['approved-worker']['endpoint']='tcp://remote:2375'
        self.assertEqual(definitions['approved-worker'].endpoint,'unix:///nonexistent/owned-validator.sock')
        with self.assertRaises(ValueError):definitions['approved-worker'].create()

    def test_actual_unix_socket_definition_uses_exact_endpoint_and_profile_snapshot(self):
        with tempfile.TemporaryDirectory()as tmp,socket.socket(socket.AF_UNIX)as handle:
            path=Path(tmp)/'worker.sock';handle.bind(str(path));endpoint='unix://'+str(path)
            definition=registered_workers({'approved-worker':{'endpoint':endpoint,'isolationProfiles':{}}})['approved-worker']
            worker=definition.create()
            self.assertEqual(worker.endpoint,endpoint);self.assertEqual(worker.isolation_profiles,{})

    def test_unknown_remote_privileged_and_ambiguous_registrations_rejected(self):
        good={'endpoint':'unix:///owned/validator.sock'}
        for entries in [[],{'../worker':good},{'approved-worker':{}},
                        {'approved-worker':{**good,'privileged':True}},
                        {'approved-worker':{'endpoint':'tcp://127.0.0.1:2375'}},
                        {'approved-worker':{'endpoint':'unix://relative'}},
                        {'approved-worker':{**good,'isolationProfiles':{'unreviewed':{}}}},
                        {'approved-worker':{**good,'isolationProfiles':{'chromium-userns-v1':{'path':'relative','sha256':'f'*64}}}},
                        {f'worker-{i}':good for i in range(17)}]:
            with self.subTest(entries=entries),self.assertRaises(ValueError):registered_workers(entries)
