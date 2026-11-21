import asyncio
import json
import unittest
from unittest.mock import AsyncMock, Mock, patch

from server.diagram_authoring import CATALOGUE, DiagramRequest, draft, validate


def record(id, kind, name):
    return {'id': id, 'kind': kind, 'name': name, 'basis': 'proposed', 'source': '', 'details': []}


class DiagramAuthoringTests(unittest.IsolatedAsyncioTestCase):
    def test_memory_publishes_each_reviewed_generic_skill_with_its_notation_fields(self):
        from server.diagram_skills import publish_diagram_skills
        memory = Mock()
        memory.enabled.return_value = True
        publish_diagram_skills(memory, 'test-project')
        cards = [json.loads(entry.args[3]) for entry in memory.enqueue.call_args_list]
        self.assertEqual({card['id'] for card in cards}, {view['id'] for view in CATALOGUE})
        self.assertEqual(len(cards), 28)
        self.assertTrue(all(entry.args[1] == 'knowledge' and len(entry.args[3]) <= 1900 for entry in memory.enqueue.call_args_list))
        memory.reset_mock()
        with patch('server.diagram_skills.REVIEWED_DIGEST', 'changed'):
            publish_diagram_skills(memory, 'test-project')
        memory.enqueue.assert_not_called()
        memory.enabled.return_value = False
        publish_diagram_skills(memory, 'test-project')
        memory.enqueue.assert_not_called()

    async def test_six_passes_share_ids_and_checklist_feedback_repairs_a_gap(self):
        calls = []
        async def model(provider, name, prompt, *args, **kwargs):
            context = json.loads(prompt)
            active = context['catalogue']
            ids = {row['id'] for row in active}
            calls.append((ids, context.get('review')))
            output = {'version': 1, 'elements': [], 'relations': [], 'views': [
                {'id': 'diagram-'+row['id'], 'kind': row['id'], 'name': row['title'],
                 'elementIds': [], 'relationIds': [], 'gaps': ['Insufficient fixture evidence.']} for row in active]}
            if 'context' in ids:
                output['elements'] = [record('clinic', 'system', 'Clinic'), record('patient','actor','Patient')]
                output['relations'] = [dict(record('uses', 'interaction','Requests care'), fromId='patient', toId='clinic')]
                current = output['views'][0]
                current.update(elementIds=['clinic','patient'], relationIds=['uses'], gaps=[])
            if 'sequence' in ids:
                self.assertIn('patient', {row['id'] for row in context['existingModel']['elements']})
            if 'erd' in ids:
                output['elements'] = [record('referral','table','Referral')]
                current = next(row for row in output['views'] if row['kind']=='erd')
                current.update(elementIds=['referral'],gaps=[])
                if context.get('review'):
                    self.assertIn('Primary key', context['review']['erd'][0])
                    output['elements'][0]['details'] = [
                        {'name':'Columns','value':'referral_id uuid NOT NULL PK'}, {'name':'Primary key','value':'referral_id'}]
            return output
        payload = DiagramRequest(provider='codex',model='default',specification='A clinic receives referrals and schedules follow-up.')
        progress = AsyncMock()
        with patch('server.diagram_authoring.call_cli',side_effect=model):
            result = await draft(None,payload,lambda:asyncio.sleep(0,result=False),progress)
        self.assertEqual(len(result['views']),28)
        self.assertGreater(progress.await_count,6)
        self.assertEqual(progress.await_args_list[-1].args[0]['checkpoint']['views'][-1]['kind'],'migration')
        self.assertEqual({view['kind'] for view in result['views']},{row['id'] for row in CATALOGUE})
        self.assertFalse(next(row for row in result['views'] if row['kind']=='erd')['gaps'])
        self.assertGreater(len(calls),6)

    def test_rejects_missing_endpoints(self):
        view = {'id':'view-context','kind':'context','name':'Context','elementIds':['clinic'],'relationIds':['link'],'gaps':[]}
        with self.assertRaisesRegex(ValueError,'existing endpoints'):
            validate({'version':1,'elements':[record('clinic','system','Clinic')],
                      'relations':[dict(record('link','interaction','Action'),fromId='missing',toId='clinic')],
                      'views':[view]},['context'])

    async def test_timed_out_batch_splits_and_preserves_the_rest_of_the_set(self):
        sized = []
        async def model(provider, name, prompt, *args, **kwargs):
            active = json.loads(prompt)['catalogue']
            sized.append([row['id'] for row in active])
            if len(active)>2 and active[0]['group']=='Runtime & behaviour':
                raise TimeoutError('Fixture timeout')
            return {'version':1,'elements':[],'relations':[],'views':[
                {'id':'view-'+row['id'], 'kind':row['id'], 'name':row['title'],
                 'elementIds':[], 'relationIds':[], 'gaps':['Evidence needed.']}
                for row in active]}
        payload=DiagramRequest(provider='codex',model='default',specification='A referral workbench.')
        with patch('server.diagram_authoring.call_cli',side_effect=model):
            result=await draft(None,payload,lambda:asyncio.sleep(0,result=False))
        self.assertEqual(len(result['views']),28)
        self.assertIn(['sequence','event-flow'],sized)
        self.assertIn(['workflow'],sized)
        self.assertIn(['state','journey'],sized)

    async def test_long_sources_use_small_batches_from_the_start(self):
        sized=[]
        async def model(provider, name, prompt, *args, **kwargs):
            active=json.loads(prompt)['requiredViewKinds']
            sized.append(len(active))
            return {'version':1, 'elements':[], 'relations':[], 'views':[
                {'id':'view-'+kind, 'kind':kind, 'name':kind, 'elementIds':[],
                 'relationIds':[], 'gaps':['Evidence needed.']} for kind in active]}
        request=DiagramRequest(provider='codex',model='default',specification='Referral policy and contract. '*1500)
        with patch('server.diagram_authoring.call_cli',side_effect=model):
            result=await draft(None,request,lambda:asyncio.sleep(0,result=False))
        self.assertEqual(len(result['views']),28)
        self.assertLessEqual(max(sized),1)


