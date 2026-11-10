"""Authenticated upload/review API. Native login and storage are explicit adapters.

The initial internal-team composition has one operator-owned account. The browser
cannot choose an account, a destination, a role or an object reference. Account
membership is checked in PostgreSQL independently of the verified login token.
"""
import asyncio
import hashlib
import json
from pathlib import Path
import threading
from urllib.parse import urlsplit
from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse,Response
from starlette.concurrency import run_in_threadpool
from durable_workflow import Principal,Denied,Missing,Conflict,canonical,identifier
from invoice_object_store import LIMIT,ObjectUnavailable
from invoice_extraction import review_fields,FIELDS
from structured_output import _object

MESSAGES={'access_denied':'Sign in with an authorized staff account to continue.','not_found':'This invoice is not available to your account.','conflict':'This invoice changed. Reload it before saving or approving.','invalid_request':'Check the supplied fields and try again.','review_required':'Check the supplier, invoice date, decimal total and three-letter currency before approving.','invalid_pdf':'Choose a PDF invoice no larger than 10 MB.','busy':'Uploads are busy. Keep this file selected and try again shortly.','unavailable':'The invoice service is temporarily unavailable. Your existing invoices are preserved.'}

def error(code,status):return JSONResponse({'error':{'code':code,'message':MESSAGES[code]}},status_code=status)

def public_row(row):
    return {'id':str(row['id']),'state':row['state'],'result':row['result'],'revision':row['result_revision'],'createdAt':row['created_at'].isoformat(),'updatedAt':row['updated_at'].isoformat(),'receipt':row['receipt']}

