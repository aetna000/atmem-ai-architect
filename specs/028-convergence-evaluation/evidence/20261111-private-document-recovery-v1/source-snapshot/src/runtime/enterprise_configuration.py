"""Owned private deployment metadata and native SQL identity dispatch.

No connection, cloud request, user enrollment or schema mutation occurs on import.
Metadata is packaged by the compiler/operator, never read from a chat request.
"""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from enterprise_identity import CompanyIdentity, trusted_https
from enterprise_sources import GraphSharePoint, ConfluenceCloud
from public_faq import object_pairs


def deployment(value):
    if (not isinstance(value, dict) or set(value) != {'format', 'provider', 'accountId', 'publicOrigin', 'company', 'sources', 'parserRevision'}
        or value['format'] != 'enterprise-knowledge-v1' or value['provider'] not in {'aws', 'azure', 'gcp', 'ibm'}
        or not isinstance(value['accountId'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value['accountId'])
        or not isinstance(value['parserRevision'], str) or not re.fullmatch(r'[0-9a-f]{64}', value['parserRevision'])):
        raise ValueError('Invalid owned private deployment metadata')
    origin = trusted_https(value['publicOrigin'])
    if urlsplit(origin).path or origin.endswith('/'):
        raise ValueError('Use the canonical owned HTTPS origin')
    company = value['company']
    if not isinstance(company, dict) or set(company) != {'issuer', 'audience', 'jwksUri', 'scope', 'web'}:
        raise ValueError('Supply the existing company API and public OIDC registration')
    identity = CompanyIdentity(value['accountId'], company['issuer'], company['audience'], company['jwksUri'], company['scope'])
    from enterprise_web import company_configuration
    company_configuration(identity, company['web'])
    sources = value['sources']
    if not isinstance(sources, dict) or set(sources) != {'sharepoint', 'confluence'}:
        raise ValueError('Supply the existing SharePoint and Confluence registrations')
    graph, confluence = sources['sharepoint'], sources['confluence']
    if not isinstance(graph, dict) or set(graph) != {'tenantId', 'clientId', 'driveId', 'host'}:
        raise ValueError('Invalid owned Graph registration')
    if any(not isinstance(graph[key], str) or not re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', graph[key]) for key in ['tenantId', 'clientId']):
        raise ValueError('Use the owned Graph tenant and confidential client IDs')
    if (not isinstance(confluence, dict) or set(confluence) != {'clientId', 'cloudId', 'host', 'spaces'}
        or not isinstance(confluence['clientId'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,200}', confluence['clientId'])):
        raise ValueError('Invalid owned Confluence registration')
    # Constructor validation is local only: no delegated access is used here.
    GraphSharePoint(graph['driveId'], graph['host'], None)
    ConfluenceCloud(confluence['cloudId'], confluence['host'], confluence['spaces'], None)
    return json.loads(json.dumps(value, allow_nan=False))


def read_deployment(path=None):
    path = Path(path) if path is not None else Path(__file__).with_name('enterprise-deployment.json')
    with path.open('rb') as stream: raw = stream.read(32769)
    if len(raw) > 32768:
        raise ValueError('Owned private deployment metadata exceeds its boundary')
    return deployment(json.loads(raw, object_pairs_hook=object_pairs))


def session_domain(metadata):
    return hashlib.sha256(json.dumps({'account':metadata['accountId'],'origin':metadata['publicOrigin'],
        'company':metadata['company'],'sources':metadata['sources'],'provider':metadata['provider']},sort_keys=True,separators=(',',':')).encode()).hexdigest()


def native_database(provider, environment, role, secrets):
    from workflow_connection import aws_database, azure_database, gcp_database, ibm_database
    if role not in {'api', 'worker', 'migration'}:
        raise ValueError('Use the owned native database role')
    env = environment
    common = {'database': env['DATABASE_NAME'], 'role': role}
    if provider == 'gcp':
        transport = env.get('DATABASE_TRANSPORT', 'cloudsql-socket')
        if transport not in {'cloudsql-socket', 'cloudsql-private-proxy'}:
            raise ValueError('Use the owned Cloud SQL transport')
        return gcp_database(**common, connection_name=env['DATABASE_CONNECTION_NAME'],
            service_account_email=env['DATABASE_SERVICE_ACCOUNT'], private_proxy=transport == 'cloudsql-private-proxy')
    common.update(host=env['DATABASE_HOST'], user=env['DATABASE_USER'], ca_file=secrets.env['DATABASE_CA_FILE'])
    if provider == 'aws': return aws_database(**common, region=env['REGION'])
    if provider == 'azure': return azure_database(**common, managed_identity_client_id=env['WORKLOAD_IDENTITY_CLIENT_ID'])
    if provider == 'ibm': return ibm_database(**common, port=int(env['DATABASE_PORT']), password=secrets.reader('database_password'))
    raise ValueError('Unsupported owned database provider')


def validate_runtime(auth, role, account_id):
    if role not in {'api', 'worker'}: raise ValueError('Use a runtime database identity')
    schemas = {'enterprise_auth': 'enterprise_auth_schema.sql', 'enterprise_queries': 'enterprise_queries_schema.sql',
               'enterprise_audit': 'enterprise_audit_schema.sql'}
    if role == 'worker':
        schemas['enterprise_extractions'] = 'enterprise_extraction_schema.sql'
        schemas['enterprise_document_jobs'] = 'enterprise_document_jobs_schema.sql'
    with auth.transaction() as cursor:
        row = cursor.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone()
        if not row or any(row.values()): raise ValueError('Private runtime must use its nonadministrative database identity')
        for schema, filename in schemas.items():
            if cursor.execute('SELECT has_schema_privilege(current_user,%s,\'CREATE\') AS allowed', (schema,)).fetchone()['allowed']:
                raise ValueError('Runtime must not own private application schemas')
            # Identifiers come only from the fixed dictionary above.
            current = cursor.execute('SELECT version,source_sha256 FROM ' + schema + '.schema_version').fetchone()
            expected = hashlib.sha256(Path(__file__).with_name(filename).read_bytes()).hexdigest()
            if current != {'version': 1, 'source_sha256': expected}:
                raise ValueError('Private runtime schema differs; run the reviewed operator lifecycle')
        queue = cursor.execute('SELECT queue_version FROM enterprise_queries.schema_version').fetchone()
        if queue['queue_version'] != '3.10.0': raise ValueError('Private runtime queue version differs')
        for table in ['enterprise_auth.memberships', 'enterprise_auth.source_mappings', 'enterprise_auth.company_bindings', 'enterprise_auth.schema_version']:
            if cursor.execute('SELECT has_table_privilege(current_user,%s,\'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER,REFERENCES\') AS allowed', (table,)).fetchone()['allowed']:
                raise ValueError('Runtime must not inherit company authority writes')
        if cursor.execute("SELECT has_table_privilege(current_user,'enterprise_audit.events','SELECT,UPDATE,DELETE,TRUNCATE,TRIGGER,REFERENCES') AS allowed").fetchone()['allowed']:
            raise ValueError('Runtime must use append-only audit authority')
        if cursor.execute("SELECT has_table_privilege(current_user,'enterprise_auth.administration_events','SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER,REFERENCES') AS allowed").fetchone()['allowed']:
            raise ValueError('Runtime must not inherit operator history authority')
        if role == 'api' and cursor.execute("SELECT has_table_privilege(current_user,'enterprise_queries.procrastinate_jobs','UPDATE,DELETE,TRUNCATE') AS allowed").fetchone()['allowed']:
            raise ValueError('API must not inherit worker queue mutation authority')
        forbidden = 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER,REFERENCES' if role == 'api' else 'TRUNCATE,TRIGGER,REFERENCES'
        table = cursor.execute("SELECT c.oid::bigint AS oid FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='enterprise_document_jobs'AND c.relname='jobs'AND c.relkind='r'").fetchone()
        if not table:raise ValueError('Private document cleanup schema is missing')
        # API deliberately has no schema USAGE. Resolve the object through the
        # public system catalogue instead of broadening its application grants.
        if cursor.execute("SELECT has_table_privilege(current_user,%s::oid,%s) AS allowed", (table['oid'],forbidden)).fetchone()['allowed']:
            raise ValueError('Use only the owned worker cleanup metadata authority')
        from enterprise_sources import SourceDenied
        try:auth.require_company(cursor,account_id)
        except SourceDenied:raise ValueError('Activate the owned company registration with the reviewed operator lifecycle')from None
