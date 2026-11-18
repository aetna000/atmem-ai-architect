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

    def test_architect_login_uses_same_private_profile_after_restart(self):
        import asyncio
        import os
        import sys
        import tempfile
        from pathlib import Path
        from server import local_providers as adapters

        async def exercise(provider, variable, root):
            marker = Path(root) / 'terminal-profile'
            script = (
                "import os, pathlib; "
                f"pathlib.Path(os.environ[{variable!r}], 'login-fixture').touch(); "
                "print('https://example.invalid/authorize', flush=True)"
            )
            with patch.dict(os.environ, {variable: str(marker)}), patch.dict(
                adapters.LOGIN, {provider: [sys.executable, '-c', script]}
            ):
                self.assertEqual(adapters.account_environment(provider)[variable], str(marker))
                try:
                    result = await adapters.start_login(provider)
                    self.assertEqual(result['url'], 'https://example.invalid/authorize')
                    await adapters.LOGINS[provider][0].wait()
                    self.assertEqual(adapters.login_status(provider), 'completed')
                finally:
                    adapters.LOGINS.pop(provider, None)
                profile = Path(adapters.account_environment(provider)[variable])
                self.assertTrue((profile / 'login-fixture').is_file())
                self.assertFalse(marker.exists())
                self.assertEqual(os.environ[variable], str(marker))

        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {'ATMEM_ARCHITECT_HOME': root}):
            for provider, variable in adapters.PROFILE_KEYS.items():
                with self.subTest(provider=provider):
                    asyncio.run(exercise(provider, variable, root))