def create_app(verify,store,objects,*,account_id,public_origin,token_header=None):
    identifier(account_id);origin=urlsplit(public_origin)
    if origin.scheme not in {'https','http'}or not origin.netloc or origin.path not in {'','/'}or origin.query or origin.fragment or origin.username or(origin.scheme=='http'and origin.hostname not in {'localhost','127.0.0.1','::1'}):raise ValueError('Supply the owned HTTPS origin or explicit loopback fixture')
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None);uploads=threading.BoundedSemaphore(20)
    async def actor(request):
        supplied=request.headers.get('authorization','')
        token=request.headers.get(token_header,'')if token_header else supplied[7:]if supplied.startswith('Bearer ')else''
        try:subject=await run_in_threadpool(verify,token)
        except Exception:raise Denied('Verified staff identity required')from None
        principal=Principal(account_id,subject);await run_in_threadpool(store.authorize,principal);return principal
    @app.middleware('http')
    async def boundary(request,next_handler):
        try:
            supplied=request.headers.get('origin')
            if supplied and supplied.rstrip('/')!=public_origin.rstrip('/'):response=error('access_denied',403)
            else:response=await next_handler(request)
        except(Denied,PermissionError):response=error('access_denied',403)
        except Missing:response=error('not_found',404)
        except Conflict:response=error('conflict',409)
        except(ValueError,UnicodeError,RecursionError):response=error('invalid_request',400)
        except Exception:response=error('unavailable',503)
        response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",'Strict-Transport-Security':'max-age=31536000'})
        return response
    @app.get('/healthz')
    def health():return{'status':'running'}
    @app.get('/api/session')
    async def session(request:Request):
        user=await actor(request);return{'roles':await run_in_threadpool(store.authorize,user),'accountMode':'internal-team'}
    @app.get('/api/invoices')
    async def listing(request:Request,before:str|None=None):
        user=await actor(request);rows=await run_in_threadpool(store.list,user,before=before,limit=25)
        return{'invoices':[public_row(row)for row in rows],'next':str(rows[-1]['id'])if len(rows)==25 else None}
    @app.post('/api/invoices',status_code=202)
    async def upload(request:Request):
        user=await actor(request)
        if request.headers.get('content-type','').split(';')[0].lower()!='application/pdf':return error('invalid_pdf',400)
        if not uploads.acquire(blocking=False):return error('busy',429)
        try:
            raw=bytearray()
            try:
                async with asyncio.timeout(15):
                    async for chunk in request.stream():
                        raw.extend(chunk)
                        if len(raw)>LIMIT:return error('invalid_pdf',413)
            except TimeoutError:return error('invalid_pdf',408)
            content=bytes(raw)
            if not content.startswith(b'%PDF-'):return error('invalid_pdf',400)
            digest=hashlib.sha256(content).hexdigest();reference=await run_in_threadpool(objects.put,user.account_id,content)
            # The storage adapter supplies the pinned version; no client/model
            # object path, version, destination or account enters this call.
            if reference.get('sha256')!=digest:raise ObjectUnavailable('Uploaded digest did not match')
            current=await actor(request)
            if current!=user:raise Denied('Current identity changed during upload')
            operation=await run_in_threadpool(store.submit,user,'document',digest,reference)
            return{'invoice':public_row(await run_in_threadpool(store.get,user,operation))}
        finally:uploads.release()
    @app.get('/api/invoices/{operation_id}')
    async def detail(operation_id:str,request:Request):
        user=await actor(request);return{'invoice':public_row(await run_in_threadpool(store.get,user,operation_id))}
    @app.get('/api/invoices/{operation_id}/original')
    async def original(operation_id:str,request:Request):
        user=await actor(request);row=await run_in_threadpool(store.get,user,operation_id);raw=await run_in_threadpool(objects.load,user.account_id,row['source_ref'])
        current=await actor(request)
        if current!=user:raise Denied('Current identity changed during original read')
        await run_in_threadpool(store.get,user,operation_id)
        return Response(raw,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="invoice.pdf"'})
    async def body(request,fields):
        raw=bytearray()
        async with asyncio.timeout(5):
            async for chunk in request.stream():
                raw.extend(chunk)
                if len(raw)>10000:raise ValueError('Review request exceeds its boundary')
        value=json.loads(raw,object_pairs_hook=_object)
        if not isinstance(value,dict)or set(value)!=set(fields)or type(value.get('revision'))is not int:raise ValueError('Use an exact review revision')
        return value
    @app.post('/api/invoices/{operation_id}/approve')
    async def approve(operation_id:str,request:Request):
        user=await actor(request);value=await body(request,['revision']);current=await run_in_threadpool(store.get,user,operation_id)
        try:review_fields({name:current['result'].get(name)for name in FIELDS}if isinstance(current['result'],dict)else{})
        except ValueError:return error('review_required',400)
        row=await run_in_threadpool(store.approve,user,operation_id,value['revision']);return{'invoice':public_row(row)}
    @app.post('/api/invoices/{operation_id}/review')
    async def review(operation_id:str,request:Request):
        user=await actor(request);value=await body(request,['revision','fields','notes']);fields=review_fields(value['fields'])
        if not isinstance(value['notes'],str)or len(value['notes'])>1000:raise ValueError('Use bounded reviewer notes')
        current=await run_in_threadpool(store.get,user,operation_id)
        result={**(current['result']or{}),**fields,'reviewerNotes':value['notes'],'reviewedBy':user.subject,'requiresHumanReview':True}
        row=await run_in_threadpool(store.edit_result,user,operation_id,value['revision'],result);return{'invoice':public_row(row)}
    @app.get('/api/invoices/{operation_id}/history')
    async def history(operation_id:str,request:Request,after:int=0):
        user=await actor(request);rows=await run_in_threadpool(store.result_history,user,operation_id,after_revision=after,limit=25)
        return{'revisions':[{'revision':row['revision'],'result':row['result'],'actor':row['actor'],'createdAt':row['created_at'].isoformat()}for row in rows],'next':rows[-1]['revision']if len(rows)==25 else None}
    @app.post('/api/invoices/{operation_id}/recover')
    async def recover(operation_id:str,request:Request):
        user=await actor(request);row=await run_in_threadpool(store.recover_extraction,user,operation_id);return{'invoice':public_row(row)}
    return app
