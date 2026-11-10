"""Admission of native auth marker roles, not live provider authentication.

Reserved role names below are synthetic markers in the nonce-guarded local test
cluster. No managed database, account IAM or vendor role definition is changed.
"""
from pathlib import Path
import sys
import unittest
import uuid
import psycopg
from psycopg import sql

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(Path(__file__).resolve().parent)]
from durable_privileges_acceptance import create_runtime_roles
from workflow_database import grant_runtime_roles

class NativeAuthenticationGrantTests(unittest.TestCase):
    def setUp(self):
        self.owner,self.api,self.worker,_,_=create_runtime_roles()
    def marker(self,name):
        with psycopg.connect(self.owner)as conn:
            flags=conn.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls,rolcanlogin FROM pg_roles WHERE rolname=%s',(name,)).fetchone()
            if flags is None:conn.execute(sql.SQL('CREATE ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS').format(sql.Identifier(name)))
            elif any(flags):raise ValueError('Refusing an unrecognized local authentication marker role')
    def attach(self,name):
        self.marker(name)
        with psycopg.connect(self.owner)as conn:
            for role in [self.api,self.worker]:conn.execute(sql.SQL('GRANT {} TO {}').format(sql.Identifier(name),sql.Identifier(role)))
    def test_rds_auth_marker_requires_explicit_aws_profile_and_adds_no_workflow_authority(self):
        self.attach('rds_iam')
        for provider in [None,'azure','gcp','ibm']:
            with self.subTest(provider=provider),self.assertRaises(ValueError):
                with psycopg.connect(self.owner)as conn:grant_runtime_roles(conn,self.api,self.worker,native_provider=provider)
        with psycopg.connect(self.owner)as conn:grant_runtime_roles(conn,self.api,self.worker,native_provider='aws')
    def test_cloudsql_service_account_marker_is_accepted_only_as_a_native_google_mapping(self):
        self.attach('cloudsqliamserviceaccount')
        with self.assertRaises(ValueError):
            with psycopg.connect(self.owner)as conn:grant_runtime_roles(conn,self.api,self.worker,native_provider='aws')
        with psycopg.connect(self.owner)as conn:grant_runtime_roles(conn,self.api,self.worker,native_provider='gcp')
    def test_native_marker_does_not_allow_unreviewed_indirect_role_escalation(self):
        self.attach('rds_iam');parent='qa_'+uuid.uuid4().hex[:12]
        with psycopg.connect(self.owner)as conn:
            conn.execute(sql.SQL('CREATE ROLE {} NOLOGIN').format(sql.Identifier(parent)))
            conn.execute(sql.SQL('GRANT {} TO rds_iam').format(sql.Identifier(parent)))
        try:
            with self.assertRaises(ValueError):
                with psycopg.connect(self.owner)as conn:grant_runtime_roles(conn,self.api,self.worker,native_provider='aws')
        finally:
            with psycopg.connect(self.owner)as conn:conn.execute(sql.SQL('REVOKE {} FROM rds_iam').format(sql.Identifier(parent)))
    def test_public_or_auth_marker_data_grants_cannot_broaden_the_immutable_audit_boundary(self):
        self.attach('rds_iam')
        for target in ['PUBLIC','rds_iam']:
            with psycopg.connect(self.owner)as conn:conn.execute(sql.SQL('GRANT DELETE ON workflow.events TO {}').format(sql.SQL('PUBLIC')if target=='PUBLIC'else sql.Identifier(target)))
            try:
                with self.assertRaises(ValueError):
                    with psycopg.connect(self.owner)as conn:grant_runtime_roles(conn,self.api,self.worker,native_provider='aws')
            finally:
                with psycopg.connect(self.owner)as conn:conn.execute(sql.SQL('REVOKE DELETE ON workflow.events FROM {}').format(sql.SQL('PUBLIC')if target=='PUBLIC'else sql.Identifier(target)))

if __name__=='__main__':unittest.main(verbosity=2)
