"""Real fresh-schema provisioning, atomic directory updates and revocation."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import time
import unittest
import uuid
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(ROOT/'.local/azure-runtime-sdk'),str(ROOT/'tests/runtime')]
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from enterprise_deployment_fixture import metadata,fresh_database
from enterprise_operator import enroll,revoke,initialize,activate
from enterprise_auth_store import EnterpriseAuthStore
from enterprise_identity import CompanyPrincipal
from enterprise_sessions import CompanySessions
from enterprise_queries import producer_queries,QueryLeaseLost
from enterprise_sources import SourceDenied


class OperatorLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.database=fresh_database()

    def setUp(self):
        self.account=uuid.uuid4().hex;self.metadata=metadata(self.account)
        with psycopg.connect(self.database['owner'])as conn:activate(conn,self.metadata)
        self.principal=CompanyPrincipal(self.account,self.metadata['company']['issuer'],'alice',int(time.time())+3600)
        self.mapping={'sharepoint':'alice-native','confluence':'alice-atlassian'}
        self.auth=EnterpriseAuthStore(lambda:psycopg.connect(self.database['api']),self.database['key'])

    def test_bootstrap_owner_is_not_superuser_or_cluster_role_administrator(self):
        with psycopg.connect(self.database['owner'])as conn:
            self.assertEqual(conn.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone(),(False,False,False,False,False))
            self.assertTrue(conn.execute('SELECT pg_get_userbyid(datdba)=current_user FROM pg_database WHERE datname=current_database()').fetchone()[0])

    def provision(self,subject='alice',mappings=None):
        with psycopg.connect(self.database['owner'])as conn:return enroll(conn,self.metadata,subject,mappings or self.mapping)

    def connect_source(self):
        browser='SYNTHETIC_BROWSER_BINDING_0123456789';source='sharepoint:drive'
        state=self.auth.begin(self.principal,source,browser,{'owned':'synthetic-flow'})
        mapping,_=self.auth.consume(self.principal,source,browser,state)
        self.auth.save(self.principal,mapping,{'owned':'SYNTHETIC-PRIVATE-CREDENTIAL'})
        return self.auth.source_witness(self.principal,source)

    def test_idempotent_approved_enrollment_preserves_existing_consent_and_versions(self):
        first=self.provision();self.assertEqual(first['mappingsChanged'],2);self.connect_source()
        repeated=self.provision();self.assertEqual(repeated['mappingsChanged'],0)
        with psycopg.connect(self.database['owner'])as conn:
            self.assertEqual(conn.execute('SELECT version FROM enterprise_auth.source_mappings WHERE account_id=%s ORDER BY source_id',(self.account,)).fetchall(),[(1,),(1,)])
            self.assertEqual(conn.execute('SELECT status FROM enterprise_auth.connections WHERE account_id=%s',(self.account,)).fetchone()[0],'connected')
            audit=conn.execute('SELECT principal_key,actor,action,source_alias,mapping_version,active FROM enterprise_auth.administration_events WHERE account_id=%s AND principal_key=%s ORDER BY id',(self.account,self.principal.key)).fetchall()
        self.assertEqual(len(audit),3);self.assertNotIn('alice-native',str(audit));self.assertNotIn('SYNTHETIC-PRIVATE-CREDENTIAL',str(audit));self.assertTrue(all(row[0]==self.principal.key for row in audit))

    def test_changed_mapping_withdraws_old_credential_and_pending_receipts(self):
        self.provision();witness=self.connect_source()
        self.auth.begin(self.principal,'sharepoint:drive','SYNTHETIC_BROWSER_BINDING_0123456789',{'owned':'pending'})
        result=self.provision(mappings={**self.mapping,'sharepoint':'new-approved-native-account'});self.assertEqual(result['mappingsChanged'],1)
        with self.assertRaises(SourceDenied):self.auth.check_source_witness(self.principal,witness)
        with psycopg.connect(self.database['owner'])as conn:
            self.assertEqual(conn.execute('SELECT status,credential_ciphertext FROM enterprise_auth.connections WHERE account_id=%s',(self.account,)).fetchone(),('revoked',None))
            self.assertEqual(conn.execute('SELECT count(*)FROM enterprise_auth.attempts WHERE account_id=%s',(self.account,)).fetchone()[0],0)
            self.assertEqual(conn.execute('SELECT version FROM enterprise_auth.source_mappings WHERE account_id=%s AND source_id=%s',(self.account,'sharepoint:drive')).fetchone()[0],2)

    def test_revocation_cancels_queued_running_ready_jobs_and_keeps_other_members(self):
        self.provision();self.provision('bob',{'sharepoint':'bob-native','confluence':'bob-atlassian'});self.connect_source()
        sessions=CompanySessions(self.auth);alice=sessions.authenticate(sessions.create(self.principal).token)
        bob_principal=CompanyPrincipal(self.account,self.principal.issuer,'bob',self.principal.expires_at);bob_token=sessions.create(bob_principal).token;bob=sessions.authenticate(bob_token)
        api=producer_queries(self.auth,lambda:self.database['api'],self.account)
        worker_auth=EnterpriseAuthStore(lambda:psycopg.connect(self.database['worker']),self.database['key']);worker=producer_queries(worker_auth,lambda:self.database['worker'],self.account)
        identities=[api.submit(alice,'SYNTHETIC PRIVATE QUESTION '+str(index),str(uuid.uuid4()))for index in range(3)]
        running=worker.claim(identities[1]);ready=worker.claim(identities[2]);worker.complete(ready,{'question':ready.question,'synthetic':'private-receipt'})
        bob_id=api.submit(bob,'SYNTHETIC BOB QUESTION',str(uuid.uuid4()))
        with psycopg.connect(self.database['owner'])as conn:result=revoke(conn,self.metadata,'alice')
        self.assertTrue(result['changed'])
        with self.assertRaises(SourceDenied):self.auth.authorize(self.principal)
        with self.assertRaises(QueryLeaseLost):worker.guard(running)
        self.assertEqual(sessions.authenticate(bob_token).principal.key,bob_principal.key)
        self.assertEqual(api.get(bob,bob_id)['state'],'queued')
        with psycopg.connect(self.database['owner'])as conn:
            rows=conn.execute('SELECT state,question_ciphertext,result_ciphertext,lease_token FROM enterprise_queries.requests WHERE id=ANY(%s::uuid[])',(identities,)).fetchall()
            self.assertEqual(rows,[('cancelled',None,None,None)]*3)
            self.assertEqual(conn.execute('SELECT credential_ciphertext FROM enterprise_auth.connections WHERE account_id=%s AND principal_key=%s',(self.account,self.principal.key)).fetchone()[0],None)

    def test_reenable_does_not_resurrect_old_session_or_source_consent(self):
        self.provision();self.connect_source();sessions=CompanySessions(self.auth);old=sessions.create(self.principal).token
        with psycopg.connect(self.database['owner'])as conn:revoke(conn,self.metadata,'alice')
        self.provision()
        with self.assertRaises(SourceDenied):sessions.authenticate(old)
        with self.assertRaises(SourceDenied):self.auth.source_witness(self.principal,'sharepoint:drive')
        sessions.authenticate(sessions.create(self.principal).token)

    def test_runtime_roles_cannot_enroll_revoke_or_read_operator_history(self):
        self.provision()
        for role in ['api','worker']:
            with psycopg.connect(self.database[role])as conn:
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):enroll(conn,self.metadata,'unknown-person',self.mapping)
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):revoke(conn,self.metadata,'alice')
                with conn.transaction():
                    with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                        with conn.transaction():conn.execute('SELECT * FROM enterprise_auth.administration_events')
        self.auth.authorize(self.principal)

    def test_journal_failure_rolls_back_member_insert_even_when_caller_catches_error(self):
        role='atmem_limited_'+uuid.uuid4().hex[:12]
        with psycopg.connect(self.database['admin'],autocommit=True)as conn:
            conn.execute(sql.SQL('CREATE ROLE {} NOLOGIN').format(sql.Identifier(role)))
        with psycopg.connect(self.database['owner'])as conn:
            conn.execute(sql.SQL('GRANT USAGE ON SCHEMA enterprise_auth,enterprise_queries TO {}').format(sql.Identifier(role)))
            conn.execute(sql.SQL('GRANT SELECT ON enterprise_auth.schema_version,enterprise_queries.schema_version TO {}').format(sql.Identifier(role)))
            conn.execute(sql.SQL('GRANT SELECT,UPDATE ON enterprise_auth.company_bindings TO {}').format(sql.Identifier(role)))
            conn.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE ON enterprise_auth.memberships TO {}').format(sql.Identifier(role)))
        # Root fixture authority controls SET ROLE for this denial probe;
        # the actual production operator is deliberately not CREATEROLE.
        from psycopg.conninfo import make_conninfo
        with psycopg.connect(make_conninfo(**{**conninfo_to_dict(self.database['admin']),'dbname':conninfo_to_dict(self.database['owner'])['dbname']}))as conn:
            conn.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(role)))
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):enroll(conn,self.metadata,'alice',self.mapping)
            self.assertEqual(conn.execute('SELECT count(*)FROM enterprise_auth.memberships WHERE account_id=%s',(self.account,)).fetchone()[0],0)

    def test_concurrent_replayed_enrollment_is_idempotent(self):
        with ThreadPoolExecutor(max_workers=2)as pool:results=list(pool.map(lambda _:self.provision(),range(2)))
        self.assertEqual(sorted(row['mappingsChanged']for row in results),[0,2])
        with psycopg.connect(self.database['owner'])as conn:
            self.assertEqual(conn.execute('SELECT count(*)FROM enterprise_auth.administration_events WHERE account_id=%s',(self.account,)).fetchone()[0],4)

    def test_company_activation_is_idempotent_and_changes_fence_live_old_runtimes(self):
        from enterprise_configuration import session_domain
        import copy
        self.provision();sessions=CompanySessions(self.auth);token=sessions.create(self.principal).token;browser=sessions.authenticate(token)
        store=producer_queries(self.auth,lambda:self.database['api'],self.account);identity=store.submit(browser,'SYNTHETIC PRIVATE QUESTION',str(uuid.uuid4()))
        bound=EnterpriseAuthStore(lambda:psycopg.connect(self.database['api']),self.database['key'],company_domain=session_domain(self.metadata))
        bound.authorize(self.principal)
        with psycopg.connect(self.database['owner'])as conn:self.assertFalse(activate(conn,self.metadata)['changed'])
        self.assertEqual(sessions.authenticate(token).principal.key,self.principal.key);self.assertEqual(store.get(browser,identity)['state'],'queued')
        changed=copy.deepcopy(self.metadata);changed['sources']['sharepoint']['driveId']='new-approved-drive'
        with psycopg.connect(self.database['owner'])as conn:self.assertEqual(activate(conn,changed),{'changed':True,'registrationVersion':2})
        with self.assertRaises(SourceDenied):bound.authorize(self.principal)
        with self.assertRaises(SourceDenied):sessions.authenticate(token)
        with psycopg.connect(self.database['owner'])as conn:
            self.assertEqual(conn.execute('SELECT state,question_ciphertext FROM enterprise_queries.requests WHERE id=%s',(identity,)).fetchone(),('cancelled',None))
            with self.assertRaises(ValueError):enroll(conn,self.metadata,'alice',self.mapping)

    def test_unknown_revocation_and_invalid_bindings_never_create_accounts(self):
        with psycopg.connect(self.database['owner'])as conn:
            self.assertFalse(revoke(conn,self.metadata,'not-enrolled')['changed'])
            for subject,mappings in [('',self.mapping),('x'*256,self.mapping),('alice',{'sharepoint':'only-one'}),('alice',{**self.mapping,'extra':'unapproved'})]:
                with self.assertRaises(ValueError):enroll(conn,self.metadata,subject,mappings)
            self.assertEqual(conn.execute('SELECT count(*)FROM enterprise_auth.memberships WHERE account_id=%s',(self.account,)).fetchone()[0],0)

    def test_existing_schemas_are_not_adopted_and_failed_grants_rollback_fresh_ddl(self):
        with psycopg.connect(self.database['owner'])as conn:
            with self.assertRaises(ValueError):initialize(conn,conninfo_to_dict(self.database['api'])['user'],conninfo_to_dict(self.database['worker'])['user'])
        from durable_postgres_acceptance import fixture_dsn
        root=fixture_dsn();name='architect_qualification_'+uuid.uuid4().hex[:16]
        with psycopg.connect(root,autocommit=True)as conn:conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        from psycopg.conninfo import make_conninfo
        with psycopg.connect(make_conninfo(**{**conninfo_to_dict(root),'dbname':name}))as conn:
            with self.assertRaises(ValueError):initialize(conn,conninfo_to_dict(self.database['api'])['user'],'missing_owned_role')
            self.assertEqual(conn.execute("SELECT count(*)FROM pg_namespace WHERE nspname LIKE 'enterprise_%'").fetchone()[0],0)


if __name__=='__main__':unittest.main()
