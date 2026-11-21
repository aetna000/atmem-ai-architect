"""Shared operator initialization for CLI and fixed native jobs, never HTTP.

Validate the whole deployment before opening a connection. Authentication and
transport belong to the caller's reviewed native credential factory; this module
neither reads credentials nor chooses endpoints from model/request input.
"""
import re
from workflow_role_bootstrap import canonical_uuid,validate_runtime_bindings,bootstrap_runtime_roles
from workflow_database import initialize_database,grant_runtime_roles
from invoice_operations import owned_scope

def validate_deployment(deployment):
    if not isinstance(deployment,dict)or set(deployment)!={'provider','deploymentId','accountId','namespace','bindings','tenantId'}:raise ValueError('Use the exact documented deployment identity')
    canonical_uuid(deployment['accountId'])
    if not isinstance(deployment['namespace'],str)or not re.fullmatch(r'[a-zA-Z0-9-]{1,20}',deployment['namespace']):raise ValueError('Use the owned workflow namespace')
    if deployment['provider']!='azure'and deployment['tenantId']is not None:raise ValueError('Only the Azure profile has a native tenant mapping')
    validate_runtime_bindings(provider=deployment['provider'],deployment_id=deployment['deploymentId'],bindings=deployment['bindings'],tenant_id=deployment['tenantId'])
    return {'account_id':deployment['accountId'],'namespace':deployment['namespace']}

def initialize_runtime(connect,deployment,*,passwords=None):
    scope=validate_deployment(deployment)
    if deployment['provider']=='ibm'and not callable(passwords):raise ValueError('Use the separate owned secret-store password reader')
    # Native identity mapping and application schema are separate committed
    # phases. A retry admits only exact ownership markers, never rotates existing
    # SQL passwords, and then completes the application phase idempotently.
    with connect('postgres'if deployment['provider']=='azure'else None)as conn:
        if conn.autocommit:raise ValueError('Use an explicit operator transaction')
        if conn.info.user in {item['name']for item in deployment['bindings'].values()}:raise PermissionError('Use the separate operator identity')
        bootstrap_runtime_roles(conn,provider=deployment['provider'],deployment_id=deployment['deploymentId'],bindings=deployment['bindings'],tenant_id=deployment['tenantId'],passwords=passwords)
    with connect(None)as conn:
        if conn.autocommit:raise ValueError('Use an explicit operator transaction')
        # Database-local and shared across deployments: serialize the check and
        # CREATE, rather than allowing competing fresh-schema initializations.
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended('atmem-workflow-schema-bootstrap-v1',0))")
        if conn.execute("SELECT to_regnamespace('workflow')").fetchone()[0]is None:initialize_database(conn)
        owned_scope(conn,**scope)
        grant_runtime_roles(conn,deployment['bindings']['api']['name'],deployment['bindings']['worker']['name'],native_provider=deployment['provider'])
        conn.execute('INSERT INTO workflow.accounts(id)VALUES(%s)ON CONFLICT DO NOTHING',(scope['account_id'],))
    return {'initialized':True,'schemaVersion':1,'nativeIdentity':'Requires destination-native authentication checks; local success alone is insufficient.'}
