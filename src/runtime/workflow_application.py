"""Owned application assembly; imports neither API/JWT nor cloud SDK at startup.

Profiles are nonsecret reviewed artifacts. They do not select Python modules,
credential paths, migrations or deployment actions. Domain stages remain trusted
source supplied by the bootstrap, never executable strings from client data.
"""
import hashlib
from workflow_payload import encoded
from workflow_configuration import native_database,native_identity_realm
from workflow_profile import ApplicationProfile,load_profile,IDENTITY_KEYS

def checked_environment(profile,environment):
    if type(profile)is not ApplicationProfile:raise ValueError('Use an immutable owned application profile')
    copied=dict(environment);data=profile.data
    for key,expected in [('PROVIDER',data['provider']),('ACCOUNT_ID',data['accountId']),('ENVIRONMENT',data['environment']),('WORKFLOW_NAMESPACE',profile.namespace),('PUBLIC_ORIGIN',data['publicOrigin'])]:
        if key in copied and copied[key]!=expected:raise ValueError('Runtime configuration differs from the owned application profile')
    for key,expected in data['identitySettings'].items():
        if key in copied and copied[key]!=expected:raise ValueError('Native identity differs from the owned application profile')
    return copied


def membership_key(profile,subject):
    """Derived enrollment key from the complete verified subject and native realm.

    This is not an authentication function. Enrollment is an operator action;
    the API calls it only after cryptographic native verification. No subject
    characters are clipped; the native IdP remains the authoritative identity.
    """
    if type(profile)is not ApplicationProfile or type(subject)is not str or not 1<=len(subject.encode('utf-8'))<=16384 or any(ord(c)<32 for c in subject):raise ValueError('Use the complete verified native subject')
    data=profile.data
    return 'native-'+hashlib.sha256(encoded({'provider':data['provider'],'issuer':native_identity_realm(data['provider'],data['identitySettings']),'subject':subject})).hexdigest()


def create_native_api(profile,environment,*,connection=None,jwks=None,review_policy=None):
    from workflow_identity import native_staff_identity
    from workflow_worker import producer_store
    from workflow_http import create_app
    env=checked_environment(profile,environment);data=profile.data;provider=data['provider']
    identity=native_staff_identity(provider,data['identitySettings'],jwks=jwks)
    dsn=connection if connection is not None else native_database(provider,env,'api')
    store=producer_store(dsn,destination_contract=profile.destination,namespace=profile.namespace,payload_contract=profile.payload,operation_kind=data['operationKind'],review_policy=review_policy)
    def verify(token):return membership_key(profile,identity.verify(token))
    return create_app(verify,store,account_id=data['accountId'],public_origin=data['publicOrigin'],operation_kind=data['operationKind'],token_header=identity.token_header)


class _OwnedStage:
    def __init__(self,stage,account,kind):self.stage=stage;self.account=account;self.kind=kind
    def __getattr__(self,name):return getattr(self.stage,name)
    def __call__(self,row,*args,**kwargs):
        from workflow_errors import InvalidDispatch
        if str(row.get('account_id'))!=self.account:raise InvalidDispatch('Work belongs to a different application account; no stage was invoked')
        if row.get('kind')!=self.kind:raise InvalidDispatch('Work has a different operation policy; no stage was invoked')
        return self.stage(row,*args,**kwargs)


def create_native_worker(profile,environment,processor,deliver,*,connection=None,idempotent_destination=False,review_policy=None):
    from workflow_worker import WorkflowRuntime
    env=checked_environment(profile,environment);data=profile.data
    if not callable(processor)or not callable(deliver):raise ValueError('Supply trusted application stages')
    dsn=connection if connection is not None else native_database(data['provider'],env,'worker')
    return WorkflowRuntime(dsn,_OwnedStage(processor,data['accountId'],data['operationKind']),_OwnedStage(deliver,data['accountId'],data['operationKind']),
        destination_contract=profile.destination,payload_contract=profile.payload,operation_kind=data['operationKind'],namespace=profile.namespace,idempotent_destination=idempotent_destination,review_policy=review_policy)
