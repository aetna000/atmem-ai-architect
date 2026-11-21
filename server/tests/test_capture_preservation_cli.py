"""Execute the receiving CLI; no imports from the artifact producer."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

CLI = Path(__file__).resolve().parents[2] / 'scripts/verify-capture-preservation.py'


class CapturePreservationTests(unittest.TestCase):
    def package(self, root, name, files):
        target = root / name
        with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, value in files.items():
                body, mode = value if isinstance(value, tuple) else (value, 0o100644)
                entry = zipfile.ZipInfo(name);entry.external_attr = mode << 16
                archive.writestr(entry, body)
        return target

    def run_cli(self, root, before, after, prefixes, digest=None):
        inventory = root / 'inventory.json';out = root / 'receipt.json'
        inventory.write_text(json.dumps({'version': 1, 'beforeSha256': digest or hashlib.sha256(before.read_bytes()).hexdigest(), 'protectedPrefixes': prefixes}))
        result = subprocess.run([sys.executable, str(CLI), '--before', str(before), '--after', str(after), '--inventory', str(inventory), '--out', str(out)], capture_output=True, text=True)
        return result, json.loads(out.read_text())

    def test_real_cli_transfers_across_modules_and_languages_while_design_docs_change(self):
        for prefix, file in [('blocks/catalog/', 'catalog.rb'), ('services/sensor/', 'monitor.go')]:
            with self.subTest(prefix=prefix), tempfile.TemporaryDirectory() as folder:
                root = Path(folder);files = {prefix + file: 'Original implementation', prefix + 'config.json': '{"enabled":true}', 'specs/plan.md': 'Previous plan'}
                before = self.package(root, 'before.zip', files);after = self.package(root, 'after.zip', {**files, 'specs/plan.md': 'Refined architecture', 'docs/state.mmd': 'stateDiagram-v2'})
                result, report = self.run_cli(root, before, after, [prefix])
                self.assertEqual(result.returncode, 0, result.stderr);self.assertEqual(report['status'], 'passed');self.assertEqual(len(report['protectedFiles']), 2);self.assertEqual(report['unprotectedAddedFiles'], ['docs/state.mmd'])

    def test_changed_removed_added_code_config_or_modes_never_pass(self):
        original = {'app/main.py': 'Source', 'app/config.json': '{}'}
        changes = [{**original, 'app/main.py': 'Changed'}, {'app/config.json': '{}'}, {**original, 'app/new.py': 'New code'}, {**original, 'app/config.json': '{"enabled":true}'}, {**original, 'app/main.py': ('Source', 0o100755)}]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder);before = self.package(root, 'before.zip', original)
            for index, files in enumerate(changes):
                with self.subTest(index=index):
                    after = self.package(root, 'after.zip', files);result, report = self.run_cli(root, before, after, ['app/'])
                    self.assertNotEqual(result.returncode, 0);self.assertEqual(report['status'], 'failed');self.assertTrue(report['differences'])

    def test_wrong_baseline_empty_scope_and_unsafe_archives_reject(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder);before = self.package(root, 'before.zip', {'app/main.py': 'Source'})
            for prefixes, digest in [(['app/'], '0' * 64), (['missing/'], None), (['../app/'], None), ([], None)]:
                result, report = self.run_cli(root, before, before, prefixes, digest)
                self.assertNotEqual(result.returncode, 0);self.assertEqual(report['status'], 'rejected')
            for files in [{'app/../escape': 'Unsafe'}, {'app/link': ('target', 0o120777)}, {'APP/main.py': 'One', 'app/main.py': 'Two'}]:
                after = self.package(root, 'unsafe.zip', files);result, report = self.run_cli(root, before, after, ['app/'])
                self.assertNotEqual(result.returncode, 0);self.assertEqual(report['status'], 'rejected')
