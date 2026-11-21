"""Independent exact-package equipment journey with real local SQL/queue/TLS.

Synthetic Cognito keys/native outputs and injected local SQL/CA only. Production
source is not edited; internal Python bootstrap injection is not an HTTP feature.
"""
import asyncio,copy,hashlib,importlib,json,os,subprocess,sys,tempfile,time,uuid
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[4]
PACKAGE=Path(sys.argv[1]).resolve();OUT=Path(sys.argv[2]).resolve();APP=PACKAGE/'application'
sys.path[:0]=[str(APP),str(ROOT/'tests/runtime')]
NAMES=['workflow_profile','workflow_payload','workflow_contract','workflow_configuration','workflow_connection','workflow_errors','durable_workflow','workflow_worker','workflow_bindings','workflow_application','workflow_identity','workflow_http','workflow_database','workflow_role_bootstrap','workflow_process_stage','approved_http_destination','structured_output','structured_http','policy_review','aws_json_model','azure_structured','gcp_structured','ibm_structured']
for name in NAMES:
    module=importlib.import_module(name);assert Path(module.__file__).resolve().parent==APP,name
from durable_privileges_acceptance import create_runtime_roles
from invoice_identity_acceptance import identity_fixture
from workflow_tls_destination_fixture import TlsDestinationFixture
sys.path.insert(0,str(APP))
import psycopg,jwt,httpx
import equipment_api,equipment_worker,equipment_domain,workflow_identity
from workflow_application import membership_key
from workflow_bindings import load_bound_profile,write_binding
from workflow_contract import normalized_contract


def hashes():return {str(p.relative_to(PACKAGE)):hashlib.sha256(p.read_bytes()).hexdigest()for p in PACKAGE.rglob('*')if p.is_file()and not any(x in p.parts for x in ['__pycache__','.terraform','.git'])}


