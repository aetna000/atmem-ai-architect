"""Owned loopback TLS/SQL/browser fixture; scripted vendor/model responses only.

Never export this server or its public-client IdP/control endpoints as an app.
Private fixture certificate/key and SQL credentials remain local.
"""
import argparse
import asyncio
import base64
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import secrets
import socket
import sys
import threading
import time
from urllib.parse import parse_qs,urlencode
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src/runtime'),str(ROOT/'tests/runtime'),str(ROOT/'.local/azure-runtime-sdk')]
import jwt
import psycopg
import uvicorn
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes,serialization
from fastapi import Request
from fastapi.responses import JSONResponse,RedirectResponse,StreamingResponse
import enterprise_http_postgres as fixture_module
from enterprise_http import create_app
from enterprise_queries import producer_queries,initialize_query_store,grant_query_runtime
from enterprise_query_service import EnterpriseAnswers,EnterpriseQueryWorker
from psycopg.conninfo import conninfo_to_dict

parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);args=parser.parse_args();out=Path(args.out).resolve()
if out.exists()or not out.is_relative_to(ROOT/'.local'):raise ValueError('Use a fresh local fixture directory')
out.mkdir(parents=True,mode=0o700)
sock=socket.socket();sock.bind(('127.0.0.1',0));origin='https://127.0.0.1:'+str(sock.getsockname()[1]);fixture_module.ORIGIN=origin
fixture_module.CompanyHttpIntegration.setUpClass();fixture=fixture_module.CompanyHttpIntegration(methodName='test_login_cookie_flags_hashes_and_reload_csrf');asyncio.run(fixture.asyncSetUp())
key=fixture.signing;name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'localhost')]);now=datetime.now(timezone.utc)
import ipaddress
certificate=x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=1)).add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'),x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),critical=False).sign(key,hashes.SHA256())
private=out/'server.key';private.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()));private.chmod(0o600)
cert=out/'server.crt';cert.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
config={'clientId':'public-web-client','authorizationEndpoint':origin+'/fixture/authorize','tokenEndpoint':origin+'/fixture/token','scopes':['openid','profile','knowledge.read']}
with psycopg.connect(fixture.owner_dsn)as conn:initialize_query_store(conn);grant_query_runtime(conn,conninfo_to_dict(fixture.app_dsn)['user'],worker=True)
query_store=producer_queries(fixture.store,fixture.app_dsn,fixture.account)
held=threading.Event();release=threading.Event();model_held=threading.Event();model_release=threading.Event();pause={'answer':False,'model':False}
def make_engine(*args):
    engine=fixture.engine_factory(*args);original=engine.generate
    def generate(*values):
        if pause['model']:
            pause['model']=False;model_held.set();model_release.wait(12)
        return original(*values)
    engine.generate=generate;return engine
answers=EnterpriseAnswers(query_store,fixture.connections,make_engine)
worker=EnterpriseQueryWorker(fixture.app_dsn,answers)
app=create_app(fixture.identity,fixture.sessions,fixture.connections,make_engine,public_origin=origin,web_config=config,answers=answers)
@app.middleware('http')
async def delay_owned_answer(request,next_handler):
    response=await next_handler(request)
    if pause['answer']and request.url.path.startswith('/api/queries/')and request.method=='GET'and response.status_code==200:
        payload=b''.join([chunk async for chunk in response.body_iterator])
        ready=json.loads(payload).get('status')=='ready'
        if ready:pause['answer']=False
        async def stream():
            if ready:
                yield payload[:10];held.set();await asyncio.to_thread(release.wait,10);yield payload[10:]
            else:yield payload
        return StreamingResponse(stream(),status_code=200,headers=dict(response.headers))
    return response
codes={};counts={'companyAuthorize':0,'companyToken':0,'pkceVerified':0};lock=threading.Lock()
@app.get('/fixture/authorize')
async def authorize(request:Request):
    q=request.query_params
    if q.get('client_id')!='public-web-client'or q.get('redirect_uri')!=origin+'/company-callback'or q.get('response_type')!='code'or q.get('code_challenge_method')!='S256'or not q.get('code_challenge')or not q.get('state'):return JSONResponse({'error':'invalid_request'},status_code=400)
    code=secrets.token_urlsafe(32)
    with lock:codes[code]={'challenge':q['code_challenge'],'nonce':q.get('nonce'),'expires':time.time()+300};counts['companyAuthorize']+=1
    return RedirectResponse(origin+'/company-callback?'+urlencode({'code':code,'state':q['state']}),status_code=303)
