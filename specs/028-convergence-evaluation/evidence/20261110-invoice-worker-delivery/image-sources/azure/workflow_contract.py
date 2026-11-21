"""Nonsecret, immutable integration identity included in every human approval."""
import hashlib
import json
import re

def reviewed_contract(value):
    if (not isinstance(value,dict)or set(value)!={'id','endpointSha256','scope','mappingVersion'}
        or not isinstance(value['id'],str)or not re.fullmatch(r'[a-z0-9-]{1,80}',value['id'])
        or not isinstance(value['endpointSha256'],str)or not re.fullmatch(r'[0-9a-f]{64}',value['endpointSha256'])
        or not isinstance(value['scope'],str)or not 1<=len(value['scope'])<=200 or any(ord(c)<33 or ord(c)>126 for c in value['scope'])
        or type(value['mappingVersion'])is not int or not 1<=value['mappingVersion']<=10000):raise ValueError('Supply the reviewed nonsecret destination contract identity')
    return json.loads(json.dumps(value))

def normalized_contract(endpoint,scope):
    return reviewed_contract({'id':'normalized-action-v1','endpointSha256':hashlib.sha256(endpoint.encode('utf-8')).hexdigest(),'scope':scope,'mappingVersion':1})
