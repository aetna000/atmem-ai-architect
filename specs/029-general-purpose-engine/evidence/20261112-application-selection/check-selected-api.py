"""Exact generated API entrypoint/SQL qualification; no cloud or business worker."""
import importlib
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from unittest.mock import Mock,patch
import uuid

ROOT=Path(__file__).resolve().parents[4]
package=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve()
sys.path[:0]=[str(package),str(ROOT/'tests/runtime')]
names=['workflow_profile','workflow_payload','workflow_contract','workflow_configuration','workflow_connection','workflow_errors','durable_workflow','workflow_worker','workflow_application','workflow_identity','workflow_http','workflow_database','workflow_role_bootstrap','approved_http_destination','structured_output','structured_http','policy_review','azure_structured','gcp_structured','ibm_structured']
for name in names:
    module=importlib.import_module(name)
    assert Path(module.__file__).resolve().parent==package,name
from workflow_application import load_profile,membership_key
from durable_privileges_acceptance import create_runtime_roles
sys.path.insert(0,str(package))
import psycopg
import jwt
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa,ec

files=sorted(p for p in package.rglob('*')if p.is_file()and '__pycache__'not in p.parts)
before={str(p.relative_to(package)):hashlib.sha256(p.read_bytes()).hexdigest()for p in files}
profile=load_profile(package/'application-profile.json');data=profile.data;provider=data['provider'];settings=data['identitySettings']
owner,api_role,worker_role,api_dsn,worker_dsn=create_runtime_roles()
subject=str(uuid.uuid4());now=int(time.time());claims={'iat':now-1,'exp':now+599,'sub':subject}
if provider=='aws':claims.update(iss='https://cognito-idp.'+settings['REGION']+'.amazonaws.com/'+settings['POOL_ID'],client_id=settings['CLIENT_ID'],token_use='access',scope='openid '+settings['AUTH_SCOPE'],username='fixture-staff')
elif provider=='azure':claims.update(iss='https://login.microsoftonline.com/'+settings['TENANT_ID']+'/v2.0',aud=settings['API_CLIENT_ID'],nbf=now-1,tid=settings['TENANT_ID'],oid=subject,azp=settings['SPA_CLIENT_ID'],ver='2.0',scp='access_as_user',roles=['WorkspaceUser','owner'])
elif provider=='gcp':claims.update(iss='https://cloud.google.com/iap',aud='/projects/'+settings['PROJECT_NUMBER']+'/locations/'+settings['REGION']+'/services/'+settings['SERVICE_NAME'],email='staff@example.test')
else:claims.update(iss=settings['APPID_ISSUER'],aud=[settings['APPID_CLIENT_ID']],tenant=settings['APPID_TENANT_ID'],amr=['cloud_directory'],scope='openid appid_authenticated '+settings['AUTH_SCOPE'])
key=ec.generate_private_key(ec.SECP256R1())if provider=='gcp'else rsa.generate_private_key(public_exponent=65537,key_size=2048)
keys=Mock();keys.get_signing_key_from_jwt.return_value=SimpleNamespace(key=key.public_key())
token=jwt.encode(claims,key,algorithm='ES256'if provider=='gcp'else'RS256',headers={'kid':'synthetic-owned-key'})
with psycopg.connect(owner)as conn:
    conn.execute('INSERT INTO workflow.accounts(id) VALUES(%s) ON CONFLICT DO NOTHING',(data['accountId'],))
    conn.execute('INSERT INTO workflow.memberships(account_id,subject,roles) VALUES(%s,%s,%s)',(data['accountId'],membership_key(profile,subject),['user']))
api=importlib.import_module('api');assert Path(api.__file__).resolve().parent==package
with patch.dict(os.environ,{},clear=True):app=api.app_factory(connection=api_dsn,jwks=keys)
headers={'Origin':data['publicOrigin'],'Idempotency-Key':'qualification-'+uuid.uuid4().hex}
headers['x-goog-iap-jwt-assertion'if provider=='gcp'else'Authorization']=token if provider=='gcp'else'Bearer '+token
with TestClient(app,base_url=data['publicOrigin'])as client:
    response=client.post('/api/operations',json={'source':{'itemId':'microscope','memberId':'member-1'}},headers=headers);assert response.status_code==202,response.text
    operation=response.json()['operation'];assert operation['state']=='pending'
    again=client.post('/api/operations',json={'source':{'itemId':'microscope','memberId':'member-1'}},headers=headers);assert again.status_code==202 and again.json()['operation']['id']==operation['id']
    bad=client.post('/api/operations',json={'source':{'itemId':'microscope','memberId':'member-1'},'accountId':str(uuid.uuid4())},headers=headers);assert bad.status_code==400
    denied=client.post('/api/operations/'+operation['id']+'/approve',json={'revision':1},headers=headers);assert denied.status_code==403
with psycopg.connect(owner)as conn:
    row=conn.execute('SELECT destination_contract,workflow_key FROM workflow.operations WHERE id=%s',(operation['id'],)).fetchone()
    assert row[0]==profile.destination and row[1]==profile.namespace+'.extract'
    assert conn.execute('SELECT count(*) FROM workflow.procrastinate_jobs WHERE args->>\'operation_id\'=%s',(operation['id'],)).fetchone()[0]==1
after={str(p.relative_to(package)):hashlib.sha256(p.read_bytes()).hexdigest()for p in files};assert before==after
out.write_text(json.dumps({'passed':True,'provider':provider,'sourcesUnchanged':True,'sourceHashes':before,'checks':['actual generated api.app_factory','real native JWT crypto with synthetic key lookup','restricted local SQL API role','durable enqueue and exact profile namespace/declaration','same-input HTTP replay has one real queue row','caller account override denied','ordinary member cannot approve'],'cloudOperations':False,'businessProcessorExecuted':False,'boundary':'Exact source emitted from selected project component; local ASGI/JWT/SQL only. Domain worker, resource linkage and full application remain pending.'},indent=2)+'\n')
print(provider+': selected API entrypoint and owned SQL/queue checks pass')
