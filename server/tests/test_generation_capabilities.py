import json
import unittest
from server.skills import ROOT,generation_guidance
from server.prompts import SYSTEM_PROMPT

class GenerationCapabilitiesTests(unittest.TestCase):
    def test_planner_uses_same_catalogue_as_exporter(self):
        catalogue=json.loads((ROOT/'agent-skills/generation-capabilities.json').read_text())
        guidance=generation_guidance()
        for contract in catalogue['contracts']:
            self.assertIn(contract['id'],guidance)
            self.assertIn(contract['id'],SYSTEM_PROMPT)
        self.assertIn('never substitute a different provider',guidance)
    def test_every_required_skill_has_an_integrity_record(self):
        catalogue=json.loads((ROOT/'agent-skills/generation-capabilities.json').read_text())
        manifest=json.loads((ROOT/'agent-skills/specialists/manifest.json').read_text())
        import hashlib
        for name in catalogue['skills']+catalogue['providers']:
            digest=hashlib.sha256((ROOT/f'agent-skills/specialists/{name}/SKILL.md').read_bytes()).hexdigest()
            self.assertEqual(manifest[name],digest,name)
