"""Owned application assembly; imports neither API/JWT nor cloud SDK at startup.

Profiles are nonsecret reviewed artifacts. They do not select Python modules,
credential paths, migrations or deployment actions. Domain stages remain trusted
source supplied by the bootstrap, never executable strings from client data.
"""
import base64
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from workflow_payload import PayloadContract,encoded
from workflow_contract import bind_payload_contract,bind_application_contract
from workflow_configuration import owned_origin,native_database,native_identity_realm
from durable_workflow import identifier

IDENTITY_KEYS={
 'aws':('REGION','POOL_ID','CLIENT_ID','AUTH_ORIGIN','AUTH_SCOPE'),
 'azure':('TENANT_ID','API_CLIENT_ID','SPA_CLIENT_ID'),
 'gcp':('PROJECT_NUMBER','REGION','SERVICE_NAME'),
 'ibm':('APPID_TENANT_ID','APPID_CLIENT_ID','APPID_ISSUER','AUTH_SCOPE')}


@dataclass(frozen=True,init=False)
class ApplicationProfile:
    _encoded:bytes

    def __init__(self,value):
        raw=encoded(value);data=json.loads(raw)
        keys={'format','provider','componentId','environment','accountId','publicOrigin','operationKind','identitySettings','payloadContract','destinationContract'}
        if type(data)is not dict or set(data)!=keys or data['format']!='approval-application-v1':raise ValueError('Use the exact versioned application profile')
        if type(data['provider'])is not str or data['provider']not in IDENTITY_KEYS:raise ValueError('Use the selected application provider')
        if type(data['componentId'])is not str or not 1<=len(data['componentId'].encode('utf-8'))<=512 or any(ord(c)<32 for c in data['componentId']):raise ValueError('Use the complete bounded component identity')
        if type(data['environment'])is not str or data['environment']not in {'staging','production','qualification'}:raise ValueError('Use the reviewed deployment environment')
        identifier(data['accountId']);owned_origin(data['publicOrigin'])
        if type(data['operationKind'])is not str or data['operationKind']not in {'document','draft','account_change'}:raise ValueError('Use an explicit owned operation policy')
        identity=data['identitySettings']
        if type(identity)is not dict or set(identity)!=set(IDENTITY_KEYS[data['provider']])or any(type(v)is not str or not 1<=len(v.encode('utf-8'))<=2000 for v in identity.values()):raise ValueError('Use the complete nonsecret native identity settings')
        if type(data['destinationContract'])is not dict or 'applicationContractSha256'in data['destinationContract']:raise ValueError('Use the reviewed base destination; application binding is generated')
        bind_payload_contract(data['destinationContract'],PayloadContract(data['payloadContract']))
        object.__setattr__(self,'_encoded',raw)

    @property
    def data(self):return json.loads(self._encoded)
    @property
    def payload(self):return PayloadContract(self.data['payloadContract'])
    @property
    def sha256(self):return hashlib.sha256(self._encoded).hexdigest()
    @property
    def destination(self):return bind_application_contract(bind_payload_contract(self.data['destinationContract'],self.payload),self.sha256)
    @property
    def binding_sha256(self):
        value={key:self.data[key]for key in ['provider','componentId','environment','accountId']}
        return hashlib.sha256(encoded(value)).hexdigest()
    @property
    def namespace(self):
        # Explicit native alias, not truncation of the saved component identity.
        # 88-bit digest encoding fits the existing task/notification constraints.
        return 'w'+base64.b32encode(bytes.fromhex(self.binding_sha256)[:11]).decode().lower().rstrip('=')


def load_profile(path):
    if not isinstance(path,(str,Path))or not Path(path).is_absolute():raise ValueError('Use an owned absolute application profile path')
    with Path(path).open('rb')as stream:raw=stream.read(64001)
    if len(raw)>64000:raise ValueError('Application profile exceeds its byte boundary')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate application profile field')
            result[key]=value
        return result
    return ApplicationProfile(json.loads(raw.decode('utf-8'),object_pairs_hook=unique))


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


def create_native_api(profile,environment,*,connection=None,jwks=None):
    from workflow_identity import native_staff_identity
    from workflow_worker import producer_store
    from workflow_http import create_app
    env=checked_environment(profile,environment);data=profile.data;provider=data['provider']
    identity=native_staff_identity(provider,data['identitySettings'],jwks=jwks)
    dsn=connection if connection is not None else native_database(provider,env,'api')
    store=producer_store(dsn,destination_contract=profile.destination,namespace=profile.namespace,payload_contract=profile.payload,operation_kind=data['operationKind'])
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


def create_native_worker(profile,environment,processor,deliver,*,connection=None,idempotent_destination=False):
    from workflow_worker import WorkflowRuntime
    env=checked_environment(profile,environment);data=profile.data
    if not callable(processor)or not callable(deliver):raise ValueError('Supply trusted application stages')
    dsn=connection if connection is not None else native_database(data['provider'],env,'worker')
    return WorkflowRuntime(dsn,_OwnedStage(processor,data['accountId'],data['operationKind']),_OwnedStage(deliver,data['accountId'],data['operationKind']),
        destination_contract=profile.destination,payload_contract=profile.payload,operation_kind=data['operationKind'],namespace=profile.namespace,idempotent_destination=idempotent_destination)
