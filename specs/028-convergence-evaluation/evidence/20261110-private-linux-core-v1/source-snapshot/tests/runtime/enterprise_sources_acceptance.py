"""Documented native API contract fixtures, no vendor account calls."""
import io
import json
from pathlib import Path
import sys
import time
import unittest
from urllib.error import HTTPError,URLError
from urllib.parse import parse_qs,urlsplit
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src/runtime'))
from enterprise_sources import ConfluenceCloud,DelegatedAccess,GraphSharePoint,Reply,NativeHttp,SourceChanged,SourceDenied,SourceUnavailable,checked_url

CLOUD='11111111-1111-4111-8111-111111111111'
def access(**changes):return DelegatedAccess(**{'subject':'alice','source_subject':'native-alice','token':'SYNTHETIC-USER-TOKEN','expires_at':time.time()+3600,**changes})
def reply(value,status=200,headers=None):return Reply(status,headers or {},json.dumps(value).encode())
class Http:
    def __init__(self,handler):self.handler=handler;self.calls=[]
    def get(self,url,token,*,hosts,limit=2000000):
        checked_url(url,hosts);self.calls.append((url,token,limit));return self.handler(url,token)

def graph_item(version='v1'):
    return {'id':'item1','name':'Private title','eTag':version,'file':{'mimeType':'text/plain'},'parentReference':{'driveId':'drive1'},'webUrl':'https://tenant.sharepoint.com/file'}
def profile(url):
    if url=='https://api.atlassian.com/me':return reply({'account_id':'native-alice','account_status':'active'})
    if url=='https://api.atlassian.com/oauth/token/accessible-resources':return reply([{'id':CLOUD,'url':'https://tenant.atlassian.net','scopes':['read:page:confluence','search:confluence']}])
def page(version=1,space='42'):
    return {'id':'100','title':'Private page','status':'current','spaceId':space,'version':{'number':version},'body':{'storage':{'value':'<p>Approved &amp; current</p><script>untrusted script</script>'}}}
