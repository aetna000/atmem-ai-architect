"""Architect UI adapter over the same reviewer and real AtMem project memory."""
import asyncio
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import io
import zipfile
from fastapi import APIRouter,HTTPException
from pydantic import Field
from .contracts import Strict
from .memory_service import service

ROOT=Path(__file__).resolve().parents[1]
# One source engine, included in the Architect distribution. No second user install.
CORE=ROOT/'atmem-review-hook/src'
if str(CORE) not in sys.path:sys.path.insert(0,str(CORE))
from atmem_review.engine import review_plan
from atmem_review.policy import parse_policy

router=APIRouter(prefix='/api/memory/architecture')
ACTIVE={}
LOCK=asyncio.Lock()

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()

class Target(Strict):
    projectId:str=Field(pattern=r'^[A-Za-z0-9-]{8,64}$')
class SaveRules(Target):
    content:str=Field(min_length=1,max_length=12000)
    expectedRevision:str|None=Field(default=None,pattern=r'^[a-f0-9]{64}$')
class Run(Target):
    project:dict
    environment:str=Field(default='staging',pattern=r'^(staging|production)$')

def read(memory,project,key):
    fact=memory.architecture_fact(project,key)
    return {**fact['value'],'recordId':fact['recordId']} if fact else None

def save_rules(memory,payload):
    parse_policy(payload.content)
    with memory.lock:
        previous=read(memory,payload.projectId,'architecture.policy')
        if (previous or {}).get('revision')!=payload.expectedRevision:
            raise ValueError('Rules changed. Reload before saving your changes.')
        policy={'content':payload.content,'revision':digest(payload.content),'approvedAt':now(),'approvedBy':memory.owner}
        memory.architecture_fact(payload.projectId,'architecture.policy',policy,approved=True)
        return read(memory,payload.projectId,'architecture.policy')

def configuration_snapshot(files):
    """Literal generated Terraform JSON only. Expressions stay unknown, never executed."""
    inventory=[];providers={};configs=[];unsupported=False
    def literal(value):
        if isinstance(value,str) and ('${' in value or '%{' in value):return None
        if isinstance(value,list):return [literal(v) for v in value]
        if isinstance(value,dict):return {k:literal(v) for k,v in value.items()}
        return value
    for path,text in files.items():
        if path.endswith('.tf') and text.strip():unsupported=True
        if not path.endswith('.tf.json'):continue
        data=json.loads(text)
        if data.get('module'):unsupported=True
        for provider,entries in data.get('provider',{}).items():
            for entry in entries if isinstance(entries,list) else [entries]:
                name=provider+('.'+entry['alias'] if entry.get('alias') else '')
                region=entry.get('region')
                providers[name]={'expressions':{'region':{'constant_value':literal(region)}}} if region is not None else {}
        for kind,items in data.get('resource',{}).items():
            for name,body in items.items():
                address=kind+'.'+name
                # count/for_each and unresolved modules do not establish inventory coverage.
                if 'count' in body or 'for_each' in body:unsupported=True
                inventory.append({'address':address,'type':kind,'mode':'managed','values':literal(body)})
                configs.append({'address':address,'provider_config_key':body.get('provider',kind.split('_')[0])})
    if len({r['address'] for r in inventory})!=len(inventory):raise ValueError('Duplicate generated resource identity.')
    return {'format_version':'1.2','complete':not unsupported,'planned_values':{'root_module':{'resources':inventory}},
            'configuration':{'provider_config':providers,'root_module':{'resources':configs}}}

def render(project,environment):
    node=shutil.which('node')
    if not node:raise ValueError('Node is unavailable. Restore the Architect runtime and retry.')
    result=subprocess.run([node,str(ROOT/'scripts/terraform-render.mjs')],input=json.dumps({'project':project,'environment':environment,'review':True}),capture_output=True,text=True,timeout=30,cwd=ROOT)
    if result.returncode:raise ValueError('The current design could not generate a Terraform draft. Review the design and retry.')
    return json.loads(result.stdout)

