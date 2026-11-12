"""Native read-only SharePoint/Confluence source boundary.

Per-user delegated credentials come from a trusted OAuth broker, never chat/model
input or a shared crawler identity. No private documents or permissions are cached.
These API adapters do not implement that broker, an index, or the model API.
"""
from dataclasses import dataclass, field
from html.parser import HTMLParser
import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit, unquote
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler


class SourceUnavailable(RuntimeError):
    pass


class SourceDenied(SourceUnavailable):
    pass


class SourceChanged(SourceUnavailable):
    pass


@dataclass(frozen=True)
class DelegatedAccess:
    subject: str
    source_subject: str
    token: str = field(repr=False)
    expires_at: float
    kind: str = 'delegated'

    def require(self, subject, now=None):
        now=time.time()if now is None else now
        if self.kind!='delegated'or not subject or self.subject!=subject or not self.source_subject or not isinstance(self.token,str)or not self.token or len(self.token)>32768 or any(c in self.token for c in '\r\n')or not isinstance(self.expires_at,(int,float))or isinstance(self.expires_at,bool)or not now+5<self.expires_at<now+86401:
            raise SourceDenied('source_identity_unavailable')


@dataclass(frozen=True)
class SourceDocument:
    source: str
    id: str
    version: str
    title: str = field(repr=False)
    text: str = field(repr=False)
    url: str = field(repr=False)


@dataclass(frozen=True)
class Reply:
    status: int
    headers: dict
    body: bytes = field(repr=False)


def checked_url(url,hosts):
    try:parts=urlsplit(url);port=parts.port
    except (TypeError,ValueError):raise SourceUnavailable('invalid_source_url')from None
    if parts.scheme!='https'or parts.hostname not in hosts or port not in {None,443}or parts.username or parts.password or parts.fragment or len(url)>16000 or any(c in url for c in '\r\n'):
        raise SourceUnavailable('invalid_source_url')
    return url


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,msg,headers,newurl):
        return None


class NativeHttp:
    def __init__(self):
        # A source bearer token must not be routed through environment proxies.
        self.opener=build_opener(ProxyHandler({}),NoRedirect())

    def get(self,url,token,*,hosts,limit=2000000):
        checked_url(url,hosts)
        headers={'Accept':'application/json','Cache-Control':'no-store'}
        if token:headers['Authorization']='Bearer '+token
        try:
            response=self.opener.open(Request(url,headers=headers),timeout=10)
        except HTTPError as error:
            try:
                if error.code in {301,302,303,307,308}:
                    return Reply(error.code,dict(error.headers),b'')
                if error.code in {401,403,404,410}:raise SourceDenied('source_access_denied')from None
                raise SourceUnavailable('source_request_failed')from None
            finally:error.close()
        except (URLError,OSError,ValueError):raise SourceUnavailable('source_request_failed')from None
        with response:
            body=response.read(limit+1)
            if len(body)>limit:raise SourceUnavailable('source_response_too_large')
            return Reply(response.status,dict(response.headers),body)


def decoded(reply):
    if reply.status!=200:raise SourceUnavailable('source_response_failed')
    try:value=json.loads(reply.body)
    except (ValueError,UnicodeError):raise SourceUnavailable('invalid_source_response')from None
    if not isinstance(value,dict):raise SourceUnavailable('invalid_source_response')
    return value


def identifier(value):
    if not isinstance(value,str)or not re.fullmatch(r'[A-Za-z0-9_!.,-]{1,256}',value):raise SourceUnavailable('invalid_source_identifier')
    return quote(value,safe='')


def query_text(value):
    if not isinstance(value,str)or not value.strip()or len(value)>1000 or any(ord(c)<32 for c in value):raise SourceUnavailable('invalid_source_query')
    return value.strip()


