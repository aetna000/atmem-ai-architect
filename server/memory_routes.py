"""All memory requests pass the existing loopback + bearer middleware."""
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import Field, StrictBool
from typing import Literal
from .contracts import Strict
from .memory_service import service
from . import skills
from .pricing import aws_s3, storage_quote, lambda_quote

router=APIRouter()
class Target(Strict):
    projectId:str=Field(pattern=r'^[A-Za-z0-9-]{8,64}$')
class Snapshot(Target):
    file:dict
class Setting(Target):
    enabled:StrictBool
class Profile(Target):
    field:Literal['explanation','experience','iac','preferences']
    value:str=Field(min_length=1,max_length=1000)
class Forget(Target):
    scope:Literal['user','project']
    recordId:str=Field(pattern=r'^rec_[a-f0-9]{32}$')
class Skill(Target):
    skillId:str=Field(max_length=80)
    enabled:StrictBool
class Price(Target):
    provider:Literal['aws','azure','gcp','ibm']='aws'
    region:str=Field(max_length=40)

async def invoke(fn,*args):
    try:return await asyncio.to_thread(fn,*args)
    except ValueError as exc:raise HTTPException(422,str(exc))
    except Exception:raise HTTPException(503,'AtMem is unavailable; your project still works. Run npm run setup:memory if needed.')

@router.post('/api/memory/sync')
async def sync(payload:Snapshot):
    return await invoke(service().sync,payload.projectId,payload.file)

@router.post('/api/memory/inspect')
async def inspect(payload:Target):
    memory=service()
    result=await invoke(memory.inspect,payload.projectId)
    result['skills']=skills.public(skills.catalogue(memory,payload.projectId))
    return result

@router.post('/api/memory/settings')
async def settings(payload:Setting):
    return await invoke(service().configure,payload.projectId,payload.enabled)

@router.post('/api/memory/profile')
async def profile(payload:Profile):
    return await invoke(service().profile,payload.projectId,payload.field,payload.value)

@router.post('/api/memory/forget-preview')
async def preview(payload:Forget):
    report=await invoke(service().inspect,payload.projectId)
    records=report['profile' if payload.scope=='user' else 'project']
    record=next((r for r in records if r['id']==payload.recordId),None)
    if not record:raise HTTPException(404,'Record not available in this scope')
    return {'records':[r for r in records if r['fact_key']==record['fact_key']], 'notice':'Removes this memory and its earlier values. Project data is kept; edit the project itself to change requirements or decisions.'}

@router.post('/api/memory/forget')
async def forget(payload:Forget):
    return await invoke(service().forget,payload.projectId,payload.scope,payload.recordId)

@router.post('/api/memory/skill')
async def skill(payload:Skill):
    memory=service()
    if payload.skillId not in {s['id'] for s in skills.registry()}:raise HTTPException(422,'Unknown skill')
    with memory.lock,memory.db() as db:db.execute('INSERT OR REPLACE INTO skill_settings VALUES (?,?)',(payload.skillId,int(payload.enabled)))
    return {'enabled':payload.enabled}

@router.post('/api/pricing/aws-s3')
async def price(payload:Price):
    try:return await asyncio.to_thread(aws_s3,payload.region)
    except Exception:raise HTTPException(503,'AWS storage pricing is unavailable or the region is not supported. No price was invented.')

@router.post('/api/pricing/storage')
async def storage(payload:Price):
    try:return await asyncio.to_thread(storage_quote,payload.provider,payload.region)
    except Exception:raise HTTPException(503,'The exact provider/region price could not be verified. No rate was invented.')


class LambdaPrice(Target):
    region:str=Field(max_length=40)
    architecture:Literal['x86_64','arm64']='x86_64'

@router.post('/api/pricing/lambda')
async def lambda_price(payload:LambdaPrice):
    try:return await asyncio.to_thread(lambda_quote,payload.region,payload.architecture)
    except Exception:raise HTTPException(503,'The regional Lambda price is unavailable. Retry pricing; no rate was invented.')