class DiagramReviewRegressionTests(unittest.TestCase):
    def test_explained_empty_views_are_reported_as_incomplete(self):
        from server.diagram_authoring import View, SKILLS
        from server.diagram_quality import review
        page=View(id='clinic-schema',name='Clinic schema',kind='erd',elementIds=[],relationIds=[],gaps=['Need more information.'])
        self.assertTrue(review([page],{}, {},SKILLS)['erd'])

class DiagramResumeTests(unittest.IsolatedAsyncioTestCase):
    async def test_resume_preserves_checked_page_and_requests_only_remaining_types(self):
        original={'version':1,'elements':[record('clinic','system','Clinic')],
                  'relations':[],'views':[{'id':'clinic-context','kind':'context','name':'Clinic context',
                  'elementIds':['clinic'],'relationIds':[],'gaps':['External actors await owner confirmation.']}]}
        requested=[]
        async def model(provider,name,prompt,*args,**kwargs):
            payload=json.loads(prompt);kinds=payload['requiredViewKinds'];requested.extend(kinds)
            return {'version':1,'elements':[],'relations':[],'views':[
                {'id':'view-'+kind,'name':kind,'kind':kind,'elementIds':[],'relationIds':[],
                 'gaps':['Fixture lacks the relevant evidence.']} for kind in kinds]}
        progress=AsyncMock()
        payload=DiagramRequest(provider='codex',model='default',specification='A clinic receives referrals.',resume=original)
        with patch('server.diagram_authoring.call_cli',side_effect=model):
            result=await draft(None,payload,lambda:asyncio.sleep(0,result=False),progress)
        self.assertNotIn('context',requested)
        self.assertEqual(result['views'][0],original['views'][0])
        self.assertEqual(result['elements'][0],original['elements'][0])
        self.assertEqual(len(result['views']),28)
        self.assertEqual(len(progress.await_args_list[-1].args[0]['checkpoint']['views']),28)
