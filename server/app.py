from .settings import setting, home as product_home
"""Loopback-only AtMem AI Architect sidecar. No cloud discovery or deployment endpoints."""
import asyncio, os, secrets, shutil
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from .architect import AtMemArchitect
from .contracts import ChatRequest
from .local_providers import capabilities, models, start_login
from .memory_routes import router as memory_router
from .agent_runtime import run as run_architect
from .memory_service import service as memory_service, safe as memory_safe

app=FastAPI(title='AtMem AI Architect helper',docs_url=None,redoc_url=None,openapi_url=None)
app.include_router(memory_router)
from .voice_routes import router as voice_router, engine as voice_engine
app.include_router(voice_router)

@app.on_event("shutdown")
async def shutdown_voice():
    await voice_engine.close()

from .terraform_routes import router as terraform_router
app.include_router(terraform_router)
from .emulation_routes import router as emulation_router
app.include_router(emulation_router)
from .engineering_routes import router as engineering_router, close as close_engineering
app.include_router(engineering_router)

@app.on_event('shutdown')
async def shutdown_engineering():
    await close_engineering()
TOKEN=secrets.token_urlsafe(32)
ARCHITECT=AtMemArchitect()
ALLOWED_HOSTS={'127.0.0.1:5174','localhost:5174','127.0.0.1:8766','localhost:8766','testserver'}
ALLOWED_ORIGINS={'http://127.0.0.1:5174','http://localhost:5174'}
for _port in (setting('PORT'),setting('SIDECAR_PORT')):
    if _port and _port.isdigit() and 1024 <= int(_port) <= 65535:
        ALLOWED_HOSTS.update({f'127.0.0.1:{_port}',f'localhost:{_port}'})
        ALLOWED_ORIGINS.update({f'http://127.0.0.1:{_port}',f'http://localhost:{_port}'})
TURN_LOCK=asyncio.Lock()

@app.middleware('http')
async def local_boundary(request:Request,call_next):
    if request.headers.get('host','') not in ALLOWED_HOSTS:
        return JSONResponse({'detail':'Unrecognised local host'},status_code=403)
    origin=request.headers.get('origin')
    if origin and origin not in ALLOWED_ORIGINS:
        return JSONResponse({'detail':'Cross-origin requests are not allowed'},status_code=403)
    if request.method not in {'GET','POST'}:
        return JSONResponse({'detail':'Method not allowed'},status_code=405)
    if request.method=='POST':
        if not secrets.compare_digest(request.headers.get('authorization',''),f'Bearer {TOKEN}'):
            return JSONResponse({'detail':'Missing local session token'},status_code=401)
        limit=12_000_000 if request.url.path=='/api/architect' else 2_100_000 if request.url.path in {'/api/projects/save','/api/memory/sync','/api/voice/transcribe'} else 250000
        if len(await request.body())>limit:
            return JSONResponse({'detail':'Request too large'},status_code=413)
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    return response

@app.get('/api/session')
async def session():
    found=await asyncio.to_thread(capabilities)
    return {'token':TOKEN,'status':'local-sidecar','providers':{**found,
        'anthropic':{'available':bool(ARCHITECT.keys.get('anthropic') or os.getenv('ANTHROPIC_API_KEY')),'description':'API key supplied to the sidecar environment'},
        'openai':{'available':bool(ARCHITECT.keys.get('openai') or os.getenv('OPENAI_API_KEY')),'description':'API key supplied to the sidecar environment'},
        'gemini-api':{'available':bool(ARCHITECT.keys.get('gemini-api') or os.getenv('GEMINI_API_KEY')),'description':'Ephemeral API key or GEMINI_API_KEY'},
        'xai':{'available':bool(ARCHITECT.keys.get('xai') or os.getenv('XAI_API_KEY')),'description':'xAI API key for Grok'},
        'bedrock':{'available':bool(setting('ENABLE_BEDROCK')),'description':'Explicit opt-in plus AWS SDK credential chain; credentials not probed'},
    },'cloudExecution':False,'mcpEnabled':False,'engineeringEnabled':setting('ENABLE_ENGINEERING')=='1','sdkTimeoutNote':'Stopping a submitted remote model request may not stop provider-side computation or billing.'}

