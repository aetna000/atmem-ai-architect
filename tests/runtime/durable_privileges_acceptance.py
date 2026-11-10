"""Use distinct nonadministrative DB logins, not owner-powered grant mocks."""
from pathlib import Path
import secrets
import sys
import unittest
import uuid
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict,make_conninfo

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(Path(__file__).resolve().parent)]
from durable_postgres_acceptance import fixture_dsn
from durable_fixture_tasks import fixture_tasks,FIXTURE_CONTRACT
from durable_workflow import WorkflowStore,Principal
from workflow_database import grant_runtime_roles

def create_runtime_roles():
    owner_dsn=fixture_dsn();prefix='qa_'+uuid.uuid4().hex[:12];api_role=prefix+'_api';worker_role=prefix+'_worker';api_password=secrets.token_urlsafe(32);worker_password=secrets.token_urlsafe(32)
    with psycopg.connect(owner_dsn)as conn:
        for name,password in [(api_role,api_password),(worker_role,worker_password)]:conn.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS').format(sql.Identifier(name),sql.Literal(password)))
        grant_runtime_roles(conn,api_role,worker_role)
    api_dsn=make_conninfo(**{**conninfo_to_dict(owner_dsn),'user':api_role,'password':api_password});worker_dsn=make_conninfo(**{**conninfo_to_dict(owner_dsn),'user':worker_role,'password':worker_password})
    return owner_dsn,api_role,worker_role,api_dsn,worker_dsn

class RuntimeDatabasePrivilegesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.owner_dsn,cls.api_role,cls.worker_role,cls.api_dsn,cls.worker_dsn=create_runtime_roles()
    def setUp(self):
        self.account=str(uuid.uuid4());self.user=Principal(self.account,'privilege-staff');self.reviewer=Principal(self.account,'privilege-reviewer');namespace=uuid.uuid4().hex
        _,extract,dispatch=fixture_tasks(self.api_dsn,namespace);self.api=WorkflowStore(self.api_dsn,extract,dispatch,destination_contract=FIXTURE_CONTRACT)
        _,worker_extract,worker_dispatch=fixture_tasks(self.worker_dsn,namespace);self.worker=WorkflowStore(self.worker_dsn,worker_extract,worker_dispatch,destination_contract=FIXTURE_CONTRACT)
        with psycopg.connect(self.owner_dsn)as conn:
            conn.execute('INSERT INTO workflow.accounts(id) VALUES(%s)',(self.account,))
            for actor,roles in [(self.user,['user']),(self.reviewer,['reviewer'])]:conn.execute('INSERT INTO workflow.memberships(account_id,subject,roles) VALUES(%s,%s,%s)',(actor.account_id,actor.subject,roles))
    def test_api_submission_approval_and_worker_completion_use_only_their_granted_roles(self):
        operation=self.api.submit(self.user,'document','privilege-document',{'sha256':'a'*64});lease=self.worker.claim_extract(operation);self.worker.record_result(operation,str(lease['lease_token']),{'supplier':'Privilege fixture'});self.api.approve(self.reviewer,operation,1);send=self.worker.claim_dispatch(operation);self.worker.record_sent(operation,str(send['lease_token']),{'externalId':'privileged-synthetic-001'});self.assertEqual(self.api.get(self.user,operation)['state'],'sent')
    def test_runtime_roles_cannot_edit_membership_or_delete_audit_or_own_the_schema(self):
        for dsn in [self.api_dsn,self.worker_dsn]:
            for statement,args in [("UPDATE workflow.memberships SET roles=ARRAY['owner'] WHERE account_id=%s",(self.account,)),('UPDATE workflow.memberships SET active=false WHERE account_id=%s',(self.account,)),('DELETE FROM workflow.events WHERE account_id=%s',(self.account,)),('CREATE TABLE workflow.forbidden_ddl(id integer)',())]:
                with self.subTest(statement=statement,user=conninfo_to_dict(dsn)['user']):
                    with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                        with psycopg.connect(dsn)as conn:conn.execute(statement,args)
    def test_api_cannot_prune_worker_jobs_or_escalate_to_the_migration_role(self):
        for statement in ['DELETE FROM workflow.procrastinate_jobs',"UPDATE workflow.procrastinate_jobs SET status='succeeded'","SET ROLE qualification_admin"]:
            with self.subTest(statement=statement):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    with psycopg.connect(self.api_dsn)as conn:conn.execute(statement)
    def test_runtime_roles_cannot_change_or_erase_historical_result_snapshots(self):
        for dsn in [self.api_dsn,self.worker_dsn]:
            for statement in ["UPDATE workflow.results_history SET result='{}'::jsonb",'DELETE FROM workflow.results_history']:
                with self.subTest(statement=statement):
                    with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                        with psycopg.connect(dsn)as conn:conn.execute(statement)
    def test_granting_administrator_credentials_to_an_application_is_rejected(self):
        with self.assertRaises(ValueError):
            with psycopg.connect(self.owner_dsn)as conn:grant_runtime_roles(conn,'qualification_admin',self.worker_role)
    def test_reusing_a_role_removes_preexisting_column_level_membership_permissions(self):
        with psycopg.connect(self.owner_dsn)as conn:
            conn.execute(sql.SQL('GRANT UPDATE(roles,active) ON workflow.memberships TO {}').format(sql.Identifier(self.api_role)))
            grant_runtime_roles(conn,self.api_role,self.worker_role)
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            with psycopg.connect(self.api_dsn)as conn:conn.execute("UPDATE workflow.memberships SET roles=ARRAY['owner'] WHERE account_id=%s",(self.account,))
    def test_unreviewed_inherited_roles_and_schema_owners_are_rejected(self):
        name='qa_'+uuid.uuid4().hex[:12];parent=name+'_parent';child=name+'_child'
        with psycopg.connect(self.owner_dsn)as conn:
            for role in [parent,child]:conn.execute(sql.SQL('CREATE ROLE {} NOLOGIN').format(sql.Identifier(role)))
            conn.execute(sql.SQL('GRANT {} TO {}').format(sql.Identifier(parent),sql.Identifier(child)))
        with self.assertRaises(ValueError):
            with psycopg.connect(self.owner_dsn)as conn:grant_runtime_roles(conn,child,self.worker_role)
        with psycopg.connect(self.owner_dsn)as conn:
            conn.execute(sql.SQL('REVOKE {} FROM {}').format(sql.Identifier(parent),sql.Identifier(child)))
            conn.execute(sql.SQL('CREATE SCHEMA {} AUTHORIZATION {}').format(sql.Identifier(name),sql.Identifier(child)))
        with self.assertRaises(ValueError):
            with psycopg.connect(self.owner_dsn)as conn:grant_runtime_roles(conn,child,self.worker_role)

if __name__=='__main__':unittest.main(verbosity=2)
