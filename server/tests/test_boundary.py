import asyncio, json, unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from server.app import app, TOKEN
from server.contracts import Project, ArchitectResponse, ChatRequest
from server.architect import AtMemArchitect
from server.upstream.agent.aws_architect import AWSArchitectAgent

PROJECT={'version':1,'revision':4,'name':'Fixture graph','provider':'gcp','requirements':'Use Google Cloud','nodes':[],'edges':[]}

class BoundaryTests(unittest.TestCase):
    def setUp(self):self.client=TestClient(app)
    def test_session_contains_capabilities_but_no_credentials(self):
        result=self.client.get('/api/session');self.assertEqual(result.status_code,200)
        payload=result.json();self.assertEqual(payload['cloudExecution'],False);self.assertEqual(payload['mcpEnabled'],False)
        self.assertNotIn('api_key',json.dumps(payload));self.assertEqual(result.headers['cache-control'],'no-store')
    def test_cross_origin_session_rejected(self):
        self.assertEqual(self.client.get('/api/session',headers={'Origin':'https://evil.example'}).status_code,403)
    def test_dns_rebinding_host_rejected(self):
        self.assertEqual(self.client.get('/api/session',headers={'Host':'evil.example'}).status_code,403)
    def test_chat_requires_token(self):
        self.assertEqual(self.client.post('/api/architect',json={}).status_code,401)
    def test_validated_chat_uses_mocked_agent_no_network(self):
        response=ArchitectResponse(message='What latency does your model require?',phase='Discovery')
        with patch('server.app.ARCHITECT.call',new=AsyncMock(return_value=response)) as call:
            result=self.client.post('/api/architect',headers={'Authorization':f'Bearer {TOKEN}'},json={'message':'Help design this','model':'claude-opus-5-5','provider':'claude-code','project':PROJECT,'history':[]})
            self.assertEqual(result.status_code,200);self.assertEqual(result.json()['phase'],'Discovery');call.assert_awaited_once()
    def test_request_rejects_executable_config(self):
        project=dict(PROJECT);project['nodes']=[{'id':'x','position':{'x':0,'y':0},'data':{'label':'Unsafe','kind':'tool','provider':'tools','config':{'command':'curl example.com'}}}]
        response=self.client.post('/api/architect',headers={'Authorization':f'Bearer {TOKEN}'},json={'message':'Help','model':'claude-opus-5-5','project':project})
        self.assertEqual(response.status_code,422)
    def test_duplicate_blocks_and_dangling_wires_rejected(self):
        project=dict(PROJECT);project['edges']=[{'id':'bad','source':'x','target':'y'}]
        with self.assertRaises(ValueError):Project.model_validate(project)
    def test_model_output_revision_mismatch_rejected(self):
        raw={'message':'A proposal','phase':'Architecture','proposal':{'baseRevision':1,'title':'Change','body':'Test','next':PROJECT}}
        architect=AtMemArchitect();request=ChatRequest(message='change it',model='claude-opus-5-5',project=PROJECT)
        with patch.object(architect,'_claude',new=AsyncMock(return_value=raw)):
            with self.assertRaisesRegex(ValueError,'wrong revision'):asyncio.run(architect.call(request,AsyncMock(return_value=False)))
    def test_upstream_retry_is_used_and_non_throttle_errors_are_not_retried(self):
        agent=AWSArchitectAgent();agent.agent=lambda message: (_ for _ in ()).throw(ValueError('bad request'))
        with patch.object(agent.rate_limiter,'wait_if_needed') as limiter:
            with self.assertRaises(ValueError):agent._call_agent_with_retry('test')
            self.assertEqual(limiter.call_count,1)
    def test_upstream_retry_backs_off_on_throttle(self):
        agent=AWSArchitectAgent();calls=[]
        def fake(message):
            calls.append(message)
            if len(calls)==1:raise RuntimeError('Too many requests')
            return 'ok'
        agent.agent=fake
        with patch.object(agent.rate_limiter,'wait_if_needed'),patch('server.upstream.agent.aws_architect.time.sleep') as sleep:
            self.assertEqual(agent._call_agent_with_retry('test'),'ok');sleep.assert_called_once_with(2)

if __name__=='__main__':unittest.main()

class MaintenanceContractTests(unittest.TestCase):
    def test_maintenance_blocks_measures_and_scope_accepted(self):
        node=lambda i,kind,extra={}:{'id':i,'position':{'x':0,'y':0},'data':{'label':i,'kind':kind,'provider':'ibm',**extra}}
        project=dict(PROJECT,domain='maintenance',nodes=[node('s','stream',{'poc':True}),node('o','output',{'measures':[{'label':'Precision','path':'training.precision','op':'>=','target':0.8},{'label':'Grounded','path':'grounded','op':'==','target':True}]})],edges=[{'id':'w','source':'s','target':'o'}])
        parsed=Project.model_validate(project)
        self.assertTrue(parsed.nodes[0].data.poc);self.assertIs(parsed.nodes[1].data.measures[1].target,True);self.assertEqual(parsed.nodes[1].data.measures[0].target,0.8)
    def test_measure_paths_cannot_carry_code(self):
        project=dict(PROJECT,nodes=[{'id':'o','position':{'x':0,'y':0},'data':{'label':'o','kind':'output','provider':'aws','measures':[{'label':'x','path':'__import__("os")','op':'==','target':1}]}}])
        with self.assertRaises(ValueError):Project.model_validate(project)