class GraphSharePoint:
    def __init__(self,drive_id,sharepoint_host,access,*,http=None):
        self.drive_id=drive_id;self.drive=identifier(drive_id);self.source='sharepoint:'+drive_id
        if not isinstance(sharepoint_host,str)or not re.fullmatch(r'[a-z0-9][a-z0-9-]*\.sharepoint\.com',sharepoint_host):raise SourceUnavailable('invalid_sharepoint_host')
        self.host=sharepoint_host;self.access=access;self.http=http or NativeHttp()
        self.base='https://graph.microsoft.com/v1.0'

    def _get(self,path,subject):
        self.access.require(subject)
        return decoded(self.http.get(self.base+path,self.access.token,hosts={'graph.microsoft.com'}))

    def identify(self,subject):
        if self._get('/me?$select=id',subject).get('id')!=self.access.source_subject:raise SourceDenied('source_identity_mismatch')

    def search(self,question,subject,*,limit=20):
        if type(limit)is not int or not 1<=limit<=100:raise SourceUnavailable('invalid_search_limit')
        self.identify(subject)
        q=quote(query_text(question).replace("'","''"),safe='')
        route=f"/drives/{self.drive}/root/search(q='{q}')"
        url=self.base+route+'?'+urlencode({'$top':min(limit,100),'$select':'id,file,parentReference'})
        result=[];seen=set();pages=set()
        while url and len(result)<limit:
            checked_url(url,{'graph.microsoft.com'})
            if unquote(urlsplit(url).path)!=unquote(urlsplit(self.base+route).path)or url in pages or len(pages)>=20:raise SourceUnavailable('invalid_source_paging')
            pages.add(url);self.access.require(subject)
            value=decoded(self.http.get(url,self.access.token,hosts={'graph.microsoft.com'}))
            if not isinstance(value.get('value'),list):raise SourceUnavailable('invalid_source_response')
            for row in value['value']:
                if not isinstance(row,dict):raise SourceUnavailable('invalid_source_response')
                if row.get('parentReference',{}).get('driveId')!=self.drive_id or not isinstance(row.get('file'),dict):continue
                identity=row.get('id');identifier(identity)
                if identity not in seen:seen.add(identity);result.append(identity)
                if len(result)==limit:break
            url=value.get('@odata.nextLink')
        return tuple(result)

    def metadata(self,identity,subject):
        value=self._get('/drives/'+self.drive+'/items/'+identifier(identity)+'?'+urlencode({'$select':'id,name,eTag,file,parentReference,webUrl,deleted'}),subject)
        if value.get('id')!=identity or value.get('deleted')or not isinstance(value.get('file'),dict)or value.get('parentReference',{}).get('driveId')!=self.drive_id or not isinstance(value.get('eTag'),str)or not value['eTag']:
            raise SourceDenied('source_document_unavailable')
        checked_url(value.get('webUrl',''),{self.host})
        return value

    def fetch(self,identity,subject,decode):
        self.identify(subject);before=self.metadata(identity,subject)
        self.access.require(subject)
        reply=self.http.get(self.base+'/drives/'+self.drive+'/items/'+identifier(identity)+'/content',self.access.token,hosts={'graph.microsoft.com'},limit=10000000)
        if reply.status==302:
            # Download capability URL is short lived: never persist/log it and
            # never forward the Graph bearer token to the storage endpoint.
            location=reply.headers.get('Location')or reply.headers.get('location')
            checked_url(location,{self.host})
            reply=self.http.get(location,None,hosts={self.host},limit=10000000)
        if reply.status!=200:raise SourceUnavailable('source_download_failed')
        text=decode(reply.body,before['file'].get('mimeType','application/octet-stream'))
        if not isinstance(text,str)or not text.strip()or len(text)>200000:raise SourceUnavailable('source_document_unsupported')
        after=self.metadata(identity,subject)
        if after['eTag']!=before['eTag']:raise SourceChanged('source_document_changed')
        title=after.get('name')
        if not isinstance(title,str)or not title or len(title)>1000:raise SourceUnavailable('invalid_source_response')
        return SourceDocument(self.source,identity,after['eTag'],title,text,after['webUrl'])

    def revalidate(self,document,subject):
        if document.source!=self.source or self.metadata(document.id,subject)['eTag']!=document.version:raise SourceChanged('source_document_changed')


