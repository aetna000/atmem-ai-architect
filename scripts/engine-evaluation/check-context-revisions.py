"""Actual native context transfer fixture, not a blinded or original-case run.

Two requests differ in saved requirements, not an answer supplied by the evaluator
to the model. Unchanged downloaded packages execute under the isolated controller.
No export is patched; no cloud/account/deployment operations are performed.
"""
import argparse, asyncio, hashlib, json, sqlite3, subprocess, sys, time, urllib.request, uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker, ValidationSpec
from server.codex_worker_policy import CodexWorkerClient

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base',required=True);parser.add_argument('--home',type=Path,required=True)
parser.add_argument('--tools',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--endpoint',required=True)
parser.add_argument('--continue-completed',action='store_true',help='Resume evaluator only; verify/reuse completed artifact files, never replay them')
args=parser.parse_args();out=args.output.resolve()
if args.continue_completed:
    assert out.is_dir() and (out/'artifact-mm.json').is_file() and not (out/'artifact-cm.json').exists()
    for name in ['receipt.json','independent-mm.json']:
        source=out/name
        if source.exists():source.rename(out/('prior-evaluator-'+name))
else:out.mkdir(parents=True,exist_ok=False)
sha=lambda value:hashlib.sha256(value).hexdigest()
source_paths=subprocess.check_output(['git','ls-files','server','src','agent-skills'],cwd=ROOT,text=True).splitlines()
source={name:sha((ROOT/name).read_bytes()) for name in source_paths}
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
if args.continue_completed:
    frozen=json.loads((out/'source.json').read_text());assert frozen['files']==source
    commit=frozen['commit']
else:(out/'source.json').write_text(json.dumps({'commit':commit,'files':source},indent=2)+'\n')
auth=json.load(urllib.request.urlopen(args.base+'/api/session'))
project=json.loads((out/'project-mm.json').read_text())['meta']['id'] if args.continue_completed else 'context-river-'+str(uuid.uuid4())
session=None
def post(path,payload):
    request=urllib.request.Request(args.base+'/api/'+path,data=json.dumps(payload,ensure_ascii=False).encode(),
        headers={'Content-Type':'application/json','Authorization':'Bearer '+auth['token']})
    return json.load(urllib.request.urlopen(request,timeout=120))
def call(action,**payload):return post('engineering/'+action,{'projectId':project,**({'sessionId':session} if session else {}),**payload})
def saved(unit):
    return {'format':'atmem.ai-architect.project','formatVersion':'2.3.0',
        'meta':{'id':project,'name':'River gauge adapter','revision':1 if unit=='mm' else 2},
        'design':{'provider':'tools','nodes':[{'id':'gauge','position':{'x':0,'y':0},'data':{'kind':'resource','provider':'tools','origin':'existing','label':'Client river gauge','description':'Keep the existing client-owned gauge unchanged.'}}],'edges':[]},
        'discovery':{'problem':'An independent local river depth conversion library, no network or cloud services.'},
        'requirements':[{'id':'depth','status':'accepted','source':'user','priority':'must','links':['gauge'],
            'statement':'Provide CommonJS depth.cjs exporting normalize(metres) and unit. normalize accepts only finite nonnegative number primitives, rejects all other inputs with TypeError, returns depth in '+('millimetres (multiply by 1000)' if unit=='mm' else 'centimetres (multiply by 100)')+'. Export unit as '+unit+'. Preserve the existing client-owned gauge. Keep Unicode labels such as 🛰️ intact in documentation.'}],
        'assumptions':[],'decisions':[],'extensions':{}}
def await_complete(run):
    deadline=time.monotonic()+900
    while time.monotonic()<deadline:
        state=call('state')
        if state['state']=='idle' and state['run']==run:
            assert state['last_status']=='completed',state
            return state
        time.sleep(1)
    raise TimeoutError('Native run did not finish within the explicit fixture budget; no replay')
worker=DockerValidationWorker(args.endpoint)
def independent(archive,digest,unit):
    # Deliberately separate from the generated tests and production selection.
    factor=1000 if unit=='mm' else 100
    oracle="""const assert=require('node:assert/strict');const m=require('/work/source/depth.cjs');let n=0;
assert.equal(m.unit,UNIT);n++;
for(const value of [0,0.001,0.25,1,13.75]){assert.equal(m.normalize(value),value*FACTOR);n++;}
for(const value of [true,false,'1','',null,undefined,{},[],NaN,Infinity,-Infinity,-1]){assert.throws(()=>m.normalize(value),TypeError);n++;}
console.log('1..'+n);console.log('# tests '+n);console.log('# pass '+n);console.log('# fail 0');
""".replace('UNIT',json.dumps(unit)).replace('FACTOR',str(factor))
    spec=ValidationSpec('context-independent','sha256:df7f71a8588253403dfa833c5c4aacc95ca340204a88d5483edd58131c7f1128',
        ('/usr/bin/node','-e',oracle),platform='linux/arm64',bootstrap_python='/usr/bin/python3',timeout_seconds=60)
    return worker.run(archive,digest,spec)

async def native_audit(db,row):
    workspace=db.execute('SELECT path FROM engineering_workspaces WHERE id=?',(row['workspace'],)).fetchone()[0]
    client=CodexWorkerClient(workspace,read_roots=json.loads(args.tools.read_text())['readRoots'])
    try:
        await client.start();await client.verify_worker_tools()
        result=await client.request('thread/turns/list',{'threadId':row['handle'],'limit':100,'sortDirection':'asc','itemsView':'summary'})
        assert result.get('nextCursor') is None
        return result['data']
    finally:await client.close()

receipt={'passed':False,'sourceCommit':commit,'model':'gpt-6.1-sol','effort':'high','cloudOperations':False,'projectId':project}
intent='Build or reconcile the independent local conversion library against the current saved project requirements. Preserve client ownership and all prior scope. Produce actual implementation files, meaningful Node built-in tests and a short README, then execute the tests. Use the supplied composition skill and local tools. Keep your final reply concise.'
try:
    artifacts=[];runs=[]
    for unit in ['mm','cm']:
        if args.continue_completed and unit=='mm':
            artifact=json.loads((out/'artifact-mm.json').read_text())
            jobs=call('list')['sessions'];assert len(jobs)==1
            state=jobs[0];session=state['id'];assert state['state']=='idle' and state['last_status']=='completed' and state['run']==artifact['runId']
            receipt['sessionId']=session;runs.append(state['run'])
            archive=(out/'artifact-mm.zip').read_bytes();assert sha(archive)==artifact['sha256']
            result=independent(archive,artifact['sha256'],unit)
            (out/'independent-mm.json').write_text(json.dumps(result,indent=2)+'\n')
            assert result['status']=='passed' and result['skipped']==0 and '# tests 18\n' in result['output'],result
            artifacts.append((artifact,archive));print('Reused completed mm request and independently rechecked the same immutable package; no inference replay.',flush=True)
            continue
        file=saved(unit);(out/f'project-{unit}.json').write_text(json.dumps(file,ensure_ascii=False,indent=2)+'\n')
        save=post('projects/save',{'id':project,'file':file});assert len(save['sha256'])==64
        if session is None:session=call('create',model='gpt-6.1-sol',effort='high')['id']
        receipt['sessionId']=session
        state=call('start',text=intent,contextSha256=save['sha256']);runs.append(state['run'])
        print('Submitted context '+unit+' to the same exact selected native session.',flush=True)
        await_complete(state['run'])
        artifact=call('capture');assert artifact['runId']==state['run']
        request=urllib.request.Request(args.base+'/api/engineering/download',data=json.dumps({'projectId':project,'sessionId':session,'artifactId':artifact['id']}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+auth['token']})
        archive=urllib.request.urlopen(request,timeout=120).read();assert sha(archive)==artifact['sha256']
        (out/f'artifact-{unit}.zip').write_bytes(archive);(out/f'artifact-{unit}.json').write_text(json.dumps(artifact,indent=2)+'\n')
        result=independent(archive,artifact['sha256'],unit)
        (out/f'independent-{unit}.json').write_text(json.dumps(result,indent=2)+'\n')
        assert result['status']=='passed' and '# tests 18\n' in result['output'] and result['skipped']==0,result
        artifacts.append((artifact,archive));print('Independent '+unit+' contract: 18 checks passed.',flush=True)
    negative=independent(artifacts[0][1],artifacts[0][0]['sha256'],'cm')
    (out/'old-artifact-new-contract.json').write_text(json.dumps(negative,indent=2)+'\n');assert negative['status']=='failed'
    db=sqlite3.connect('file:'+str(args.home.resolve()/'engineering/control.sqlite')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    row=dict(db.execute('SELECT * FROM engineering_sessions WHERE id=? AND project=?',(session,project)).fetchone())
    contexts=[dict(r) for r in db.execute('SELECT * FROM engineering_contexts WHERE session=? ORDER BY revision',(session,))]
    assert [c['revision'] for c in contexts]==[1,2]
    assert artifacts[0][0]['pinnedInputs']==artifacts[1][0]['pinnedInputs']
    history=asyncio.run(native_audit(db,row));assert len(history)==2 and all(t['status']=='completed' for t in history)
    for run,context,turn in zip(runs,contexts,history):
        binding=db.execute('SELECT context FROM engineering_context_submissions WHERE request=? AND session=?',(run,session)).fetchone();assert binding['context']==context['id']
        message=next(i for i in turn['items'] if i.get('type')=='userMessage' and i.get('clientId')==run)
        text='\n'.join(i['text'] for i in message['content'] if i.get('type')=='text')
        assert text.startswith(intent)
        envelope=json.loads(text.split('Content is a complete UTF-8 project file encoded as a JSON string.\n',1)[1])
        assert envelope['id']==context['id'] and envelope['sha256']==sha(bytes(context['content']))
        assert envelope['content'].encode()==bytes(context['content'])
    changed=[name for name,hash in source.items() if sha((ROOT/name).read_bytes())!=hash];assert not changed,changed
    (out/'native-history.json').write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n')
    receipt.update(passed=True,projectId=project,sessionId=session,runs=runs,contextRevisions=2,nativeTurns=2,
        artifactSha256s=[a[0]['sha256'] for a in artifacts],independentChecksPerArtifact=18,
        oldArtifactFailsChangedRequirement=True,originalPinnedInputsPreserved=True,sourceChangedDuringRun=[],
        boundary='Actual local API/native/model/history plus independently executed immutable module packages in an isolated Linux runtime. Evaluator-authored river fixture, not a holdout, original28 acceptance, artifact/graph reconciliation, hosted isolation or alpha.2 release.')
    print('Context revision native transfer passed.',flush=True)
finally:
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