async def execute(memory,payload,policy,state):
    async def event(text):
        state['actions'].append({'text':text,'at':now()})
        await asyncio.to_thread(memory.architecture_fact,payload.projectId,'architecture.review',state)
    try:
        await event('Generating Terraform from the current design')
        generated=await asyncio.to_thread(render,payload.project,payload.environment)
        files=generated['files'];state['designSha256']=generated['designSha256'];state['projectSha256']=state['designSha256']
        await event('Checking infrastructure against saved rules')
        snapshot=configuration_snapshot(files)
        request={'artifacts':[{'kind':'plan','path':'architect/design.json','content':json.dumps(payload.project)}],
                 'rules':{'path':'atmem://project/'+payload.projectId+'/architecture.policy/'+policy['revision'],'content':policy['content']},
                 'terraform_plan':{'path':'generated-configuration-snapshot.json','json':snapshot},'options':{'cost_estimate':'off'}}
        report=await asyncio.to_thread(review_plan,request)
        # The normalized snapshot is static draft evidence, never a cloud plan.
        report['risks'].append({'id':'configuration_only','severity':'info','description':'Static generated Terraform configuration only; expressions remain unknown. No cloud plan, deployment or tests were run.','related_rule_ids':[]})
        with memory.lock:
            current=read(memory,payload.projectId,'architecture.policy')
            state.update(state='completed' if current and current['revision']==policy['revision'] else 'stale',report=report,
                         fileDigests={p:hashlib.sha256(t.encode()).hexdigest() for p,t in files.items() if p.endswith(('.tf','.tf.json'))})
            state['actions'].append({'text':'Rules review '+report['verdict'].upper(),'at':now()})
            memory.architecture_fact(payload.projectId,'architecture.review',state)
    except Exception:
        state.update(state='failed',error='Review could not finish. Check AtMem and the generated design, then retry.')
        state['actions'].append({'text':'Review failed; no approval issued','at':now()})
        try:await asyncio.to_thread(memory.architecture_fact,payload.projectId,'architecture.review',state)
        except Exception:pass
    finally:
        async with LOCK:ACTIVE.pop((str(memory.home),payload.projectId),None)

def engineering_gate(memory,project,project_file):
    """Do not accept a code run against another approved policy or design revision."""
    policy=read(memory,project,'architecture.policy')
    if not policy:return None
    embedded=project_file.get('extensions',{}).get('architecturePolicy')
    if not isinstance(embedded,dict) or embedded.get('revision')!=policy['revision'] or embedded.get('content')!=policy['content']:
        raise ValueError('Save the current approved rules with this project before coding.')
    review=read(memory,project,'architecture.review')
    design=render(project_file,(review or {}).get('environment','staging'))
    if not review or review.get('state')!='completed' or review.get('policyRevision')!=policy['revision'] or review.get('designSha256')!=design['designSha256']:
        raise ValueError('Review the current design against your saved project rules before coding.')
    if review['report']['verdict']=='fail':raise ValueError('Resolve the infrastructure rule violations before coding.')
    return policy

def remember_engineering(memory,project,session_state,events):
    """Project-scoped public journal facts, not model assertions of test success."""
    if not events:return 'unchanged'
    with memory.lock:
        previous=read(memory,project,'architecture.implementation')
        sessions=(previous or {}).get('sessions',{})
        ident=session_state['id'];sequence=events[-1]['sequence']
        if sessions.get(ident,{}).get('sequence',-1)>=sequence:return 'unchanged'
        if ident not in sessions and len(sessions)>=100:raise ValueError('Implementation history reached its explicit session bound.')
        sessions[ident]={'sessionId':ident,'runId':session_state.get('run'),'state':session_state['state'],
                         'lastStatus':session_state.get('last_status'),'sequence':sequence,
                         'eventKinds':[e['kind'] for e in events],
                         'boundary':'Observed worker activity. Completion is not test, policy or specification acceptance.'}
        memory.architecture_fact(project,'architecture.implementation',{'recordedAt':now(),'sessions':sessions})
    return 'remembered'

