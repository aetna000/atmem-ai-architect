"""Operator migration/bootstrap API; never an application HTTP endpoint.

Use the separate approved migration credential. Native cloud principal mapping,
connection TLS and account authorization are provider-specific setup steps.
"""
import hashlib
from pathlib import Path
import re
import psycopg
from psycopg import sql
from psycopg.rows import tuple_row
import procrastinate
from procrastinate.schema import SchemaManager

QUEUE_TABLES=['procrastinate_jobs','procrastinate_events','procrastinate_workers','procrastinate_periodic_defers']

def initialize_database(conn):
    if procrastinate.__version__!='3.10.0':raise ValueError('Use the reviewed queue dependency before migration')
    # CREATE, not CREATE IF NOT EXISTS: do not adopt an unrelated existing schema
    # or run a fresh schema over a production version that needs real migrations.
    body=(Path(__file__).parent/'workflow_schema.sql').read_bytes()
    conn.execute('CREATE SCHEMA workflow')
    conn.execute('SET LOCAL search_path=workflow,pg_catalog')
    conn.execute(SchemaManager.get_schema())
    conn.execute(body.decode('utf-8'))
    conn.execute('INSERT INTO workflow.schema_version(version,source_sha256,queue_version) VALUES(1,%s,%s)',(hashlib.sha256(body).hexdigest(),procrastinate.__version__))
    conn.execute('REVOKE ALL ON SCHEMA workflow FROM PUBLIC')
    conn.execute('REVOKE ALL ON ALL TABLES IN SCHEMA workflow FROM PUBLIC')
    conn.execute('REVOKE ALL ON ALL SEQUENCES IN SCHEMA workflow FROM PUBLIC')
    conn.execute('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA workflow FROM PUBLIC')

def grant_runtime_roles(conn,api_role,worker_role):
    expected=hashlib.sha256((Path(__file__).parent/'workflow_schema.sql').read_bytes()).hexdigest()
    with conn.cursor(row_factory=tuple_row)as cursor:
        row=cursor.execute('SELECT version,source_sha256,queue_version FROM workflow.schema_version').fetchone()
    if row!=(1,expected,'3.10.0'):raise ValueError('Use the owned exact schema version; review migrations before changing grants')
    if api_role==worker_role:raise ValueError('Application and worker database identities must be separate')
    for role in [api_role,worker_role]:
        if not isinstance(role,str)or not re.fullmatch(r'[A-Za-z0-9_.@-]{1,63}',role):raise ValueError('Use the reviewed existing native database principal name')
        with conn.cursor(row_factory=tuple_row)as cursor:
            flags=cursor.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=%s',(role,)).fetchone()
        if not flags or any(flags):raise ValueError('A runtime identity must be an existing nonadministrative database role')
        with conn.cursor(row_factory=tuple_row)as cursor:
            elevated=cursor.execute("WITH RECURSIVE parents AS (SELECT oid,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=%s UNION SELECT r.oid,r.rolsuper,r.rolcreatedb,r.rolcreaterole,r.rolreplication,r.rolbypassrls FROM pg_roles r JOIN pg_auth_members m ON m.roleid=r.oid JOIN parents p ON p.oid=m.member) SELECT EXISTS(SELECT 1 FROM parents WHERE rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls) OR has_database_privilege(%s,current_database(),'CREATE')",(role,role)).fetchone()[0]
        if elevated:raise ValueError('Do not use an inherited administrator or database owner as a runtime identity')
        with conn.cursor(row_factory=tuple_row)as cursor:
            inherited_or_owned=cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member WHERE r.rolname=%s) OR EXISTS(SELECT 1 FROM pg_namespace n JOIN pg_roles r ON r.oid=n.nspowner WHERE r.rolname=%s) OR EXISTS(SELECT 1 FROM pg_class c JOIN pg_roles r ON r.oid=c.relowner WHERE r.rolname=%s) OR EXISTS(SELECT 1 FROM pg_proc p JOIN pg_roles r ON r.oid=p.proowner WHERE r.rolname=%s)",(role,role,role,role)).fetchone()[0]
        # Provider-native login-role mappings need their own reviewed grant path;
        # this portable bootstrap accepts dedicated roles without inherited
        # privileges or object ownership that REVOKE cannot remove.
        if inherited_or_owned:raise ValueError('Use a dedicated runtime role without unreviewed memberships or object ownership')
        name=sql.Identifier(role)
        conn.execute(sql.SQL('REVOKE ALL ON SCHEMA workflow FROM {}').format(name))
        conn.execute(sql.SQL('REVOKE ALL ON ALL TABLES IN SCHEMA workflow FROM {}').format(name))
        # PostgreSQL 17's table REVOKE also removes corresponding column grants;
        # keep a native regression for reused role grants rather than assuming it.
        # https://www.postgresql.org/docs/17/sql-revoke.html
        conn.execute(sql.SQL('REVOKE ALL ON ALL SEQUENCES IN SCHEMA workflow FROM {}').format(name))
        conn.execute(sql.SQL('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA workflow FROM {}').format(name))
        conn.execute(sql.SQL('GRANT USAGE ON SCHEMA workflow TO {}').format(name))
        conn.execute(sql.SQL('GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA workflow TO {}').format(name))
        conn.execute(sql.SQL('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA workflow TO {}').format(name))
        conn.execute(sql.SQL('GRANT SELECT ON workflow.schema_version,workflow.accounts,workflow.memberships,workflow.operations,workflow.events,workflow.results_history TO {}').format(name))
        # PostgreSQL requires UPDATE on at least one column for SELECT FOR SHARE.
        # Only this inert locking column is writable; roles/active/identity are not.
        # https://www.postgresql.org/docs/17/ddl-priv.html
        conn.execute(sql.SQL('GRANT UPDATE(authorization_lock) ON workflow.memberships TO {}').format(name))
        conn.execute(sql.SQL('GRANT INSERT,UPDATE ON workflow.operations TO {}').format(name))
        conn.execute(sql.SQL('GRANT INSERT ON workflow.events TO {}').format(name))
        conn.execute(sql.SQL('GRANT INSERT ON workflow.results_history TO {}').format(name))
    # API notifications are append-only; it cannot finish/prune/rewrite worker
    # jobs, alter memberships, delete audit history or migrate the schema.
    api=sql.Identifier(api_role);worker=sql.Identifier(worker_role)
    conn.execute(sql.SQL('GRANT SELECT,INSERT ON workflow.procrastinate_jobs,workflow.procrastinate_events TO {}').format(api))
    for table in QUEUE_TABLES:
        conn.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE ON workflow.{} TO {}').format(sql.Identifier(table),worker))
