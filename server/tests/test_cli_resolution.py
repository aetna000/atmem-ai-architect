import unittest
from types import SimpleNamespace
from unittest.mock import patch
from server.local_providers import cli_command,signed_in,models

class CliResolutionTests(unittest.TestCase):
    def test_windows_shim_path_is_one_argument_and_caller_arguments_are_preserved(self):
        binary=r'C:\Users\user name\AppData\Roaming\npm\codex.CMD'
        with patch('server.local_providers.shutil.which',return_value=binary):
            self.assertEqual(cli_command(['codex','app-server','--listen','stdio://']),[binary,'app-server','--listen','stdio://'])
    def test_status_and_catalogue_use_resolved_path(self):
        binary=r'C:\Users\user\AppData\Roaming\npm\codex.CMD'
        with patch('server.local_providers.shutil.which',return_value=binary),patch('subprocess.run')as run:
            run.return_value=SimpleNamespace(returncode=0,stdout='Logged in using ChatGPT',stderr='')
            self.assertTrue(signed_in('codex'))
            self.assertEqual(run.call_args.args[0],[binary,'login','status'])
            run.return_value=SimpleNamespace(stdout='{"models":[{"slug":"test-model","supported_reasoning_levels":[{"effort":"high"}]}]}')
            self.assertEqual(models('codex')[0]['efforts'],['high'])
            self.assertEqual(run.call_args.args[0],[binary,'debug','models'])