async def main():
    before=hashes();checks=[];owner,api_role,worker_role,api_dsn,worker_dsn=create_runtime_roles()
    assert (APP/'workflow_schema.sql').read_bytes()==(ROOT/'src/runtime/workflow_schema.sql').read_bytes(),'Local bootstrap schema must match exact package'
    identity,subject,token,claims,settings=identity_fixture('aws');reviewer=str(uuid.uuid4());other=str(uuid.uuid4());account=str(uuid.uuid4());sink=TlsDestinationFixture()
    task=None
    try:
        with tempfile.TemporaryDirectory(prefix='atmem-equipment-oracle-')as tmp:
            root=Path(tmp);ledger={'version':1,'outputs':[]};envname='qualification';scope='independent-equipment'
            values=[('api','publicOrigin','https://application.example'),*[( 'identity',key,settings[key])for key in ['POOL_ID','CLIENT_ID','AUTH_ORIGIN','AUTH_SCOPE']],('destination','endpointSha256',normalized_contract(sink.url,scope)['endpointSha256']),('destination','scope',scope)]
            for owner_id,name,value in values:ledger['outputs'].append({'componentId':'work:'+owner_id,'provider':'aws','environment':envname,'name':name,'value':value,'sensitive':False,'sourceSha256':'a'*64})
            inputs=root/'outputs.json';inputs.write_text(json.dumps(ledger));configured=root/'configured'
            run=subprocess.run([sys.executable,'-I',str(PACKAGE/'scripts/configure.py'),'--account-id',account,'--environment',envname,'--ledger',str(inputs),'--out',str(configured)],capture_output=True,text=True)
            assert run.returncode==0,run.stderr;checks.append('actual exported isolated receiving-input CLI resolves fixed AWS profile and real fixture destination')
            profile=load_bound_profile(configured/'application-template.json',configured/'binding')
            secret=root/'destination.token';secret.write_text(sink.token);secret.chmod(0o600)
            environment={'BINDING_DIRECTORY':str(configured/'binding'),'APPLICATION_TEMPLATE':str(configured/'application-template.json'),'DESTINATION_ENDPOINT':sink.url,'DESTINATION_CREDENTIAL_FILE':str(secret),'PYTHONDONTWRITEBYTECODE':'1'}
            with psycopg.connect(owner)as conn:
                conn.execute('INSERT INTO workflow.accounts(id) VALUES(%s)',(account,))
                for who,roles in [(subject,['user']),(other,['user']),(reviewer,['reviewer'])]:conn.execute('INSERT INTO workflow.memberships(account_id,subject,roles) VALUES(%s,%s,%s)',(account,membership_key(profile,who),roles))
            native_identity=workflow_identity.native_staff_identity
            with patch.dict(os.environ,environment,clear=True),patch('workflow_application.native_database',return_value=api_dsn),patch('workflow_identity.native_staff_identity',side_effect=lambda provider,config,**kwargs:native_identity(provider,config,jwks=identity.verify.jwks)):
                app=equipment_api.app()
            with patch('workflow_application.native_database',return_value=worker_dsn):worker=equipment_worker.build(environment)
            # Explicit synthetic CA for the actual HTTPS child; no production
            # trust disabling, destination replacement or callback substitution.
            worker.deliver.stage.environment['SSL_CERT_FILE']=str(sink.ca_file)
            checks.append('actual exported API/worker factories; distinct restricted local SQL roles; generated child stages retained')
            def headers(who=subject):
                bearer=token if who==subject else jwt.encode({**claims,'sub':who},private_key,algorithm='RS256',headers={'kid':'fixture-key'})
                return {'Authorization':'Bearer '+bearer,'Origin':profile.data['publicOrigin'],'Idempotency-Key':'oracle-'+who}
            # Sign distinct user tokens with an independent fixture key; the
            # application still verifies native issuer/client/scope and signature.
            from cryptography.hazmat.primitives.asymmetric import rsa
            from types import SimpleNamespace
            private_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
            identity.verify.jwks.get_signing_key_from_jwt.return_value=SimpleNamespace(key=private_key.public_key())
            refreshed={**claims,'iat':int(time.time())-1,'exp':int(time.time())+599}
            claims.clear();claims.update(refreshed)
            token=jwt.encode({**claims,'sub':subject},private_key,algorithm='RS256',headers={'kid':'fixture-key'})
            task=asyncio.create_task(worker.run(install_signal_handlers=False,fetch_job_polling_interval=.05,shutdown_graceful_timeout=2))
            async def state(operation):
                with psycopg.connect(owner)as conn:return conn.execute('SELECT state FROM workflow.operations WHERE id=%s',(operation,)).fetchone()[0]
            async def until(operation,expected):
                for _ in range(400):
                    if task.done():await task
                    if await state(operation)==expected:return
                    await asyncio.sleep(.05)
                raise AssertionError('Expected operation state '+expected+'; observed '+str(await state(operation)))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url=profile.data['publicOrigin'])as client:
                source={'itemId':'microscope','memberId':'member-1','requestedDays':30,'fragile':False}
                result=await client.post('/api/operations',json={'source':source},headers=headers());assert result.status_code==202,result.text;operation=result.json()['operation']['id']
                repeat=await client.post('/api/operations',json={'source':source},headers=headers());assert repeat.status_code==202 and repeat.json()['operation']['id']==operation
                await until(operation,'review');row=await client.get('/api/operations/'+operation,headers=headers());assert row.json()['operation']['result']=={'loanDays':14,'inspectionRequired':False}
                checks.append('real queue and exact bounded process child apply normal-equipment14-day policy; duplicate input has one operation')
                denied=await client.get('/api/operations/'+operation,headers=headers(other));assert denied.status_code in {403,404},denied.text
                listing=await client.get('/api/operations',headers=headers(other));assert listing.status_code==200 and not listing.json()['operations']
                denied=await client.post('/api/operations/'+operation+'/approve',json={'revision':1},headers=headers());assert denied.status_code==403
                checks.append('ordinary staff own-read/list isolation and reviewer-only approval through real native JWT signatures/live memberships')
                for bad in [{'source':source,'accountId':str(uuid.uuid4())},{'source':{**source,'requestedDays':True}}]:
                    denied=await client.post('/api/operations',json=bad,headers=headers());assert denied.status_code==400,denied.text
                checks.append('caller account override and boolean-as-integer input rejected')
                approved=await client.post('/api/operations/'+operation+'/approve',json={'revision':1},headers=headers(reviewer));assert approved.status_code==200,approved.text
                await until(operation,'sent');assert len(sink.calls)==1 and sink.calls[0]['body']['result']=={'itemId':'microscope','memberId':'member-1','loanDays':14,'inspectionRequired':False},sink.calls
                checks.append('reviewer approval dispatches exact source-bound fulfilment mapping via real bounded child and loopback TLS once')
                changed_inputs=copy.deepcopy(ledger)
                next(item for item in changed_inputs['outputs']if item['componentId']=='work:destination'and item['name']=='scope')['value']='changed-review-scope'
                changed_ledger=root/'changed-outputs.json';changed_ledger.write_text(json.dumps(changed_inputs));changed_binding=root/'changed-binding';write_binding(configured/'application-template.json',changed_ledger,changed_binding)
                with patch.dict(os.environ,{**environment,'BINDING_DIRECTORY':str(changed_binding)},clear=True),patch('workflow_application.native_database',return_value=api_dsn),patch('workflow_identity.native_staff_identity',side_effect=lambda provider,config,**kwargs:native_identity(provider,config,jwks=identity.verify.jwks)):
                    changed_app=equipment_api.app()
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=changed_app),base_url=profile.data['publicOrigin'])as changed_client:
                    rejected=await changed_client.post('/api/operations/'+operation+'/approve',json={'revision':1},headers=headers(reviewer));assert rejected.status_code==409,rejected.text
                checks.append('changed receiving destination/profile contract cannot reapprove an older operation')
                changed_template=json.loads((configured/'application-template.json').read_text());changed_template['payloadContract']['result']['properties']['loanDays']['maximum']=15
                altered=root/'altered-template.json';altered.write_text(json.dumps(changed_template));altered_binding=root/'altered-binding';write_binding(altered,inputs,altered_binding)
                with patch.dict(os.environ,{**environment,'APPLICATION_TEMPLATE':str(altered),'BINDING_DIRECTORY':str(altered_binding)},clear=True),patch('workflow_application.native_database')as native_database:
                    try:equipment_api.app()
                    except ValueError:pass
                    else:raise AssertionError('Changed compiled equipment payload policy started')
                    native_database.assert_not_called()
                checks.append('altered payload policy cannot start the compiled application before native database setup')

                fragile={**source,'itemId':'glassware','fragile':True};h={**headers(),'Idempotency-Key':'fragile-'+uuid.uuid4().hex};response=await client.post('/api/operations',json={'source':fragile},headers=h);assert response.status_code==202,response.text;second=response.json()['operation']['id'];await until(second,'review')
                invalid=await client.post('/api/operations/'+second+'/review',json={'revision':1,'result':{'loanDays':4,'inspectionRequired':True}},headers=headers(reviewer));assert invalid.status_code in {400,409},invalid.text
                checks.append('fragile3-day policy enforced against otherwise type-valid reviewer edits')
                edited=await client.post('/api/operations/'+second+'/review',json={'revision':1,'result':{'loanDays':2,'inspectionRequired':True}},headers=headers(reviewer));assert edited.status_code==200,edited.text;revision=edited.json()['operation']['revision'];assert revision==2
                stale=await client.post('/api/operations/'+second+'/approve',json={'revision':1},headers=headers(reviewer));assert stale.status_code==409,stale.text
                checks.append('valid reviewer edit advances revision; stale revision cannot approve')
                sink.mode='pending';approved=await client.post('/api/operations/'+second+'/approve',json={'revision':revision},headers=headers(reviewer));assert approved.status_code==200,approved.text
                await until(second,'unknown');calls=len(sink.calls);await asyncio.sleep(.4);assert len(sink.calls)==calls==2
                with psycopg.connect(owner)as conn:jobs_before=conn.execute('SELECT count(*) FROM workflow.procrastinate_jobs WHERE args->>\'operation_id\'=%s',(second,)).fetchone()[0]
                retry=await client.post('/api/operations/'+second+'/approve',json={'revision':revision},headers=headers(reviewer));assert retry.status_code in {200,409},retry.text
                if retry.status_code==200:assert retry.json()['operation']['state']=='unknown',retry.text
                await asyncio.sleep(.2)
                with psycopg.connect(owner)as conn:
                    assert conn.execute('SELECT count(*) FROM workflow.procrastinate_jobs WHERE args->>\'operation_id\'=%s',(second,)).fetchone()[0]==jobs_before
                    assert conn.execute('SELECT state FROM workflow.operations WHERE id=%s',(second,)).fetchone()[0]=='unknown'
                assert len(sink.calls)==calls
                checks.append('accepted-but-unconfirmed TLS outcome stays unknown; repeated approval creates no new job or external attempt')
                with psycopg.connect(owner)as conn:conn.execute('UPDATE workflow.memberships SET active=false WHERE account_id=%s AND subject=%s',(account,membership_key(profile,subject)))
                denied=await client.get('/api/operations/'+operation,headers=headers());assert denied.status_code==403,denied.text
                checks.append('revoked live membership overrides an unexpired signed native token')
            task.cancel()
            try:await task
            except asyncio.CancelledError:pass
            task=None
        after=hashes();assert before==after,'Exported source changed'
        receipt={'passed':True,'checks':checks,'sourcesUnchanged':True,'sourceHashes':before,'cloudOperations':False,'boundary':'Exact generated equipment application, actual JWT crypto/restricted local SQL/Procrastinate/child processes/loopback TLS. Cognito keys, public native outputs, SQL role injection and TLS CA are explicit fixtures. No AWS identity/IAM/network/resource, clean image or full-project acceptance.'}
        OUT.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':True,'checks':len(checks),'sourcesUnchanged':True}))
    finally:
        if task is not None:
            task.cancel()
            try:await task
            except asyncio.CancelledError:pass
        sink.close()


try:asyncio.run(main())
except Exception as error:
    OUT.write_text(json.dumps({'passed':False,'errorType':type(error).__name__,'message':str(error),'cloudOperations':False},indent=2)+'\n');raise