@app.post('/api/architect')
async def architect(payload:ChatRequest,request:Request):
    if payload.provider=='bedrock' and not setting('ENABLE_BEDROCK'):
        raise HTTPException(409,'Bedrock is disabled. Explicitly enable it in the local sidecar environment.')
    if TURN_LOCK.locked():raise HTTPException(409,"We're still working on your last message — give it a moment.")
    async with TURN_LOCK:
        try:
            return await run_architect(ARCHITECT,payload,request.is_disconnected)
        except asyncio.CancelledError:
            return JSONResponse({'detail':'Request cancelled'},status_code=499)
        except (ValueError,TimeoutError) as exc:
            # Model output may contain user content: do not return validation dumps.
            if isinstance(exc,TimeoutError):raise HTTPException(504,"The model took too long to answer. Let's try again, or pick a faster thinking level.")
            raise HTTPException(422,"The model's drawing didn't fit together, so we left the board as it was. Let's try asking again.")
        except RuntimeError as exc:
            raise HTTPException(409,str(exc))
        except Exception:
            raise HTTPException(502,"The model didn't answer. Let's check the connection — sign-in, model or usage limits.")

@app.post('/api/credentials')
async def credentials(request:Request):
    payload=await request.json()
    if not isinstance(payload,dict) or set(payload)!={'provider','key'} or payload.get('provider') not in {'anthropic','openai','gemini-api','xai'} or not isinstance(payload.get('key'),str) or len(payload['key'])>5000:
        raise HTTPException(422,'Invalid credential request.')
    provider=payload['provider'];key=payload['key'].strip()
    if key:ARCHITECT.keys[provider]=key
    else:ARCHITECT.keys.pop(provider,None)
    return {'provider':provider,'configuredInMemory':bool(key)}

@app.post('/api/login')
async def login(request:Request):
    payload=await request.json()
    if not isinstance(payload,dict) or set(payload)!={'provider'} or not isinstance(payload.get('provider'),str):
        raise HTTPException(422,'Invalid sign-in request.')
    try:return await start_login(payload['provider'])
    except RuntimeError as exc:raise HTTPException(409,str(exc))

@app.post('/api/models')
async def list_models(request:Request):
    payload=await request.json()
    if not isinstance(payload,dict) or set(payload)!={'provider'} or not isinstance(payload.get('provider'),str):
        raise HTTPException(422,'Invalid model request.')
    provider=payload['provider']
    if provider in API_MODELS:
        key=ARCHITECT.keys.get(provider) or os.getenv(API_MODELS[provider][0])
        if not key:return {'models':[],'reason':'Add your API key to see your models.'}
        try:return {'models':await asyncio.to_thread(api_models,provider,key)}
        except Exception:return {'models':[],'reason':"Couldn't list models with that key. Check it and try again."}
    found=await asyncio.to_thread(models,provider)
    return {'models':found,**({} if found else {'reason':'Sign in first to see your models.'})}

# Model lists straight from each provider's API, using the user's key (never stored on disk).
API_MODELS={'openai':('OPENAI_API_KEY','https://api.openai.com/v1/models'),'anthropic':('ANTHROPIC_API_KEY','https://api.anthropic.com/v1/models'),
            'gemini-api':('GEMINI_API_KEY','https://generativelanguage.googleapis.com/v1beta/models'),'xai':('XAI_API_KEY','https://api.x.ai/v1/models')}
def api_models(provider,key):
    import json as _json, urllib.request
    url=API_MODELS[provider][1]
    headers={'Authorization':f'Bearer {key}'}
    if provider=='anthropic':headers={'x-api-key':key,'anthropic-version':'2023-06-01'}
    if provider=='gemini-api':headers={'x-goog-api-key':key}
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=10) as response:
        data=_json.loads(response.read())
    if provider=='gemini-api':
        return [{'id':m['name'].removeprefix('models/'),'name':m.get('displayName',m['name']),'efforts':[]} for m in data.get('models',[]) if 'generateContent' in m.get('supportedGenerationMethods',[])]
    items=data.get('data',[])
    return [{'id':m['id'],'name':m.get('display_name') or m['id'],'efforts':[]} for m in items]

