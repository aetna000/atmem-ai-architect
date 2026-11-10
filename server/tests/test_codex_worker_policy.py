from pathlib import Path
import tempfile
import unittest
import copy
from unittest.mock import patch
from server.codex_worker_policy import PROFILE,CodexWorkerClient,worker_command


class WorkerPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.binary=self.root/'bin/codex';self.binary.parent.mkdir();self.binary.write_text('synthetic executable fixture')
        self.which=patch('server.codex_worker_policy.shutil.which',return_value=str(self.binary));self.which.start()
        self.servers=patch('server.codex_worker_policy.configured_mcp_names',return_value=['local-server']);self.servers.start()
        self.overrides=patch('server.codex_worker_policy.configured_shell_override_names',return_value=['PRIVATE_TOKEN']);self.overrides.start()
    def tearDown(self):self.overrides.stop();self.servers.stop();self.which.stop();self.temp.cleanup()
    def test_policy_denies_host_reads_and_network_without_disabling_local_file_tools(self):
        command=worker_command([self.root/'bin']);wire='\n'.join(command)
        self.assertEqual(command[0],str(self.binary.resolve()))
        self.assertIn('":root"="deny"',wire);self.assertIn('extends=":workspace"',wire)
        self.assertIn('network={enabled=true,domains={}',wire);self.assertIn('allow_local_binding=false',wire);self.assertIn('features.network_proxy=true',wire);self.assertIn(f'default_permissions="{PROFILE}"',wire)
        self.assertIn('mcp_servers={}',wire);self.assertIn('features.plugins=false',wire)
        self.assertIn('mcp_servers.local-server.enabled=false',wire)
        self.assertIn('allow_login_shell=false',wire);self.assertIn('shell_environment_policy.inherit="core"',wire)
        self.assertIn('shell_environment_policy.set.PRIVATE_TOKEN=""',wire)
    def test_read_roots_cannot_grant_root_home_or_credential_trees(self):
        for path in [Path('/'),Path.home(),Path.home().parent,Path.home()/'.codex']:
            with self.subTest(path=path):
                with self.assertRaises(ValueError):worker_command([path])
    def test_symlinks_resolve_before_read_root_admission(self):
        link=self.root/'innocent-tools';link.symlink_to(Path.home())
        with self.assertRaises(ValueError):worker_command([link])

    def test_unusual_mcp_key_is_rejected_instead_of_creating_an_ineffective_override(self):
        with patch('server.codex_worker_policy.configured_mcp_names',return_value=['server.with.dots']):
            with self.assertRaises(ValueError):worker_command()


class EffectiveWorkerPolicyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.client=object.__new__(CodexWorkerClient);self.client.workspace=self.root
        filesystem={':root':'deny',':minimal':'read',':tmpdir':'deny',':slash_tmp':'deny'}
        network={'enabled':True,'domains':{},'allow_local_binding':False,'unix_sockets':{str(self.root/'.worker-tmp'):'allow'}}
        self.client.expected_worker_profile={'filesystem':filesystem,'network':network}
        self.config={'mcp_servers':{'local-server':{'enabled':False}},'features':{'apps':False,'plugins':False,'network_proxy':True,'shell_snapshot':False},'web_search':'disabled','allow_login_shell':False,
                     'shell_environment_policy':{'inherit':'core','ignore_default_excludes':False,'set':{'TMPDIR':str(self.root/'.worker-tmp')}},
                     'permissions':{PROFILE:{'extends':':workspace','filesystem':dict(filesystem,glob_scan_max_depth=None),'network':network}}}
        self.states=[{'name':'local-server','runtimeStatus':None,'tools':{},'resources':[],'resourceTemplates':[]}]
        async def request(method,params):
            return {'config':self.config} if method=='config/read' else {'data':self.states}
        self.client.request=request
    async def asyncTearDown(self):self.temp.cleanup()
    async def test_disabled_mcp_definitions_without_exposed_tools_are_accepted(self):
        summary=await self.client.verify_worker_tools()
        self.assertTrue(summary['allDisabled']);self.assertEqual(summary['exposedMcpTools'],0)
    async def test_effective_layer_cannot_reenable_tools_or_widen_read_network_or_environment_access(self):
        mutations=[lambda c:c['mcp_servers']['local-server'].update(enabled=True),
                   lambda c:c['features'].update(plugins=True),
                   lambda c:c['permissions'][PROFILE]['filesystem'].update({':root':'read'}),
                   lambda c:c['permissions'][PROFILE]['network'].update(domains={'*':'allow'}),
                   lambda c:c['shell_environment_policy']['set'].update(PRIVATE_TOKEN='synthetic-only'),
                   lambda c:c.update(allow_login_shell=True)]
        original=copy.deepcopy(self.config)
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                self.config=copy.deepcopy(original);mutate(self.config)
                with self.assertRaises(RuntimeError):await self.client.verify_worker_tools()
    async def test_disabled_configuration_does_not_override_an_exposed_tool_surface(self):
        self.states[0]['tools']={'unexpected':{}}
        with self.assertRaises(RuntimeError):await self.client.verify_worker_tools()
    async def test_client_cannot_attest_its_safe_profile_for_a_different_active_profile(self):
        with self.assertRaises(RuntimeError):await self.client.verify_worker_tools('different-profile')
