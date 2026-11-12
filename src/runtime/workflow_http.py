"""Typed approval-workflow HTTP boundary with operator-owned tenant and policy.

No domain inference, identity provider, role administration or automatic execution
is provided here. Trusted bootstrap supplies the verifier, typed store and origin.
Acceptance means durable enqueue, never completed processing or delivery.
"""
import asyncio
import json
import re
import threading
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from durable_workflow import Principal, Denied, Missing, Conflict, identifier
from workflow_payload import PayloadContract
from workflow_configuration import owned_origin

MAX_BODY = 66000  # Includes the envelope; typed data itself remains <=64000.


class BodyTooLarge(ValueError): pass
class UnsupportedBody(ValueError): pass
class Busy(RuntimeError): pass


def public_operation(row, *, include_source=False):
    result = {'id':str(row['id']), 'state':row['state'], 'revision':row['result_revision'],
            'result':row['result'], 'receipt':row['receipt'],
            'createdAt':row['created_at'].isoformat(), 'updatedAt':row['updated_at'].isoformat()}
    if include_source: result['source'] = row['source_ref']
    return result


async def body(request, fields):
    types = request.headers.getlist('content-type')
    if len(types) != 1 or types[0].split(';')[0].lower() != 'application/json':
        raise UnsupportedBody('Use application/json')
    lengths = request.headers.getlist('content-length')
    if len(lengths) > 1 or lengths and not re.fullmatch(r'0|[1-9][0-9]{0,8}',lengths[0]):
        raise ValueError('Use an exact body length')
    expected = int(lengths[0]) if lengths else None
    if expected is not None and expected > MAX_BODY: raise BodyTooLarge()
    raw = bytearray()
    async with asyncio.timeout(5):
        async for chunk in request.stream():
            if len(raw) + len(chunk) > MAX_BODY: raise BodyTooLarge()
            raw.extend(chunk)
    if expected is not None and len(raw) != expected: raise ValueError('Body length differs')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError('Duplicate application field')
            result[key] = value
        return result
    def constant(_): raise ValueError('Nonfinite JSON is unsupported')
    value = json.loads(raw.decode('utf-8'),object_pairs_hook=unique,parse_constant=constant)
    if type(value) is not dict or set(value) != set(fields): raise ValueError('Use the exact operation envelope')
    return value


