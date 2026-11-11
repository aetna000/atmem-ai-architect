"""A concrete, explicit normalized external-action HTTP contract.

This is not an invented vendor API. Destination operators must verify this exact
idempotent contract or implement a reviewed native mapping. A model/visitor cannot
choose the endpoint, credentials, identity header, method or replay policy.
"""
import hashlib
import http.client
import json
import re
import ssl
from urllib.parse import urlsplit
from durable_workflow import canonical,identifier
from workflow_errors import ExternalOutcomeUnknown,DestinationNotAttempted,InvalidDispatch
from workflow_contract import normalized_contract,bind_payload_contract,bind_application_contract

class ApprovedHttpDestination:
    def __init__(self,endpoint,credential,*,destination_scope,idempotency_verified=False,tls_context=None,allowed_kinds=('document',),payload_contract=None,application_contract_sha256=None):
        try:target=urlsplit(endpoint)
        except (TypeError,ValueError):raise ValueError('Invalid operator destination')from None
        if (not isinstance(endpoint,str)or len(endpoint)>2000 or target.scheme!='https' or not target.hostname or target.username or target.password
            or target.query or target.fragment or any(ord(c)<33 for c in endpoint)):raise ValueError('Use a fixed reviewed HTTPS destination without embedded credentials, query or fragment')
        try:port=target.port or 443
        except ValueError:raise ValueError('Invalid destination port')from None
        if not 1<=port<=65535 or not callable(credential)or type(idempotency_verified)is not bool:raise ValueError('Invalid owned destination configuration')
        if not isinstance(allowed_kinds,(tuple,list,set,frozenset))or not allowed_kinds or not set(allowed_kinds)<={'document','draft','account_change'}:raise ValueError('Invalid owned operation allowlist')
        context=tls_context or ssl.create_default_context()
        if not isinstance(context,ssl.SSLContext)or context.verify_mode!=ssl.CERT_REQUIRED or not context.check_hostname:raise ValueError('TLS certificate and hostname verification are mandatory')
        self.host=target.hostname;self.port=port;self.path=target.path or'/';self.credential=credential;self.idempotency_verified=idempotency_verified;self.context=context;self.allowed_kinds=frozenset(allowed_kinds)
        self.contract=bind_payload_contract(normalized_contract(endpoint,destination_scope),payload_contract)
        if application_contract_sha256 is not None:self.contract=bind_application_contract(self.contract,application_contract_sha256)
        self.payload_contract=payload_contract
    def __call__(self,row,*,idempotency_key,payload_sha256):
        try:identifier(idempotency_key)
        except (ValueError,TypeError):raise InvalidDispatch('Invalid approved operation identity')from None
        if (str(row.get('id'))!=idempotency_key or row.get('state')!='dispatching' or not row.get('approved_by')or row.get('approved_hash')!=payload_sha256
            or row.get('kind')not in self.allowed_kinds or not isinstance(payload_sha256,str)or not re.fullmatch(r'[0-9a-f]{64}',payload_sha256)):raise InvalidDispatch('A current allowed approved dispatch snapshot is required')
        if row.get('destination_contract')!=self.contract:raise InvalidDispatch('Approved integration identity no longer matches this destination')
        if self.payload_contract is not None:
            try:
                if self.contract['payloadContractSha256']!=self.payload_contract.sha256:raise ValueError()
                self.payload_contract.validate('source',row['source_ref']);self.payload_contract.validate('result',row['result'])
            except (KeyError,ValueError):raise InvalidDispatch('Approved application contract no longer matches this destination')from None
        snapshot={'kind':row['kind'],'source':row['source_ref'],'destination':row['destination_contract'],'result':row['result'],'revision':row['result_revision']}
        if hashlib.sha256(canonical(snapshot,140000)).hexdigest()!=payload_sha256:raise InvalidDispatch('Approved payload snapshot changed')
        # Source storage references and credentials stay inside our boundary.
        body=canonical({'operation_id':idempotency_key,'payload_sha256':payload_sha256,'kind':row['kind'],'result':row['result']},70000)
        try:token=self.credential()
        except Exception:raise DestinationNotAttempted('Destination credential unavailable; no request made')from None
        if not isinstance(token,str)or not 1<=len(token)<=16000 or any(ord(c)<33 or ord(c)>126 for c in token):raise DestinationNotAttempted('Destination credential unavailable; no request made')
        connection=http.client.HTTPSConnection(self.host,self.port,timeout=8,context=self.context)
        try:
            connection.request('POST',self.path,body=body,headers={'Content-Type':'application/json','Accept':'application/json','Authorization':'Bearer '+token,'Idempotency-Key':idempotency_key})
            response=connection.getresponse();raw=response.read(8193)
            # No redirects, inferred success, 202-as-completed, or error-body logs.
            if response.status not in {200,201}or len(raw)>8192 or response.getheader('Content-Type','').split(';')[0].lower()!='application/json':raise ExternalOutcomeUnknown('Destination completion is unconfirmed')
            def unique(pairs):
                result={}
                for key,value in pairs:
                    if key in result:raise ValueError('Duplicate receipt field')
                    result[key]=value
                return result
            reply=json.loads(raw,object_pairs_hook=unique)
            if (not isinstance(reply,dict)or set(reply)!={'operation_id','payload_sha256','external_id','status'}or reply['operation_id']!=idempotency_key
                or reply['payload_sha256']!=payload_sha256 or reply['status']!='completed' or not isinstance(reply['external_id'],str)or not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,200}',reply['external_id'])):raise ExternalOutcomeUnknown('Destination completion is unconfirmed')
            return {'externalId':reply['external_id'],'operationId':idempotency_key,'payloadSha256':payload_sha256}
        except ExternalOutcomeUnknown:raise
        except Exception:raise ExternalOutcomeUnknown('Destination completion is unconfirmed')from None
        finally:connection.close()