class PageText(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.parts=[];self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in {'script','style'}:self.hidden+=1
        elif not self.hidden and tag in {'p','br','div','li','h1','h2','h3','tr'}:self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in {'script','style'}and self.hidden:self.hidden-=1
    def handle_data(self,data):
        if not self.hidden:self.parts.append(data)


class ConfluenceCloud:
    def __init__(self,cloud_id,site_host,spaces,access,*,http=None):
        if not isinstance(cloud_id,str)or not re.fullmatch(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',cloud_id):raise SourceUnavailable('invalid_confluence_cloud')
        if not isinstance(site_host,str)or not re.fullmatch(r'[a-z0-9][a-z0-9-]*\.atlassian\.net',site_host):raise SourceUnavailable('invalid_confluence_host')
        if not isinstance(spaces,dict)or not spaces or len(spaces)>100 or any(not isinstance(k,str)or not re.fullmatch(r'[A-Za-z0-9_~-]{1,128}',k)or not isinstance(v,str)or not re.fullmatch(r'[0-9]{1,30}',v)for k,v in spaces.items()):raise SourceUnavailable('invalid_confluence_spaces')
        self.source='confluence:'+cloud_id;self.cloud_id=cloud_id;self.base='https://api.atlassian.com/ex/confluence/'+cloud_id;self.host=site_host;self.space_ids=set(spaces.values());self.space_keys=set(spaces);self.access=access;self.http=http or NativeHttp()

    def _get(self,path,subject):
        self.access.require(subject)
        return decoded(self.http.get(self.base+path,self.access.token,hosts={'api.atlassian.com'}))

    def identify(self,subject):
        self.access.require(subject)
        value=decoded(self.http.get('https://api.atlassian.com/me',self.access.token,hosts={'api.atlassian.com'}))
        if value.get('account_id')!=self.access.source_subject or value.get('account_status')!='active':raise SourceDenied('source_identity_mismatch')
        reply=self.http.get('https://api.atlassian.com/oauth/token/accessible-resources',self.access.token,hosts={'api.atlassian.com'})
        try:resources=json.loads(reply.body)
        except (ValueError,UnicodeError):raise SourceUnavailable('invalid_source_response')from None
        if reply.status!=200 or not isinstance(resources,list):raise SourceUnavailable('invalid_source_response')
        allowed=[r for r in resources if isinstance(r,dict)and r.get('id')==self.cloud_id and r.get('url')=='https://'+self.host]
        if len(allowed)!=1 or not isinstance(allowed[0].get('scopes'),list)or 'read:page:confluence'not in allowed[0]['scopes']or not {'search:confluence','read:content-details:confluence'}.intersection(allowed[0]['scopes']):raise SourceDenied('source_site_unavailable')

    def search(self,question,subject,*,limit=20):
        if type(limit)is not int or not 1<=limit<=100:raise SourceUnavailable('invalid_search_limit')
        self.identify(subject);term=query_text(question).replace('\\','\\\\').replace('"','\\"')
        # IDs and query are data, never executable caller-supplied CQL.
        cql='type=page AND space in ('+','.join('"'+key+'"'for key in sorted(self.space_keys))+') AND text ~ "'+term+'"'
        route='/wiki/rest/api/search';url=self.base+route+'?'+urlencode({'cql':cql,'limit':min(limit,25)})
        result=[];seen=set();pages=set()
        while url and len(result)<limit:
            checked_url(url,{'api.atlassian.com'})
            if urlsplit(url).path!=urlsplit(self.base+route).path or url in pages or len(pages)>=20:raise SourceUnavailable('invalid_source_paging')
            self.access.require(subject);pages.add(url)
            value=decoded(self.http.get(url,self.access.token,hosts={'api.atlassian.com'}))
            if not isinstance(value.get('results'),list):raise SourceUnavailable('invalid_source_response')
            for row in value['results']:
                content=row.get('content',{})if isinstance(row,dict)else{}
                identity=content.get('id')
                if content.get('type')!='page':continue
                if not isinstance(identity,str)or not re.fullmatch(r'[0-9]{1,30}',identity):raise SourceUnavailable('invalid_source_response')
                if identity not in seen:seen.add(identity);result.append(identity)
                if len(result)==limit:break
            next_url=value.get('_links',{}).get('next');url=None
            if next_url:
                if next_url.startswith('/rest/api/search?'):url=self.base+'/wiki'+next_url
                elif next_url.startswith('/wiki/rest/api/search?'):url=self.base+next_url
                else:url=next_url
        return tuple(result)

    def fetch(self,identity,subject,decode=None):
        if not isinstance(identity,str)or not re.fullmatch(r'[0-9]{1,30}',identity):raise SourceUnavailable('invalid_source_identifier')
        self.identify(subject)
        value=self._get('/wiki/api/v2/pages/'+identity+'?body-format=storage',subject)
        if value.get('id')!=identity or value.get('status')!='current'or value.get('spaceId')not in self.space_ids:raise SourceDenied('source_document_unavailable')
        version=value.get('version',{}).get('number');title=value.get('title');html=value.get('body',{}).get('storage',{}).get('value')
        if type(version)is not int or version<1 or not isinstance(title,str)or not title or len(title)>1000 or not isinstance(html,str)or len(html)>1000000:raise SourceUnavailable('invalid_source_response')
        parser=PageText();parser.feed(html);text=''.join(parser.parts).strip()
        if not text or len(text)>200000:raise SourceUnavailable('source_document_unsupported')
        # Construct a fixed same-site citation, never an API-supplied redirect URL.
        return SourceDocument(self.source,identity,str(version),title,text,'https://'+self.host+'/wiki/pages/viewpage.action?pageId='+identity)

    def revalidate(self,document,subject):
        if document.source!=self.source or self.fetch(document.id,subject).version!=document.version:raise SourceChanged('source_document_changed')
