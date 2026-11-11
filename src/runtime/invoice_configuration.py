"""Owned non-HTTP deployment and native SQL credential configuration.

Shared by API, worker and fixed operator jobs. Importing this module neither
loads staff JWT/HTTP adapters nor performs cloud requests or secret reads.
"""
import json
from pathlib import Path
from workflow_configuration import native_database,mounted_secret
from structured_output import _object

def owned_deployment():
    with(Path(__file__).parent/'invoice-deployment.json').open('rb')as stream:raw=stream.read(1025)
    if len(raw)>1024:raise ValueError('Invalid owned invoice deployment metadata')
    deployment=json.loads(raw,object_pairs_hook=_object)
    if not isinstance(deployment,dict)or set(deployment)!={'format','provider'}or deployment['format']!='invoice-workflow-v1':raise ValueError('Invalid owned invoice deployment metadata')
    if deployment['provider']not in {'aws','azure','gcp','ibm'}:raise ValueError('Unsupported owned invoice provider')
    return deployment
