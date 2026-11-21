"""Company-session API and native source consent callbacks.

Existing company login supplies the verified API bearer token at bootstrap. The
browser cannot choose an account, source account, model, URL or permission mapping.
Native secrets/model/decoding/SQL transports are separate owned adapters.
"""
from dataclasses import dataclass
import html
import json
import re
from urllib.parse import parse_qs,urlsplit
from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse,HTMLResponse,RedirectResponse,Response
from starlette.concurrency import run_in_threadpool
from enterprise_identity import trusted_https
from enterprise_sources import SourceDenied,SourceUnavailable,checked_url
from public_faq import InvalidAnswer,object_pairs

COOKIE='__Host-enterprise-session'
CSRF='x-csrf-token'


@dataclass(frozen=True)
class SourceConnection:
    label: str
    kind: str
    driver: object


def problem(code,status):
    messages={'signin':'Sign in with your company account to continue.','forbidden':'Your account cannot access this workspace. Ask your workspace owner for access.','request':'Check your question or refresh this page and try again.','setup':'Your workspace owner needs to enable a company source for your account.','source':'Connect your company sources before asking a question.','busy':'Your source connection is updating. Try again in a moment.','capacity':'You already have questions processing. Wait for one to finish or cancel it before asking another.','unavailable':'Your workspace could not finish this answer. Please try again shortly.','answer':'This answer could not be verified against your current sources. Please try again.'}
    return JSONResponse({'error':{'code':code,'message':messages[code]}},status_code=status)


def callback_notice(label):
    title='We could not finish connecting '+label
    return HTMLResponse('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><main><h1>'+html.escape(title)+'</h1><p>Return to your workspace, sign in if needed, and choose Connect again.</p><a href="/">Return to your workspace</a></main></html>',status_code=400)


