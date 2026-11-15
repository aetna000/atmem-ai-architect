"""Firebase-backed, X-only control plane. Payments remain deferred."""
import os
from typing import Any, Literal
from dataclasses import dataclass
from fastapi import FastAPI,Header,Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel,ConfigDict,Field,StrictStr,StrictInt,StrictBool
from starlette.concurrency import run_in_threadpool
from .api import BodyLimit,AccountRateLimit,RateExceeded
from .auth import Unauthorized,Forbidden,AuthenticationUnavailable
from .credits import CreditLedger,CreditError,Conflict,AccountUnavailable,InsufficientCredits
from .credentials import CredentialVault,CredentialsUnavailable
from .x_access import FirebaseXIdentity,XWhitelist
from .projects import Profiles,Projects,ProjectUnavailable
from .pilot_settings import PilotSettings,OpenRouterCatalog,CatalogUnavailable
from .firestore_store import FirestoreTransactions
from .storage_projects import StorageProjects
from .workspace_projects import WorkspaceProjects
from .workspace_jobs import WorkspaceJobs,transfer_store

PREFIX='/api/ai-architect'


class Body(BaseModel):model_config=ConfigDict(extra='forbid',strict=True)
class ProfileBody(Body):
    revision:StrictInt=Field(ge=1)
    displayName:StrictStr|None=Field(default=None,max_length=120)
    aiConnection:Literal['managed','openrouter']|None=None
class KeyBody(Body):
    revision:StrictInt=Field(ge=0)
    apiKey:StrictStr=Field(min_length=20,max_length=512,repr=False)
class RevisionBody(Body):revision:StrictInt=Field(ge=0)
class UploadBody(Body):
    requestId:StrictStr=Field(min_length=1,max_length=128)
    title:StrictStr=Field(min_length=1,max_length=120)
    size:StrictInt=Field(ge=1,le=64*1024*1024)
    sha256:StrictStr=Field(min_length=64,max_length=64)
    projectId:StrictStr|None=None
    revision:StrictInt=Field(default=0,ge=0)
class NewProjectBody(Body):
    requestId:StrictStr=Field(min_length=1,max_length=128)
    title:StrictStr=Field(default='New project',min_length=1,max_length=120)
class WorkspaceJobBody(Body):
    requestId:StrictStr=Field(min_length=1,max_length=128)
    projectId:StrictStr=Field(min_length=8,max_length=64)
    path:StrictStr=Field(min_length=5,max_length=150)
    method:Literal['POST','GET']='POST'
    body:dict[str,Any]|None=None
    transferId:StrictStr|None=None
class TransferBody(Body):
    requestId:StrictStr=Field(min_length=1,max_length=128)
    size:StrictInt=Field(ge=1,le=64*1024*1024)
    sha256:StrictStr=Field(min_length=64,max_length=64)
class ChunkBody(Body):
    data:StrictStr=Field(max_length=350000)
    sha256:StrictStr=Field(min_length=64,max_length=64)
class AccessBody(Body):
    revision:StrictInt=Field(ge=0)
    allowed:StrictBool
    role:Literal['user','admin']='user'
class SettingsBody(Body):
    revision:StrictInt=Field(ge=1)
    changes:dict[str,Any]


@dataclass
class PilotServices:
    store:Any
    identity:Any
    access:Any
    vault:Any=None
    catalog:Any=None
    managed_ai_ready:bool=False
    projects:Any=None
    workspace_jobs:Any=None
    workspace_transfers:Any=None


