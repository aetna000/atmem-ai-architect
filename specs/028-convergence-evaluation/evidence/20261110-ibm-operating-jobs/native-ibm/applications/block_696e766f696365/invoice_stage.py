"""Trusted bounded worker child. JSON-only protocol, no request-selected commands."""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from invoice_native import native_objects,owned_deployment,destination_contract,mounted_secret
from invoice_processing import InvoiceProcessor
from invoice_parser_transport import ParserClient,google_parser_authorization,azure_parser_authorization,ibm_parser_authorization
from approved_http_destination import ApprovedHttpDestination
from workflow_contract import normalized_contract
from workflow_errors import TemporaryWork,PermanentWork,ExternalOutcomeUnknown,DestinationNotAttempted,InvalidDispatch
from structured_output import _object
from policy_review import verify_policy_review

def replay_review(environment,contract):
    encoded=environment.get('DESTINATION_REPLAY_REVIEW_BASE64','')
    if not encoded:return False
    if not isinstance(encoded,str)or len(encoded)>8192:raise ValueError('Invalid owned destination review')
    verify_policy_review(encoded,{'contract':contract,'idempotency':'same-key-same-payload-one-effect'})
    return True

def native_processor(provider,environment,*,objects=None,parser=None,model=None):
    if provider not in {'aws','azure','gcp','ibm'}:raise ValueError('Unsupported owned model provider')
    env=environment
    if model is None:
        if provider=='aws':
            from aws_json_model import BedrockJsonModel,read_model_config
            model=BedrockJsonModel(read_model_config(env))
        elif provider=='azure':
            from azure_structured import AzureModel,read_model_config
            model=AzureModel(read_model_config(env))
        elif provider=='gcp':
            from gcp_structured import VertexModel,read_model_config
            model=VertexModel(read_model_config(env))
        elif provider=='ibm':
            from ibm_structured import WatsonModel,read_model_config
            # Internal workspace UUID and IBM cloud account are different owners.
            model=WatsonModel(read_model_config({**env,'ACCOUNT_ID':env['IBM_ACCOUNT_ID']}))
        else:raise ValueError('Unsupported owned model provider')
    if parser is None:
        authorization=google_parser_authorization(env['PARSER_AUDIENCE'])if provider=='gcp'else azure_parser_authorization(env['PARSER_AUDIENCE'],env['WORKLOAD_IDENTITY_CLIENT_ID'])if provider=='azure'else ibm_parser_authorization(env['PARSER_SHARED_TOKEN_FILE'])if provider=='ibm'else None
        # AWS uses owned network restrictions; IBM additionally requires a
        # separately provisioned parser-only token. No public anonymous parser URL
        # is supplied by a browser/model. Infrastructure must prove that wiring.
        parser=ParserClient(env['PARSER_ENDPOINT'],authorization)
    return InvoiceProcessor(objects if objects is not None else native_objects(provider,env),parser,model)

def dispatch_operation(operation,identity,environment):
    from invoice_retention import retained
    if not retained(operation):raise InvalidDispatch('Invoice retention period ended; no request was made')
    env=environment;contract=destination_contract(env)
    if normalized_contract(env['DESTINATION_ENDPOINT'],env['DESTINATION_SCOPE'])!=contract:raise InvalidDispatch('Destination differs from the approved contract')
    try:verified=replay_review(env,contract)
    except Exception:raise DestinationNotAttempted('Destination review must be renewed; no request was made')from None
    destination=ApprovedHttpDestination(env['DESTINATION_ENDPOINT'],mounted_secret(env['DESTINATION_TOKEN_FILE'],maximum=20000),destination_scope=env['DESTINATION_SCOPE'],idempotency_verified=verified)
    return destination(operation,**identity)

def main():
    mode=sys.argv[1]if len(sys.argv)==2 else None;status='temporary'if mode=='extract'else'unknown';result={}
    try:
        raw=sys.stdin.buffer.read(140001)
        if len(raw)>140000:raise ValueError('Stage input exceeds its boundary')
        value=json.loads(raw,object_pairs_hook=_object)
        if not isinstance(value,dict)or set(value)!={'operation','identity'}or not isinstance(value['operation'],dict)or not isinstance(value['identity'],dict):raise ValueError('Invalid owned stage input')
        provider=owned_deployment()['provider']
        if mode=='extract':
            if value['identity']:raise ValueError('Extraction cannot select an action identity')
            result=native_processor(provider,os.environ)(value['operation']);status='ok'
        elif mode=='dispatch':result=dispatch_operation(value['operation'],value['identity'],os.environ);status='ok'
        else:raise ValueError('Use the owned extraction or dispatch command')
    except PermanentWork:status='permanent'if mode=='extract'else'invalid'
    except InvalidDispatch:status='invalid'
    except DestinationNotAttempted:status='not_attempted'
    except TemporaryWork:status='temporary'
    except ExternalOutcomeUnknown:status='unknown'
    except Exception:pass
    sys.stdout.write(json.dumps({'status':status,'result':result},ensure_ascii=False,allow_nan=False))

if __name__=='__main__':main()
