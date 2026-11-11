import hashlib
import io
from pathlib import Path
import os
import tempfile
import unittest
import zipfile
from server.engineering_artifacts import EngineeringArtifacts
from server.engineering_sessions import ModelSelection, ProjectScope, SessionError, SqliteSessionStore


class EngineeringArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = self.root/'worker'
        self.workspace.mkdir()
        self.store = SqliteSessionStore(self.root/'control.sqlite')
        self.scope = ProjectScope('local-owner','project-one')
        self.session = self.store.create(self.scope,'owned-workspace','backend','private-handle', ModelSelection('selected-model','high'))['id']
        self.store.reserve(self.scope,self.session,'run-one','Preserve full intent.')
        self.store.attach_turn(self.scope,self.session,'run-one','turn-one')
        self.artifacts = EngineeringArtifacts(self.store)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def settle(self, status='completed'):
        self.store.terminal(self.scope,self.session,'run-one','turn-one',status)

    def test_immutable_package_digest_exact_content_modes_and_scope(self):
        self.settle()
        (self.workspace/'infra').mkdir()
        (self.workspace/'infra/main.tf').write_text('resource "local_file" "example" {}')
        (self.workspace/'run.sh').write_text('#!/bin/sh\nexit 0\n')
        (self.workspace/'run.sh').chmod(0o755)
        manifest = self.artifacts.capture(self.scope,self.session,self.workspace)
        (self.workspace/'run.sh').write_text('different content')
        saved, archive = self.artifacts.get(self.scope,self.session,manifest['id'])
        self.assertEqual(hashlib.sha256(archive).hexdigest(), saved['sha256'])
        self.assertEqual(saved['model'],'selected-model')
        self.assertEqual(saved['effort'],'high')
        self.assertEqual(saved['validation'],'not_established_by_artifact_capture')
        with zipfile.ZipFile(io.BytesIO(archive)) as package:
            self.assertEqual(package.read('run.sh'), b'#!/bin/sh\nexit 0\n')
            self.assertTrue(package.getinfo('run.sh').external_attr >> 16 & 0o111)
        for scope in [ProjectScope('other-owner','project-one'),ProjectScope('local-owner','project-two')]:
            with self.assertRaises(SessionError): self.artifacts.get(scope,self.session,manifest['id'])
        self.assertNotIn(str(self.workspace),str(saved))
        self.assertNotIn('private-handle',str(saved))

    def test_active_and_unsafe_files_never_leave_partial_artifact(self):
        with self.assertRaises(SessionError): self.artifacts.capture(self.scope,self.session,self.workspace)
        self.settle()
        outside = self.root/'outside'
        outside.write_text('private')
        for kind in ['symlink','directory-symlink','hardlink','fifo']:
            path = self.workspace/'unsafe'
            if kind == 'symlink': path.symlink_to(outside)
            elif kind == 'directory-symlink': path.symlink_to(self.root,target_is_directory=True)
            elif kind == 'hardlink': os.link(outside,path)
            else: os.mkfifo(path)
            with self.subTest(kind=kind), self.assertRaises(SessionError):
                self.artifacts.capture(self.scope,self.session,self.workspace)
            path.unlink()
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM engineering_artifacts').fetchone()[0],0)

    def test_oversize_or_excess_entries_explicitly_fail(self):
        self.settle()
        (self.workspace/'large.txt').write_bytes(b'123456')
        bounded = EngineeringArtifacts(self.store,max_bytes=5)
        with self.assertRaisesRegex(SessionError,'byte limit'): bounded.capture(self.scope,self.session,self.workspace)
        bounded = EngineeringArtifacts(self.store,max_files=1)
        (self.workspace/'extra.txt').write_text('x')
        with self.assertRaisesRegex(SessionError,'entry limit'): bounded.capture(self.scope,self.session,self.workspace)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM engineering_artifacts').fetchone()[0],0)

    def test_worker_metadata_exclusion_explicit_and_partial_status_retained(self):
        self.settle('interrupted')
        (self.workspace/'.worker-tmp').mkdir()
        (self.workspace/'.worker-tmp/socket-link').symlink_to('/does-not-exist')
        (self.workspace/'partial.py').write_text('print("unfinished")')
        manifest = self.artifacts.capture(self.scope,self.session,self.workspace)
        self.assertEqual(manifest['turnStatus'],'interrupted')
        self.assertEqual(manifest['excluded'],['.worker-tmp'])
        self.assertEqual([f['path'] for f in manifest['files']],['partial.py'])

    def test_artifacts_transfer_across_non_terraform_domain(self):
        self.settle()
        (self.workspace/'sensor.csv').write_text('time,value\n0,20\n')
        (self.workspace/'processor.py').write_text('def convert(value): return value / 100\n')
        manifest = self.artifacts.capture(self.scope,self.session,self.workspace)
        self.assertEqual({f['path'] for f in manifest['files']},{'sensor.csv','processor.py'})

    def test_changed_or_missing_pinned_inputs_cannot_pass_capture(self):
        self.settle()
        content = b'Keep the existing deployment.'
        (self.workspace/'intent.json').write_bytes(content)
        expected = {'intent.json':hashlib.sha256(content).hexdigest()}
        manifest = self.artifacts.capture(self.scope,self.session,self.workspace,expected_inputs=expected)
        self.assertEqual(manifest['pinnedInputs'],expected)
        for changed in [b'Replace all deployments.',None]:
            if changed is None: (self.workspace/'intent.json').unlink()
            else: (self.workspace/'intent.json').write_bytes(changed)
            with self.assertRaisesRegex(SessionError,'Pinned project evidence'):
                self.artifacts.capture(self.scope,self.session,self.workspace,expected_inputs=expected)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM engineering_artifacts').fetchone()[0],1)

    def test_missing_or_invalid_pinned_digest_is_not_treated_as_matching_a_missing_file(self):
        self.settle()
        for value in [{'missing':None},{'missing':'not-a-digest'},{'../outside':'a'*64},['invalid']]:
            with self.assertRaises(ValueError):self.artifacts.capture(self.scope,self.session,self.workspace,expected_inputs=value)
