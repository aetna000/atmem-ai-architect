"""Owned static browser assets and public OIDC registration configuration."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from fastapi.responses import FileResponse
from enterprise_identity import trusted_https


def company_configuration(identity,config):
    if not isinstance(config,dict)or set(config)!={'clientId','authorizationEndpoint','tokenEndpoint','scopes'}:raise ValueError('Supply only public company OIDC registration fields')
    if not isinstance(config['clientId'],str)or not 1<=len(config['clientId'])<=200:raise ValueError('Use the owned public company client ID')
    authorization=trusted_https(config['authorizationEndpoint']);token=trusted_https(config['tokenEndpoint'])
    scopes=config['scopes']
    if not isinstance(scopes,list)or not 3<=len(scopes)<=8 or any(not isinstance(scope,str)or not 1<=len(scope)<=300 or any(c.isspace()for c in scope)for scope in scopes)or len(set(scopes))!=len(scopes)or not {'openid','profile'}.issubset(scopes)or 'offline_access'in scopes or not any(scope==identity.scope or scope.endswith('/'+identity.scope)for scope in scopes):raise ValueError('Use OIDC and the owned delegated API scope without browser refresh credentials')
    return {'issuer':identity.issuer,'clientId':config['clientId'],'authorizationEndpoint':authorization,'tokenEndpoint':token,'scopes':list(scopes)}


def install_web(app,identity,connections,config,static_root=None):
    company=company_configuration(identity,config)
    token=company['tokenEndpoint']
    root=Path(static_root)if static_root is not None else Path(__file__).parent
    lock=json.loads((root/'enterprise-web-lock.json').read_text())
    if hashlib.sha256((root/'enterprise-web-app.js').read_bytes()).hexdigest()!=lock['bundleSha256']:raise ValueError('Use the exact reviewed browser bundle')
    # Native source constructors already validate these tenant citation hosts.
    hosts=sorted({entry.driver.host for entry in connections.values()})
    public={'company':company,'citationHosts':hosts,'authorizationOrigins':['https://login.microsoftonline.com','https://auth.atlassian.com']}
    @app.get('/api/web-config')
    def web_config():return public
    @app.get('/')
    @app.get('/company-callback')
    def index():return FileResponse(root/'enterprise-web.html',media_type='text/html')
    @app.get('/assets/workspace.js')
    def javascript():return FileResponse(root/'enterprise-web-app.js',media_type='application/javascript')
    @app.get('/assets/workspace.css')
    def stylesheet():return FileResponse(root/'enterprise-web.css',media_type='text/css')
    @app.get('/assets/notices.txt')
    def notices():return FileResponse(root/'enterprise-web-notices.txt',media_type='text/plain')
    return "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self' "+urlsplit(token).scheme+'://'+urlsplit(token).netloc+"; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
