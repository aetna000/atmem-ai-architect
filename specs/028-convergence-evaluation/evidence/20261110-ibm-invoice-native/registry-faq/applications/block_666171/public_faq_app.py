"""Explicit public-only FAQ application; private app authentication stays separate."""
import json
import os
from pathlib import Path
import re
from public_catalog_store import HttpCatalogStore,S3CatalogStore
from public_faq import PublicFaq,object_pairs
from structured_http import create_app as create_http_app

def gateway_origin(origin,region):
    # The HTTP API is created before its Lambda integration, so its owned origin
    # is an explicit environment input without a resource self-reference cycle.
    if not isinstance(origin,str) or not re.fullmatch(r'https://[a-z0-9]{1,20}\.execute-api\.'+re.escape(region)+r'\.amazonaws\.com',origin):raise ValueError('Invalid owned HTTP API origin')
    return origin

def create_app(config,store,model,*,static_root=None,origin_validator=None):
    # Only this explicitly selected public application admits anonymous visitors.
    # No caller can select a provider, model, source, tool or editing operation.
    c={**config,'max_input':2000,'csp':"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"}
    return create_http_app(c,lambda token:'anonymous-public-reader',PublicFaq(store.load,model.generate),lambda:{'maxInputBytes':2000,'requestDeadlineMs':28000,'sourcePolicy':'public-catalog-only'},
        static_root=static_root,require_origin=True,origin_validator=origin_validator)

def app_factory():
    root=Path(__file__).parent
    with (root/'faq-deployment.json').open('rb') as stream:raw=stream.read(1025)
    if len(raw)>1024:raise ValueError('Invalid owned FAQ deployment metadata')
    deployment=json.loads(raw,object_pairs_hook=object_pairs)
    if not isinstance(deployment,dict) or set(deployment)!={'provider','format'} or deployment['format']!='public-faq-v1':raise ValueError('Invalid owned FAQ deployment contract')
    provider=deployment['provider'];env=os.environ;validator=None
    if provider=='aws':
        from aws_json_model import BedrockJsonModel,read_model_config
        c=read_model_config(env);model=BedrockJsonModel(c);store=S3CatalogStore(env['CATALOG_BUCKET'],c['REGION'],env['ACCOUNT_ID']);c['PUBLIC_ORIGIN']=gateway_origin(env['PUBLIC_ORIGIN'],c['REGION'])
    elif provider=='azure':
        from azure_structured import AzureModel,read_model_config
        c=read_model_config(env);model=AzureModel(c);store=HttpCatalogStore('azure','',env['CATALOG_CONTAINER'],lambda:{'Authorization':'Bearer '+model.credential.get_token('https://storage.azure.com/.default').token},account=env['CATALOG_ACCOUNT'])
        c['PUBLIC_ORIGIN']=env.get('PUBLIC_ORIGIN') or 'https://'+env['WEBSITE_HOSTNAME']
        if not re.fullmatch(r'https://[a-z0-9-]{2,100}(?:\.[a-z0-9-]{2,60})?\.azurewebsites\.net',c['PUBLIC_ORIGIN']):raise ValueError('Invalid application origin')
    elif provider=='gcp':
        from gcp_structured import VertexModel,read_model_config
        c=read_model_config(env);model=VertexModel(c);store=HttpCatalogStore('gcp',c['REGION'],env['CATALOG_BUCKET'],model.workload_headers)
        c['PUBLIC_ORIGIN']=env['PUBLIC_ORIGIN']
        if not re.fullmatch(r'https://[a-z0-9-]+(?:\.[a-z0-9-]+)?\.run\.app',c['PUBLIC_ORIGIN']):raise ValueError('Invalid application origin')
    elif provider=='ibm':
        from ibm_structured import WatsonModel,read_model_config
        c=read_model_config(env);model=WatsonModel(c);store=HttpCatalogStore('ibm',c['MODEL_REGION'],env['CATALOG_BUCKET'],model._headers)
        c['PUBLIC_ORIGIN']=env.get('PUBLIC_ORIGIN') or 'https://'+env['CE_APP']+'.'+env['CE_SUBDOMAIN']+'.'+env['CE_DOMAIN']
        if not re.fullmatch(r'https://[a-z0-9-]+\.[a-z0-9-]+\.[a-z]{2}-[a-z]+\.codeengine(?:\.dev)?\.appdomain\.cloud',c['PUBLIC_ORIGIN']):raise ValueError('Invalid application origin')
    else:raise ValueError('Unsupported owned FAQ provider')
    return create_app(c,store,model,static_root=root/'web',origin_validator=validator)
