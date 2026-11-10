"""Owner-authorized live 28-project benchmark. No cloud plans/apply; preserve failures."""
import argparse,asyncio,hashlib,json,pathlib,re,subprocess,sys,time,shutil
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
CORPUS=ROOT/'benchmarks/convergence/scenarios.json'

def freeze_knowledge_evidence(root,snapshot=None):
    """Copy only active pinned proof receipts, retaining all knowledge gates."""
    root=pathlib.Path(root).resolve();proofs=[]
    catalogue=json.loads((root/'knowledge/engineering-practices.json').read_text())
    for row in catalogue['records']:
        if row.get('status')!='active'or row.get('source',{}).get('archived')or row.get('evidenceLevel')!='locally-tested':continue
        proof=row.get('localVerification',{});path=(root/proof.get('receipt','')).resolve()
        if not path.is_relative_to(root/'specs')or not path.is_file()or hashlib.sha256(path.read_bytes()).hexdigest()!=proof.get('sha256'):raise ValueError('Cannot freeze an absent, escaped or changed knowledge proof receipt')
        if json.loads(path.read_text()).get('passed')is not True or not proof.get('scope'):raise ValueError('Cannot freeze unqualified local knowledge evidence')
        proofs.append({'practiceId':row['id'],'receipt':path.relative_to(root).as_posix(),'sha256':proof['sha256'],'scope':proof['scope']})
    # Validate every source before writing any receipt; never symlink mutable proof.
    if snapshot is not None:
        snapshot=pathlib.Path(snapshot).resolve()
        for proof in proofs:
            source=root/proof['receipt'];target=snapshot/proof['receipt'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
            if hashlib.sha256(target.read_bytes()).hexdigest()!=proof['sha256']:raise ValueError('Knowledge proof changed while freezing')
        (snapshot/'knowledge-evidence.json').write_text(json.dumps({'format':'atmem-frozen-knowledge-evidence-v1','proofs':proofs,'boundary':'Pinned existing locally tested scopes only; no new runtime/deployment claim.'},indent=2)+'\n')
    return proofs

def validate_case_selection(selected):
    corpus=json.loads(CORPUS.read_text())
    known={provider+'-'+scenario['id'] for provider in corpus['providers'] for scenario in corpus['scenarios']}
    unknown=set(selected or [])-known
    if unknown:raise ValueError('Unknown benchmark case IDs: '+', '.join(sorted(unknown)))
    if selected and len(selected)!=len(set(selected)):raise ValueError('Duplicate benchmark case IDs')

def complete_client_facts(scenario,used):
    remaining=[key for key in scenario['facts'] if key not in used]
    if not remaining:return None
    used.update(remaining)
    return 'Here are the remaining project facts before we finalize the handoff. Preserve these requirements and update the system as needed. '+ ' '.join(scenario['facts'][key] for key in remaining)

def bridge(payload):
    run=subprocess.run(['node',str(ROOT/'scripts/convergence-bridge.mjs')],input=json.dumps(payload),capture_output=True,text=True,cwd=ROOT,timeout=45)
    if run.returncode:raise RuntimeError('Bridge: '+run.stderr[-2000:])
    return json.loads(run.stdout)

def question(response):
    if response.get('followUp'):return response['followUp']['question']
    matches=re.findall(r'[^.!?\n]*\?',response.get('message',''))
    return matches[-1].strip('* \t') if matches else None

def reply(scenario,q,used):
    text=q.lower();facts=scenario['facts'];keys=[]
    for key,pattern in [('users',r'user|who|staff|team|member|sign.in|account|authenticat'),('data',r'file|document|data|retain|retention|content|format'),('money',r'credit|payment|currenc|trial|webhook'),('integrations',r'existing|connect|source|sharepoint|confluence|crm|website|api'),('location',r'region|country|where|residen|location'),('scale',r'how many|scale|load|volume|request|concurren|traffic'),('quality',r'approve|saf|permission|failure|recovery|reliable|quality|citation'),('budget',r'budget|cost|spend'),('operations',r'backup|restore|rollback|operat')]:
        if re.search(pattern,text) and key in facts:keys.append(key)
    # The client supplies business facts; implementation facts are the Architect's work.
    technical=bool(re.search(r'\bport\b|dockerfile|startup command|sdk|\barn\b|resource group|which model|model.id|instance type|terraform variable',text))
    if technical:return 'I do not know those implementation details. Recommend and document a suitable best-practice choice for this system; ask me only if a business decision materially changes it.',True
    selected=keys[:2] or [k for k in facts if k not in used][:2]
    if not selected:return 'Use the goals and business facts already provided. Recommend the remaining engineering choices and produce the complete architecture and coding-agent handoff; keep any genuine implementation or evidence gaps explicit.',False
    used.update(selected)
    return ' '.join(facts[k] for k in selected),False

async def evaluate(args):
    from server.architect import AtMemArchitect
    from server.agent_runtime import run
    from server.contracts import ChatRequest
    from server.memory_service import MemoryService
    corpus=json.loads(CORPUS.read_text());out=pathlib.Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    memory=MemoryService(out/'isolated-home');model=AtMemArchitect();results=[]
    manifest={'corpusSha256':hashlib.sha256(CORPUS.read_bytes()).hexdigest(),'baseCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'modelProvider':args.provider,'requestedModel':args.model,'effort':args.effort,'maxTurns':args.max_turns,'cloudOperations':False,'selectedCaseIds':args.case,'sourceSnapshot':str(ROOT),'constitutionSha256':hashlib.sha256((ROOT/'CONSTITUTION.md').read_bytes()).hexdigest(),'runnerSha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'bridgeSha256':hashlib.sha256((ROOT/'scripts/convergence-bridge.mjs').read_bytes()).hexdigest(),'sourceHashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['server','src','agent-skills','benchmarks/convergence'] for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}}
    manifest['interactionProtocol']='complete-client-brief-before-export-v2' if args.complete_client_brief else 'reactive-facts-v1'
    manifest['knowledgeEvidence']=freeze_knowledge_evidence(ROOT)
    manifest['knowledgeCatalogueSha256']=hashlib.sha256((ROOT/'knowledge/engineering-practices.json').read_bytes()).hexdigest()
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    cases=[(provider,s) for provider in corpus['providers'] for s in corpus['scenarios']]
    if args.case:cases=[x for x in cases if x[0]+'-'+x[1]['id'] in args.case]
    for provider,scenario in cases:
        case_id=provider+'-'+scenario['id'];folder=out/case_id;folder.mkdir(exist_ok=True)
        if args.resume and (folder/'result.json').exists():results.append(json.loads((folder/'result.json').read_text()));continue
        prompt=scenario['intent']+' Use '+corpus['providers'][provider]+'. Recommend a coherent system and the engineering choices. Ask only a small material business question when needed; do not make me configure the system.'
        state=bridge({'action':'initial','id':'evaluation-'+case_id,'scenario':scenario,'provider':provider,'message':prompt});project=state['project'];history=[];turns=[];used=set();start=time.monotonic();technical_questions=0;seen=set();error=None
        for turn in range(1,args.max_turns+1):
            if turn>1:state=bridge({'action':'prepare','project':project,'message':prompt});project=state['project']
            request=ChatRequest(projectId=project['id'],message=prompt,provider=args.provider,model=args.model,effort=args.effort,stage='design',origin='chat',project=state['agentProject'],context=state['context'],history=history[-12:])
            (folder/f'turn-{turn}-request.json').write_text(json.dumps(request.model_dump(exclude_none=True),indent=2)+'\n')
            async def disconnected():return False
            try:
                with patch('server.agent_runtime.service',return_value=memory):response=await asyncio.wait_for(run(model,request,disconnected),timeout=520)
                (folder/f'turn-{turn}-response.json').write_text(json.dumps(response,indent=2)+'\n')
                applied=bridge({'action':'apply','project':project,'message':prompt,'response':response});project=applied['project']
                q=question(response);normalized=re.sub(r'\W+',' ',q.lower()).strip() if q else None;repeated=bool(normalized and normalized in seen)
                if normalized:seen.add(normalized)
                row={'turn':turn,'question':q,'repeatedQuestion':repeated,'scopePreserved':applied['scopePreserved'],'proposal':bool(response.get('proposal')),'internalResponseRepairs':response.get('contextUsed',{}).get('responseRepairAttempts',0),'modelResponseEncodings':response.get('contextUsed',{}).get('modelResponseEncodings',[]),'modelResponseJsonBytes':response.get('contextUsed',{}).get('modelResponseJsonBytes')}
                history += [{'role':'user','text':prompt},{'role':'assistant','text':response['message']}];turns.append(row)
                print(case_id,'turn',turn,'nodes',len(project['nodes']),'question',bool(q),flush=True)
                if not q:
                    completion=complete_client_facts(scenario,used) if args.complete_client_brief else None
                    if completion:
                        row['clientFactCompletionQueued']=True;prompt=completion;continue
                    break
                prompt,technical=reply(scenario,q,used);row['technicalQuestion']=technical;technical_questions+=int(technical)
                if repeated or technical_questions>=2:break
            except Exception as exc:
                error={'type':type(exc).__name__,'message':str(exc)[:2000]};print(case_id,'error',error['type'],flush=True);break
        (folder/'project.json').write_text(json.dumps(project,indent=2)+'\n')
        try:
            export=bridge({'action':'export','project':project,'output':str(folder/'handoff')});(folder/'export-assessment.json').write_text(json.dumps(export,indent=2)+'\n')
            quality=export['quality'];missing=[r for r in quality['components'] if r['coverage']=='implementation_required']
            proposed=[n for n in project['nodes'] if n['data'].get('origin')!='existing' and n['data']['kind']!='note'];wrong=[n['id'] for n in proposed if n['data']['provider'] not in (provider,'tools')]
            package_static=bool(project['nodes']) and quality['infrastructureComplete'] and not quality['fatalFindings'] and not export['missingDependencies'] and not wrong
            package={'staticCandidate':package_static,'implementationRequired':len(missing),'connectionGaps':sum(f['code']=='connection-required' for f in quality['findings']),'fatalFindings':quality['fatalFindings'],'wrongProviderNodes':wrong,'files':len(export['files']),'tasks':export['taskCount'],'runtime':'not_yet_qualified','nearDeploymentQualified':False}
        except Exception as exc:package={'nearDeploymentQualified':False,'exportError':{'type':type(exc).__name__,'message':str(exc)[:1000]}}
        result={'case':case_id,'scenario':scenario['id'],'difficulty':scenario['difficulty'],'provider':provider,'userExchanges':len(turns),'clarificationQuestions':sum(bool(t['question']) for t in turns),'technicalQuestions':technical_questions,'repeatedQuestions':sum(t['repeatedQuestion'] for t in turns),'convergedWithoutQuestion':bool(turns and not turns[-1]['question']),'durationSeconds':round(time.monotonic()-start,2),'clientFactKeysDelivered':sorted(used),'clientBriefComplete':set(used)==set(scenario['facts']),'turns':turns,'error':error,'package':package,'acceptance':scenario['acceptance'],'status':'requires_independent_review_and_runtime_qualification'}
        (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');results.append(result)
        (out/'results.json').write_text(json.dumps({'cases':len(results),'results':results,'cloudOperations':False},indent=2)+'\n')
        print(case_id,'export',package.get('staticCandidate'),'implementation gaps',package.get('implementationRequired'),flush=True)
        if error and re.search(r'usage|rate.limit|quota|sign.in|authenticat',error.get('message',''),re.I):break
    print('Results:',out,flush=True)
async def replay_turn(args):
    from server.architect import AtMemArchitect
    from server.agent_runtime import run
    from server.contracts import ChatRequest
    from server.memory_service import MemoryService
    out=pathlib.Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    raw=pathlib.Path(args.replay_turn).read_bytes();request=ChatRequest.model_validate(json.loads(raw))
    (out/'replay-request.json').write_bytes(raw)
    source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['server','src','agent-skills','knowledge'] for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    metadata={'kind':'exact-request-engine-replay','requestSha256':hashlib.sha256(raw).hexdigest(),'sourceHashes':source_hashes,'nativeModel':request.model,'nativeProvider':request.provider,'scope':'Single recorded request regression, not a new complete project or 28-case pass. Canonical JSON byte counts are not model token usage.','cloudOperations':False}
    (out/'replay-manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    memory=MemoryService(out/'isolated-home');start=time.monotonic()
    async def disconnected():return False
    try:
        with patch('server.agent_runtime.service',return_value=memory):response=await asyncio.wait_for(run(AtMemArchitect(),request,disconnected),timeout=520)
        (out/'replay-response.json').write_text(json.dumps(response,indent=2)+'\n')
        metrics={'completed':True,'seconds':round(time.monotonic()-start,2),'observedHostContext':response.get('contextUsed',{}),'proposal':bool(response.get('proposal'))}
    except Exception as error:metrics={'completed':False,'seconds':round(time.monotonic()-start,2),'errorType':type(error).__name__,'message':str(error)[:1000]}
    (out/'replay-result.json').write_text(json.dumps(metrics,indent=2)+'\n')
    print(json.dumps({k:v for k,v in metrics.items() if k!='observedHostContext'}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--live',action='store_true',required=True);p.add_argument('--provider',choices=['codex','claude-code'],default='codex');p.add_argument('--model',default='default');p.add_argument('--effort',default='medium');p.add_argument('--max-turns',type=int,default=10);p.add_argument('--case',action='append');p.add_argument('--complete-client-brief',action='store_true');p.add_argument('--replay-turn');p.add_argument('--resume',action='store_true');p.add_argument('--output',required=True);p.add_argument('--frozen',action='store_true');args=p.parse_args()
    try:validate_case_selection(args.case)
    except ValueError as error:p.error(str(error))
    if not args.frozen:
        out=pathlib.Path(args.output).resolve();snapshot=out/'source';snapshot.mkdir(parents=True,exist_ok=True)
        if not (snapshot/'scripts/evaluate-convergence.py').exists():
            for name in ['CONSTITUTION.md','knowledge','src','server','scripts','agent-skills','.specify','public','packages','benchmarks','package.json','package-lock.json']:
                source=ROOT/name
                if source.is_dir():shutil.copytree(source,snapshot/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'),dirs_exist_ok=True)
                elif source.exists():shutil.copyfile(source,snapshot/name)
            for name in ['node_modules','.venv','.memory-venv']:
                if (ROOT/name).exists() and not (snapshot/name).exists():(snapshot/name).symlink_to(ROOT/name,target_is_directory=True)
            freeze_knowledge_evidence(ROOT,snapshot)
            (snapshot/'.local').mkdir(exist_ok=True)
            for name in ['cloud-emulators','provider-cache']:
                if (ROOT/'.local'/name).exists() and not (snapshot/'.local'/name).exists():(snapshot/'.local'/name).symlink_to(ROOT/'.local'/name,target_is_directory=True)
        forwarded=[arg for arg in sys.argv[1:]]
        output_index=forwarded.index('--output');forwarded[output_index+1]=str(out)
        if args.replay_turn:forwarded[forwarded.index('--replay-turn')+1]=str(pathlib.Path(args.replay_turn).resolve())
        raise SystemExit(subprocess.call([sys.executable,str(snapshot/'scripts/evaluate-convergence.py'),*forwarded,'--frozen'],cwd=snapshot))
    asyncio.run(replay_turn(args) if args.replay_turn else evaluate(args))
