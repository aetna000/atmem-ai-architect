"""Operator-only native SQL identity bootstrap; never an application endpoint.

Create owned logins, preserve unrelated existing roles, and never implicitly rotate
an existing password. Google IAM users must first be created by this package's
native Cloud SQL user resource. Azure mappings use authoritative object/tenant IDs,
not display-name guesses. Execute only during an authorized destination bootstrap.
"""
import json
import re
import uuid
from psycopg import sql
from psycopg.rows import tuple_row

def canonical_uuid(value):
    if not isinstance(value,str)or str(uuid.UUID(value))!=value:raise ValueError('Use a canonical owned UUID')
    return value

def role_marker(provider,deployment_id,purpose,binding):
    return'atmem-owned-runtime-v1:'+json.dumps({'provider':provider,'deployment':deployment_id,'purpose':purpose,'principal':binding['principal']},sort_keys=True,separators=(',',':'))

def azure_principal(conn,name):
    # Named output aliases avoid relying on case folding of Microsoft's documented
    # camel-case output labels, while preserving its exact six-column contract.
    with conn.cursor(row_factory=tuple_row)as cursor:
        return cursor.execute('SELECT role_name::text,principal_type,object_id,tenant_id,mfa,admin FROM pg_catalog.pgaadauth_list_principals(false) AS mapped(role_name,principal_type,object_id,tenant_id,mfa,admin) WHERE role_name=%s',(name,)).fetchone()

