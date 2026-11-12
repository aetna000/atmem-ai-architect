"""Driver differential invariants with local doubles; never model-quality proof."""
import argparse
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from server.engineering_sessions import BackendEvent

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('paired_engine_driver',ROOT/'scripts/engine-evaluation/paired-native.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)


class Backend:
    name='driver-fixture'
    instances=[]
    def __init__(self,workspaces,*,instructions,**kwargs):
        self.workspace=next(iter(workspaces.values()));self.instructions=instructions
        self.skill=(self.workspace/'.agents/skills/composition/SKILL.md').is_file()
        self.__class__.instances.append(self)
    async def create(self,*args):return 'native-thread'
    async def start(self,scope,handle,text,selection,*,request_id):
        self.input=text;self.selection=selection
        (self.workspace/'generated.txt').write_text('synthetic output; not an application')
        return 'native-turn'
    async def next_event(self,*args):return BackendEvent('native-turn','completed')
    async def close(self):pass


class PairedEngineDriverTests(unittest.IsolatedAsyncioTestCase):
    async def test_arm_identity_skill_and_input_stay_distinct_under_toolchain_staging(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);repo=root/'source';repo.mkdir();out=root/'run';out.mkdir()
            (repo/'.venv/bin').mkdir(parents=True);(repo/'.venv/bin/terraform').write_text('synthetic tool')
            (repo/'.local/provider-cache').mkdir(parents=True)
            skill=repo/'agent-skills/specialists/composition/SKILL.md';skill.parent.mkdir(parents=True);skill.write_text('General composition guidance')
            args=argparse.Namespace(output=out,model='selected-test-model',effort='high',seconds=30)
            Backend.instances=[]
            with patch.object(driver,'ROOT',repo),patch.object(driver,'CodexEngineeringBackend',Backend):
                native=await driver.arm(args,'native','Identical plain client brief')
                specialized=await driver.arm(args,'specialized','Identical plain client brief')
            self.assertEqual([native['arm'],specialized['arm']],['native','specialized'])
            self.assertIsNone(native['skillSha256']);self.assertEqual(specialized['skillSha256'],driver.sha(skill))
            self.assertFalse(Backend.instances[0].skill);self.assertTrue(Backend.instances[1].skill)
            self.assertEqual(Backend.instances[0].instructions,'');self.assertTrue(Backend.instances[1].instructions)
            self.assertEqual(Backend.instances[0].input,Backend.instances[1].input)
            self.assertEqual(native['inputSha256'],specialized['inputSha256'])
            self.assertEqual(Backend.instances[0].selection,Backend.instances[1].selection)
            self.assertEqual(set(native['files']),{'generated.txt'})
            self.assertEqual(set(specialized['files']),{'generated.txt'})