class ContextTests(unittest.TestCase):
    def test_read_only_context_reaches_the_model_prompt(self):
        request=ChatRequest(message='Which region?',model='m',project=PROJECT,context=[{'type':'decision','id':'adr-003','text':'cloud.region — Region: eu-central-1 (Accepted)'}])
        payload=json.loads(AtMemArchitect.context(request))
        self.assertEqual(payload['readOnlyContext'][0]['id'],'adr-003')
    def test_context_rejects_unknown_types_and_fields(self):
        for item in [{'type':'command','id':'x','text':'rm'},{'type':'decision','id':'x','text':'t','extra':1}]:
            with self.assertRaises(ValueError):ChatRequest(message='m',model='m',project=PROJECT,context=[item])

class SkillsTests(unittest.TestCase):
    def test_agent_skills_are_in_the_system_prompt(self):
        from server.prompts import SYSTEM_PROMPT
        for text in ['You are AtMem AI Architect','"not sure" is always acceptable','What should this system help someone do?','RAG: answering questions from your documents','Which actions need a person to approve them first?']:
            self.assertIn(text,SYSTEM_PROMPT)
    def test_discovery_context_and_journey_stages_accepted(self):
        for stage in ['discover','design','review','estimate','deploy']:
            ChatRequest(message='m',model='m',project=PROJECT,stage=stage,context=[{'type':'discovery','id':'next-question','text':'Who will use it?'}])

class ProjectStoreTests(unittest.TestCase):
    def setUp(self):
        import tempfile,os
        self.dir=tempfile.TemporaryDirectory();os.environ['ATFORMA_HOME']=self.dir.name
        self.client=TestClient(app);self.h={'Authorization':f'Bearer {TOKEN}'}
    def tearDown(self):
        import os;os.environ.pop('ATFORMA_HOME',None);self.dir.cleanup()
    def file(self,name):
        return {'format':'atforma.project','formatVersion':'2.1.0','meta':{'id':'p1','name':name,'revision':1,'updatedAt':'2026-11-05T10:00:00Z'},'design':{'nodes':[],'edges':[]}}
    def post(self,path,body):return self.client.post(path,headers=self.h,json=body)
    def test_save_list_bin_restore_and_purge(self):
        self.assertEqual(self.post('/api/projects/save',{'id':'project-0001','file':self.file('RAG for HR')}).status_code,200)
        listed=self.post('/api/projects/list',{}).json();self.assertEqual([p['name'] for p in listed['projects']],['RAG for HR']);self.assertEqual(listed['bin'],[])
        self.assertEqual(self.post('/api/projects/get',{'id':'project-0001'}).json()['meta']['name'],'RAG for HR')
        self.assertEqual(self.post('/api/projects/purge',{'id':'project-0001'}).status_code,404,'only binned projects can be deleted for good')
        self.post('/api/projects/trash',{'id':'project-0001'})
        listed=self.post('/api/projects/list',{}).json();self.assertEqual(listed['projects'],[]);self.assertEqual(listed['bin'][0]['name'],'RAG for HR')
        self.assertEqual(self.post('/api/projects/save',{'id':'project-0001','file':self.file('x')}).status_code,409,'autosave never resurrects a binned project')
        self.post('/api/projects/restore',{'id':'project-0001'})
        self.assertEqual(len(self.post('/api/projects/list',{}).json()['projects']),1)
        self.post('/api/projects/trash',{'id':'project-0001'});self.assertEqual(self.post('/api/projects/purge',{'id':'project-0001'}).status_code,200)
        listed=self.post('/api/projects/list',{}).json();self.assertEqual(listed['projects']+listed['bin'],[])
    def test_save_digest_binds_exact_utf8_file_bytes(self):
        import hashlib
        from pathlib import Path
        result=self.post('/api/projects/save',{'id':'project-unicode','file':self.file('Gauge 🛰️ — centimetres')})
        self.assertEqual(result.status_code,200)
        content=(Path(self.dir.name)/'projects/project-unicode.atforma.json').read_bytes()
        self.assertEqual(result.json()['sha256'],hashlib.sha256(content).hexdigest())
        self.assertIn('🛰️'.encode(),content)
    def test_ids_and_files_are_validated_and_token_required(self):
        self.assertEqual(self.post('/api/projects/get',{'id':'../../etc/passwd'}).status_code,422)
        self.assertEqual(self.post('/api/projects/save',{'id':'project-0002','file':{'format':'other'}}).status_code,422)
        self.assertEqual(self.client.post('/api/projects/list',json={}).status_code,401)