def bootstrap_runtime_roles(conn,*,provider,deployment_id,bindings,passwords=None,tenant_id=None):
    canonical_uuid(deployment_id)
    if provider not in {'aws','azure','gcp','ibm'}or not isinstance(bindings,dict)or set(bindings)!={'api','worker'}:raise ValueError('Use the complete owned native role bindings')
    if provider=='azure':
        canonical_uuid(tenant_id)
        if conn.info.dbname!='postgres':raise ValueError('Azure principal mapping must run on the native postgres database before application schema bootstrap')
    if provider=='ibm'and not callable(passwords):raise ValueError('Use the separate owned secret-store password reader')
    names=[]
    for purpose,binding in bindings.items():
        fields={'name','principal','created_by_package'}if provider=='gcp'else{'name','principal'}
        if not isinstance(binding,dict)or set(binding)!=fields or not isinstance(binding['name'],str)or not re.fullmatch(r'[A-Za-z0-9_.@-]{1,63}',binding['name']):raise ValueError('Invalid native SQL role binding')
        principal=binding['principal']
        if provider in {'azure','ibm'}:canonical_uuid(principal)
        elif provider=='aws':
            if not isinstance(principal,str)or not re.fullmatch(r'arn:aws:iam::[0-9]{12}:role/[A-Za-z0-9+=,.@_/-]{1,512}',principal):raise ValueError('Use the exact owned workload role ARN')
        else:
            if(binding['created_by_package']is not True or not isinstance(principal,str)or not re.fullmatch(r'[a-z][a-z0-9-]{4,29}@[a-z][a-z0-9-]{4,28}[a-z0-9]\.iam\.gserviceaccount\.com',principal)or binding['name']!=principal.removesuffix('.gserviceaccount.com')):raise ValueError('Only the package-created service account IAM user may be admitted here')
        names.append(binding['name'])
    if len(set(names))!=2:raise ValueError('API and worker logins must be separate')
    # Serialize bootstrap for one deployment, including retries after a partial
    # operator run. This lock does not confer ownership over an unrelated role.
    conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('atmem-native-role-bootstrap:'+deployment_id,))
    result={}
    for purpose,binding in bindings.items():
        name=binding['name'];identifier=sql.Identifier(name);marker=role_marker(provider,deployment_id,purpose,binding)
        with conn.cursor(row_factory=tuple_row)as cursor:
            existing=cursor.execute("SELECT r.oid,shobj_description(r.oid,'pg_authid'),r.rolsuper,r.rolcreatedb,r.rolcreaterole,r.rolreplication,r.rolbypassrls,r.rolcanlogin FROM pg_roles r WHERE rolname=%s",(name,)).fetchone()
        if existing:
            if any(existing[2:7])or not existing[7]:raise ValueError('Native runtime role must be a nonadministrative login')
            if existing[1]!=marker:
                if provider!='gcp'or existing[1]is not None:raise ValueError('Refusing to adopt or repoint an unrelated existing database role')
                with conn.cursor(row_factory=tuple_row)as cursor:
                    parents=cursor.execute('SELECT p.rolname FROM pg_auth_members m JOIN pg_roles p ON p.oid=m.roleid WHERE m.member=%s',(existing[0],)).fetchall()
                if not parents or not {row[0]for row in parents}<={'cloudsqliamuser','cloudsqliamserviceaccount'}:raise ValueError('The native service-account authentication marker is missing or broadened')
                # Complete ownership/effective-grant admission still runs in the
                # application database before runtime grants are installed.
                conn.execute(sql.SQL('COMMENT ON ROLE {} IS {}').format(identifier,sql.Literal(marker)))
        elif provider=='gcp':raise ValueError('Apply the owned Cloud SQL IAM user resource before SQL bootstrap')
        elif provider=='azure':
            conn.execute("SELECT pg_catalog.pgaadauth_create_principal_with_oid(%s,%s,'service',false,false)",(name,binding['principal']))
            conn.execute(sql.SQL('COMMENT ON ROLE {} IS {}').format(identifier,sql.Literal(marker)))
        else:
            password=sql.SQL('NULL')
            if provider=='ibm':
                secret=passwords(purpose,binding['principal'])
                if not isinstance(secret,str)or not 24<=len(secret.encode('utf-8'))<=500 or '\0'in secret:raise ValueError('Use a strong operator-managed SQL credential')
                # Send a client-side SCRAM verifier rather than plaintext in SQL
                # DDL/statement logs. The verifier remains sensitive DBA metadata.
                verifier=conn.pgconn.encrypt_password(secret.encode(),name.encode(),algorithm=b'scram-sha-256').decode('ascii');password=sql.Literal(verifier)
            conn.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}').format(identifier,password))
            if provider=='aws':
                with conn.cursor(row_factory=tuple_row)as cursor:available=cursor.execute("SELECT 1 FROM pg_roles WHERE rolname='rds_iam'").fetchone()
                if not available:raise ValueError('The native RDS IAM authentication role is missing')
                conn.execute(sql.SQL('GRANT rds_iam TO {}').format(identifier))
            conn.execute(sql.SQL('COMMENT ON ROLE {} IS {}').format(identifier,sql.Literal(marker)))
        if provider=='azure':
            mapped=azure_principal(conn,name)
            if not mapped or len(mapped)!=6 or mapped[0]!=name or mapped[1]!='service'or mapped[2]!=binding['principal']or mapped[3]!=tenant_id or mapped[4]!=0 or mapped[5]!=0:raise ValueError('Native Entra role mapping differs from the owned service principal/tenant or has administrator/MFA flags')
        # Re-read after native creation as well as on repeat operator runs. A
        # provider function must not silently install an administrative login.
        with conn.cursor(row_factory=tuple_row)as cursor:
            flags=cursor.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls,rolcanlogin FROM pg_roles WHERE rolname=%s',(name,)).fetchone()
            parents=cursor.execute('SELECT p.rolname FROM pg_auth_members m JOIN pg_roles p ON p.oid=m.roleid JOIN pg_roles child ON child.oid=m.member WHERE child.rolname=%s',(name,)).fetchall()
        if not flags or any(flags[:5])or not flags[5]:raise ValueError('Native runtime role must be a nonadministrative login')
        allowed={'rds_iam'}if provider=='aws'else{'cloudsqliamuser','cloudsqliamserviceaccount'}if provider=='gcp'else set()
        if not {row[0]for row in parents}<=allowed:raise ValueError('Native runtime role has an unreviewed inherited authority')
        if provider=='aws':
            # Repair only the authentication membership of an already owned
            # role. Never adopt unrelated logins or remove another grant.
            conn.execute(sql.SQL('GRANT rds_iam TO {}').format(identifier))
        if provider=='gcp'and not parents:raise ValueError('Native Cloud SQL IAM authentication membership is missing')
        conn.execute(sql.SQL('ALTER ROLE {} CONNECTION LIMIT {}').format(identifier,sql.Literal(48 if purpose=='api'else 24)))
        result[purpose]=name
    return result
