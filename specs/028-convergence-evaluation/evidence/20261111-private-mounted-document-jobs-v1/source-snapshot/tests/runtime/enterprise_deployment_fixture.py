"""Guarded fresh local bootstrap fixture, never a generated application asset."""
import hashlib
import uuid
import secrets
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict,make_conninfo
from cryptography.fernet import Fernet
from durable_postgres_acceptance import fixture_dsn
from enterprise_operator import initialize
from enterprise_oauth_acceptance import TENANT,CLIENT,CLOUD

REVISION=hashlib.sha256(b'synthetic-utf8-byte-bound-decoder-v1').hexdigest()


def metadata(account,provider='gcp',origin='https://app.example'):
    return {'format':'enterprise-knowledge-v1','provider':provider,'accountId':account,'publicOrigin':origin,
        'company':{'issuer':'https://company.example/issuer','audience':'knowledge-api','jwksUri':'https://company.example/jwks','scope':'knowledge.read',
            'web':{'clientId':'existing-company-web','authorizationEndpoint':'https://company.example/authorize','tokenEndpoint':'https://company.example/token','scopes':['openid','profile','knowledge.read']}},
        'sources':{'sharepoint':{'tenantId':TENANT,'clientId':CLIENT,'driveId':'drive','host':'tenant.sharepoint.com'},
            'confluence':{'clientId':'client','cloudId':CLOUD,'host':'tenant.atlassian.net','spaces':{'ENG':'42'}}},'parserRevision':REVISION}


def fresh_database():
    root=fixture_dsn();settings=conninfo_to_dict(root);database='architect_qualification_'+uuid.uuid4().hex[:16]
    roles={name:('atmem_'+name+'_'+uuid.uuid4().hex[:12],secrets.token_urlsafe(32))for name in ['api','worker','operator']}
    with psycopg.connect(root,autocommit=True)as conn:
        for role,password in roles.values():conn.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}').format(sql.Identifier(role),sql.Literal(password)))
        conn.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(sql.Identifier(database),sql.Identifier(roles['operator'][0])))
    owner=make_conninfo(**{**settings,'dbname':database,'user':roles['operator'][0],'password':roles['operator'][1]})
    with psycopg.connect(owner)as conn:initialize(conn,roles['api'][0],roles['worker'][0])
    return {'owner':owner,'admin':root,**{name:make_conninfo(**{**settings,'dbname':database,'user':role,'password':password})for name,(role,password)in roles.items()},'key':Fernet.generate_key()}
