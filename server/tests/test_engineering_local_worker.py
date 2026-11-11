import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from server.engineering_routes import LocalEngineeringService
from server.engineering_sessions import ModelSelection, ProjectScope


class LocalWorkerRegistrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_operator_toolchain_staging_and_durable_project_registration(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);tools=root/'trusted-tools';tools.mkdir()
            binary=tools/'python';binary.write_text('synthetic tool, never executed')
            context=root/'project.json';context.write_text('{"requirements":"Preserve telemetry API"}')
            config={'ENGINEERING_TOOL_ROOTS':json.dumps([str(tools)]),
                    'ENGINEERING_TOOLCHAIN':json.dumps({'python':str(binary)})}
            with patch('server.engineering_routes.home',return_value=root),patch('server.engineering_routes.setting',side_effect=config.get):
                worker=LocalEngineeringService()
                scope=ProjectScope('local-owner','project-one')
                selection=ModelSelection('selected-model','high')
                async def fake_create(scope,workspace,selection):
                    return worker.sessions._public(worker.store.create(scope,workspace,worker.backend.name,'fake-private-thread',selection))
                worker.sessions.create=fake_create
                state=await worker.create(scope,context,selection)
                row=worker.store.get(scope,state['id']);path=worker.backend._workspace(scope,row['workspace'])
                self.assertEqual((path/'project-context.json').read_text(),context.read_text())
                self.assertEqual((path/'.tools/python').resolve(),binary.resolve())
                manifest=json.loads((path/'.tools/toolchain.json').read_text())
                self.assertEqual(manifest['tools'],{'python':'./.tools/python'})
                self.assertTrue((path/'.agents/skills/composition/SKILL.md').is_file())
                self.assertTrue((path/'ATMEM_DELIVERY.md').is_file())
                self.assertTrue((path/'atmem-tools/prepare.py').is_file())
                events=worker.jobs.journal.read(scope,state['id'])
                self.assertEqual(events[0]['kind'],'created')
                self.assertEqual(len(events[0]['inputDigests']),4)
                await worker.close()
                restarted=LocalEngineeringService()
                self.assertEqual(restarted.backend._workspace(scope,row['workspace']),path)
                self.assertEqual(restarted.jobs.state(scope,state['id'])['model'],'selected-model')
                await restarted.close()
                shutil.rmtree(path)

    async def test_native_working_check_uses_owned_pinned_checkpoint_and_reuses_exact_bytes(self):
        from server.tests.test_validation_jobs import Worker
        from server.validation_jobs import RegisteredValidator
        from server.local_validation import ValidationSpec
        import asyncio
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);context=root/'project.json';context.write_text('{"requirements":"Preserve measurement contracts"}')
            with patch('server.engineering_routes.home',return_value=root),patch('server.engineering_routes.setting',return_value=None):
                worker=LocalEngineeringService();scope=ProjectScope('local-owner','project-one');selection=ModelSelection('exact-model','high')
                async def fake_create(scope,workspace,selection):return worker.sessions._public(worker.store.create(scope,workspace,worker.backend.name,'private-thread',selection))
                worker.sessions.create=fake_create;state=await worker.create(scope,context,selection);row=worker.store.get(scope,state['id']);path=worker.backend._workspace(scope,row['workspace'])
                worker.store.reserve(scope,state['id'],'run-one','Implement module');worker.store.attach_turn(scope,state['id'],'run-one','turn-one')
                executor=Worker();worker.checks.worker=executor;worker.checks.validators={'module-tests':RegisteredValidator('Module contract',ValidationSpec('module-tests','sha256:'+'a'*64,('/usr/local/bin/python3','check.py')))}
                (path/'library.py').write_text('VALUE = 1')
                async def invoke(identity,validator='module-tests'):return await worker.native_tools.invoke(scope,row['workspace'],'turn-one',identity,'atmem_check_working',{'validatorId':validator})
                rejected=await invoke('unknown','foreign');self.assertFalse(rejected['success']);self.assertEqual(worker.store.db.execute('select count(*) from engineering_checkpoints').fetchone()[0],0)
                first=json.loads((await invoke('first'))['contentItems'][0]['text']);await asyncio.gather(*list(worker.checks.tasks.values()));second=json.loads((await invoke('second'))['contentItems'][0]['text'])
                self.assertEqual(first['checkpoint']['id'],second['checkpoint']['id']);self.assertEqual(first['check']['id'],second['check']['id']);self.assertEqual(len(executor.calls),1);self.assertEqual(worker.artifacts.manifests(scope,state['id']),[])
                (path/'library.py').write_text('VALUE = 2');third=json.loads((await invoke('third'))['contentItems'][0]['text']);await asyncio.gather(*list(worker.checks.tasks.values()));self.assertNotEqual(first['checkpoint']['sha256'],third['checkpoint']['sha256']);self.assertEqual(len(executor.calls),2)
                await worker.close();shutil.rmtree(path)

    async def test_operator_tool_paths_need_registered_read_roots(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);safe=root/'safe';safe.mkdir();other=root/'other';other.write_text('not a permitted tool')
            config={'ENGINEERING_TOOL_ROOTS':json.dumps([str(safe)]),
                    'ENGINEERING_TOOLCHAIN':json.dumps({'python':str(other)})}
            with patch('server.engineering_routes.home',return_value=root),patch('server.engineering_routes.setting',side_effect=config.get):
                with self.assertRaisesRegex(RuntimeError,'qualified tool read root'):LocalEngineeringService()
