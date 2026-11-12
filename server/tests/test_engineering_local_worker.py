import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from server.engineering_routes import LocalEngineeringService
from server.engineering_sessions import ModelSelection, ProjectScope


class LocalWorkerRegistrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_context_updates_are_control_owned_without_rewriting_workspace_pins(self):
        import hashlib, uuid
        from server.engineering_sessions import SessionError
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'projects').mkdir()
            context=root/'projects/project-one.atforma.json'
            original=json.dumps({'format':'atmem.ai-architect.project','meta':{'id':'project-one'},
                'requirements':['Preserve the existing observatory.'],'design':{'provider':'tools'}}).encode()
            context.write_bytes(original)
            with patch('server.engineering_routes.home',return_value=root),patch('server.engineering_routes.setting',return_value=None):
                worker=LocalEngineeringService();scope=ProjectScope('local-owner','project-one')
                async def fake_create(scope,workspace,selection):return worker.sessions._public(worker.store.create(scope,workspace,worker.backend.name,'fake-thread',selection))
                worker.sessions.create=fake_create
                state=await worker.create(scope,context,ModelSelection('exact-model','high'))
                path=worker.backend._workspace(scope,worker.store.get(scope,state['id'])['workspace'])
                try:
                    pins=worker.pinned_inputs(scope,state['id']).copy()
                    first=worker.attach_context(scope,state['id'],str(uuid.uuid4()),hashlib.sha256(original).hexdigest())
                    changed=original.replace(b'observatory',b'observatory; report non-BMP Unicode labels')
                    context.write_bytes(changed)
                    with self.assertRaises(SessionError):worker.attach_context(scope,state['id'],str(uuid.uuid4()),first['sha256'])
                    second=worker.attach_context(scope,state['id'],str(uuid.uuid4()),hashlib.sha256(changed).hexdigest())
                    self.assertEqual(second['revision'],2)
                    self.assertEqual((path/'project-context.json').read_bytes(),original)
                    self.assertEqual(worker.pinned_inputs(scope,state['id']),pins)
                    self.assertEqual(worker.contexts.get(scope,state['id'],first['id'])['content'].encode(),original)
                    context.unlink();context.symlink_to(path/'project-context.json')
                    with self.assertRaises(Exception):worker.attach_context(scope,state['id'],str(uuid.uuid4()),first['sha256'])
                finally:
                    await worker.close();shutil.rmtree(path)

    async def test_native_registration_retains_selected_virtualenv_and_requires_its_read_root(self):
        import subprocess,sys,venv
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);environment=root/'public-python';venv.EnvBuilder(with_pip=False).create(environment);binary=environment/'bin/python'
            probe=subprocess.run([str(binary),'-I','-c',"import sysconfig;print(sysconfig.get_path('purelib'))"],capture_output=True,text=True,check=True)
            (Path(probe.stdout.strip())/'atmem_dependency_canary.py').write_text('VALUE=41\n')
            context=root/'project.json';context.write_text('{"requirements":"Keep shared worker dependencies"}')
            base_root=str(Path(sys.executable).resolve().parent)
            config={'ENGINEERING_TOOL_ROOTS':json.dumps([base_root]),'ENGINEERING_TOOLCHAIN':json.dumps({'python':str(binary)})}
            with patch('server.engineering_routes.home',return_value=root),patch('server.engineering_routes.setting',side_effect=config.get),self.assertRaisesRegex(RuntimeError,'qualified.*read root'):LocalEngineeringService()
            config['ENGINEERING_TOOL_ROOTS']=json.dumps([base_root,str(environment)])
            with patch('server.engineering_routes.home',return_value=root),patch('server.engineering_routes.setting',side_effect=config.get):
                worker=LocalEngineeringService();scope=ProjectScope('local-owner','environment-test')
                async def fake_create(scope,workspace,selection):return worker.sessions._public(worker.store.create(scope,workspace,worker.backend.name,'fake-thread',selection))
                worker.sessions.create=fake_create;state=await worker.create(scope,context,ModelSelection('exact-model','high'));path=worker.backend._workspace(scope,worker.store.get(scope,state['id'])['workspace'])
                try:
                    result=subprocess.run([str(path/'.tools/python'),'-I','-c','import atmem_dependency_canary;assert atmem_dependency_canary.VALUE==41'],capture_output=True,text=True)
                    self.assertEqual(result.returncode,0,result.stderr);self.assertFalse((path/'.tools/python').is_symlink())
                    self.assertEqual(worker.toolchain['python'],str(binary.absolute()))
                finally:await worker.close();shutil.rmtree(path)

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
                self.assertEqual(set(events[0]['inputDigests']),{'project-context.json','.agents/skills/composition/SKILL.md','ATMEM_DELIVERY.md','atmem-tools/prepare.py','atmem-tools/architecture-work.schema.json','atmem-tools/application-runtime.json','atmem-tools/materialize-runtime.py'})
                import hashlib
                schema=path/'atmem-tools/architecture-work.schema.json'
                self.assertEqual(events[0]['inputDigests']['atmem-tools/architecture-work.schema.json'],hashlib.sha256(schema.read_bytes()).hexdigest())
                self.assertEqual(json.loads(schema.read_text())['properties']['version']['const'],1)
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

    async def test_named_only_service_native_catalog_and_working_checkpoint_need_no_default_worker(self):
        import asyncio
        from server.tests.test_validation_jobs import Worker
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);context=root/'project.json';context.write_text('{"requirements":"Preserve source ownership"}')
            entry={'id':'placed-tests','label':'Explicit placed check','image':'sha256:'+'a'*64,
                   'command':['/usr/local/bin/python3','check.py'],'workerId':'approved-executor'}
            config={'ENGINEERING_VALIDATORS':json.dumps([entry]),'ENGINEERING_VALIDATOR_WORKERS':json.dumps({'approved-executor':{'endpoint':'unix:///owned/unavailable.sock'}})}
            executor=Worker()
            with patch('server.engineering_routes.home',return_value=root),patch('server.engineering_routes.setting',side_effect=config.get),patch('server.validation_workers.WorkerRegistration.create',side_effect=[ValueError('not ready'),executor]):
                worker=LocalEngineeringService();scope=ProjectScope('local-owner','project-one')
                async def fake_create(scope,workspace,selection):return worker.sessions._public(worker.store.create(scope,workspace,worker.backend.name,'private-thread',selection))
                worker.sessions.create=fake_create
                state=await worker.create(scope,context,ModelSelection('exact-model','high'));row=worker.store.get(scope,state['id']);path=worker.backend._workspace(scope,row['workspace'])
                worker.store.reserve(scope,state['id'],'run-one','Implement owned module');worker.store.attach_turn(scope,state['id'],'run-one','turn-one')
                try:
                    first=worker.validation_service();self.assertFalse(first.available());self.assertIsNone(first.worker)
                    result=await worker.native_tools.invoke(scope,row['workspace'],'turn-one','catalog','atmem_check_catalog',{})
                    catalog=json.loads(result['contentItems'][0]['text']);self.assertTrue(catalog['available'])
                    self.assertEqual(catalog['validators'][0]['placement'],{'workerId':'approved-executor','status':'configured'})
                    (path/'library.py').write_text('VALUE = 1')
                    result=await worker.native_tools.invoke(scope,row['workspace'],'turn-one','check','atmem_check_working',{'validatorId':'placed-tests'})
                    self.assertTrue(result['success']);await asyncio.gather(*list(worker.checks.tasks.values()))
                    self.assertEqual(len(executor.calls),1);self.assertIsNone(worker.checks.worker)
                    self.assertEqual(worker.store.get(scope,state['id'])['model'],'exact-model')
                finally:
                    await worker.close();shutil.rmtree(path)
