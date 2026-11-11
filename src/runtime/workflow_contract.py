"""Nonsecret, immutable integration identity included in every human approval."""
import hashlib
import json
import re
if __package__:
    from .workflow_payload import PayloadContract
else:
    from workflow_payload import PayloadContract

def reviewed_contract(value):
    fields={'id','endpointSha256','scope','mappingVersion'}
    optional={'payloadContractSha256','applicationContractSha256'}
    if (not isinstance(value,dict)or not fields<=set(value)<=fields|optional
        or not isinstance(value['id'],str)or not re.fullmatch(r'[a-z0-9-]{1,80}',value['id'])
        or not isinstance(value['endpointSha256'],str)or not re.fullmatch(r'[0-9a-f]{64}',value['endpointSha256'])
        or not isinstance(value['scope'],str)or not 1<=len(value['scope'])<=200 or any(ord(c)<33 or ord(c)>126 for c in value['scope'])
        or type(value['mappingVersion'])is not int or not 1<=value['mappingVersion']<=10000
        or any(key in value and(not isinstance(value[key],str)or not re.fullmatch(r'[0-9a-f]{64}',value[key]))for key in optional)):raise ValueError('Supply the reviewed nonsecret destination contract identity')
    return json.loads(json.dumps(value))

def normalized_contract(endpoint,scope):
    return reviewed_contract({'id':'normalized-action-v1','endpointSha256':hashlib.sha256(endpoint.encode('utf-8')).hexdigest(),'scope':scope,'mappingVersion':1})

def bind_payload_contract(destination,payload_contract):
    result=reviewed_contract(destination)
    if payload_contract is not None and type(payload_contract)is not PayloadContract:raise ValueError('Use an owned immutable application payload contract')
    bound=result.get('payloadContractSha256')
    if bound is not None and(payload_contract is None or bound!=payload_contract.sha256):raise ValueError('Application contract does not match its destination binding')
    if payload_contract is not None:result['payloadContractSha256']=payload_contract.sha256
    return result

def bind_application_contract(destination,sha256):
    result=reviewed_contract(destination)
    if type(sha256)is not str or not re.fullmatch(r'[0-9a-f]{64}',sha256):raise ValueError('Use an exact owned application declaration digest')
    if 'applicationContractSha256'in result and result['applicationContractSha256']!=sha256:raise ValueError('Application declaration binding changed')
    result['applicationContractSha256']=sha256
    return result