def create_app(verify, store, *, account_id, public_origin, operation_kind='draft', token_header=None):
    identifier(account_id); origin = owned_origin(public_origin)
    if not callable(verify) or type(getattr(store,'payload_contract',None)) is not PayloadContract:
        raise ValueError('Supply an owned verifier and typed application store')
    if type(operation_kind) is not str or operation_kind not in {'document','draft','account_change'}: raise ValueError('Use an owned operation policy')
    if getattr(store,'operation_kind',None) not in {None,operation_kind}: raise ValueError('HTTP and stored operation policies differ')
    if token_header is not None and (type(token_header) is not str or token_header != 'x-goog-iap-jwt-assertion'): raise ValueError('Unsupported native identity transport')
    app = FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    policy = getattr(store, 'review_policy', None)
    def representation(row): return public_operation(row, include_source=policy is not None)
    slots = threading.BoundedSemaphore(20)
    def error(code,status): return JSONResponse({'error':{'code':code}},status_code=status)
    async def actor(request):
        if token_header:
            headers = request.headers.getlist(token_header)
            token = headers[0] if len(headers) == 1 else ''
        else:
            headers = request.headers.getlist('authorization')
            supplied = headers[0] if len(headers) == 1 else ''
            token = supplied[7:] if supplied.startswith('Bearer ') else ''
        if not token or len(token) > 16384: raise Denied('Verified identity required')
        try: subject = await run_in_threadpool(verify,token)
        except Exception: raise Denied('Verified identity required') from None
        try: principal = Principal(account_id,subject)
        except ValueError: raise Denied('Verified identity required') from None
        await run_in_threadpool(store.authorize,principal)
        return principal
    async def mutation(request,fields):
        user = await actor(request)
        if request.query_params: raise ValueError('Mutations do not accept query configuration')
        value = await body(request,fields)
        if await actor(request) != user: raise Denied('Identity changed while reading input')
        return user,value
    @app.middleware('http')
    async def boundary(request,next_handler):
        acquired = False
        try:
            origins = request.headers.getlist('origin')
            if len(origins) > 1 or origins and origins[0] != origin: raise Denied('Wrong application origin')
            if request.method not in {'GET','HEAD','OPTIONS'}:
                if origins != [origin]: raise Denied('Exact application origin required')
                acquired = slots.acquire(blocking=False)
                if not acquired: raise Busy()
            response = await next_handler(request)
        except Denied: response = error('access_denied',403)
        except Missing: response = error('not_found',404)
        except Conflict: response = error('conflict',409)
        except BodyTooLarge: response = error('body_too_large',413)
        except UnsupportedBody: response = error('unsupported_content_type',415)
        except Busy: response = error('busy',429)
        except TimeoutError: response = error('body_timeout',408)
        except (ValueError,UnicodeError,RecursionError): response = error('invalid_request',400)
        except Exception: response = error('unavailable',503)
        finally:
            if acquired: slots.release()
        response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
            'Referrer-Policy':'no-referrer','Strict-Transport-Security':'max-age=31536000',
            'Content-Security-Policy':"default-src 'none'; frame-ancestors 'none'; base-uri 'none'"})
        return response
    @app.get('/healthz')
    def health(): return {'status':'running'}
    @app.get('/api/session')
    async def session(request:Request):
        user = await actor(request)
        if request.query_params: raise ValueError('No session overrides are accepted')
        return {'roles':await run_in_threadpool(store.authorize,user),'accountMode':'operator-owned'}
    @app.post('/api/operations',status_code=202)
    async def submit(request:Request):
        user,value = await mutation(request,['source'])
        keys = request.headers.getlist('idempotency-key')
        if len(keys) != 1 or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}',keys[0]):
            raise ValueError('Use a stable bounded operation key')
        operation = await run_in_threadpool(store.submit,user,operation_kind,keys[0],value['source'])
        return {'operation':representation(await run_in_threadpool(store.get,user,operation))}
    @app.get('/api/operations')
    async def listing(request:Request):
        user = await actor(request)
        if set(request.query_params)-{'before'} or len(request.query_params.getlist('before')) > 1:
            raise ValueError('Use the bounded operation cursor')
        rows = await run_in_threadpool(store.list,user,before=request.query_params.get('before'),limit=25)
        return {'operations':[representation(row) for row in rows], 'next':str(rows[-1]['id']) if len(rows)==25 else None}
    @app.get('/api/operations/{operation_id}')
    async def detail(operation_id:str,request:Request):
        user = await actor(request)
        if request.query_params: raise ValueError('No operation overrides are accepted')
        return {'operation':representation(await run_in_threadpool(store.get,user,operation_id))}
    @app.post('/api/operations/{operation_id}/review')
    async def review(operation_id:str,request:Request):
        user,value = await mutation(request,['revision','result'])
        if type(value['revision']) is not int: raise ValueError('Use an exact revision')
        row = await run_in_threadpool(store.edit_result,user,operation_id,value['revision'],value['result'])
        return {'operation':representation(row)}
    if policy is not None:
        @app.post('/api/operations/{operation_id}/inspect')
        async def inspect(operation_id:str,request:Request):
            user,_ = await mutation(request,[])
            row = await run_in_threadpool(store.inspect,user,operation_id)
            return {'operation':representation(row),'payloadSha256':store._fingerprint(row),
                    'destination':row['destination_contract']}
        @app.get('/api/operations/{operation_id}/history')
        async def history(operation_id:str,request:Request):
            user = await actor(request)
            if set(request.query_params)-{'afterRevision'}: raise ValueError('Invalid history cursor')
            cursors = request.query_params.getlist('afterRevision')
            if len(cursors)>1 or cursors and not re.fullmatch(r'0|[1-9][0-9]{0,9}',cursors[0]): raise ValueError('Invalid history cursor')
            rows = await run_in_threadpool(store.result_history,user,operation_id,after_revision=int(cursors[0]) if cursors else 0)
            return {'history':[{'revision':r['revision'],'result':r['result'],'actor':r['actor'],
                                'createdAt':r['created_at'].isoformat()} for r in rows]}
    @app.post('/api/operations/{operation_id}/approve')
    async def approve(operation_id:str,request:Request):
        user,value = await mutation(request,['revision','payloadSha256'] if policy is not None else ['revision'])
        if type(value['revision']) is not int: raise ValueError('Use an exact revision')
        if policy is not None:
            row = await run_in_threadpool(store.approve,user,operation_id,value['revision'],value['payloadSha256'])
        else:
            row = await run_in_threadpool(store.approve,user,operation_id,value['revision'])
        return {'operation':representation(row)}
    return app
