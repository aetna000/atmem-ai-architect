"""Pure versioned application declaration, shared by engine and delivered runtime."""
import base64
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import uuid
from urllib.parse import urlsplit
if __package__:
    from .workflow_payload import PayloadContract,encoded
    from .workflow_contract import bind_payload_contract,bind_application_contract
else:
    from workflow_payload import PayloadContract,encoded
    from workflow_contract import bind_payload_contract,bind_application_contract


def identifier(value):
    if type(value)is not str or str(uuid.UUID(value))!=value:raise ValueError('Use a canonical account UUID')
    return value


def owned_origin(value):
    try:
        parts = urlsplit(value)
        port = parts.port
    except (TypeError, ValueError): raise ValueError('Use the exact owned application origin') from None
    if (type(value) is not str or not parts.hostname or parts.username or parts.password or
        parts.query or parts.fragment or parts.path or
        (port is not None and not 1 <= port <= 65535) or
        any(ord(c) < 33 or ord(c) > 126 for c in value) or
        (parts.scheme != 'https' and not (parts.scheme == 'http' and parts.hostname in {'localhost','127.0.0.1','::1'}))):
        raise ValueError('Use the exact HTTPS origin or explicit loopback test origin')
    return value


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
