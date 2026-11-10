"""Fixed browser assets and reviewed public sign-in configuration, no private data."""
from pathlib import Path
import re
from urllib.parse import urlsplit
from fastapi.responses import FileResponse

def install_web(app,configuration,root=None):
    if not isinstance(configuration,dict):raise ValueError('Supply owned public browser configuration')
    config=dict(configuration);mode=config.get('mode')
    if mode=='proxy':
        if set(config)!={'mode','loginPath','logoutPath'}:raise ValueError('Invalid proxy sign-in configuration')
        for field in ['loginPath','logoutPath']:
            value=config[field]
            if field=='logoutPath'and value is None:continue
            if not isinstance(value,str)or not value.startswith('/')or value.startswith('//')or '\\'in value or any(ord(c)<33 or ord(c)>126 for c in value):raise ValueError('Use an owned same-origin sign-in path')
        connect="'self'"
    elif mode=='oauth-pkce':
        if set(config)!={'mode','authOrigin','authorizationEndpoint','tokenEndpoint','clientId','scopes'}:raise ValueError('Invalid public PKCE configuration')
        origin=urlsplit(config['authOrigin'])
        if origin.scheme!='https'or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?(?::443)?',origin.netloc)or'..'in origin.netloc or origin.path not in {'','/'}or origin.username or origin.query or origin.fragment:raise ValueError('Use the exact trusted HTTPS authorization origin')
        for field in ['authorizationEndpoint','tokenEndpoint']:
            value=urlsplit(config[field])
            if value.scheme!='https'or value.netloc!=origin.netloc or value.username or value.query or value.fragment:raise ValueError('Sign-in endpoints must belong to the trusted authority')
        for field in ['clientId','scopes']:
            if not isinstance(config[field],str)or not 1<=len(config[field])<=1024 or any(ord(c)<32 or ord(c)>126 for c in config[field]):raise ValueError('Invalid public client configuration')
        connect="'self' "+origin.scheme+'://'+origin.netloc
    else:raise ValueError('Use native proxy or authorization-code PKCE sign-in')
    assets=Path(root or Path(__file__).parent)
    for name in ['invoice-web.html','invoice-web.js','invoice-web.css']:
        if not(assets/name).is_file():raise ValueError('Invoice browser asset is missing')
    @app.get('/config.json')
    def public_configuration():return config
    @app.get('/')
    def index():return FileResponse(assets/'invoice-web.html',media_type='text/html')
    @app.get('/app.js')
    def script():return FileResponse(assets/'invoice-web.js',media_type='text/javascript')
    @app.get('/app.css')
    def style():return FileResponse(assets/'invoice-web.css',media_type='text/css')
    return "default-src 'self'; script-src 'self'; style-src 'self'; connect-src "+connect+"; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
