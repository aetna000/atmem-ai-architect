"""Actual owned-loopback PostgreSQL, restricted broker role and crypto tests.

Creates a fresh synthetic database/role; no vendor credential or cloud is used.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import secrets
import sys
import threading
import time
import unittest
import uuid
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'.local/azure-runtime-sdk'),str(ROOT/'tests/runtime')]
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict,make_conninfo
from cryptography.fernet import Fernet
from durable_postgres_acceptance import fixture_dsn
from enterprise_auth_store import EnterpriseAuthStore,CredentialBox,initialize_auth_store,grant_auth_runtime
from enterprise_identity import CompanyPrincipal
from enterprise_sources import DelegatedAccess,SourceDenied,SourceUnavailable

BROWSER='SYNTHETIC_BROWSER_NONCE_A_0123456789'
OTHER_BROWSER='SYNTHETIC_BROWSER_NONCE_B_0123456789'

class EnterpriseCredentialTransactions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture=fixture_dsn();database='architect_qualification_'+uuid.uuid4().hex[:16];role='atmem_ent_'+uuid.uuid4().hex[:16];password=secrets.token_urlsafe(32)
        with psycopg.connect(fixture,autocommit=True)as conn:
            conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
            conn.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {}').format(sql.Identifier(role),sql.Literal(password)))
        settings=conninfo_to_dict(fixture);cls.owner_dsn=make_conninfo(**{**settings,'dbname':database});cls.app_dsn=make_conninfo(**{**settings,'dbname':database,'user':role,'password':password})
        with psycopg.connect(cls.owner_dsn)as conn:initialize_auth_store(conn);grant_auth_runtime(conn,role)
        cls.key=Fernet.generate_key()
    def setUp(self):
        self.account=uuid.uuid4().hex;self.principal=CompanyPrincipal(self.account,'https://company.example/issuer','alice',int(time.time())+3600);self.other=CompanyPrincipal(self.account,'https://company.example/issuer','bob',int(time.time())+3600)
        self.store=EnterpriseAuthStore(lambda:psycopg.connect(self.app_dsn,connect_timeout=3),self.key)
        with psycopg.connect(self.owner_dsn)as conn:
            for principal in [self.principal,self.other]:
                conn.execute('INSERT INTO enterprise_auth.memberships VALUES(%s,%s,%s,%s,true)',(self.account,principal.key,principal.issuer,principal.subject))
                conn.execute('INSERT INTO enterprise_auth.source_mappings VALUES(%s,%s,%s,%s,1,true)',(self.account,principal.key,'sharepoint:drive',principal.subject+'-native'))
    def connected(self,principal=None):
        principal=principal or self.principal;state=self.store.begin(principal,'sharepoint:drive',BROWSER,{'verifier':'SYNTHETIC-PKCE-SECRET'});mapping,flow=self.store.consume(principal,'sharepoint:drive',BROWSER,state);self.store.save(principal,mapping,{'refresh_token':'SYNTHETIC-INITIAL-REFRESH'});return mapping
    def rotated(self,mapping,material,principal=None):
        principal=principal or self.principal
        return {**material,'refresh_token':'SYNTHETIC-ROTATED-REFRESH'},DelegatedAccess(principal.key,mapping.source_subject,'SYNTHETIC-ACCESS',time.time()+3600)
    def state(self,principal=None):
        principal=principal or self.principal
        with psycopg.connect(self.owner_dsn)as conn:return conn.execute('SELECT status,credential_ciphertext FROM enterprise_auth.connections WHERE account_id=%s AND principal_key=%s',(self.account,principal.key)).fetchone()

    def test_native_msal_consent_cache_and_restart_use_actual_encrypted_sql(self):
        from enterprise_oauth import GraphConsent
        from enterprise_oauth_acceptance import OAuthHttp,Profiles,TENANT,CLIENT
        from urllib.parse import parse_qs,urlsplit
        http=OAuthHttp();profiles=Profiles();driver=GraphConsent(self.store,TENANT,CLIENT,'https://app.example/oauth/graph','drive','tenant.sharepoint.com',lambda:'SYNTHETIC-CLIENT-SECRET',http=http,profile_http=profiles)
        start=driver.start(self.principal,BROWSER);http.nonce=parse_qs(urlsplit(start.url).query)['nonce'][0];driver.finish(self.principal,BROWSER,start.state,'SYNTHETIC-CODE')
        self.assertEqual(self.state()[0],'connected');self.assertNotIn('SYNTHETIC_REFRESH',self.state()[1])
        replacement=EnterpriseAuthStore(lambda:psycopg.connect(self.app_dsn),self.key);driver.store=replacement
        self.assertEqual(driver.credentials(self.principal).source_subject,'alice-native')
        self.assertEqual(len([c for c in http.calls if c[0]=='POST']),1)
        with self.assertRaises(SourceDenied):driver.finish(self.principal,BROWSER,start.state,'SYNTHETIC-CODE')

    def test_native_confluence_rotation_persists_with_actual_sql(self):
        from enterprise_oauth import ConfluenceConsent
        from enterprise_oauth_acceptance import OAuthHttp,Profiles,CLOUD
        source='confluence:'+CLOUD
        with psycopg.connect(self.owner_dsn)as conn:conn.execute('INSERT INTO enterprise_auth.source_mappings VALUES(%s,%s,%s,%s,1,true)',(self.account,self.principal.key,source,'alice-native'))
        http=OAuthHttp();driver=ConfluenceConsent(self.store,'client','https://app.example/oauth/confluence',CLOUD,'tenant.atlassian.net',{'ENG':'42'},lambda:'SYNTHETIC-CLIENT-SECRET',http=http,profile_http=Profiles())
        start=driver.start(self.principal,BROWSER);driver.finish(self.principal,BROWSER,start.state,'SYNTHETIC-CODE');driver.credentials(self.principal);driver.credentials(self.principal)
        posts=[c for c in http.calls if c[0]=='POST'];self.assertEqual([c[2]['json'].get('refresh_token')for c in posts],[None,'SYNTHETIC_REFRESH_1','SYNTHETIC_REFRESH_2'])
        with psycopg.connect(self.owner_dsn)as conn:row=conn.execute('SELECT credential_ciphertext FROM enterprise_auth.connections WHERE account_id=%s AND source_id=%s',(self.account,source)).fetchone()
        self.assertNotIn('SYNTHETIC_REFRESH',row[0])

    def test_grant_refuses_broker_with_inherited_authority_write_access(self):
        role='atmem_bad_'+uuid.uuid4().hex[:12]
        with psycopg.connect(self.owner_dsn)as conn:
            conn.execute(sql.SQL('CREATE ROLE {} LOGIN').format(sql.Identifier(role)))
            conn.execute(sql.SQL('GRANT UPDATE ON enterprise_auth.memberships TO {}').format(sql.Identifier(role)))
            with self.assertRaisesRegex(ValueError,'write privileges'):grant_auth_runtime(conn,role)

    def test_restricted_runtime_cannot_modify_membership_or_source_identity(self):
        for query in ['UPDATE enterprise_auth.memberships SET active=true','UPDATE enterprise_auth.source_mappings SET source_subject=\'attacker\'','TRUNCATE enterprise_auth.connections','DELETE FROM enterprise_auth.events']:
            with psycopg.connect(self.app_dsn)as conn:
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):conn.execute(query)

    def test_weak_browser_nonce_or_supplied_state_is_rejected_before_storage(self):
        with self.assertRaises(SourceDenied):self.store.begin(self.principal,'sharepoint:drive','short',{})
        with self.assertRaises(SourceDenied):self.store.begin(self.principal,'sharepoint:drive',BROWSER,{},state='predictable')
        with psycopg.connect(self.owner_dsn)as conn:self.assertEqual(conn.execute('SELECT count(*)FROM enterprise_auth.attempts WHERE account_id=%s',(self.account,)).fetchone()[0],0)

    def test_state_is_single_use_under_eight_concurrent_callbacks(self):
        state=self.store.begin(self.principal,'sharepoint:drive',BROWSER,{'verifier':'SYNTHETIC-PKCE-SECRET'})
        def consume(_):
            try:return self.store.consume(self.principal,'sharepoint:drive',BROWSER,state)[1]
            except SourceDenied:return None
        with ThreadPoolExecutor(max_workers=8)as pool:results=list(pool.map(consume,range(8)))
        self.assertEqual(sum(r is not None for r in results),1);self.assertIn({'verifier':'SYNTHETIC-PKCE-SECRET'},results)
        with psycopg.connect(self.owner_dsn)as conn:
            row=conn.execute('SELECT state_sha256,flow_ciphertext FROM enterprise_auth.attempts WHERE account_id=%s',(self.account,)).fetchone()
        self.assertNotEqual(row[0],state);self.assertNotIn('SYNTHETIC-PKCE-SECRET',row[1])

    def test_state_rejects_other_browser_person_source_and_expired_attempt(self):
        state=self.store.begin(self.principal,'sharepoint:drive',BROWSER,{'flow':'data'})
        for principal,source,browser in [(self.other,'sharepoint:drive',BROWSER),(self.principal,'other-source',BROWSER),(self.principal,'sharepoint:drive',OTHER_BROWSER)]:
            with self.assertRaises(SourceDenied):self.store.consume(principal,source,browser,state)
        with psycopg.connect(self.owner_dsn)as conn:conn.execute("UPDATE enterprise_auth.attempts SET expires_at=clock_timestamp()-interval '1 second'WHERE account_id=%s",(self.account,))
        with self.assertRaises(SourceDenied):self.store.consume(self.principal,'sharepoint:drive',BROWSER,state)

    def test_concurrent_flow_limit_does_not_race_past_five(self):
        def begin(_):
            try:return self.store.begin(self.principal,'sharepoint:drive',BROWSER,{})
            except SourceUnavailable:return None
        with ThreadPoolExecutor(max_workers=8)as pool:results=list(pool.map(begin,range(8)))
        self.assertEqual(sum(x is not None for x in results),5)

    def test_membership_and_mapping_changes_reject_pending_state(self):
        state=self.store.begin(self.principal,'sharepoint:drive',BROWSER,{})
        with psycopg.connect(self.owner_dsn)as conn:conn.execute('UPDATE enterprise_auth.source_mappings SET version=2 WHERE account_id=%s AND principal_key=%s',(self.account,self.principal.key))
        with self.assertRaises(SourceDenied):self.store.consume(self.principal,'sharepoint:drive',BROWSER,state)
        with psycopg.connect(self.owner_dsn)as conn:conn.execute('UPDATE enterprise_auth.memberships SET active=false WHERE account_id=%s AND principal_key=%s',(self.account,self.principal.key))
        with self.assertRaises(SourceDenied):self.store.authorize(self.principal)

    def test_encrypted_credentials_survive_new_store_but_not_cross_person_copy(self):
        self.connected();row=self.state();self.assertNotIn('SYNTHETIC-INITIAL-REFRESH',row[1])
        replacement=EnterpriseAuthStore(lambda:psycopg.connect(self.app_dsn),self.key);seen=[]
        def refresh(mapping,material):seen.append(material['refresh_token']);return self.rotated(mapping,material)
        self.assertEqual(replacement.credentials(self.principal,'sharepoint:drive',refresh).source_subject,'alice-native');self.assertEqual(seen,['SYNTHETIC-INITIAL-REFRESH'])
        self.connected(self.other)
        with psycopg.connect(self.owner_dsn)as conn:conn.execute('UPDATE enterprise_auth.connections SET credential_ciphertext=%s WHERE account_id=%s AND principal_key=%s',(self.state()[1],self.account,self.other.key))
        with self.assertRaises(SourceDenied):self.store.credentials(self.other,'sharepoint:drive',lambda m,c:self.rotated(m,c,self.other))

    def test_concurrent_refresh_is_fenced_and_rotated_cache_is_next_input(self):
        self.connected();entered=threading.Event();release=threading.Event();seen=[]
        def refresh(mapping,material):seen.append(material['refresh_token']);entered.set();release.wait(5);return self.rotated(mapping,material)
        with ThreadPoolExecutor(max_workers=2)as pool:
            first=pool.submit(self.store.credentials,self.principal,'sharepoint:drive',refresh);self.assertTrue(entered.wait(3))
            with self.assertRaisesRegex(SourceUnavailable,'source_refresh_in_progress'):self.store.credentials(self.principal,'sharepoint:drive',refresh)
            release.set();first.result(timeout=5)
        self.store.credentials(self.principal,'sharepoint:drive',refresh);self.assertEqual(seen,['SYNTHETIC-INITIAL-REFRESH','SYNTHETIC-ROTATED-REFRESH'])

    def test_process_crash_leaves_durable_fence_and_stale_refresh_requires_reconnect(self):
        self.connected();called=[]
        class Crash(BaseException):pass
        def crash(mapping,material):called.append(True);raise Crash()
        with self.assertRaises(Crash):self.store.credentials(self.principal,'sharepoint:drive',crash)
        self.assertEqual(self.state()[0],'refreshing')
        with self.assertRaises(SourceUnavailable):self.store.credentials(self.principal,'sharepoint:drive',crash)
        self.assertEqual(called,[True])
        with psycopg.connect(self.owner_dsn)as conn:conn.execute("UPDATE enterprise_auth.connections SET updated_at=clock_timestamp()-interval '2 minutes'WHERE account_id=%s",(self.account,))
        with self.assertRaises(SourceDenied):self.store.credentials(self.principal,'sharepoint:drive',crash)
        self.assertEqual(self.state(),('needs_reconnect',None));self.assertEqual(called,[True])

    def test_refresh_uncertainty_discards_secret_and_never_replays_old_token(self):
        self.connected();called=[]
        def uncertain(mapping,material):called.append(True);raise RuntimeError('PRIVATE-REFRESH-TOKEN-AND-HTTP-BODY')
        with self.assertRaises(SourceDenied)as caught:self.store.credentials(self.principal,'sharepoint:drive',uncertain)
        self.assertNotIn('PRIVATE',str(caught.exception));self.assertEqual(self.state(),('needs_reconnect',None))
        with self.assertRaises(SourceDenied):self.store.credentials(self.principal,'sharepoint:drive',uncertain)
        self.assertEqual(called,[True])

    def test_consent_completion_receipt_is_single_use_and_time_bounded(self):
        mapping=self.connected()
        with self.assertRaises(SourceDenied):self.store.save(self.principal,mapping,{'refresh_token':'SYNTHETIC-REPLAYED-CONSENT'})
        state=self.store.begin(self.principal,'sharepoint:drive',BROWSER,{})
        mapping,_=self.store.consume(self.principal,'sharepoint:drive',BROWSER,state)
        with psycopg.connect(self.owner_dsn)as conn:conn.execute("UPDATE enterprise_auth.attempts SET consumed_at=clock_timestamp()-interval '2 minutes'WHERE state_sha256=%s",(mapping.attempt_sha256,))
        with self.assertRaises(SourceDenied):self.store.save(self.principal,mapping,{'refresh_token':'SYNTHETIC-EXPIRED-CONSENT'})
        self.assertEqual(self.state()[0],'connected')

    def test_disconnect_during_initial_consent_exchange_cannot_be_undone(self):
        self.connected()
        state=self.store.begin(self.principal,'sharepoint:drive',BROWSER,{'flow':'new-consent'})
        mapping,_=self.store.consume(self.principal,'sharepoint:drive',BROWSER,state)
        self.store.disconnect(self.principal,'sharepoint:drive')
        with self.assertRaises(SourceDenied):self.store.save(self.principal,mapping,{'refresh_token':'SYNTHETIC-LATE-CONSENT'})
        self.assertEqual(self.state(),('revoked',None))

    def test_disconnect_during_refresh_cannot_be_undone_by_late_response(self):
        self.connected()
        def refresh(mapping,material):self.store.disconnect(self.principal,'sharepoint:drive');return self.rotated(mapping,material)
        with self.assertRaises(SourceDenied):self.store.credentials(self.principal,'sharepoint:drive',refresh)
        self.assertEqual(self.state(),('revoked',None))

    def test_company_revocation_during_refresh_withholds_access_and_clears_material(self):
        self.connected()
        def refresh(mapping,material):
            with psycopg.connect(self.owner_dsn)as conn:conn.execute('UPDATE enterprise_auth.memberships SET active=false WHERE account_id=%s AND principal_key=%s',(self.account,self.principal.key))
            return self.rotated(mapping,material)
        with self.assertRaises(SourceDenied):self.store.credentials(self.principal,'sharepoint:drive',refresh)
        self.assertEqual(self.state(),('needs_reconnect',None))

    def test_cross_account_access_and_source_refresh_identity_mismatch_deny(self):
        self.connected();other=CompanyPrincipal('other-company',self.principal.issuer,self.principal.subject,self.principal.expires_at)
        with self.assertRaises(SourceDenied):self.store.credentials(other,'sharepoint:drive',self.rotated)
        def wrong(mapping,material):return material,DelegatedAccess(self.principal.key,'bob-native','SYNTHETIC',time.time()+3600)
        with self.assertRaises(SourceDenied):self.store.credentials(self.principal,'sharepoint:drive',wrong)
        self.assertEqual(self.state(),('needs_reconnect',None))

if __name__=='__main__':unittest.main()
