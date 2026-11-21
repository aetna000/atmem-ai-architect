import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from server.settings import setting,home

class RenameCompatibilityTests(unittest.TestCase):
    def test_new_settings_take_precedence_and_legacy_settings_still_work(self):
        with patch.dict(os.environ,{'ATMEM_ARCHITECT_HOME':'/new','ATFORMA_HOME':'/old'},clear=True):
            self.assertEqual(str(home()),'/new')
            del os.environ['ATMEM_ARCHITECT_HOME']
            self.assertEqual(str(home()),'/old')
    def test_existing_installation_keeps_history_and_new_installation_uses_new_home(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{},clear=True), patch('server.settings.Path.home',return_value=Path(tmp)):
            self.assertEqual(home(),Path(tmp)/'.atmem-ai-architect')
            (Path(tmp)/'.atforma').mkdir()
            self.assertEqual(home(),Path(tmp)/'.atforma')