@app.post('/fixture/token')
async def token(request:Request):
    body=await request.body()
    if len(body)>8192:return JSONResponse({'error':'invalid_request'},status_code=400)
    q=parse_qs(body.decode(),keep_blank_values=True,max_num_fields=12)
    if any(len(values)!=1 for values in q.values()):return JSONResponse({'error':'invalid_request'},status_code=400)
    get=lambda k:q.get(k,[''])[0]
    with lock:record=codes.pop(get('code'),None);counts['companyToken']+=1
    expected=base64.urlsafe_b64encode(hashlib.sha256(get('code_verifier').encode()).digest()).decode().rstrip('=')
    if not record or record['expires']<time.time()or get('grant_type')!='authorization_code'or get('client_id')!='public-web-client'or get('redirect_uri')!=origin+'/company-callback'or expected!=record['challenge']:return JSONResponse({'error':'invalid_grant'},status_code=400)
    with lock:counts['pkceVerified']+=1
    now=int(time.time());base={'iss':fixture.principal.issuer,'sub':'alice','iat':now,'exp':now+3600}
    access=jwt.encode({**base,'aud':'knowledge-api','scp':'knowledge.read'},key,algorithm='RS256',headers={'kid':'fixture-key'})
    identity=jwt.encode({**base,'aud':'public-web-client',**({'nonce':record['nonce']}if record['nonce']else{})},key,algorithm='RS256',headers={'kid':'fixture-key'})
    return {'access_token':access,'id_token':identity,'token_type':'Bearer','expires_in':3600,'scope':'openid profile knowledge.read'}

def control():
    for line in sys.stdin:
        try:
            packet=json.loads(line);command=packet.get('command')
            if command=='graph_nonce':fixture.graph_http.nonce=packet['nonce'];result={'ok':True}
            elif command in {'revoke','restore'}:
                with psycopg.connect(fixture.owner_dsn)as conn:conn.execute('UPDATE enterprise_auth.memberships SET active=%s WHERE account_id=%s AND principal_key=%s',(command=='restore',fixture.account,fixture.principal.key))
                result={'ok':True}
            elif command=='injection':fixture.source_title='<img src=x onerror="window.privateXss=true">';result={'ok':True}
            elif command=='hold_answer':pause['answer']=True;held.clear();release.clear();result={'ok':True}
            elif command=='release_answer':release.set();result={'ok':True}
            elif command=='hold_model':pause['model']=True;model_held.clear();model_release.clear();result={'ok':True}
            elif command=='release_model':model_release.set();result={'ok':True}
            elif command=='inspect':
                with psycopg.connect(fixture.owner_dsn)as conn:query_count=conn.execute('SELECT count(*)FROM enterprise_queries.requests WHERE account_id=%s',(fixture.account,)).fetchone()[0]
                result={'answerHeld':held.is_set(),'modelHeld':model_held.is_set(),'queryRequests':query_count,**counts,'modelCalls':len(fixture.model_calls),'auditEvents':len(fixture.audit),'graphCodeExchanges':sum(c[0]=='POST'for c in fixture.graph_http.calls),'confluenceExchanges':sum(c[0]=='POST'for c in fixture.confluence_http.calls)}
            else:raise ValueError('Unknown local fixture command')
            print(json.dumps({'control':packet.get('id'),'result':result}),flush=True)
        except Exception:print(json.dumps({'control':packet.get('id'),'error':'fixture_control_failed'}),flush=True)
threading.Thread(target=control,daemon=True).start()
print(json.dumps({'ready':origin,'fixture':'owned-loopback-TLS-SQL','vendorCalls':False}),flush=True)
server=uvicorn.Server(uvicorn.Config(app,log_level='error',access_log=False,ssl_keyfile=str(private),ssl_certfile=str(cert)))
async def serve():
    task=asyncio.create_task(worker.run(install_signal_handlers=False,fetch_job_polling_interval=.05,shutdown_graceful_timeout=1))
    try:await server.serve(sockets=[sock])
    finally:
        task.cancel()
        try:await task
        except asyncio.CancelledError:pass
asyncio.run(serve())
asyncio.run(fixture.asyncTearDown())