def create_pilot_app(services):
    app=FastAPI(title='AtMem AI Architect',docs_url=None,redoc_url=None,openapi_url=None)
    app.add_middleware(BodyLimit)
    profiles=Profiles(services.store);projects=services.projects or Projects(services.store,profiles)
    settings=PilotSettings(services.store,services.access,services.catalog or OpenRouterCatalog())
    workspace_projects=WorkspaceProjects(services.store,profiles,projects)
    rate=AccountRateLimit(services.store)

    async def signed_in(authorization,action='account',maximum=60):
        identity=await run_in_threadpool(services.identity.verify,authorization)
        actor=await run_in_threadpool(services.access.authorize,identity)
        await run_in_threadpool(rate.admit,actor.uid,action,maximum)
        return actor

    def wallet():
        policy=settings.current()
        return CreditLedger(services.store,welcome_units=policy['welcomeMicros'],policy_version='pilot-'+str(policy['revision']))

    @app.exception_handler(RequestValidationError)
    async def bad_body(request,error):return JSONResponse({'detail':'Check the submitted fields'},status_code=422)
    for exception,status in [(Unauthorized,401),(Forbidden,403),(AuthenticationUnavailable,503),(RateExceeded,429),
                (ProjectUnavailable,404),(AccountUnavailable,403),(InsufficientCredits,402),(Conflict,409),
                (CreditError,400),(CredentialsUnavailable,503),(CatalogUnavailable,503)]:
        async def error_response(request,error,status=status):return JSONResponse({'detail':str(error)},status_code=status)
        app.add_exception_handler(exception,error_response)

    @app.get(PREFIX+'/health')
    def health():return {'service':'AtMem AI Architect','mode':'firebase-x-pilot','paymentsAvailable':False}

    @app.post(PREFIX+'/profile')
    async def profile(authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'register',10)
        record=await run_in_threadpool(profiles.register,actor)
        balance=await run_in_threadpool(lambda:wallet().register(actor.uid))
        policy=await run_in_threadpool(settings.current)
        return {'profile':record,'admin':actor.admin,'balanceMicros':balance['available'],'reservedMicros':balance['reserved'],
                'currency':'usd','paymentsAvailable':False,'ai':{'model':policy['model'],'reasoning':'medium',
                'workspaceAvailable':services.workspace_jobs is not None,'managedAvailable':services.managed_ai_ready and policy['platformSpendingEnabled']}}

    @app.get(PREFIX+'/workspace/session')
    async def workspace_session(authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'workspace-session',120)
        record=await run_in_threadpool(profiles.get,actor.uid)
        policy=await run_in_threadpool(settings.current)
        return {'profile':record,'ai':{'model':policy['model'],'reasoning':'medium',
                'workspaceAvailable':services.workspace_jobs is not None,
                'managedAvailable':services.managed_ai_ready and policy['platformSpendingEnabled'] and not record['disabled']}}

    @app.patch(PREFIX+'/profile')
    async def update_profile(body:ProfileBody,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'profile',20)
        return await run_in_threadpool(profiles.update,actor.uid,revision=body.revision,display_name=body.displayName,ai_connection=body.aiConnection)

    @app.get(PREFIX+'/projects')
    async def list_projects(authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization)
        return await run_in_threadpool(projects.list,actor.uid)

    @app.post(PREFIX+'/workspace/projects/new')
    async def create_project(body:NewProjectBody,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'new-project',10)
        return await run_in_threadpool(workspace_projects.create,actor.uid,body.requestId,body.title)

    @app.post(PREFIX+'/workspace/projects/{pid}/trash')
    async def trash_project(pid:str,body:RevisionBody,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'trash',20)
        return await run_in_threadpool(workspace_projects.move,actor.uid,pid,body.revision,True)

    @app.post(PREFIX+'/workspace/projects/{pid}/restore')
    async def restore_project(pid:str,body:RevisionBody,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'restore',20)
        return await run_in_threadpool(workspace_projects.move,actor.uid,pid,body.revision,False)

    @app.post(PREFIX+'/workspace/transfers')
    async def begin_transfer(body:TransferBody,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'workspace-transfer',30)
        if services.workspace_transfers is None:raise CredentialsUnavailable('Workspace workers are unavailable')
        return await run_in_threadpool(services.workspace_transfers.begin,actor.uid,body.requestId,title='Workspace request',size=body.size,sha256=body.sha256)

    @app.put(PREFIX+'/workspace/transfers/{upload_id}/parts/{part}')
    async def transfer_chunk(upload_id:str,part:int,body:ChunkBody,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'workspace-chunks',600)
        if services.workspace_transfers is None:raise CredentialsUnavailable('Workspace workers are unavailable')
        return await run_in_threadpool(services.workspace_transfers.put_chunk,actor.uid,upload_id,part,body.data,body.sha256)

    @app.post(PREFIX+'/workspace/transfers/{upload_id}/complete')
    async def finish_transfer(upload_id:str,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'workspace-transfer-complete',30)
        if services.workspace_transfers is None:raise CredentialsUnavailable('Workspace workers are unavailable')
        return await run_in_threadpool(services.workspace_transfers.complete,actor.uid,upload_id)

    @app.delete(PREFIX+'/workspace/transfers/{pid}')
    async def remove_transfer(pid:str,body:RevisionBody,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'workspace-transfer-delete',30)
        if services.workspace_transfers is None:raise CredentialsUnavailable('Workspace transfers are unavailable')
        return await run_in_threadpool(services.workspace_transfers.remove,actor.uid,pid,body.revision)

    @app.post(PREFIX+'/workspace/jobs')
    async def submit_workspace_job(body:WorkspaceJobBody,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'workspace-jobs',120)
        if services.workspace_jobs is None:raise CredentialsUnavailable('Workspace workers are unavailable')
        if (body.body is None)==(body.transferId is None):raise CreditError('Supply one complete workspace payload')
        payload=body.body
        if body.transferId is not None:
            if services.workspace_transfers is None:raise CredentialsUnavailable('Workspace transfers are unavailable')
            _,raw=await run_in_threadpool(services.workspace_transfers.download,actor.uid,body.transferId)
            import json
            payload=json.loads(raw)
        return await run_in_threadpool(services.workspace_jobs.submit,actor.uid,body.requestId,body.projectId,body.path,payload,body.method)

    @app.get(PREFIX+'/workspace/projects/{pid}/jobs/{job_id}')
    async def workspace_job(pid:str,job_id:str,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'workspace-poll',600)
        if services.workspace_jobs is None:raise CredentialsUnavailable('Workspace workers are unavailable')
        return await run_in_threadpool(services.workspace_jobs.read,actor.uid,pid,job_id)

    @app.delete(PREFIX+'/workspace/projects/{pid}/jobs/{job_id}')
    async def cancel_workspace_job(pid:str,job_id:str,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'workspace-cancel',30)
        if services.workspace_jobs is None:raise CredentialsUnavailable('Workspace workers are unavailable')
        return await run_in_threadpool(services.workspace_jobs.cancel,actor.uid,pid,job_id)

    @app.get(PREFIX+'/workspace/projects/{pid}/jobs/{job_id}/result/{part}')
    async def workspace_result_part(pid:str,job_id:str,part:int,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'workspace-result-chunks',600)
        if services.workspace_jobs is None:raise CredentialsUnavailable('Workspace workers are unavailable')
        return await run_in_threadpool(services.workspace_jobs.result_chunk,actor.uid,pid,job_id,part)

    @app.post(PREFIX+'/projects/uploads')
    async def begin_upload(body:UploadBody,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'save',10)
        return await run_in_threadpool(projects.begin,actor.uid,body.requestId,title=body.title,size=body.size,sha256=body.sha256,pid=body.projectId,revision=body.revision)

    @app.put(PREFIX+'/projects/uploads/{upload_id}/parts/{part}')
    async def put_chunk(upload_id:str,part:int,body:ChunkBody,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'chunks',600)
        return await run_in_threadpool(projects.put_chunk,actor.uid,upload_id,part,body.data,body.sha256)

    @app.post(PREFIX+'/projects/uploads/{upload_id}/complete')
    async def complete_upload(upload_id:str,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'complete',10)
        return await run_in_threadpool(projects.complete,actor.uid,upload_id)

    @app.delete(PREFIX+'/projects/uploads/{upload_id}')
    async def cancel_upload(upload_id:str,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'cancel',20)
        return await run_in_threadpool(projects.cancel,actor.uid,upload_id)

    @app.get(PREFIX+'/projects/{pid}/download')
    async def download(pid:str,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'download',20)
        record,raw=await run_in_threadpool(projects.download,actor.uid,pid)
        return Response(raw,media_type='application/json',headers={'Content-Disposition':f'attachment; filename="project-{record["id"]}.json"','ETag':'"'+record['sha256']+'"'})

    @app.delete(PREFIX+'/projects/{pid}')
    async def remove_project(pid:str,body:RevisionBody,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'delete',20)
        return await run_in_threadpool(projects.remove,actor.uid,pid,body.revision)

    @app.get(PREFIX+'/provider/openrouter')
    async def key_status(authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization)
        if services.vault is None:raise CredentialsUnavailable('OpenRouter key storage is not configured yet')
        return await run_in_threadpool(services.vault.status,actor.uid,'openrouter')

    @app.put(PREFIX+'/provider/openrouter')
    async def save_key(body:KeyBody,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'keys',10)
        if services.vault is None:raise CredentialsUnavailable('OpenRouter key storage is not configured yet')
        return await run_in_threadpool(services.vault.update,actor.uid,'openrouter',body.apiKey,body.revision)

    @app.delete(PREFIX+'/provider/openrouter')
    async def remove_key(body:RevisionBody,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'keys',10)
        if services.vault is None:raise CredentialsUnavailable('OpenRouter key storage is not configured yet')
        return await run_in_threadpool(services.vault.remove,actor.uid,'openrouter',body.revision)

    @app.get(PREFIX+'/admin/whitelist')
    async def whitelist(authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization)
        return await run_in_threadpool(services.access.list,actor)

    @app.put(PREFIX+'/admin/whitelist/{subject}')
    async def edit_whitelist(subject:str,body:AccessBody,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'admin',20)
        return await run_in_threadpool(services.access.update,actor,subject,allowed=body.allowed,role=body.role,revision=body.revision)

    @app.get(PREFIX+'/admin/models')
    async def models(authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization);actor.require_admin()
        return await run_in_threadpool(settings.catalog.current)

    @app.get(PREFIX+'/admin/settings')
    async def get_settings(authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization);actor.require_admin()
        return await run_in_threadpool(settings.current)

    @app.patch(PREFIX+'/admin/settings')
    async def edit_settings(body:SettingsBody,authorization:str|None=Header(default=None)):
        actor=await signed_in(authorization,'settings',10)
        return await run_in_threadpool(settings.update,actor,body.revision,body.changes)

    return app


