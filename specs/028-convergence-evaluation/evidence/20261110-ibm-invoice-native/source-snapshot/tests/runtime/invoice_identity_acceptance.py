"""Actual JWT signatures plus real local DB/API membership, not live IdP evidence."""
from pathlib import Path
import base64
import json
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import uuid
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(Path(__file__).resolve().parent),str(ROOT/'.local/azure-runtime-sdk')]
import httpx
import jwt
import psycopg
from cryptography.hazmat.primitives.asymmetric import rsa,ec
from invoice_identity import native_staff_identity,CognitoStaffVerifier
from invoice_native import create_native_api
from invoice_http_acceptance import OwnedObjectsFixture
from durable_privileges_acceptance import create_runtime_roles
from durable_fixture_tasks import FIXTURE_CONTRACT
from durable_workflow import Denied
from workflow_worker import producer_store

TENANT='11111111-1111-1111-1111-111111111111';API='22222222-2222-2222-2222-222222222222';SPA='33333333-3333-3333-3333-333333333333'

def identity_fixture(provider):
    now=int(time.time());subject=str(uuid.uuid4());key=ec.generate_private_key(ec.SECP256R1())if provider=='gcp'else rsa.generate_private_key(public_exponent=65537,key_size=2048)
    keys=Mock();keys.get_signing_key_from_jwt.return_value=SimpleNamespace(key=key.public_key());claims={'iat':now-1,'exp':now+599,'sub':subject}
    if provider=='aws':
        settings={'REGION':'ap-southeast-2','POOL_ID':'ap-southeast-2_Fixture','CLIENT_ID':'fixtureclient123','AUTH_ORIGIN':'https://invoice-fixture.auth.ap-southeast-2.amazoncognito.com','AUTH_SCOPE':'invoice/process'}
        claims.update({'iss':'https://cognito-idp.ap-southeast-2.amazonaws.com/ap-southeast-2_Fixture','client_id':settings['CLIENT_ID'],'token_use':'access','scope':'openid invoice/process','username':'staff-fixture'})
    elif provider=='azure':
        settings={'TENANT_ID':TENANT,'API_CLIENT_ID':API,'SPA_CLIENT_ID':SPA}
        claims.update({'iss':'https://login.microsoftonline.com/'+TENANT+'/v2.0','aud':API,'nbf':now-1,'tid':TENANT,'oid':subject,'azp':SPA,'ver':'2.0','scp':'access_as_user','roles':['WorkspaceUser','owner']})
    elif provider=='gcp':
        settings={'PROJECT_NUMBER':'123456789012','REGION':'australia-southeast1','SERVICE_NAME':'invoice-api'}
        subject='accounts.google.com:'+subject;claims.update({'iss':'https://cloud.google.com/iap','aud':'/projects/123456789012/locations/australia-southeast1/services/invoice-api','email':'staff@example.test','sub':subject})
    else:
        settings={'APPID_TENANT_ID':TENANT,'APPID_CLIENT_ID':API,'APPID_ISSUER':'https://au-syd.appid.cloud.ibm.com/oauth/v4/'+TENANT,'AUTH_SCOPE':'invoice/process'}
        claims.update({'iss':settings['APPID_ISSUER'],'aud':[API],'tenant':TENANT,'amr':['cloud_directory'],'scope':'openid appid_authenticated invoice/process'})
    identity=native_staff_identity(provider,settings,jwks=keys);algorithm='ES256'if provider=='gcp'else'RS256'
    def token(changes=None,signing_key=None):return jwt.encode({**claims,**(changes or {})},signing_key or key,algorithm=algorithm,headers={'kid':'owned-synthetic-key'})
    return identity,subject,token,claims,settings