def create_app(identity,sessions,connections,make_engine,*,public_origin,web_config=None,static_root=None,answers=None):
    trusted_https(public_origin);origin=urlsplit(public_origin)
    if origin.path not in {'','/'}or public_origin.endswith('/'):raise ValueError('Use the canonical owned HTTPS origin without a trailing slash')
    if not isinstance(connections,dict)or not 1<=len(connections)<=20 or not callable(make_engine):raise ValueError('Supply owned native source and application adapters')
    grants=set()
    for alias,entry in connections.items():
        if not isinstance(alias,str)or not re.fullmatch(r'[a-z][a-z0-9_-]{0,31}',alias)or not isinstance(entry,SourceConnection)or entry.kind not in {'graph','confluence'}or not isinstance(entry.label,str)or not 1<=len(entry.label)<=80:raise ValueError('Invalid configured source connection')
        driver=entry.driver
        if driver.store is not sessions.auth or driver.redirect!=public_origin+'/oauth/callback/'+alias:raise ValueError('Source consent must use the owned store and exact callback')
        key=(entry.kind,driver.client,getattr(driver,'tenant',None))
        if key in grants:raise ValueError('Use one consent/cache per vendor grant and share it across its document sources')
        grants.add(key)
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    callback_paths={'/oauth/callback/'+alias for alias in connections}
    auth=sessions.auth
    if answers is not None and(answers.store.auth is not auth or answers.store.account_id!=identity.account_id or answers.connections!=connections):raise ValueError('Queued answers must use the same owned account, authority and sources')
    csp="default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    if web_config is not None:
        if answers is None:raise ValueError('The browser workspace requires the durable question service')
        from enterprise_web import install_web
        csp=install_web(app,identity,connections,web_config,static_root)
    def cookie(request):
        fields=[part.strip().split('=',1)for header in request.headers.getlist('cookie')for part in header.split(';')]
        matches=[value for field,*value in fields if field==COOKIE]
        if len(matches)>1:raise SourceDenied('company_identity_required')
        return request.cookies.get(COOKIE,'')
    async def actor(request,*,csrf=False):
        session=await run_in_threadpool(sessions.authenticate,cookie(request))
        if session.principal.account_id!=identity.account_id:raise SourceDenied('company_identity_required')
        if csrf:
            if request.headers.get('origin')!=public_origin:raise SourceDenied('browser_request_denied')
            session.require_csrf(request.headers.get(CSRF,''))
        return session
    async def body(request,limit=8192):
        data=bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data)>limit:raise ValueError('Body exceeds the owned request limit')
        return bytes(data)
    async def json_body(request):
        if request.headers.get('content-type','').split(';')[0].strip().lower()!='application/json':raise ValueError('Use JSON')
        value=json.loads(await body(request),object_pairs_hook=object_pairs)
        if not isinstance(value,dict):raise ValueError('Use an object')
        return value
    def source(alias):
        if alias not in connections:raise ValueError('Unknown source')
        return connections[alias]
    @app.middleware('http')
    async def boundary(request,next_handler):
        try:
            callback=request.url.path in callback_paths
            supplied=request.headers.get('origin')
            if not callback and supplied and supplied!=public_origin:response=problem('forbidden',403)
            else:response=await next_handler(request)
        except SourceDenied as error:
            code=str(error)
            if code in {'company_identity_required','company_identity_expired'}:response=problem('signin',401)
            elif code=='source_consent_unavailable':response=problem('unavailable',503)
            elif code=='source_mapping_required':response=problem('setup',403)
            elif code in {'source_reconnection_required','source_consent_required'}:response=problem('source',409)
            else:response=problem('forbidden',403)
        except SourceUnavailable as error:response=problem('capacity',429)if str(error)=='query_capacity_reached'else problem('busy'if str(error)=='source_refresh_in_progress'else'unavailable',503)
        except InvalidAnswer:response=problem('answer',503)
        except(ValueError,UnicodeError,RecursionError):response=problem('request',400)
        except Exception:response=problem('unavailable',503)
        response.headers.update({'Cache-Control':'no-store','Pragma':'no-cache','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Strict-Transport-Security':'max-age=31536000','Content-Security-Policy':csp})
        return response
    @app.get('/healthz')
    def health():return {'status':'running'}
    @app.post('/api/session')
    async def bootstrap(request:Request):
        if request.headers.get('origin')!=public_origin:raise SourceDenied('browser_request_denied')
        if await json_body(request)!={}:raise ValueError('No caller identity fields')
        header=request.headers.get('authorization','')
        principal=await run_in_threadpool(identity.verify,header[7:]if header.startswith('Bearer ')else'')
        created=await run_in_threadpool(sessions.create,principal,cookie(request))
        response=JSONResponse({'signedIn':True,'csrfToken':created.csrf})
        response.set_cookie(COOKIE,created.token,max_age=created.max_age,secure=True,httponly=True,samesite='none',path='/')
        return response
    @app.get('/api/session')
    async def describe(request:Request):
        # Non-simple header blocks cross-site scripts/tags from retrieving CSRF.
        # No CORS capability is granted to another origin.
        if request.headers.get('x-workspace-request')!='session':raise SourceDenied('browser_request_denied')
        user=await actor(request)
        rows=[]
        for alias,entry in connections.items():rows.append({'id':alias,'name':entry.label,'status':await run_in_threadpool(auth.connection_status,user.principal,entry.driver.source_id)})
        return {'signedIn':True,'csrfToken':user.csrf,'sources':rows}
    @app.delete('/api/session')
    async def logout(request:Request):
        user=await actor(request,csrf=True);await run_in_threadpool(sessions.revoke,user)
        response=Response(status_code=204);response.delete_cookie(COOKIE,path='/',secure=True,httponly=True,samesite='none');return response
    @app.post('/api/sources/{alias}/connect')
    async def connect(alias:str,request:Request):
        user=await actor(request,csrf=True);entry=source(alias)
        if await json_body(request)!={}:raise ValueError('No caller source or callback settings')
        if await run_in_threadpool(auth.connection_status,user.principal,entry.driver.source_id)=='needs_setup':raise SourceDenied('source_mapping_required')
        start=await run_in_threadpool(entry.driver.start,user.principal,user.browser_nonce)
        checked_url(start.url,{'login.microsoftonline.com'if entry.kind=='graph'else'auth.atlassian.com'})
        return {'authorizationUrl':start.url}
    @app.delete('/api/sources/{alias}')
    async def disconnect(alias:str,request:Request):
        user=await actor(request,csrf=True);entry=source(alias);await run_in_threadpool(auth.disconnect,user.principal,entry.driver.source_id);return Response(status_code=204)
    @app.api_route('/oauth/callback/{alias}',methods=['GET','POST'])
    async def callback(alias:str,request:Request):
        entry=source(alias)
        try:
            if request.method!=('POST'if entry.kind=='graph'else'GET'):raise ValueError('Incorrect consent response method')
            user=await actor(request)
            if request.method=='POST':
                if request.headers.get('content-type','').split(';')[0].strip().lower()!='application/x-www-form-urlencoded':raise ValueError('Incorrect consent content type')
                params=parse_qs((await body(request,16384)).decode('utf-8'),keep_blank_values=True,strict_parsing=True,max_num_fields=12)
            else:
                if len(request.url.query)>16384:raise ValueError('Consent response too large')
                params=parse_qs(request.url.query,keep_blank_values=True,strict_parsing=True,max_num_fields=12)
            if any(len(values)!=1 for values in params.values())or not params.get('state'):raise ValueError('Invalid consent response')
            if params.get('error'):
                await run_in_threadpool(auth.consume,user.principal,entry.driver.source_id,user.browser_nonce,params['state'][0]);return callback_notice(entry.label)
            if not params.get('code'):raise ValueError('Missing consent code')
            await run_in_threadpool(entry.driver.finish,user.principal,user.browser_nonce,params['state'][0],params['code'][0])
            return RedirectResponse('/?connection=connected&source='+alias,status_code=303)
        except Exception:return callback_notice(entry.label)
    @app.post('/api/ask')
    async def ask(request:Request):
        user=await actor(request,csrf=True);value=await json_body(request)
        if set(value)!={'question'}or not isinstance(value['question'],str)or not value['question'].strip()or len(value['question'])>1000:raise ValueError('Supply only the question')
        def answer():
            def authorize(subject):
                if subject!=user.principal.key:raise SourceDenied('company_identity_required')
                sessions.authenticate(cookie(request))
            from enterprise_knowledge import current_engine
            engine=current_engine(auth,connections,user.principal,make_engine,authorize)
            result=engine.answer(value['question'],user.principal.key)
            # Independent final company-session gate, beyond source document gates.
            sessions.authenticate(cookie(request))
            return result
        return await run_in_threadpool(answer)
    @app.post('/api/queries')
    async def submit_question(request:Request):
        user=await actor(request,csrf=True);value=await json_body(request)
        if answers is None:raise SourceUnavailable('question_worker_unavailable')
        if set(value)!={'question','requestId'}or not isinstance(value['question'],str)or not value['question'].strip()or len(value['question'])>1000:raise ValueError('Supply a question and request identity')
        from enterprise_queries import QueryConflict
        try:identity=await run_in_threadpool(answers.store.submit,user,value['question'],value['requestId'])
        except QueryConflict:return JSONResponse({'error':{'code':'request','message':'This question could not be submitted. Please send it again.'}},status_code=409)
        return JSONResponse({'id':identity,'status':'queued'},status_code=202)
    @app.get('/api/queries/{query_id}')
    async def question_status(query_id:str,request:Request):
        if request.headers.get('x-workspace-request')!='session':raise SourceDenied('browser_request_denied')
        user=await actor(request)
        if answers is None:raise SourceUnavailable('question_worker_unavailable')
        from enterprise_queries import QueryMissing
        try:result=await run_in_threadpool(answers.status,user,query_id)
        except QueryMissing:return JSONResponse({'error':{'code':'request','message':'This question is no longer available.'}},status_code=404)
        await run_in_threadpool(sessions.authenticate,cookie(request))
        return result
    @app.get('/api/queries')
    async def pending_questions(request:Request):
        if request.headers.get('x-workspace-request')!='session':raise SourceDenied('browser_request_denied')
        user=await actor(request)
        if answers is None:raise SourceUnavailable('question_worker_unavailable')
        return {'queries':await run_in_threadpool(answers.store.pending,user)}
    @app.delete('/api/queries/{query_id}')
    async def cancel_question(query_id:str,request:Request):
        user=await actor(request,csrf=True)
        if answers is None:raise SourceUnavailable('question_worker_unavailable')
        from enterprise_queries import QueryMissing
        try:await run_in_threadpool(answers.store.cancel,user,query_id)
        except QueryMissing:return JSONResponse({'error':{'code':'request','message':'This question is no longer available.'}},status_code=404)
        return Response(status_code=204)
    return app
