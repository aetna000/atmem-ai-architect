import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src/runtime'))
from public_faq import CatalogUnavailable,parse_catalog
from public_faq_app import create_app,gateway_origin

TEXT='Refund requests are accepted within thirty days after purchase.'
def current():return parse_catalog(json.dumps({'format':'atmem-public-faq-v1','revision':'v1','articles':[{'id':'refund','revision':'r1','title':'Refund policy','text':TEXT,'url':'https://help.example.test/refund','visibility':'public'}]}).encode(),'etag1')

class PublicFaqHttpTests(unittest.TestCase):
    def setUp(self):
        self.store=Mock();self.store.load.return_value=current();self.model=Mock();self.model.generate.return_value=json.dumps({'answer':'Request a refund within thirty days.','citations':[{'id':'refund','quote':TEXT}],'abstained':False})
        self.client=TestClient(create_app({'PUBLIC_ORIGIN':'https://help.example.test'},self.store,self.model));self.headers={'Origin':'https://help.example.test'}
    def test_explicit_public_endpoint_serves_cited_answer_without_user_identity(self):
        response=self.client.post('/api/ask',headers=self.headers,json={'text':'refund policy'})
        self.assertEqual(response.status_code,200);self.assertTrue(response.json()['requiresHumanReview']);self.assertEqual(response.json()['result']['citations'][0]['id'],'refund');self.assertEqual(response.headers['Cache-Control'],'no-store')
        self.assertEqual(self.client.get('/config.json').json()['sourcePolicy'],'public-catalog-only');self.assertEqual(self.client.get('/healthz').json(),{'status':'running'})
    def test_origin_missing_wrong_or_private_source_overrides_never_call_model(self):
        for headers in [{},{'Origin':'https://attacker.test'}]:self.assertEqual(self.client.post('/api/ask',headers=headers,json={'text':'refund'}).status_code,403)
        for body in [{'text':'refund','source':'private'},{'text':'refund','role':'editor'},{'text':'é'*1001}]:self.assertEqual(self.client.post('/api/ask',headers=self.headers,json=body).status_code,400)
        self.store.load.assert_not_called();self.model.generate.assert_not_called()
    def test_no_http_editor_route_can_be_unlocked_by_forged_headers(self):
        for url in ['/api/catalog','/api/articles','/api/admin/articles']:
            self.assertEqual(self.client.post(url,headers={**self.headers,'Authorization':'Bearer forged-editor'},json={'delete':'refund'}).status_code,404)
        self.store.save.assert_not_called()
    def test_unknown_question_abstains_without_calling_model(self):
        response=self.client.post('/api/ask',headers=self.headers,json={'text':'What is the weather in Paris?'})
        self.assertEqual(response.status_code,200);self.assertTrue(response.json()['result']['abstained']);self.assertEqual(response.json()['result']['citations'],[]);self.model.generate.assert_not_called()
    def test_source_outage_or_forged_citation_does_not_leak_input_or_return_partial_answer(self):
        self.store.load.side_effect=CatalogUnavailable();response=self.client.post('/api/ask',headers=self.headers,json={'text':'refund PRIVATE_INPUT'})
        self.assertEqual(response.status_code,503);self.assertNotIn('PRIVATE_INPUT',response.text);self.assertNotIn('result',response.json());self.model.generate.assert_not_called()
        self.store.load.side_effect=None;self.model.generate.return_value=json.dumps({'answer':'PRIVATE_BAD_ANSWER','citations':[{'id':'private-payroll','quote':TEXT}],'abstained':False})
        response=self.client.post('/api/ask',headers=self.headers,json={'text':'refund'})
        self.assertEqual(response.status_code,503);self.assertNotIn('PRIVATE_BAD_ANSWER',response.text);self.assertNotIn('result',response.json())
    def test_owned_gateway_origin_does_not_admit_another_site_region_or_request_path(self):
        origin='https://abc123.execute-api.ap-southeast-2.amazonaws.com'
        self.assertEqual(gateway_origin(origin,'ap-southeast-2'),origin)
        client=TestClient(create_app({'PUBLIC_ORIGIN':origin},self.store,self.model),base_url=origin)
        self.assertEqual(client.post('/api/ask',headers={'Origin':origin},json={'text':'refund'}).status_code,200)
        for value in [None,'null','https://attacker.test',origin+'.attacker.test',origin.replace('https:','http:'),origin+'/path',origin+'?query=1',origin+':444',origin.replace('ap-southeast-2','us-east-1')]:
            with self.subTest(origin=value):
                with self.assertRaises(ValueError):gateway_origin(value,'ap-southeast-2')
                if value:self.assertEqual(client.post('/api/ask',headers={'Origin':value},json={'text':'refund'}).status_code,403)

if __name__=='__main__':unittest.main()