def remember_bindings(memory,project,receipt):
    if receipt.get('status')!='prepared':return
    content=receipt['content']
    if hashlib.sha256(content.encode()).hexdigest()!=receipt['sha256']:raise ValueError('Specification binding receipt integrity failed.')
    payload=json.loads(content)
    if payload['projectId']!=project:raise ValueError('Specification bindings belong to another project.')
    with memory.lock:
        previous=read(memory,project,'architecture.bindings');sessions=(previous or {}).get('sessions',{})
        session=payload['sessionId']
        if session not in sessions and len(sessions)>=100:raise ValueError('Binding history reached its session bound.')
        sessions[session]={'receiptSha256':receipt['sha256'],'artifactId':payload['artifactId'],'artifactSha256':payload['artifactSha256'],
            'runId':payload['runId'],'contextSha256':payload['context']['sha256'],'fileDigests':payload['files'],
            'records':[{'id':r['id'],'kind':r['kind'],'dependsOn':r['dependsOn'],'files':r['data'].get('files',[]),'specTaskIds':r['data'].get('specTaskIds',[])} for r in payload['proposal']['records']],
            'boundary':'Specification/task/file provenance only. Test execution and semantic acceptance require independent evidence.'}
        memory.architecture_fact(project,'architecture.bindings',{'recordedAt':now(),'sessions':sessions})

def remember_specification(memory,project,context):
    if context.get('projectId')!=project or context.get('specification',{}).get('contextSha256')!=context.get('sha256'):
        raise ValueError('Specification snapshot is outside this project/context.')
    with memory.lock:
        previous=read(memory,project,'architecture.specification')
        if previous and previous.get('contextSha256')==context['sha256'] and digest(previous['specification'])==digest(context['specification']):return
        memory.architecture_fact(project,'architecture.specification',{'recordedAt':now(),'contextId':context['id'],
            'contextSha256':context['sha256'],'revision':context['revision'],'specification':context['specification'],
            'boundary':'Generated task inventory for this submitted specification, not completed implementation or accepted tests.'})

def remember_validation(memory,project,session,artifact,checks):
    if not checks:return 'unchanged'
    if any(c.get('sessionId')!=session or c.get('artifactId')!=artifact for c in checks):raise ValueError('Validation receipt scope does not match the artifact.')
    rows=[{key:c.get(key) for key in ('id','validatorId','label','artifactId','artifactSha256','contractSha256','state')}|{'resultStatus':(c.get('result') or {}).get('status')} for c in checks]
    with memory.lock:
        previous=read(memory,project,'architecture.validation');sessions=(previous or {}).get('sessions',{})
        if session not in sessions and len(sessions)>=100:raise ValueError('Validation memory reached its session bound.')
        value={'artifactId':artifact,'checks':rows,'boundary':'Backend validation receipts for these exact captured bytes, not full specification acceptance.'}
        if sessions.get(session)==value:return 'unchanged'
        sessions[session]=value;memory.architecture_fact(project,'architecture.validation',{'recordedAt':now(),'sessions':sessions})
    return 'remembered'

