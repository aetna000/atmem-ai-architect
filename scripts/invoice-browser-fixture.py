"""Loopback fixture over real workflow/HTTP/browser sources and owned PostgreSQL.

Identity cookies, PDF storage and extraction are explicitly synthetic. This helper
is never exported. It does not exercise cloud auth, real OCR, models or delivery.
"""
import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
import socket
import sys
import threading
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'tests/runtime'),str(ROOT/'.local/azure-runtime-sdk')]
import psycopg
import uvicorn
from fastapi import Request
from fastapi.responses import JSONResponse,RedirectResponse
from durable_privileges_acceptance import create_runtime_roles
from durable_fixture_tasks import FIXTURE_CONTRACT
from durable_workflow import Denied,Principal
from workflow_worker import WorkflowRuntime,producer_store
from invoice_http import create_app
from invoice_http_acceptance import OwnedObjectsFixture

owner,_,_,api_dsn,worker_dsn=create_runtime_roles();account=str(uuid.uuid4());namespace='q'+uuid.uuid4().hex[:12]
with psycopg.connect(owner)as conn:
    conn.execute('INSERT INTO workflow.accounts(id)VALUES(%s)',(account,))
    for subject,roles in [('staff',['user']),('reviewer',['reviewer']),('supervisor',['supervisor'])]:conn.execute('INSERT INTO workflow.memberships(account_id,subject,roles)VALUES(%s,%s,%s)',(account,subject,roles))
release=threading.Event();release.set();effects=[]
expired=False
pkce=len(sys.argv)>1 and sys.argv[1]=='--pkce'
def processor(row):
    if not release.wait(20):raise RuntimeError('Synthetic extraction hold exceeded')
    return{'supplier':'<img src=x onerror=alert(1)> Fixture supplies','invoice_date':'2026-11-10','total':'42.50','currency':'AUD','requiresHumanReview':True,'notes':'Synthetic extraction: compare with the original PDF.','fieldEvidence':{'total':{'page':1,'channel':'text','quote':'Total: AUD 42.50'}}}
def deliver(row,**identity):effects.append(identity['idempotency_key']);return{'externalId':'synthetic-'+str(len(effects))}
worker=WorkflowRuntime(worker_dsn,processor,deliver,destination_contract=FIXTURE_CONTRACT,namespace=namespace)
store=producer_store(api_dsn,destination_contract=FIXTURE_CONTRACT,namespace=namespace)
def verify(token):
    if pkce and token=='fixture-access-token':return'reviewer'
    if token not in {'staff','reviewer','supervisor'}:raise Denied('Synthetic fixture login required')
    return token
sock=socket.socket();sock.bind(('127.0.0.1',0));origin='http://127.0.0.1:'+str(sock.getsockname()[1])
web_config={'mode':'oauth-pkce','authOrigin':'https://identity.fixture.invalid','authorizationEndpoint':'https://identity.fixture.invalid/authorize','tokenEndpoint':'https://identity.fixture.invalid/token','clientId':'fixture-public-client','scopes':'openid invoice/review'}if pkce else{'mode':'proxy','loginPath':'/login','logoutPath':'/logout'}
app=create_app(verify,store,OwnedObjectsFixture(),account_id=account,public_origin=origin,web_config=web_config)
@app.middleware('http')
async def fixture_identity(request,next_handler):
    if expired and request.url.path.startswith('/api/'):
        return JSONResponse({'error':'explicit-expired-proxy-fixture'},status_code=401)if request.headers.get('x-requested-with')=='XMLHttpRequest'else RedirectResponse('/login',status_code=302)
    if pkce:return await next_handler(request)
    subject=request.cookies.get('invoice-fixture','')
    request.scope['headers']=[(k,v)for k,v in request.scope['headers']if k!=b'authorization']+[(b'authorization',('Bearer '+subject).encode())]
    return await next_handler(request)
@app.get('/login')
def login():
    response=RedirectResponse('/');response.set_cookie('invoice-fixture','staff',httponly=True,samesite='strict');return response
@app.get('/logout')
def logout():
    response=RedirectResponse('/');response.delete_cookie('invoice-fixture');return response
@app.post('/_fixture')
async def control(request:Request):
    global expired
    value=await request.json();action=value.get('action');response=JSONResponse({'effects':len(effects)})
    if action=='hold':release.clear()
    elif action=='release':release.set()
    elif action=='expire':expired=True
    elif action=='identity':
        if value.get('subject')not in {'staff','reviewer','supervisor'}:raise ValueError('Invalid synthetic identity')
        response.set_cookie('invoice-fixture',value['subject'],httponly=True,samesite='strict')
    elif action in {'revoke','restore'}:
        with psycopg.connect(owner)as conn:conn.execute('UPDATE workflow.memberships SET active=%s WHERE account_id=%s',(action=='restore',account))
    elif action=='external-edit':
        operation=value['operation'];lease=worker.store.get(Principal(account,'reviewer'),operation)
        worker.store.edit_result(Principal(account,'reviewer'),operation,lease['result_revision'],{**lease['result'],'supplier':'Another reviewer saved this supplier'})
    elif action!='inspect':raise ValueError('Unknown fixture control')
    return response
@asynccontextmanager
async def lifespan(app):
    task=asyncio.create_task(worker.run(install_signal_handlers=False,fetch_job_polling_interval=.05,shutdown_graceful_timeout=1))
    try:yield
    finally:
        release.set();task.cancel()
        try:await task
        except asyncio.CancelledError:pass
app.router.lifespan_context=lifespan
print(json.dumps({'origin':origin,'boundary':'Real local HTTP/browser/PostgreSQL/queue; synthetic identity, objects, processor and destination.'}),flush=True)
uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=sock.getsockname()[1],log_level='warning',access_log=False)).run(sockets=[sock])