class NativeSourceContracts(unittest.TestCase):
    def test_native_http_denials_close_response_and_hide_upstream_body(self):
        for status in [401,403,404,410,429,503]:
            body=io.BytesIO(b'PRIVATE-UPSTREAM-BODY');error=HTTPError('https://graph.microsoft.com/v1.0/private',status,'secret upstream detail',{},body)
            class Opener:
                def open(self,request,timeout):raise error
            transport=NativeHttp();transport.opener=Opener()
            with self.assertRaises(SourceUnavailable)as caught:transport.get('https://graph.microsoft.com/v1.0/me','SYNTHETIC',hosts={'graph.microsoft.com'})
            self.assertNotIn('PRIVATE',str(caught.exception));self.assertNotIn('secret',str(caught.exception));self.assertTrue(body.closed)

    def test_native_http_redirect_is_not_followed_and_oversize_closes_stream(self):
        body=io.BytesIO(b'ignored');error=HTTPError('https://graph.microsoft.com/v1.0/content',302,'Found',{'Location':'https://tenant.sharepoint.com/download'},body);calls=[]
        class Opener:
            def open(self,request,timeout):calls.append(request);raise error
        transport=NativeHttp();transport.opener=Opener();result=transport.get('https://graph.microsoft.com/v1.0/content','SYNTHETIC',hosts={'graph.microsoft.com'})
        self.assertEqual(result.status,302);self.assertEqual(len(calls),1);self.assertTrue(body.closed)
        class Response(io.BytesIO):
            status=200;headers={}
        response=Response(b'123456')
        class Big:
            def open(self,request,timeout):return response
        transport.opener=Big()
        with self.assertRaisesRegex(SourceUnavailable,'source_response_too_large'):transport.get('https://graph.microsoft.com/v1.0/content','SYNTHETIC',hosts={'graph.microsoft.com'},limit=5)
        self.assertTrue(response.closed)

    def test_credentials_expiry_subject_and_app_only_deny_without_network(self):
        for credential,subject in [(access(subject='bob'),'alice'),(access(kind='application'),'alice'),(access(expires_at=time.time()),'alice'),(access(expires_at=float('nan')),'alice'),(access(token='bad\nheader'),'alice')]:
            http=Http(lambda u,t:reply({}));source=GraphSharePoint('drive1','tenant.sharepoint.com',credential,http=http)
            with self.assertRaises(SourceDenied):source.search('policy',subject)
            self.assertEqual(http.calls,[])
        self.assertNotIn('SYNTHETIC-USER-TOKEN',repr(access()))

    def test_graph_paging_dedup_and_drive_scope(self):
        calls=[]
        def handler(url,token):
            if '/me?'in url:return reply({'id':'native-alice'})
            calls.append(url)
            if len(calls)==1:return reply({'value':[{'id':'item1','file':{},'parentReference':{'driveId':'drive1'}},{'id':'other','file':{},'parentReference':{'driveId':'other-drive'}}],'@odata.nextLink':url+'&$skipToken=next'})
            return reply({'value':[{'id':'item1','file':{},'parentReference':{'driveId':'drive1'}},{'id':'item2','file':{},'parentReference':{'driveId':'drive1'}}]})
        http=Http(handler);source=GraphSharePoint('drive1','tenant.sharepoint.com',access(),http=http)
        self.assertEqual(source.search("Alice's plan",'alice'),('item1','item2'));self.assertEqual(len(calls),2);self.assertIn("Alice%27%27s%20plan",calls[0])

    def test_graph_foreign_paging_refuses_token_exfiltration(self):
        def handler(url,token):return reply({'id':'native-alice'})if'/me?'in url else reply({'value':[],'@odata.nextLink':'https://evil.example/collect'})
        http=Http(handler);source=GraphSharePoint('drive1','tenant.sharepoint.com',access(),http=http)
        with self.assertRaises(SourceUnavailable):source.search('policy','alice')
        self.assertEqual(len(http.calls),2)

    def test_graph_download_strips_bearer_and_rechecks_version(self):
        def handler(url,token):
            if '/me?'in url:return reply({'id':'native-alice'})
            if url.endswith('/content'):return Reply(302,{'Location':'https://tenant.sharepoint.com/download?capability=SYNTHETIC'},b'')
            if '/download?'in url:self.assertIsNone(token);return Reply(200,{},b'authorized content')
            return reply(graph_item())
        http=Http(handler);source=GraphSharePoint('drive1','tenant.sharepoint.com',access(),http=http)
        document=source.fetch('item1','alice',lambda raw,mime:raw.decode());self.assertEqual(document.text,'authorized content');self.assertNotIn('authorized content',repr(document));source.revalidate(document,'alice');self.assertEqual(len([c for c in http.calls if'/items/item1?'in c[0]]),3)

    def test_graph_foreign_download_refused_before_storage_request(self):
        def handler(url,token):
            if '/me?'in url:return reply({'id':'native-alice'})
            if url.endswith('/content'):return Reply(302,{'Location':'https://evil.example/private'},b'')
            return reply(graph_item())
        http=Http(handler);source=GraphSharePoint('drive1','tenant.sharepoint.com',access(),http=http)
        with self.assertRaises(SourceUnavailable):source.fetch('item1','alice',lambda raw,mime:'text')
        self.assertFalse(any('evil.example'in c[0]for c in http.calls))

    def test_graph_mid_download_change_or_revocation_denies_document(self):
        for revoked in [False,True]:
            reads=[]
            def handler(url,token):
                if '/me?'in url:return reply({'id':'native-alice'})
                if url.endswith('/content'):return Reply(200,{},b'authorized content')
                reads.append(url)
                if len(reads)>1 and revoked:raise SourceDenied('source_access_denied')
                return reply(graph_item('v2'if len(reads)>1 else'v1'))
            source=GraphSharePoint('drive1','tenant.sharepoint.com',access(),http=Http(handler))
            with self.assertRaises(SourceUnavailable):source.fetch('item1','alice',lambda raw,mime:'text')

    def test_graph_identity_mismatch_and_source_outage(self):
        http=Http(lambda url,token:reply({'id':'bob'}));source=GraphSharePoint('drive1','tenant.sharepoint.com',access(),http=http)
        with self.assertRaises(SourceDenied):source.search('policy','alice')
        self.assertEqual(len(http.calls),1)
        def down(url,token):raise SourceUnavailable('source_request_failed')
        source=GraphSharePoint('drive1','tenant.sharepoint.com',access(),http=Http(down))
        with self.assertRaises(SourceUnavailable):source.search('policy','alice')

    def confluence(self,handler):return ConfluenceCloud(CLOUD,'tenant.atlassian.net',{'ENG':'42'},access(),http=Http(handler))
    def test_confluence_native_cql_keys_and_paged_opaque_ids(self):
        queries=[]
        def handler(url,token):
            identity=profile(url)
            if identity:return identity
            queries.append(parse_qs(urlsplit(url).query))
            return reply({'results':[{'content':{'id':'100','type':'page'}}],'_links':{'next':'/rest/api/search?cursor=next'}})if len(queries)==1 else reply({'results':[{'content':{'id':'101','type':'page'}}]})
        source=self.confluence(handler);self.assertEqual(source.search('a "quoted" question','alice'),('100','101'))
        self.assertIn('space in ("ENG")',queries[0]['cql'][0]);self.assertNotIn('space in (42)',queries[0]['cql'][0]);self.assertIn('\\"quoted\\"',queries[0]['cql'][0])

    def test_confluence_current_page_space_id_and_sanitized_text(self):
        source=self.confluence(lambda url,token:profile(url)or reply(page()));document=source.fetch('100','alice');self.assertEqual(document.text,'Approved & current');self.assertEqual(document.version,'1');self.assertNotIn('Private page',repr(document));source.revalidate(document,'alice')

    def test_confluence_wrong_space_archived_and_revoked_deny(self):
        for value in [page(space='999'),{**page(),'status':'trashed'}]:
            source=self.confluence(lambda url,token:profile(url)or reply(value))
            with self.assertRaises(SourceDenied):source.fetch('100','alice')
        calls=[]
        def handler(url,token):
            identity=profile(url)
            if identity:return identity
            calls.append(url)
            if len(calls)>1:raise SourceDenied('source_access_denied')
            return reply(page())
        source=self.confluence(handler);document=source.fetch('100','alice')
        with self.assertRaises(SourceDenied):source.revalidate(document,'alice')

    def test_confluence_version_change_detected_and_site_grant_required(self):
        calls=[]
        def handler(url,token):
            identity=profile(url)
            if identity:return identity
            calls.append(url);return reply(page(len(calls)))
        source=self.confluence(handler);document=source.fetch('100','alice')
        with self.assertRaises(SourceChanged):source.revalidate(document,'alice')
        source=self.confluence(lambda url,token:reply([])if'accessible-resources'in url else profile(url))
        with self.assertRaises(SourceDenied):source.search('policy','alice')

    def test_confluence_foreign_paging_and_identity_mismatch(self):
        source=self.confluence(lambda url,token:profile(url)or reply({'results':[],'_links':{'next':'https://evil.example/private'}}))
        with self.assertRaises(SourceUnavailable):source.search('policy','alice')
        source=self.confluence(lambda url,token:reply({'account_id':'bob','account_status':'active'}))
        with self.assertRaises(SourceDenied):source.search('policy','alice')

if __name__=='__main__':unittest.main()