def artifact_review(memory,project,manifest,archive):
    """Review captured output bytes, excluding the supplied handoff baseline."""
    policy=read(memory,project,'architecture.policy')
    if not policy:raise ValueError('Save approved project rules before reviewing implementation.')
    if hashlib.sha256(archive).hexdigest()!=manifest['sha256']:raise ValueError('Captured package integrity failed.')
    files={}
    with zipfile.ZipFile(io.BytesIO(archive)) as package:
        for entry in manifest['files']:
            path=entry['path']
            if entry['kind']!='file' or path.startswith('atmem-inputs/') or path in manifest.get('pinnedInputs',{}):continue
            if not path.endswith(('.tf','.tf.json')):continue
            info=package.getinfo(path)
            if info.file_size>2_000_000 or sum(len(v.encode()) for v in files.values())+info.file_size>8_000_000:raise ValueError('Terraform output exceeds the static review bound.')
            content=package.read(path)
            if len(content)!=entry['bytes'] or hashlib.sha256(content).hexdigest()!=entry['sha256']:raise ValueError('Captured Terraform file integrity failed.')
            files[path]=content.decode('utf-8')
    if not files:raise ValueError('No generated Terraform files are captured yet.')
    request={'artifacts':[{'kind':'plan','path':'artifact/'+manifest['id'],'content':'Captured implementation Terraform; supplied baseline files are excluded.'}],
             'rules':{'path':'atmem://project/'+project+'/architecture.policy/'+policy['revision'],'content':policy['content']},
             'terraform_plan':{'path':'captured-configuration-snapshot.json','json':configuration_snapshot(files)},'options':{'cost_estimate':'off'}}
    report=review_plan(request)
    # Unsupported HCL/modules/expressions remain unresolved, even if all
    # supported predicates happen to be inapplicable to the captured subset.
    if not request['terraform_plan']['json']['complete'] or not request['terraform_plan']['json']['planned_values']['root_module']['resources']:
        if report['verdict']=='pass':report['verdict']='warn'
        report['unverified'].append({'rule_id':'IMPLEMENTATION-COVERAGE','reason':'Some captured Terraform cannot be expanded statically. Validate the complete actual plan before approval.'})
    current=read(memory,project,'architecture.policy')
    result={'recordedAt':now(),'artifactId':manifest['id'],'artifactSha256':manifest['sha256'],'runId':manifest['runId'],
            'policyRevision':policy['revision'],'state':'completed' if current and current['revision']==policy['revision'] else 'stale',
            'evidenceLevel':'captured_static_configuration_only','report':report,'fileCount':len(files)}
    memory.architecture_fact(project,'architecture.artifact_review',result)
    return result

@router.post('/status')
async def status(payload:Target):
    memory=service()
    try:
        # Keep the registry observation consistent with the memory snapshot.
        # A completed writer cannot retire between reading an older running
        # record and checking ACTIVE, otherwise a healthy finish looks aborted.
        async with LOCK:
            policy=await asyncio.to_thread(read,memory,payload.projectId,'architecture.policy')
            review=await asyncio.to_thread(read,memory,payload.projectId,'architecture.review')
            if review and review['state']=='running' and (str(memory.home),payload.projectId) not in ACTIVE:
                review={**review,'state':'interrupted','error':'The service restarted. Run the review again.'}
        return {'policy':policy,'review':review}
    except ValueError as e:raise HTTPException(422,str(e))
    except Exception:raise HTTPException(503,'AtMem memory is unavailable. Restore memory and retry.')

@router.post('/rules')
async def rules(payload:SaveRules):
    try:return await asyncio.to_thread(save_rules,service(),payload)
    except ValueError as e:raise HTTPException(422,str(e))
    except Exception:raise HTTPException(503,'Rules were not saved. Restore AtMem memory and retry.')

@router.post('/run')
async def run(payload:Run):
    memory=service();key=(str(memory.home),payload.projectId)
    if payload.project.get('id')!=payload.projectId:raise HTTPException(422,'The project identity does not match.')
    if len(json.dumps(payload.project).encode())>2_000_000:raise HTTPException(413,'Project exceeds the review request limit.')
    async with LOCK:
        if key in ACTIVE:raise HTTPException(409,'This project already has a running review.')
        try:
            policy=await asyncio.to_thread(read,memory,payload.projectId,'architecture.policy')
            if not policy:raise ValueError('Save your project rules in AtMem before reviewing.')
            state={'id':str(uuid.uuid4()),'state':'running','startedAt':now(),'projectSha256':digest(payload.project),'policyRevision':policy['revision'],'environment':payload.environment,'actions':[{'text':'Loading approved rules from AtMem','at':now()}]}
            await asyncio.to_thread(memory.architecture_fact,payload.projectId,'architecture.review',state)
            ACTIVE[key]=asyncio.create_task(execute(memory,payload,policy,state))
            return state
        except ValueError as e:raise HTTPException(422,str(e))
        except Exception:raise HTTPException(503,'Review could not start. Restore AtMem memory and retry.')
