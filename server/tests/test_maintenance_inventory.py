from pathlib import Path
import subprocess
import tempfile
import unittest
import json

from server.maintenance.inventory import snapshot, inventory, validate_snapshot
from server.maintenance.recipes import applicability, propose
from server.maintenance.patches import apply_candidate, check_patch, source_map, build_candidate

FIXTURES = Path(__file__).resolve().parents[2] / 'tests/maintenance/fixtures'


def source(name):
    return snapshot({'main.tf': (FIXTURES / name / 'main.tf').read_text()}, 'repository-001')


class InventoryTests(unittest.TestCase):
    def test_actual_hcl_and_aliases_never_evaluate_expressions(self):
        value = source('holdout')
        report = inventory(value)
        self.assertEqual(len(report['resources']), 2)
        self.assertIn('aws.west', report['files']['main.tf']['traversals'])
        self.assertIn('local.primary', report['files']['main.tf']['traversals'])

    def test_tampering_paths_secrets_and_unparseable_source(self):
        for path in ['../main.tf', '/main.tf', 'a/../main.tf', 'a//main.tf', 'a\\main.tf', '.git/config']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                snapshot({path: 'terraform {}'}, 'repository-001')
        for path, text in [('secret.tfvars', 'x=1'), ('.env', 'PRIVATE=1'), ('main.tf', 'x="sk-' + 'a' * 30 + '"')]:
            with self.assertRaises(ValueError):
                snapshot({path: text}, 'repository-001')
        value = source('baseline')
        value.files[0].text += '\n# changed'
        with self.assertRaises(ValueError):
            validate_snapshot(value)
        with self.assertRaises(ValueError):
            inventory(snapshot({'main.tf': 'resource { unclosed'}, 'repository-001'))
        large = inventory(snapshot({'main.tf': 'locals { beyond_json_precision = 1e9999 }'}, 'repository-001'))
        self.assertEqual(large['files']['main.tf']['blocks'][0]['attributes'][0]['expression'], '1e9999')
        json.dumps(large, allow_nan=False)  # Retain the expression; never invent infinity in JSON.

    def test_executable_constructs_block_without_grandfathering(self):
        for name in ['external', 'http', 'provisioner', 'backend']:
            with self.subTest(name=name):
                _, findings = applicability(source(name))
                self.assertIn('executable_construct', [f.code for f in findings])

    def test_hcl_with_invalid_terraform_labels_is_actionable_not_an_internal_error(self):
        for text in ['resource "aws_batch_job_queue" {}', 'module {}', 'data "aws_ami" {}']:
            with self.subTest(text=text):
                _, findings = applicability(snapshot({'main.tf': text}, 'repository-001'))
                self.assertIn('invalid_block_shape', [f.code for f in findings])

    def test_real_recipe_preserves_semantics_and_every_comment(self):
        for name in ['baseline', 'holdout']:
            with self.subTest(name=name):
                value = source(name)
                candidate, findings = propose(value)
                self.assertFalse(findings)
                self.assertFalse(check_patch(source_map(value), candidate))
                after = apply_candidate(source_map(value), candidate)['main.tf']
                self.assertIn('# preserve this expression' if name == 'holdout' else '# Queue order', after)
                self.assertNotIn('compute_environments =', after)
                self.assertIn('"6.0.0"', after)
                self.assertIn('"5.100.0"', value.files[0].text)

    def test_dynamic_is_not_a_success_and_policy_denies_model_scope_expansion(self):
        candidate, findings = propose(source('dynamic'))
        self.assertIsNone(candidate)
        self.assertIn('unsupported_queue_expression', [f.code for f in findings])
        value = source('baseline')
        good, _ = propose(value)
        before = source_map(value)
        after = apply_candidate(before, good)
        after['main.tf'] = after['main.tf'].replace('priority = 10', 'priority = 99')
        self.assertIn('semantic_scope_violation', [f.code for f in check_patch(before, build_candidate(before, after))])
        after['main.tf'] += '\ndata "http" "exfiltrate" { url = "https://example.invalid" }\n'
        self.assertTrue(check_patch(before, build_candidate(before, after)))

    def test_source_changes_and_automation_paths_never_slip_through(self):
        value = source('baseline')
        before = source_map(value)
        before['.github/workflows/deploy.yml'] = 'on: push\n'
        candidate, _ = propose(snapshot(before, 'repository-001'))
        after = apply_candidate(before, candidate)
        after['.github/workflows/deploy.yml'] = 'on: pull_request\n'
        self.assertIn('forbidden_path_change', [f.code for f in check_patch(before, build_candidate(before, after))])
        after = apply_candidate(before, candidate)
        after['main.tf'] = after['main.tf'].replace('hashicorp/aws', 'malicious/aws')
        self.assertTrue(check_patch(before, build_candidate(before, after)))

    def test_unicode_offsets_and_patch_apply_without_final_newline(self):
        original = '# 日本語 source evidence\n' + (FIXTURES / 'baseline/main.tf').read_text().rstrip('\n')
        value = snapshot({'main.tf': original}, 'repository-001')
        candidate, findings = propose(value)
        self.assertFalse(findings)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'main.tf'
            target.write_text(original)
            patch = '\n'.join(c.diff for c in candidate.changes).encode()
            result = subprocess.run(['git', '-C', folder, 'apply', '-'], input=patch, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(target.read_text(), apply_candidate(source_map(value), candidate)['main.tf'])
        candidate.changes[0].diff = 'misleading patch'
        with self.assertRaisesRegex(ValueError, 'Displayed patch'):
            apply_candidate(source_map(value), candidate)
