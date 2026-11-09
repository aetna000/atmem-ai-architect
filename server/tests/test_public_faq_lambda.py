"""Real Mangum HTTP API v2 event adaptation; model/storage are scripted."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src/runtime'))
from mangum import Mangum
from public_faq import parse_catalog
from public_faq_app import create_app

ORIGIN='https://faq123.execute-api.ap-southeast-2.amazonaws.com'
TEXT='Unused adapters can be returned within twenty-one days after delivery.'

def event(path='/api/ask',body=None,origin=ORIGIN,method='POST'):
    return {'version':'2.0','routeKey':'$default','rawPath':path,'rawQueryString':'','headers':{'host':'faq123.execute-api.ap-southeast-2.amazonaws.com','content-type':'application/json',**({'origin':origin}if origin else {})},'requestContext':{'accountId':'123456789012','apiId':'faq123','domainName':'faq123.execute-api.ap-southeast-2.amazonaws.com','domainPrefix':'faq123','http':{'method':method,'path':path,'protocol':'HTTP/1.1','sourceIp':'127.0.0.1','userAgent':'synthetic-fixture'},'requestId':'fixture-request','routeKey':'$default','stage':'$default','time':'10/Nov/2026:00:00:00 +0000','timeEpoch':1794268800000},'body':json.dumps({'text':'adapter returns'}if body is None else body),'isBase64Encoded':False}

class PublicFaqLambdaTests(unittest.TestCase):
    def setUp(self):
        self.store=Mock();self.store.load.return_value=parse_catalog(json.dumps({'format':'atmem-public-faq-v1','revision':'v1','articles':[{'id':'returns','revision':'r1','title':'Adapter returns','text':TEXT,'url':'','visibility':'public'}]}).encode(),'"version1"')
        self.model=Mock();self.model.generate.return_value=json.dumps({'answer':'Return unused adapters within twenty-one days.','citations':[{'id':'returns','quote':TEXT}],'abstained':False})
        self.adapter=Mangum(create_app({'PUBLIC_ORIGIN':ORIGIN},self.store,self.model),lifespan='off')
    def test_actual_v2_event_produces_cited_proxy_response_and_no_store_headers(self):
        reply=self.adapter(event(),Mock());self.assertEqual(reply['statusCode'],200);body=json.loads(reply['body']);self.assertEqual(body['result']['citations'][0]['id'],'returns');self.assertFalse(reply['isBase64Encoded']);self.assertEqual(reply['headers']['cache-control'],'no-store')
    def test_reused_lambda_adapter_does_not_reuse_an_answer_after_article_deletion(self):
        self.assertEqual(self.adapter(event(),Mock())['statusCode'],200)
        self.store.load.return_value=parse_catalog(b'{"format":"atmem-public-faq-v1","revision":"deleted","articles":[]}','"version2"')
        reply=self.adapter(event(),Mock());self.assertEqual(reply['statusCode'],200);self.assertTrue(json.loads(reply['body'])['result']['abstained']);self.assertEqual(self.model.generate.call_count,1)
    def test_http_event_cannot_add_source_or_editor_authority_or_bypass_origin(self):
        for request in [event(origin=None),event(origin='https://attacker.test')]:self.assertEqual(self.adapter(request,Mock())['statusCode'],403)
        self.assertEqual(self.adapter(event(body={'text':'adapter returns','source':'private'}),Mock())['statusCode'],400);self.model.generate.assert_not_called();self.store.load.assert_not_called()
    def test_health_and_browser_assets_are_represented_as_real_proxy_responses(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);(root/'index.html').write_text('<!doctype html><title>Public FAQ</title>');(root/'app.js').write_text('/* synthetic browser asset */');(root/'app.css').write_text('body { color: black; }')
            adapter=Mangum(create_app({'PUBLIC_ORIGIN':ORIGIN},self.store,self.model,static_root=root),lifespan='off')
            for path in ['/','/app.js','/app.css','/healthz','/config.json']:
                reply=adapter(event(path,method='GET'),Mock());self.assertEqual(reply['statusCode'],200,path);self.assertEqual(reply['headers']['cache-control'],'no-store')
        self.model.generate.assert_not_called();self.store.load.assert_not_called()

if __name__=='__main__':unittest.main()
