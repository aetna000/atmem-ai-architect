"""Owned SQL bootstrap on real local PostgreSQL; vendor mappings are fixtures.

No RDS, Entra, Cloud SQL or IBM authentication service is exercised here. Roles
and authentication markers belong solely to the nonce-guarded local cluster.
"""
from pathlib import Path
import secrets
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import uuid
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict,make_conninfo

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(Path(__file__).resolve().parent)]
from durable_postgres_acceptance import fixture_dsn
from workflow_role_bootstrap import bootstrap_runtime_roles,role_marker

class NativeRoleBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.owner=fixture_dsn();self.deployment=str(uuid.uuid4());prefix='qa_'+uuid.uuid4().hex[:12]
        self.bindings={purpose:{'name':prefix+'_'+purpose,'principal':'arn:aws:iam::123456789012:role/'+prefix+'_'+purpose}for purpose in ['api','worker']}
    def marker(self,name):
        with psycopg.connect(self.owner)as conn:
            flags=conn.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls,rolcanlogin FROM pg_roles WHERE rolname=%s',(name,)).fetchone()
            if flags is None:conn.execute(sql.SQL('CREATE ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS').format(sql.Identifier(name)))
            elif any(flags):raise ValueError('Unexpected local authentication marker')
    def bootstrap(self,provider='aws',**kwargs):
        with psycopg.connect(self.owner)as conn:
            return bootstrap_runtime_roles(conn,provider=provider,deployment_id=self.deployment,bindings=self.bindings,**kwargs)
    def test_owned_aws_roles_are_idempotent_and_restore_only_auth_membership(self):
        self.marker('rds_iam');expected={p:b['name']for p,b in self.bindings.items()}
        self.assertEqual(self.bootstrap(),expected)
        with psycopg.connect(self.owner)as conn:
            conn.execute(sql.SQL('REVOKE rds_iam FROM {}').format(sql.Identifier(expected['api'])))
        self.assertEqual(self.bootstrap(),expected)
        with psycopg.connect(self.owner)as conn:
            for purpose,binding in self.bindings.items():
                row=conn.execute("SELECT rolconnlimit,shobj_description(oid,'pg_authid'),pg_has_role(oid,'rds_iam','MEMBER') FROM pg_roles WHERE rolname=%s",(binding['name'],)).fetchone()
                self.assertEqual(row,(48 if purpose=='api'else 24,role_marker('aws',self.deployment,purpose,binding),True))
    def test_unowned_roles_and_changed_principals_are_never_adopted(self):
        self.marker('rds_iam');name=self.bindings['api']['name']
        with psycopg.connect(self.owner)as conn:conn.execute(sql.SQL('CREATE ROLE {} LOGIN').format(sql.Identifier(name)))
        with self.assertRaisesRegex(ValueError,'unrelated'):self.bootstrap()
        self.setUp();self.bootstrap();self.bindings['api']['principal']+='-changed'
        with self.assertRaisesRegex(ValueError,'unrelated'):self.bootstrap()
    def test_owned_role_with_unreviewed_parent_is_rejected_without_removing_grant(self):
        self.marker('rds_iam');self.bootstrap();parent='qa_'+uuid.uuid4().hex[:12];name=self.bindings['api']['name']
        with psycopg.connect(self.owner)as conn:
            conn.execute(sql.SQL('CREATE ROLE {} NOLOGIN').format(sql.Identifier(parent)))
            conn.execute(sql.SQL('GRANT {} TO {}').format(sql.Identifier(parent),sql.Identifier(name)))
        with self.assertRaisesRegex(ValueError,'inherited'):self.bootstrap()
        with psycopg.connect(self.owner)as conn:self.assertTrue(conn.execute('SELECT pg_has_role(%s,%s,\'MEMBER\')',(name,parent)).fetchone()[0])
    def test_ibm_separate_sql_password_uses_scram_and_repeated_bootstrap_does_not_rotate(self):
        passwords={p:secrets.token_urlsafe(32)for p in self.bindings};reads=[]
        for binding in self.bindings.values():binding['principal']=str(uuid.uuid4())
        def password(purpose,principal):reads.append((purpose,principal));return passwords[purpose]
        self.bootstrap('ibm',passwords=password);self.assertEqual(len(reads),2)
        def no_rotation(*args):raise AssertionError('Existing passwords must not be silently rotated')
        self.bootstrap('ibm',passwords=no_rotation)
        for purpose,binding in self.bindings.items():
            dsn=make_conninfo(**{**conninfo_to_dict(self.owner),'user':binding['name'],'password':passwords[purpose]})
            with psycopg.connect(dsn)as conn:self.assertEqual(conn.execute('SELECT current_user').fetchone()[0],binding['name'])
            with psycopg.connect(self.owner)as conn:
                verifier=conn.execute('SELECT rolpassword FROM pg_authid WHERE rolname=%s',(binding['name'],)).fetchone()[0]
                self.assertTrue(verifier.startswith('SCRAM-SHA-256$'));self.assertNotIn(passwords[purpose],verifier)
    def test_cloudsql_requires_native_created_login_and_auth_membership(self):
        self.marker('cloudsqliamserviceaccount');suffix=uuid.uuid4().hex[:12]
        self.bindings={p:{'name':f'{p}-{suffix}@owned-project.iam','principal':f'{p}-{suffix}@owned-project.iam.gserviceaccount.com','created_by_package':True}for p in ['api','worker']}
        with self.assertRaisesRegex(ValueError,'Apply the owned'):self.bootstrap('gcp')
        with psycopg.connect(self.owner)as conn:
            for binding in self.bindings.values():
                conn.execute(sql.SQL('CREATE ROLE {} LOGIN').format(sql.Identifier(binding['name'])))
                conn.execute(sql.SQL('GRANT cloudsqliamserviceaccount TO {}').format(sql.Identifier(binding['name'])))
        self.assertEqual(self.bootstrap('gcp'),{p:b['name']for p,b in self.bindings.items()})
        with psycopg.connect(self.owner)as conn:conn.execute(sql.SQL('REVOKE cloudsqliamserviceaccount FROM {}').format(sql.Identifier(self.bindings['api']['name'])))
        with self.assertRaisesRegex(ValueError,'membership is missing'):self.bootstrap('gcp')
    def test_azure_mapping_is_rejected_on_application_database(self):
        for binding in self.bindings.values():binding['principal']=str(uuid.uuid4())
        with self.assertRaisesRegex(ValueError,'native postgres database'):self.bootstrap('azure',tenant_id=str(uuid.uuid4()))
    def test_azure_authoritative_mapping_must_match_tenant_oid_and_nonadmin_flags(self):
        # Only the vendor mapping functions are scripted. Role DDL, transaction
        # rollback, identity markers and post-create privilege checks use PG.
        tenant=str(uuid.uuid4());mapping={};calls=[]
        for binding in self.bindings.values():binding['principal']=str(uuid.uuid4())
        class AzureMappingFixture:
            info=SimpleNamespace(dbname='postgres')
            def __init__(self,conn):self.conn=conn
            def cursor(self,**kwargs):return self.conn.cursor(**kwargs)
            def execute(self,query,args=None):
                if isinstance(query,str)and query.startswith('SELECT pg_catalog.pgaadauth_create_principal_with_oid'):
                    calls.append(args);name,oid=args
                    self.conn.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS').format(sql.Identifier(name)))
                    mapping[name]=(name,'service',oid,tenant,0,0)
                    return None
                return self.conn.execute(query,args)
        def run():
            with psycopg.connect(self.owner)as conn,patch('workflow_role_bootstrap.azure_principal',side_effect=lambda _,name:mapping.get(name)):
                return bootstrap_runtime_roles(AzureMappingFixture(conn),provider='azure',deployment_id=self.deployment,bindings=self.bindings,tenant_id=tenant)
        self.assertEqual(run(),{p:b['name']for p,b in self.bindings.items()});run();self.assertEqual(len(calls),2)
        name=self.bindings['api']['name'];original=mapping[name]
        for index,value in [(1,'user'),(2,str(uuid.uuid4())),(3,str(uuid.uuid4())),(4,1),(5,1)]:
            with self.subTest(index=index):
                changed=list(original);changed[index]=value;mapping[name]=tuple(changed)
                with self.assertRaisesRegex(ValueError,'Entra role mapping'):run()
        mapping[name]=original
        with psycopg.connect(self.owner)as conn:conn.execute(sql.SQL('ALTER ROLE {} CREATEDB').format(sql.Identifier(name)))
        with self.assertRaisesRegex(ValueError,'nonadministrative'):run()

if __name__=='__main__':unittest.main(verbosity=2)