def configured_pilot_app():
    if os.environ.get('ARCHITECT_STRIPE_MODE','disabled')!='disabled':raise ValueError('Stripe is TODO for the X pilot')
    environment=os.environ['ARCHITECT_DATA_ENVIRONMENT']
    if environment not in {'sandbox','production'}:raise ValueError('Choose an explicit data environment')
    if environment=='production' and any(os.environ.get(name) for name in (
        'FIRESTORE_EMULATOR_HOST','FIREBASE_AUTH_EMULATOR_HOST','STORAGE_EMULATOR_HOST')):
        raise ValueError('Production cannot use Firebase emulators')
    project=os.environ['ARCHITECT_GOOGLE_PROJECT']
    namespace='architect_pilot_'+environment
    base_store=FirestoreTransactions.configured(project,os.environ['ARCHITECT_FIRESTORE_DATABASE'])
    store=FirestoreTransactions(base_store.client,namespace=namespace)
    admins=[x.strip() for x in os.environ['ARCHITECT_ADMIN_X_IDS'].split(',') if x.strip()]
    initial=[x.strip() for x in os.environ.get('ARCHITECT_ALLOWED_X_IDS','').split(',') if x.strip()]
    access=XWhitelist(store,admin_ids=admins,initial_ids=initial)
    profiles=Profiles(store)
    vault=CredentialVault.configured(store,profiles) if os.environ.get('ARCHITECT_BYOK_KEYRING') else None
    from google.cloud import storage
    bucket=storage.Client(project=project).bucket(os.environ['ARCHITECT_FIREBASE_STORAGE_BUCKET'])
    projects=StorageProjects(store,profiles,bucket,object_prefix=namespace)
    jobs=WorkspaceJobs(store,profiles,projects,bucket,prefix=namespace+'_jobs')
    transfers=transfer_store(store,profiles,bucket,namespace+'_transfers')
    enabled=os.environ.get('ARCHITECT_NATIVE_WORKSPACE_ENABLED')=='1'
    return create_pilot_app(PilotServices(store,FirebaseXIdentity(project),access,vault,projects=projects,
        managed_ai_ready=enabled,workspace_jobs=jobs if enabled else None,workspace_transfers=transfers if enabled else None))
