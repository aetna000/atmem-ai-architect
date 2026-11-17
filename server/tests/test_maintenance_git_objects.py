"""Canonical object hashes checked by Git itself, not an author-generated expected hash."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from server.maintenance.git_objects import tree_sha, commit_object
from server.maintenance.github_adapter import git_blob_sha


class GitObjectTests(unittest.TestCase):
    def test_nested_sort_modes_and_commit_match_independent_git(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            files = {'a.tf': b'terraform {}\n', 'a/b.tf': b'output "x" { value = 1 }', 'a.c.tf': b'# sorted before directory\n'}
            entries = []
            for name, content in files.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                entries.append({'path': name, 'type': 'blob', 'mode': '100644', 'sha': git_blob_sha(content)})
            subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
            tree = subprocess.check_output(['git', '-C', str(root), 'write-tree'], text=True).strip()
            self.assertEqual(tree_sha(entries), tree)
            parent = 'a' * 40
            message = 'AtMem migration\n\nIntent: fixed-private-nonce\n'
            predicted, payload = commit_object(tree, parent, message, 1700000000)
            person = 'AtMem AI Architect <architect@atmem.ai> 1700000000 +0000'
            raw = ('tree ' + tree + '\nparent ' + parent + '\nauthor ' + person + '\ncommitter ' + person + '\n\n' + message).encode()
            expected = subprocess.check_output(['git', '-C', str(root), 'hash-object', '-t', 'commit', '--stdin'], input=raw).decode().strip()
            self.assertEqual(predicted, expected)
            self.assertEqual(payload['parents'], [parent])
            changed = {'a.tf': ('100644', git_blob_sha(b'# changed\n'))}
            (root / 'a.tf').write_bytes(b'# changed\n')
            subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
            expected = subprocess.check_output(['git', '-C', str(root), 'write-tree'], text=True).strip()
            self.assertEqual(tree_sha(entries, changed), expected)

    def test_ambiguous_paths_and_refs_never_get_object_id(self):
        with self.assertRaises(ValueError):
            tree_sha([{'path': '../escape', 'type': 'blob', 'mode': '100644', 'sha': 'a' * 40}])
        with self.assertRaises(ValueError):
            tree_sha([{'path': 'a', 'type': 'blob', 'mode': '100644', 'sha': 'a' * 40},
                      {'path': 'a/b', 'type': 'blob', 'mode': '100644', 'sha': 'b' * 40}])
        with self.assertRaises(ValueError):
            commit_object('moving-ref', 'a' * 40, 'message\n', 1700000000)