# ---- Projects: saved under the user's account on this computer (~/.atforma), with a rubbish bin ----
import json as _json, re as _re
from pathlib import Path as _Path
from datetime import datetime as _dt, timezone as _tz

def _home():
    root=product_home()
    (root/'projects').mkdir(parents=True,exist_ok=True);(root/'bin').mkdir(parents=True,exist_ok=True)
    return root
def _pid(payload):
    pid=payload.get('id') if isinstance(payload,dict) else None
    if not isinstance(pid,str) or not _re.fullmatch(r'[A-Za-z0-9-]{8,64}',pid):raise HTTPException(422,'Invalid project id.')
    return pid
def _summary(path):
    try:
        data=_json.loads(path.read_text(encoding='utf-8'));meta=data.get('meta',{})
        return {'id':path.name.removesuffix('.atforma.json'),'name':str(meta.get('name','Untitled'))[:200],'updatedAt':meta.get('updatedAt'),
                'blocks':len(data.get('design',{}).get('nodes',[])),'binnedAt':_dt.fromtimestamp(path.stat().st_mtime,_tz.utc).isoformat() if path.parent.name=='bin' else None}
    except Exception:
        return None
def _list(folder):
    items=[x for x in (_summary(p) for p in (_home()/folder).glob('*.atforma.json')) if x]
    return sorted(items,key=lambda x:x.get('binnedAt') or x.get('updatedAt') or '',reverse=True)

@app.post('/api/projects/list')
async def projects_list():
    return {'projects':_list('projects'),'bin':_list('bin'),'folder':str(_home())}

@app.post('/api/projects/get')
async def projects_get(request:Request):
    pid=_pid(await request.json())
    path=_home()/'projects'/f'{pid}.atforma.json'
    if not path.exists():raise HTTPException(404,'Project not found.')
    return _json.loads(path.read_text(encoding='utf-8'))

@app.post('/api/projects/save')
async def projects_save(request:Request):
    payload=await request.json();pid=_pid(payload)
    file=payload.get('file')
    if not isinstance(file,dict) or file.get('format') not in {'atmem.ai-architect.project','atforma.project'}:raise HTTPException(422,'Not an AtMem AI Architect project file.')
    if not memory_safe(file):raise HTTPException(422,'Project content looks like a credential; remove it before saving.')
    if (_home()/'bin'/f'{pid}.atforma.json').exists():raise HTTPException(409,'This project is in the bin. Restore it first.')
    target=_home()/'projects'/f'{pid}.atforma.json';tmp=target.with_suffix('.tmp')
    tmp.write_text(_json.dumps(file,ensure_ascii=False),encoding='utf-8');tmp.replace(target)
    try:memory=await asyncio.to_thread(memory_service().sync,pid,file)
    except Exception:memory={'status':'unavailable'}
    return {'saved':True,'memory':memory}

@app.post('/api/projects/trash')
async def projects_trash(request:Request):
    pid=_pid(await request.json());src=_home()/'projects'/f'{pid}.atforma.json'
    if not src.exists():raise HTTPException(404,'Project not found.')
    dst=_home()/'bin'/src.name;src.replace(dst);dst.touch()
    return {'binned':True}

@app.post('/api/projects/restore')
async def projects_restore(request:Request):
    pid=_pid(await request.json());src=_home()/'bin'/f'{pid}.atforma.json'
    if not src.exists():raise HTTPException(404,'Not in the bin.')
    src.replace(_home()/'projects'/src.name)
    return {'restored':True}

@app.post('/api/projects/purge')
async def projects_purge(request:Request):
    pid=_pid(await request.json());path=_home()/'bin'/f'{pid}.atforma.json'
    if not path.exists():raise HTTPException(404,'Only projects in the bin can be deleted for good.')
    path.unlink()
    return {'deleted':True}