class CognitoCredentialTests(unittest.TestCase):
    def setUp(self):self.identity,self.subject,self.token,self.claims,self.settings=identity_fixture('aws')
    def test_real_signed_access_token(self):self.assertEqual(self.identity.verify(self.token()),self.subject)
    def test_id_machine_wrong_client_scope_expired_and_malformed_claims_are_denied(self):
        for changes in [{'token_use':'id'},{'client_id':'other'},{'scope':'openid'},{'sub':'machine-client'},{'username':''},{'exp':int(time.time())-1},{'exp':int(time.time())+7200},{'iat':str(self.claims['iat'])},{'iss':'https://attacker.invalid'}]:
            with self.subTest(changes=changes),self.assertRaises(Denied):self.identity.verify(self.token(changes))
    def test_forged_unsigned_and_unavailable_key_fail_closed(self):
        other=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        for token in [self.token(signing_key=other),jwt.encode(self.claims,'',algorithm='none'),'malformed','x'*16385]:
            with self.assertRaises(Denied):self.identity.verify(token)
        self.identity.verify.jwks.get_signing_key_from_jwt.side_effect=TimeoutError()
        with self.assertRaises(Denied):self.identity.verify(self.token())
    def test_cross_region_pool_or_authority_and_extra_secret_fields_are_rejected(self):
        for changes in [{'POOL_ID':'us-east-1_Fixture'},{'AUTH_ORIGIN':'https://invoice.auth.us-east-1.amazoncognito.com'},{'CLIENT_SECRET':'private'}]:
            with self.assertRaises(ValueError):native_staff_identity('aws',{**self.settings,**changes})

class NativeStaffApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_each_native_signed_identity_is_bound_to_live_database_membership_and_approval_role(self):
        for provider in ['aws','azure','gcp','ibm']:
            with self.subTest(provider=provider):
                identity,subject,token,claims,settings=identity_fixture(provider);self.assertEqual(identity.verify(token()),subject)
                owner,_,_,api_dsn,worker_dsn=create_runtime_roles();account=str(uuid.uuid4());namespace='q'+uuid.uuid4().hex[:12]
                with psycopg.connect(owner)as conn:
                    conn.execute('INSERT INTO workflow.accounts(id)VALUES(%s)',(account,));conn.execute('INSERT INTO workflow.memberships(account_id,subject,roles)VALUES(%s,%s,%s)',(account,subject,['user']))
                api=producer_store(api_dsn,destination_contract=FIXTURE_CONTRACT,namespace=namespace);worker=producer_store(worker_dsn,destination_contract=FIXTURE_CONTRACT,namespace=namespace);objects=OwnedObjectsFixture();origin='https://invoice.example.test'
                environment={**settings,'ACCOUNT_ID':account,'PUBLIC_ORIGIN':origin,'WORKFLOW_NAMESPACE':namespace,'DESTINATION_CONTRACT_BASE64':base64.b64encode(json.dumps(FIXTURE_CONTRACT).encode()).decode()}
                app=create_native_api(provider,environment,connection=api_dsn,objects=objects,jwks=identity.verify.jwks)
                headers={identity.token_header or'Authorization':token()if identity.token_header else'Bearer '+token(),'Origin':origin}
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url=origin)as client:
                    response=await client.post('/api/invoices',content=b'%PDF-1.7\nExplicit identity boundary fixture\n%%EOF',headers={**headers,'Content-Type':'application/pdf'});self.assertEqual(response.status_code,202,response.text);operation=response.json()['invoice']['id']
                    lease=worker.claim_extract(operation);worker.record_result(operation,str(lease['lease_token']),{'supplier':'Identity fixture','invoice_date':'2026-11-10','total':'42.50','currency':'AUD'})
                    self.assertEqual((await client.post('/api/invoices/'+operation+'/approve',headers=headers,json={'revision':1})).status_code,403)
                    # No token role claim can replace this independent live SQL
                    # membership admission. Azure's forged owner claim above is ignored.
                    self.assertEqual((await client.get('/api/session',headers=headers)).json()['roles'],['user'])
                    self.assertEqual((await client.get('/api/session',headers={'Authorization':'Bearer forged','x-goog-authenticated-user-email':'staff@example.test'})).status_code,403)
                    other=str(uuid.uuid4());other_token=token({'oid':other,'sub':other}if provider=='azure'else{'sub':other})
                    other_headers={identity.token_header or'Authorization':other_token if identity.token_header else'Bearer '+other_token}
                    self.assertEqual((await client.get('/api/session',headers=other_headers)).status_code,403)
                    with psycopg.connect(owner)as conn:conn.execute('UPDATE workflow.memberships SET active=false WHERE account_id=%s AND subject=%s',(account,subject))
                    for path in ['/api/session','/api/invoices/'+operation,'/api/invoices/'+operation+'/original']:
                        self.assertEqual((await client.get(path,headers=headers)).status_code,403)

if __name__=='__main__':unittest.main(verbosity=2)
