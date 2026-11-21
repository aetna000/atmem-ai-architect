"""Terraform apply emulator: the real Terraform CLI and real provider plugin run
the full lifecycle against a loopback cloud API. No cloud account is contacted.

Lifecycle: init -> validate -> plan -> apply -> independent API read-back ->
convergence plan -> destroy -> leak check. Every stage is reported; an emulator
gap is never promoted to a pass.

Runs inside the isolated emulator runtime (scripts/setup-terraform-emulator.py):

    python -I server/terraform_emulator.py --dir <terraform directory>

AWS is the first backend (Moto server). Azure, Google Cloud and IBM are
registered provider families without a backend yet; they report `unavailable`.
"""
import argparse
import collections
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse

try:
    from . import terraform_emulator_engines as engines
except ImportError:  # run as a script inside the isolated runtime
    import importlib.util
    _spec = importlib.util.spec_from_file_location('terraform_emulator_engines', Path(__file__).with_name('terraform_emulator_engines.py'))
    engines = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(engines)

REPORT_VERSION = 1
ACCOUNT_ID = '123456789012'
DEFAULT_REGION = 'ap-southeast-2'
OUTPUT_LIMIT = 16000
COMMAND_TIMEOUT = 900
TIMED_OUT = 124
# Provider source -> provider family. A family needs a backend before any run.
PROVIDER_FAMILIES = {
    'hashicorp/aws': 'aws',
    'hashicorp/azurerm': 'azure', 'hashicorp/azuread': 'azure', 'azure/azapi': 'azure',
    'hashicorp/google': 'gcp', 'hashicorp/google-beta': 'gcp',
    'ibm-cloud/ibm': 'ibm',
}
# Providers that never call a cloud API; allowed beside any family.
LOCAL_PROVIDERS = {'hashicorp/random', 'hashicorp/null', 'hashicorp/local', 'hashicorp/archive', 'hashicorp/time', 'hashicorp/tls', 'hashicorp/external', 'terraform.io/builtin/terraform'}
BOUNDARIES = [
    'Emulated API responses are not AWS. IAM and resource policies are stored, not enforced.',
    'Provisioning time, quotas, account limits, service availability and pricing are not emulated.',
    'Lambda, ECS and other compute is registered through the API; its code is not executed here.',
    'Bedrock knowledge-base registration does not validate vector-index existence, IAM grants, embedding availability, ingestion or retrieval.',
    'A pass proves the Terraform lifecycle against the emulator, not an account plan or deployment.',
]


def stop_process_tree(process):
    """Stop only the owned worker and descendants on the local platform."""
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        else:
            os.killpg(process.pid, 9)
    except ProcessLookupError:
        pass


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def tail(text):
    return text[-OUTPUT_LIMIT:]


# ---------------------------------------------------------------- backends

def emulator_error(code, message, service, body, environ):
    """Error body in the wire protocol the calling SDK expects for this service."""
    from xml.sax.saxutils import escape
    if service == 's3':
        return 'application/xml', f'<?xml version="1.0" encoding="UTF-8"?><Error><Code>{code}</Code><Message>{escape(message)}</Message></Error>'.encode()
    query = body[:7] == b'Action=' or b'&Action=' in body[:4096] or 'Action=' in environ.get('QUERY_STRING', '')
    if query or service in ('cloudfront', 'route53'):
        return 'text/xml', f'<ErrorResponse><Error><Type>Sender</Type><Code>{code}</Code><Message>{escape(message)}</Message></Error><RequestId>emulator</RequestId></ErrorResponse>'.encode()
    return 'application/x-amz-json-1.1', json.dumps({'__type': code, 'message': message, 'Message': message}).encode()


class CborBridge:
    """Translate one smithy rpc-v2-cbor call to the awsJson call Moto serves.

    The Terraform AWS provider's CloudWatch client speaks rpc-v2-cbor; Moto
    5.2.5 server mode routes only the JSON and query forms of the same API.
    Conversion is shape-aware through the pinned botocore service model, so
    timestamps, blobs and numbers keep their types in both directions.
    """
    SERVICES = {'monitoring': 'cloudwatch'}
    PATH = re.compile(r'/service/([\w.-]+)/operation/(\w+)')
    models = {}

    def __init__(self, service, path):
        import botocore.session
        match = self.PATH.fullmatch(path)
        name = self.SERVICES.get(service, service)
        if name not in self.models:
            self.models[name] = botocore.session.get_session().get_service_model(name)
        model = self.models[name]
        if not match or model.metadata.get('targetPrefix') != match[1] or 'json' not in model.metadata.get('protocols', []):
            raise LookupError(f'No JSON form of {path} is known for {service}')
        self.operation = model.operation_model(match[2])

    def request(self, environ, body):
        from botocore import parsers, serialize
        parser = parsers.RpcV2CBORParser()
        params = {}
        if body and self.operation.input_shape is not None:
            raw = parser.parse_data_item(parser.get_peekable_stream_from_bytes(body))
            params = parser._parse_shape(self.operation.input_shape, raw)
        # The JSON serializer reads the wire protocol from the model metadata.
        serializer = serialize.JSONSerializer()
        request = serializer.serialize_to_request(params, self.operation)
        encoded = request['body'] if isinstance(request['body'], bytes) else str(request['body']).encode()
        environ.update({'PATH_INFO': '/', 'RAW_URI': '/', 'REQUEST_URI': '/', 'CONTENT_TYPE': request['headers']['Content-Type'], 'HTTP_X_AMZ_TARGET': request['headers']['X-Amz-Target'], 'CONTENT_LENGTH': str(len(encoded)), 'wsgi.input': io.BytesIO(encoded)})
        for header in ('HTTP_SMITHY_PROTOCOL', 'HTTP_ACCEPT', 'HTTP_X_AMZN_QUERY_MODE'):
            environ.pop(header, None)
        return encoded

    def response(self, status, body):
        """Returns (headers, body) in rpc-v2-cbor for the JSON answer."""
        from botocore import parsers, serialize
        headers = [('smithy-protocol', 'rpc-v2-cbor')]
        if status >= 400:
            try:
                error = json.loads(body or b'{}')
            except ValueError:
                error = {'__type': 'EmulatorInternalError', 'message': body[:300].decode('utf-8', 'replace')}
            code = str(error.get('__type') or error.get('code') or status).rsplit('#', 1)[-1]
            message = str(error.get('message') or error.get('Message') or '')
            encoded = bytearray()
            serializer = serialize.RpcV2CBORSerializer()
            encoded.append(0xA2)
            for text in ('__type', code, 'message', message):
                serializer._serialize_type_string(encoded, text, None, None)
            return headers + [('Content-Type', 'application/cbor'), ('x-amzn-query-error', f'{code};Sender')], bytes(encoded)
        shape = self.operation.output_shape
        if shape is None:
            return headers, b''
        parsed = parsers.JSONParser().parse({'body': body or b'{}', 'headers': {}, 'status_code': status}, shape)
        parsed.pop('ResponseMetadata', None)
        encoded = bytearray()
        serialize.RpcV2CBORSerializer()._serialize_data_item(encoded, parsed, shape)
        return headers + [('Content-Type', 'application/cbor')], bytes(encoded)


class RequestLog:
    """WSGI middleware recording every API call the provider makes."""

    def __init__(self, app):
        self.app = app
        self.calls = []
        self.lock = threading.Lock()
        self.engine_lock = threading.RLock()
        self.recording = True
        self.adapters = []
        self.engines = []
        self.started = time.monotonic()

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path.startswith('/moto-api'):
            return self.app(environ, start_response)
        try:
            length = int(environ.get('CONTENT_LENGTH') or 0)
        except ValueError:
            length = 0
        body = environ['wsgi.input'].read(length) if length else b''
        environ['wsgi.input'] = io.BytesIO(body)
        scope = re.search(r'Credential=[^/]+/\d+/([^/]+)/([^/]+)/aws4_request', environ.get('HTTP_AUTHORIZATION', ''))
        service = scope[2] if scope else 'unknown'
        operation = environ.get('HTTP_X_AMZ_TARGET', '').rsplit('.', 1)[-1]
        if not operation and b'Action=' in body[:4096]:
            operation = (urllib.parse.parse_qs(body[:4096].decode('latin-1')).get('Action') or [''])[0]
        if not operation:
            operation = (urllib.parse.parse_qs(environ.get('QUERY_STRING', '')).get('Action') or [''])[0]
        if not operation:
            operation = environ.get('REQUEST_METHOD', '') + ' ' + re.sub(r'/[^/]{20,}', '/{id}', path)
        bridge = None
        if environ.get('HTTP_SMITHY_PROTOCOL') == 'rpc-v2-cbor':
            operation = path.rsplit('/', 1)[-1]
            try:
                bridge = CborBridge(service, path)
                body = bridge.request(environ, body)
            except Exception as error:  # unknown service or shape: an explicit gap below
                bridge = None
                environ['atmem.cbor_error'] = f'{type(error).__name__}: {error}'
        record = {'service': service, 'operation': operation, 'status': 0, 't': round(time.monotonic() - self.started, 2)}
        if bridge:
            record['protocolBridge'] = 'rpc-v2-cbor'
        try:
            with self.engine_lock:
                answered = engines.dispatch(self.engines, service, environ, path, body) if self.engines and not bridge else None
        except Exception as error:
            # A custom engine defect is permanent too: never let an HTTP 500
            # trigger minutes of SDK retries or be mistaken for AWS behavior.
            detail = f'{service}:{operation}: {type(error).__name__}: {str(error)[:200]}'
            record.update(status=400, emulatorError=True, error=detail, engine='atmem-engine-dispatch')
            with self.lock:
                if self.recording:
                    self.calls.append(record)
            content_type, message = emulator_error('EmulatorInternalError', detail, service, body, environ)
            start_response('400 Bad Request', [('Content-Type', content_type), ('Content-Length', str(len(message))), ('x-amzn-ErrorType', 'EmulatorInternalError')])
            return [message]
        if answered:
            # An AtMem-built engine implements this API; the base emulator is not consulted.
            engine, reply = answered
            record.update(operation=reply.operation, status=reply.status, engine=engine.name)
            if reply.status >= 400:
                record['error'] = reply.body[:300].decode('utf-8', 'replace')
                if b'EmulatorNotImplemented' in reply.body:
                    record['notImplemented'] = True
                if b'EmulatorInternalError' in reply.body:
                    record['emulatorError'] = True
            with self.lock:
                if self.recording:
                    self.calls.append(record)
            reason = {200: 'OK', 201: 'Created', 204: 'No Content', 400: 'Bad Request', 404: 'Not Found', 409: 'Conflict', 412: 'Precondition Failed'}.get(reply.status, 'Status')
            start_response(f'{reply.status} {reason}', [('Content-Type', reply.content_type), ('Content-Length', str(len(reply.body))), ('x-amzn-RequestId', 'atmem-engine'), *reply.headers])
            return [reply.body]

        status_holder = {}

        def capture(status, headers, exc_info=None):
            # Deferred: a 5xx from the emulator is rewritten before it is sent.
            status_holder.update(status=status, headers=headers)
            record['status'] = int(status.split()[0])

        try:
            chunks = list(self.app(environ, capture))
            failure = None
        except NotImplementedError as error:
            chunks, failure = [], ('EmulatorNotImplemented', str(error))
            record['status'] = 501
        if record['status'] in (404, 405) and failure is None and b''.join(chunks)[:15].lower().startswith(b'<!doctype html'):
            # The emulator has no route for this API at all; its web framework answered.
            failure = ('EmulatorNotImplemented', 'The emulator has no route for this operation')
        if record['status'] >= 500 and failure is None:
            text = b''.join(chunks)[:600].decode('utf-8', 'replace')
            implemented = 'not been implemented' not in text and 'NotImplemented' not in text
            failure = ('EmulatorInternalError' if implemented else 'EmulatorNotImplemented', text)
        if failure:
            # AWS SDKs retry 5xx for minutes. An emulator gap is permanent, so it
            # is answered once as a non-retryable error the provider reports verbatim.
            code, detail = failure
            record.update(error=detail[:300], **({'notImplemented': True} if code == 'EmulatorNotImplemented' else {'emulatorError': True}))
            with self.lock:
                if self.recording:
                    self.calls.append(record)
            content_type, message = emulator_error(code, f'{service}:{operation}: {detail[:300]}', service, body, environ)
            start_response('400 Bad Request', [('Content-Type', content_type), ('Content-Length', str(len(message))), ('x-amzn-ErrorType', code)])
            return [message]
        if bridge:
            try:
                bridged, payload = bridge.response(record['status'], b''.join(chunks))
            except Exception as error:
                record.update(error=f'Protocol bridge failed: {type(error).__name__}: {error}'[:300], emulatorError=True)
                bridged, payload = bridge.response(400, json.dumps({'__type': 'EmulatorInternalError', 'message': record['error']}).encode())
                status_holder['status'] = '400 Bad Request'
                record['status'] = 400
            chunks = [payload]
            status_holder['headers'] = bridged + [('Content-Length', str(len(payload)))]
        start_response(status_holder['status'], status_holder['headers'])
        if record['status'] < 300:
            for adapter in self.adapters:
                adapter(environ, body, path)
        if record['status'] >= 400:
            record['error'] = b''.join(chunks)[:300].decode('utf-8', 'replace')
        record['t'] = round(time.monotonic() - self.started, 2)
        with self.lock:
            if self.recording:
                self.calls.append(record)
        return chunks

    def summary(self):
        by_service = collections.Counter(call['service'] for call in self.calls)
        operations = sorted({call['service'] + ':' + call['operation'] for call in self.calls if call['status'] < 400})
        gaps = sorted({call['service'] + ':' + call['operation'] for call in self.calls if call.get('notImplemented')})
        server_errors = [{key: call[key] for key in ('service', 'operation', 'error')} for call in self.calls if call.get('emulatorError')][:25]
        by_engine = collections.Counter(call.get('engine', 'moto') for call in self.calls)
        return {'total': len(self.calls), 'byEngine': dict(sorted(by_engine.items())), 'byService': dict(sorted(by_service.items())), 'successfulOperations': operations, 'notImplemented': gaps, 'serverErrors': server_errors}

    def timeline(self):
        return [[call['t'], call['service'], call['operation'], call['status']] for call in self.calls]


def create_bucket_tags_adapter(environ, body, path):
    """Moto 5.2.5 ignores tags sent inside CreateBucketConfiguration; AWS stores them."""
    if environ.get('REQUEST_METHOD') != 'PUT' or environ.get('QUERY_STRING') or b'<Tags>' not in body:
        return
    name = path.strip('/')
    if not name or '/' in name:
        return
    import xml.etree.ElementTree as ElementTree
    from moto.s3.models import s3_backends
    tags = []
    for tag in ElementTree.fromstring(body).iter():
        if tag.tag.rsplit('}', 1)[-1] == 'Tag':
            pair = {child.tag.rsplit('}', 1)[-1]: child.text or '' for child in tag}
            tags.append({'Key': pair['Key'], 'Value': pair.get('Value', '')})
    backend = s3_backends[ACCOUNT_ID]['aws']
    backend.tagger.tag_resource(backend.get_bucket(name).arn, tags)


def install_alias_mapping_adapter():
    """Moto 5.2.5 rewrites an alias-qualified event source mapping target to the
    alias's current version ARN. AWS returns the alias ARN the caller supplied."""
    from moto.awslambda.models import EventSourceMapping
    if getattr(EventSourceMapping, '_atmem_alias_adapter', False):
        return
    original = EventSourceMapping.__init__
    alias_arn = re.compile(r'arn:aws[\w-]*:lambda:[\w-]+:\d{12}:function:[\w-]+:(?![0-9]+$)[\w-]+')

    def create(self, spec):
        original(self, spec)
        if alias_arn.fullmatch(spec.get('FunctionName') or ''):
            self.function_arn = spec['FunctionName']
    EventSourceMapping.__init__ = create
    EventSourceMapping._atmem_alias_adapter = True


def install_redrive_allow_adapter():
    """Moto 5.2.5 stores RedriveAllowPolicy but rejects reading it by name, so
    the provider waits forever for the attribute it just set."""
    from moto.sqs.models import Queue
    if 'RedriveAllowPolicy' in Queue.BASE_ATTRIBUTES:
        return
    original = Queue.attributes.fget
    Queue.BASE_ATTRIBUTES = [*Queue.BASE_ATTRIBUTES, 'RedriveAllowPolicy']
    Queue.redrive_allow_policy = None
    setter = Queue._set_attributes

    def set_attributes(self, attributes, now=None):
        supplied = attributes.get('RedrivePolicy')
        previous = getattr(self, 'policy', None)
        setter(self, attributes, now)
        if 'Policy' not in attributes:
            # SetQueueAttributes changes only the attributes it names; Moto clears Policy.
            self.policy = previous
        if isinstance(supplied, str):
            self._atmem_redrive_text = supplied

    def read_attributes(self):
        # AWS omits RedriveAllowPolicy until a policy is set.
        result = {key: value for key, value in original(self).items() if key != 'RedriveAllowPolicy' or value}
        text = getattr(self, '_atmem_redrive_text', None)
        # AWS returns RedrivePolicy as the caller's document; Moto re-serializes it with other whitespace.
        if text and self.redrive_policy and same_json(text, json.dumps(self.redrive_policy)):
            result['RedrivePolicy'] = text
        return result
    Queue._set_attributes = set_attributes
    Queue.attributes = property(read_attributes)


def install_policy_condition_adapter():
    """Moto 5.2.5 applies a bucket-policy statement without evaluating its
    Condition, so `Deny ... if aws:SecureTransport is false` denies every
    object request. Conditional statements are stored and returned unchanged
    but not enforced, matching the stated boundary that policies are not enforced."""
    from moto.s3.models import FakeBucket
    if getattr(FakeBucket, '_atmem_condition_adapter', False):
        return
    from moto.iam.access_control import IAMPolicy, PermissionResult

    def get_permission(self, action, resource):
        if self.policy is None:
            return PermissionResult.NEUTRAL
        document = json.loads(self.policy.decode())
        statements = document.get('Statement', [])
        statements = statements if isinstance(statements, list) else [statements]
        document['Statement'] = [statement for statement in statements if not statement.get('Condition')]
        if not document['Statement']:
            return PermissionResult.NEUTRAL
        return IAMPolicy(json.dumps(document)).is_action_permitted(action, resource)
    FakeBucket.get_permission = get_permission
    FakeBucket._atmem_condition_adapter = True


def install_rds_parameter_source_adapter():
    """Moto stores user parameter values but omits their Source on read-back."""
    from moto.rds.models import DBParameterGroup
    if getattr(DBParameterGroup, '_atmem_parameter_source', False):
        return
    original = DBParameterGroup.update_parameters

    def update(self, parameters):
        # Do not modify the caller's objects or change parameter values/methods.
        original(self, [dict(parameter, Source='user') for parameter in parameters])
    DBParameterGroup.update_parameters = update
    DBParameterGroup._atmem_parameter_source = True


# Version-scoped repairs for observed emulator defects, never configuration bypasses.
MOTO_ADAPTERS = [
    {'id': 'moto-rds-parameter-source-v1', 'motoVersion': '5.2.5', 'install': install_rds_parameter_source_adapter,
     'reason': 'User-modified DB parameters omit Source, so the provider excludes them from read-back and proposes perpetual drift.',
     'reference': 'https://docs.aws.amazon.com/AmazonRDS/latest/APIReference/API_ModifyDBParameterGroup.html',
     'scope': 'Mark explicitly modified DB parameter values as user-sourced; retain names, values and apply methods. No engine validation or reboot semantics are implied.'},
    {'id': 'moto-s3-create-bucket-tags-v1', 'motoVersion': '5.2.5', 'apply': create_bucket_tags_adapter,
     'reason': 'Moto drops tags supplied in CreateBucketConfiguration, so the provider reads an untagged bucket and reports false drift.',
     'reference': 'https://docs.aws.amazon.com/AmazonS3/latest/API/API_CreateBucketConfiguration.html',
     'scope': 'Store exactly the tags of the successful CreateBucket request on that bucket. No other request is changed.'},
    {'id': 'moto-rpc-v2-cbor-bridge-v1', 'motoVersion': '5.2.5',
     'reason': 'The provider calls CloudWatch in the smithy rpc-v2-cbor protocol; Moto server mode routes only the JSON and query forms, so alarms could never be created.',
     'reference': 'https://smithy.io/2.0/additional-specs/protocols/smithy-rpc-v2.html',
     'scope': 'Re-encode the same operation and members between rpc-v2-cbor and awsJson using the pinned botocore model. No value is added, removed or defaulted.'},
    {'id': 'moto-sqs-redrive-allow-policy-v1', 'motoVersion': '5.2.5', 'install': install_redrive_allow_adapter,
     'reason': 'Moto stores RedriveAllowPolicy but answers InvalidAttributeName when it is read, re-serializes RedrivePolicy with different whitespace, and clears the queue Policy whenever another attribute is set, so the provider waits forever or reports false drift.',
     'reference': 'https://docs.aws.amazon.com/AWSSimpleQueueService/latest/APIReference/API_GetQueueAttributes.html',
     'scope': 'Return the stored RedriveAllowPolicy; omit it while unset. Return RedrivePolicy as the text the caller supplied when it is the same JSON document. Keep Policy when a request does not name it.'},
    {'id': 'moto-s3-policy-condition-v1', 'motoVersion': '5.2.5', 'install': install_policy_condition_adapter,
     'reason': 'Moto applies conditional bucket-policy statements unconditionally, so a deny-insecure-transport statement blocks every object upload.',
     'reference': 'https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_condition.html',
     'scope': 'Statements with a Condition are stored and returned unchanged but not enforced. Unconditional statements keep Moto behavior.'},
    {'id': 'moto-lambda-mapping-alias-arn-v1', 'motoVersion': '5.2.5', 'install': install_alias_mapping_adapter,
     'reason': 'Moto reports an alias-qualified event source mapping as targeting a numbered version, so the provider plans a change on every run.',
     'reference': 'https://docs.aws.amazon.com/lambda/latest/api/API_CreateEventSourceMapping.html',
     'scope': 'Keep the exact alias ARN supplied at creation as FunctionArn. Unqualified and version-qualified targets are unchanged.'},
]


class MotoAwsBackend:
    """Stateful AWS API on loopback, served in-process by pinned Moto."""
    family = 'aws'
    name = 'moto-server'
    qualified_versions = ('5.2.5',)

    def __init__(self):
        self.server = None
        self.log = None
        self.endpoint = None
        self.seeded = []

    @staticmethod
    def availability():
        try:
            import moto
            import flask  # noqa: F401 - required by Moto server mode
            import flask_cors  # noqa: F401
            import boto3  # noqa: F401
        except ImportError as error:
            return f'The AWS emulator runtime is incomplete ({error.name}). Run python3 scripts/setup-terraform-emulator.py.'
        if moto.__version__ not in MotoAwsBackend.qualified_versions:
            return f'Moto {moto.__version__} is not a qualified emulator version.'
        return None

    def describe(self):
        import moto
        adapters = [{key: value for key, value in adapter.items() if key not in ('apply', 'install')} for adapter in MOTO_ADAPTERS]
        built = [{'name': engine.name, 'service': engine.service, 'operations': engine.operations, 'reference': engine.reference} for engine in self.build_engines()]
        return {'name': self.name, 'engine': 'moto', 'version': moto.__version__, 'endpoint': 'loopback', 'accountId': ACCOUNT_ID, 'adapters': adapters, 'engines': built, 'implementationDigests': {'lifecycle': sha256(Path(__file__).read_bytes()), 'engines': sha256(Path(engines.__file__).read_bytes())}}

    @staticmethod
    def build_engines():
        """AtMem-built engines for APIs the base emulator does not implement."""
        def user_pools(region):
            from moto.cognitoidp.models import cognitoidp_backends
            return cognitoidp_backends[ACCOUNT_ID][region].user_pools

        def state_machines(region):
            from moto.stepfunctions.models import stepfunctions_backends
            return [machine.arn for machine in stepfunctions_backends[ACCOUNT_ID][region].state_machines]
        def serverless(region):
            from moto.opensearchserverless.models import opensearchserverless_backends
            return opensearchserverless_backends[ACCOUNT_ID][region]
        return [engines.ServerlessLifecycleEngine(serverless), engines.KnowledgeBaseEngine(lambda region: serverless(region).collections,ACCOUNT_ID), engines.CloudFrontEngine(ACCOUNT_ID), engines.AppRunnerEngine(ACCOUNT_ID), engines.BedrockGuardrailEngine(ACCOUNT_ID), engines.StepFunctionsValidationEngine(state_machines), engines.CognitoResourceServerEngine(user_pools)]

    def start(self):
        from werkzeug.serving import make_server
        from moto.moto_server.werkzeug_app import DomainDispatcherApplication, create_backend_app
        self.log = RequestLog(DomainDispatcherApplication(create_backend_app))
        self.log.adapters = [adapter['apply'] for adapter in MOTO_ADAPTERS if 'apply' in adapter]
        self.log.engines = self.build_engines()
        for adapter in MOTO_ADAPTERS:
            if 'install' in adapter:
                adapter['install']()
        import logging
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        self.server = make_server('127.0.0.1', 0, self.log, threaded=True)
        self.endpoint = f'http://127.0.0.1:{self.server.server_address[1]}'
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        if self.server:
            self.server.shutdown()

    def environment(self, folder):
        """Redirect every AWS service of the unmodified configuration to loopback."""
        return {
            'AWS_ENDPOINT_URL': self.endpoint,
            'AWS_ACCESS_KEY_ID': 'testing', 'AWS_SECRET_ACCESS_KEY': 'testing',
            'AWS_REGION': DEFAULT_REGION, 'AWS_DEFAULT_REGION': DEFAULT_REGION,
            'AWS_S3_USE_PATH_STYLE': 'true',
            'AWS_EC2_METADATA_DISABLED': 'true',
            'AWS_CONFIG_FILE': str(Path(folder) / 'no-aws-config'),
            'AWS_SHARED_CREDENTIALS_FILE': str(Path(folder) / 'no-aws-credentials'),
        }

    def client(self, service, region=DEFAULT_REGION):
        import boto3
        from botocore.config import Config
        # The emulator's own SDK checks are not provider calls.
        self.log.recording = False
        return boto3.client(service, endpoint_url=self.endpoint, region_name=region, aws_access_key_id='testing', aws_secret_access_key='testing', config=Config(retries={'max_attempts': 1}, s3={'addressing_style': 'path'}))

    def synthetic_inputs(self, variables):
        """Destination inputs a real deployment gets from its account review."""
        values = {}
        for name, declaration in variables.items():
            if name == 'review_approved':
                # The generated review gate defaults to closed; emulation is an
                # explicit local rehearsal, never a deployment approval.
                values[name] = True
            if 'default' in declaration:
                continue
            if name == 'aws_account_id':
                values[name] = ACCOUNT_ID
            elif name == 'aws_region':
                values[name] = DEFAULT_REGION
            elif re.fullmatch(r'principal_[a-z0-9_]+_arn', name):
                values[name] = f'arn:aws:iam::{ACCOUNT_ID}:role/emulated/{name[:48]}'
            elif name.endswith('_alert_topic_arns'):
                values[name] = []
        return values

    def seed(self, inputs):
        """Create the pre-existing identities the configuration only references."""
        iam = self.client('iam')
        trust = json.dumps({'Version': '2012-10-17', 'Statement': [{'Effect': 'Allow', 'Principal': {'AWS': f'arn:aws:iam::{ACCOUNT_ID}:root'}, 'Action': 'sts:AssumeRole'}]})
        for value in inputs.values():
            match = re.fullmatch(rf'arn:aws:iam::{ACCOUNT_ID}:role/(.*/)?([\w+=,.@-]+)', value) if isinstance(value, str) else None
            if match:
                try:
                    iam.create_role(RoleName=match[2], Path='/' + (match[1] or ''), AssumeRolePolicyDocument=trust)
                    self.seeded.append(value)
                except iam.exceptions.EntityAlreadyExistsException:
                    pass
        self.log.recording = True

    def remaining_resources(self):
        """Ask the tagging/inventory-independent service APIs what still exists."""
        found = []
        probes = [
            ('s3', lambda c: [b['Name'] for b in c.list_buckets().get('Buckets', [])]),
            ('sqs', lambda c: c.list_queues().get('QueueUrls', [])),
            ('dynamodb', lambda c: c.list_tables().get('TableNames', [])),
            ('lambda', lambda c: [f['FunctionName'] for f in c.list_functions().get('Functions', [])]),
            ('sns', lambda c: [t['TopicArn'] for t in c.list_topics().get('Topics', [])]),
            ('iam', lambda c: [r['Arn'] for r in c.list_roles().get('Roles', []) if r['Arn'] not in self.seeded]),
            ('iam', lambda c: [p['Arn'] for p in c.list_policies(Scope='Local').get('Policies', [])]),
            ('logs', lambda c: [g['logGroupName'] for g in c.describe_log_groups().get('logGroups', [])]),
            # Service-created default keys (DynamoDB, Secrets Manager) are not Terraform resources.
            ('kms', lambda c: [k['KeyId'] for k in c.list_keys().get('Keys', []) if (lambda m: m['KeyState'] == 'Enabled' and m.get('KeyManager') != 'AWS' and not (m.get('Description') or '').startswith(('Default key', 'Default master key')))(c.describe_key(KeyId=k['KeyId'])['KeyMetadata'])]),
            ('secretsmanager', lambda c: [s['Name'] for s in c.list_secrets().get('SecretList', [])]),
            ('ssm', lambda c: [p['Name'] for p in c.describe_parameters().get('Parameters', [])]),
            ('ec2', lambda c: [v['VpcId'] for v in c.describe_vpcs().get('Vpcs', []) if not v.get('IsDefault')]),
            ('ecr', lambda c: [r['repositoryName'] for r in c.describe_repositories().get('repositories', [])]),
            ('ecs', lambda c: [x['clusterArn'] for x in (c.describe_clusters(clusters=c.list_clusters().get('clusterArns', []) or ['none']).get('clusters', [])) if x.get('status') != 'INACTIVE']),
            ('events', lambda c: [r['Name'] for r in c.list_rules().get('Rules', [])]),
            ('apigatewayv2', lambda c: [a['ApiId'] for a in c.get_apis().get('Items', [])]),
            ('cognito-idp', lambda c: [p['Id'] for p in c.list_user_pools(MaxResults=60).get('UserPools', [])]),
            ('cloudfront', lambda c: [d['Id'] for d in c.list_distributions().get('DistributionList', {}).get('Items', [])]),
            ('stepfunctions', lambda c: [m['stateMachineArn'] for m in c.list_state_machines().get('stateMachines', [])]),
            ('rds', lambda c: [p['DBParameterGroupName'] for p in c.describe_db_parameter_groups().get('DBParameterGroups', []) if not p['DBParameterGroupName'].startswith('default.')]),
            ('rds', lambda c: [d['DBInstanceIdentifier'] for d in c.describe_db_instances().get('DBInstances', [])]),
            ('elbv2', lambda c: [b['LoadBalancerArn'] for b in c.describe_load_balancers().get('LoadBalancers', [])]),
            ('route53', lambda c: [z['Id'] for z in c.list_hosted_zones().get('HostedZones', [])]),
            ('kinesis', lambda c: c.list_streams().get('StreamNames', [])),
        ]
        for engine in self.log.engines:
            found += engine.inventory()
        for service, probe in probes:
            try:
                found += [f'{service}:{item}' for item in probe(self.client(service))]
            except Exception as error:  # an inventory probe must not hide a leak
                found.append(f'{service}:inventory-probe-failed:{type(error).__name__}')
        return found

    def verify(self, resource):
        """Independent read-back through the AWS SDK, not through Terraform."""
        verifier = AWS_VERIFIERS.get(resource['type'])
        if not verifier:
            return None
        values = resource.get('values') or {}
        region = values.get('region') or DEFAULT_REGION
        try:
            checks = verifier(lambda service: self.client(service, region), values)
        except Exception as error:
            return [{'name': 'SDK read-back', 'passed': False, 'detail': f'{type(error).__name__}: {str(error)[:300]}'}]
        return [{'name': name, 'passed': bool(passed), **({} if passed else {'detail': str(detail)[:300]})} for name, passed, detail in checks]


def same_json(left, right):
    try:
        return json.loads(left) == json.loads(right)
    except (TypeError, ValueError):
        return False


def _s3_versioning(client, v):
    actual = client('s3').get_bucket_versioning(Bucket=v['bucket']).get('Status', 'Disabled')
    wanted = v['versioning_configuration'][0]['status']
    return [('Versioning status matches', actual == wanted, f'{actual} != {wanted}')]


def _s3_public_access(client, v):
    actual = client('s3').get_public_access_block(Bucket=v['bucket'])['PublicAccessBlockConfiguration']
    pairs = {'BlockPublicAcls': 'block_public_acls', 'BlockPublicPolicy': 'block_public_policy', 'IgnorePublicAcls': 'ignore_public_acls', 'RestrictPublicBuckets': 'restrict_public_buckets'}
    return [(f'{api} matches', actual.get(api) == v.get(tf), f'{actual.get(api)} != {v.get(tf)}') for api, tf in pairs.items()]


def _s3_encryption(client, v):
    rules = client('s3').get_bucket_encryption(Bucket=v['bucket'])['ServerSideEncryptionConfiguration']['Rules']
    actual = rules[0]['ApplyServerSideEncryptionByDefault']['SSEAlgorithm']
    wanted = v['rule'][0]['apply_server_side_encryption_by_default'][0]['sse_algorithm']
    return [('Default encryption algorithm matches', actual == wanted, f'{actual} != {wanted}')]


def _s3_object(client, v):
    head = client('s3').head_object(Bucket=v['bucket'], Key=v['key'])
    return [('Object exists with the recorded ETag', head['ETag'].strip('"') == (v.get('etag') or '').strip('"'), head['ETag'])]


def _sqs_queue(client, v):
    attributes = client('sqs').get_queue_attributes(QueueUrl=v['url'], AttributeNames=['All'])['Attributes']
    checks = [('Queue ARN matches', attributes.get('QueueArn') == v.get('arn'), attributes.get('QueueArn')),
              ('Visibility timeout matches', int(attributes.get('VisibilityTimeout', -1)) == v.get('visibility_timeout_seconds'), attributes.get('VisibilityTimeout')),
              ('Retention matches', int(attributes.get('MessageRetentionPeriod', -1)) == v.get('message_retention_seconds'), attributes.get('MessageRetentionPeriod'))]
    if v.get('redrive_policy'):
        checks.append(('Redrive policy matches', same_json(attributes.get('RedrivePolicy'), v['redrive_policy']), attributes.get('RedrivePolicy')))
    return checks


def _dynamodb_table(client, v):
    table = client('dynamodb').describe_table(TableName=v['name'])['Table']
    keys = {k['KeyType']: k['AttributeName'] for k in table['KeySchema']}
    billing = table.get('BillingModeSummary', {}).get('BillingMode', 'PROVISIONED')
    return [('Table is active', table['TableStatus'] == 'ACTIVE', table['TableStatus']),
            ('Partition key matches', keys.get('HASH') == v.get('hash_key'), keys),
            ('Sort key matches', keys.get('RANGE') == v.get('range_key'), keys),
            ('Billing mode matches', billing == v.get('billing_mode'), billing)]


def _iam_role(client, v):
    role = client('iam').get_role(RoleName=v['name'])['Role']
    document = role['AssumeRolePolicyDocument']
    document = document if isinstance(document, str) else json.dumps(document)
    return [('Role ARN matches', role['Arn'] == v.get('arn'), role['Arn']),
            ('Trust policy matches', same_json(urllib.parse.unquote(document), v['assume_role_policy']), document)]


def _iam_role_policy(client, v):
    document = client('iam').get_role_policy(RoleName=v['role'], PolicyName=v['name'])['PolicyDocument']
    document = document if isinstance(document, str) else json.dumps(document)
    return [('Inline policy matches', same_json(urllib.parse.unquote(document), v['policy']), document)]


def _lambda_function(client, v):
    config = client('lambda').get_function_configuration(FunctionName=v['function_name'])
    checks = [('Runtime matches', config.get('Runtime') == v.get('runtime'), config.get('Runtime')),
              ('Handler matches', config.get('Handler') == v.get('handler'), config.get('Handler')),
              ('Memory matches', config.get('MemorySize') == v.get('memory_size'), config.get('MemorySize')),
              ('Timeout matches', config.get('Timeout') == v.get('timeout'), config.get('Timeout')),
              ('Execution role matches', config.get('Role') == v.get('role'), config.get('Role'))]
    if v.get('source_code_hash'):
        checks.append(('Deployed code hash matches the built archive', config.get('CodeSha256') == v['source_code_hash'], config.get('CodeSha256')))
    return checks


def _event_source_mapping(client, v):
    mapping = client('lambda').get_event_source_mapping(UUID=v['uuid'])
    return [('Event source matches', mapping.get('EventSourceArn') == v.get('event_source_arn'), mapping.get('EventSourceArn')),
            ('Batch size matches', mapping.get('BatchSize') == v.get('batch_size'), mapping.get('BatchSize'))]


def _log_group(client, v):
    groups = client('logs').describe_log_groups(logGroupNamePrefix=v['name'])['logGroups']
    group = next((g for g in groups if g['logGroupName'] == v['name']), None)
    if not group:
        return [('Log group exists', False, 'not found')]
    return [('Log group exists', True, ''), ('Retention matches', (group.get('retentionInDays') or 0) == (v.get('retention_in_days') or 0), group.get('retentionInDays'))]


def _exists(service, call, argument, attribute):
    def verifier(client, v):
        getattr(client(service), call)(**{argument: v[attribute]})
        return [('Resource exists through the service API', True, '')]
    return verifier


def _listed(service, call, argument, attribute, path, key):
    def verifier(client, v):
        items = getattr(client(service), call)(**{argument: [v[attribute]]})[path]
        return [('Resource exists through the service API', any(item.get(key) == v[attribute] for item in items), f'{len(items)} returned')]
    return verifier


def _rds_parameters(client, values):
    api = client('rds')
    parameters = {}
    for page in api.get_paginator('describe_db_parameters').paginate(DBParameterGroupName=values['name'], Source='user'):
        parameters.update({p['ParameterName']: p for p in page['Parameters']})
    return [('User parameter matches: ' + p['name'],
             parameters.get(p['name'], {}).get('ParameterValue') == p['value'] and parameters.get(p['name'], {}).get('ApplyMethod') == p['apply_method'],
             'Stored parameter value/apply method differs') for p in values.get('parameter', [])]


def _cloudfront_distribution(client, values):
    actual = client('cloudfront').get_distribution(Id=values['id'])['Distribution']
    config = actual['DistributionConfig']
    checks = [('Distribution ARN matches', actual['ARN'] == values['arn'], 'ARN differs'),
              ('Distribution enabled matches', config['Enabled'] == values['enabled'], 'Enabled differs')]
    wanted = {o['origin_id']: o['domain_name'] for o in values.get('origin', [])}
    found = {o['Id']: o['DomainName'] for o in config['Origins'].get('Items', [])}
    checks.append(('Origin IDs and domains match', found == wanted, 'Origins differ'))
    return checks


def _apprunner_service(client, v):
    actual = client('apprunner').describe_service(ServiceArn=v['arn'])['Service']['SourceConfiguration']
    source = v['source_configuration'][0]
    image = source['image_repository'][0]
    observed = actual['ImageRepository']
    return [
        ('Image identifier matches', observed.get('ImageIdentifier') == image['image_identifier'], observed.get('ImageIdentifier')),
        ('Image repository type matches', observed.get('ImageRepositoryType') == image['image_repository_type'], observed.get('ImageRepositoryType')),
        ('Automatic deployment setting matches', actual.get('AutoDeploymentsEnabled') == source['auto_deployments_enabled'], actual.get('AutoDeploymentsEnabled')),
        ('Image port matches', observed.get('ImageConfiguration', {}).get('Port', '8080') == (image.get('image_configuration') or [{}])[0].get('port', '8080'), observed.get('ImageConfiguration')),
    ]


def _bedrock_guardrail(client, v):
    actual = client('bedrock').get_guardrail(guardrailIdentifier=v['guardrail_id'], guardrailVersion='DRAFT')
    wanted = sorted((f['type'], f['input_strength'], f['output_strength']) for policy in v.get('content_policy_config', []) for f in policy.get('filters_config', []))
    filters = sorted((f['type'], f['inputStrength'], f['outputStrength']) for f in actual.get('contentPolicy', {}).get('filters', []))
    return [
        ('Guardrail name matches', actual.get('name') == v['name'], actual.get('name')),
        ('Blocked input message matches', actual.get('blockedInputMessaging') == v['blocked_input_messaging'], actual.get('blockedInputMessaging')),
        ('Blocked output message matches', actual.get('blockedOutputsMessaging') == v['blocked_outputs_messaging'], actual.get('blockedOutputsMessaging')),
        ('Content filter categories and strengths match', filters == wanted, filters),
    ]


def _knowledge_base(client, v):
    actual = client('bedrock-agent').get_knowledge_base(knowledgeBaseId=v['id'])['knowledgeBase']
    config = v['knowledge_base_configuration'][0]
    vector = config['vector_knowledge_base_configuration'][0]
    storage = v['storage_configuration'][0]
    target = storage['opensearch_serverless_configuration'][0]
    mapping = target['field_mapping'][0]
    observed = actual.get('storageConfiguration', {}).get('opensearchServerlessConfiguration', {})
    expected_mapping = {key: mapping[value] for key, value in [('vectorField', 'vector_field'), ('textField', 'text_field'), ('metadataField', 'metadata_field')]}
    return [
        ('Knowledge base name matches', actual.get('name') == v['name'], actual.get('name')),
        ('Knowledge base role matches', actual.get('roleArn') == v['role_arn'], actual.get('roleArn')),
        ('Knowledge base type matches', actual.get('knowledgeBaseConfiguration', {}).get('type') == config['type'], actual.get('knowledgeBaseConfiguration')),
        ('Embedding model matches', actual.get('knowledgeBaseConfiguration', {}).get('vectorKnowledgeBaseConfiguration', {}).get('embeddingModelArn') == vector['embedding_model_arn'], actual.get('knowledgeBaseConfiguration')),
        ('Storage type matches', actual.get('storageConfiguration', {}).get('type') == storage['type'], actual.get('storageConfiguration')),
        ('Collection ARN matches', observed.get('collectionArn') == target['collection_arn'], observed.get('collectionArn')),
        ('Vector index name matches', observed.get('vectorIndexName') == target['vector_index_name'], observed.get('vectorIndexName')),
        ('Vector field mapping matches', observed.get('fieldMapping') == expected_mapping, observed.get('fieldMapping')),
    ]


AWS_VERIFIERS = {
    'aws_opensearchserverless_collection': _listed('opensearchserverless', 'batch_get_collection', 'ids', 'id', 'collectionDetails', 'id'),
    'aws_apprunner_service': _apprunner_service,
    'aws_bedrockagent_knowledge_base': _knowledge_base,
    'aws_bedrock_guardrail': _bedrock_guardrail,
    'aws_db_parameter_group': _rds_parameters,
    'aws_cloudfront_distribution': _cloudfront_distribution,
    'aws_s3_bucket': _exists('s3', 'head_bucket', 'Bucket', 'bucket'),
    'aws_s3_bucket_versioning': _s3_versioning,
    'aws_s3_bucket_public_access_block': _s3_public_access,
    'aws_s3_bucket_server_side_encryption_configuration': _s3_encryption,
    'aws_s3_bucket_policy': lambda client, v: [('Bucket policy matches', same_json(client('s3').get_bucket_policy(Bucket=v['bucket'])['Policy'], v['policy']), 'policy differs')],
    'aws_s3_object': _s3_object,
    'aws_sqs_queue': _sqs_queue,
    'aws_dynamodb_table': _dynamodb_table,
    'aws_iam_role': _iam_role,
    'aws_iam_role_policy': _iam_role_policy,
    'aws_iam_policy': _exists('iam', 'get_policy', 'PolicyArn', 'arn'),
    'aws_lambda_function': _lambda_function,
    'aws_lambda_alias': lambda client, v: [('Alias points at the recorded version', client('lambda').get_alias(FunctionName=v['function_name'], Name=v['name'])['FunctionVersion'] == v.get('function_version'), 'version differs')],
    'aws_lambda_event_source_mapping': _event_source_mapping,
    'aws_cloudwatch_log_group': _log_group,
    'aws_kms_key': _exists('kms', 'describe_key', 'KeyId', 'key_id'),
    'aws_sns_topic': _exists('sns', 'get_topic_attributes', 'TopicArn', 'arn'),
    'aws_secretsmanager_secret': _exists('secretsmanager', 'describe_secret', 'SecretId', 'arn'),
    'aws_ssm_parameter': _exists('ssm', 'get_parameter', 'Name', 'name'),
    'aws_vpc': _listed('ec2', 'describe_vpcs', 'VpcIds', 'id', 'Vpcs', 'VpcId'),
    'aws_subnet': _listed('ec2', 'describe_subnets', 'SubnetIds', 'id', 'Subnets', 'SubnetId'),
    'aws_security_group': _listed('ec2', 'describe_security_groups', 'GroupIds', 'id', 'SecurityGroups', 'GroupId'),
    'aws_ecr_repository': _listed('ecr', 'describe_repositories', 'repositoryNames', 'name', 'repositories', 'repositoryName'),
    'aws_ecs_cluster': _listed('ecs', 'describe_clusters', 'clusters', 'arn', 'clusters', 'clusterArn'),
    'aws_cloudwatch_event_rule': _exists('events', 'describe_rule', 'Name', 'name'),
    'aws_apigatewayv2_api': _exists('apigatewayv2', 'get_api', 'ApiId', 'id'),
    'aws_cognito_user_pool': _exists('cognito-idp', 'describe_user_pool', 'UserPoolId', 'id'),
    'aws_sfn_state_machine': _exists('stepfunctions', 'describe_state_machine', 'stateMachineArn', 'arn'),
    'aws_kinesis_stream': _exists('kinesis', 'describe_stream_summary', 'StreamName', 'name'),
}

BACKENDS = {'aws': MotoAwsBackend}
PLANNED_FAMILIES = {
    'azure': 'Azure Terraform apply emulation is not implemented yet. Schema and mock-plan checks remain available.',
    'gcp': 'Google Cloud Terraform apply emulation is not implemented yet. Schema and mock-plan checks remain available.',
    'ibm': 'IBM Cloud Terraform apply emulation is not implemented yet. Schema and mock-plan checks remain available.',
}


# ------------------------------------------------------------ configuration

def read_configuration(folder):
    """Provider sources, root variables and backend blocks of the root module."""
    sources, variables, has_backend = set(), {}, False
    for path in sorted(Path(folder).glob('*.tf.json')):
        document = json.loads(path.read_text())
        blocks = document.get('terraform', {})
        for block in blocks if isinstance(blocks, list) else [blocks]:
            for provider in (block.get('required_providers') or {}).values():
                if isinstance(provider, dict) and provider.get('source'):
                    sources.add(provider['source'].lower().removeprefix('registry.terraform.io/'))
            has_backend = has_backend or 'backend' in block or 'cloud' in block
        declared = document.get('variable', {})
        for name, declaration in declared.items():
            variables[name] = declaration[0] if isinstance(declaration, list) else declaration
        for name in document.get('provider', {}):
            sources.add('hashicorp/' + name)
    for path in sorted(Path(folder).glob('*.tf')):
        text = re.sub(r'(?m)(#|//).*$', '', path.read_text())
        for source in re.findall(r'source\s*=\s*"([\w.-]+/[\w.-]+(?:/[\w.-]+)?)"', text):
            if not source.startswith(('.', 'git')) and source.count('/') <= 2:
                sources.add(source.lower().removeprefix('registry.terraform.io/'))
        for name in re.findall(r'(?m)^\s*provider\s+"([a-z0-9_-]+)"', text):
            sources.add('hashicorp/' + name)
        has_backend = has_backend or bool(re.search(r'(?m)^\s*(backend\s+"[a-z0-9]+"|cloud)\s*\{', text))
        for match in re.finditer(r'(?m)^\s*variable\s+"([^"]+)"\s*\{', text):
            depth, index = 1, match.end()
            while depth and index < len(text):
                depth += {'{': 1, '}': -1}.get(text[index], 0)
                index += 1
            body = text[match.end():index]
            variables[match[1]] = {'default': None} if re.search(r'(?m)^\s*default\s*=', body) else {}
    return sources, variables, has_backend


def read_test_variables(folder):
    """Qualification inputs the module declares for its own `terraform test` runs."""
    values = {}
    for path in sorted(Path(folder).glob('tests/*.tftest.hcl')):
        text = re.sub(r'(?m)^\s*(#|//).*$', '', path.read_text())
        block = re.search(r'(?ms)^variables\s*\{\n(.*?)^\}', text)
        for name, literal in re.findall(r'(?m)^\s*(\w+)\s*=\s*(.+?)\s*$', block[1] if block else ''):
            try:
                values.setdefault(name, json.loads(literal))
            except ValueError:
                continue  # an expression, not a literal: never guessed
    return values


def file_digests(folder):
    digests = {}
    for path in sorted(Path(folder).rglob('*')):
        relative = path.relative_to(folder)
        if path.is_file() and not path.is_symlink() and relative.parts[0] not in ('.terraform', '.git', 'build') and '__pycache__' not in relative.parts and not relative.name.endswith(('.tfstate', '.tfstate.backup')):
            digests[relative.as_posix()] = sha256(path.read_bytes())
    return digests


# ------------------------------------------------------------------- engine

class Run:
    def __init__(self, folder, terraform, provider_cache, backend, progress):
        self.folder = folder
        self.terraform = terraform
        self.backend = backend
        self.progress = progress
        self.timeout = COMMAND_TIMEOUT
        self.stages = []
        self.timeline = []
        self.resource_events = []
        # Sibling of the module directory; short so provider plugin sockets fit.
        home = Path(folder).parent / 'home'
        home.mkdir()
        # No inherited credentials, profiles or proxies. Plain-HTTP calls to any
        # other host (for example account-prefixed S3 Control names) are proxied
        # to the emulator; HTTPS to any real endpoint hits a closed port and fails.
        self.env = {
            'PATH': os.getenv('PATH', ''), 'HOME': str(home), 'TMPDIR': str(home),
            'TF_IN_AUTOMATION': '1', 'CHECKPOINT_DISABLE': '1', 'TF_INPUT': '0',
            'HTTP_PROXY': backend.endpoint, 'HTTPS_PROXY': 'http://127.0.0.1:9', 'NO_PROXY': '127.0.0.1,localhost',
            **backend.environment(home),
        }
        if provider_cache and Path(provider_cache).is_dir():
            config = home / 'provider-mirror.tfrc'
            config.write_text('provider_installation { filesystem_mirror { path = ' + json.dumps(str(Path(provider_cache).resolve())) + ' } }\n')
            self.env['TF_CLI_CONFIG_FILE'] = str(config)
            self.provider_source = 'local mirror'
        else:
            self.provider_source = 'registry download'

    def command_environment(self, arguments):
        environment = dict(self.env)
        # Registry access belongs only to init. Every plan/apply/refresh/destroy
        # keeps loopback proxying, including account-prefixed S3 Control hosts.
        if arguments and arguments[0] == 'init' and self.provider_source == 'registry download':
            for name in ('HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY'):
                environment.pop(name, None)
        return environment

    def command(self, *arguments, timeout=None, on_line=None):
        self.backend.log.recording = True
        limit = timeout or self.timeout
        command = [self.terraform, f'-chdir={self.folder}', *arguments]
        # Own process group: at the limit Terraform and its provider plugin die
        # together, so no orphan keeps the output pipes open.
        process = subprocess.Popen(command, env=self.command_environment(arguments), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        output, errors = [], []

        def read_output():
            for line in process.stdout:
                output.append(line)
                if on_line:
                    try:
                        on_line(line)
                    except Exception:  # live progress must never change the result
                        pass
        readers = [threading.Thread(target=read_output, daemon=True), threading.Thread(target=lambda: errors.extend(process.stderr), daemon=True)]
        for reader in readers:
            reader.start()
        try:
            code = process.wait(timeout=limit)
            message = None
        except subprocess.TimeoutExpired:
            stop_process_tree(process)
            # Keep what Terraform reported so far; the stage fails and teardown still runs.
            code, message = TIMED_OUT, f'Terraform {arguments[0]} reached the {limit}s time limit.'
        for reader in readers:
            reader.join(timeout=20)
        return subprocess.CompletedProcess(command, code, ''.join(output), message or ''.join(errors))

    def resource_progress(self, components):
        """Live per-resource events from Terraform's JSON stream, for diagram animation."""
        states = {('apply_start', 'create'): 'creating', ('apply_start', 'update'): 'creating', ('apply_complete', 'create'): 'applied', ('apply_complete', 'update'): 'applied',
                  ('apply_start', 'delete'): 'destroying', ('apply_complete', 'delete'): 'destroyed'}

        def on_line(line):
            event = json.loads(line)
            kind = event.get('type')
            if kind not in ('apply_start', 'apply_complete', 'apply_errored'):
                return
            resource = event['hook']['resource']
            state = 'failed' if kind == 'apply_errored' else states.get((kind, event['hook'].get('action')))
            if state:
                self.progress({'resource': resource['addr'], 'resourceType': resource.get('resource_type'), 'state': state, 'apiCalls': len(self.backend.log.calls), **({'component': components[resource['addr']]} if components.get(resource['addr']) else {})})
        return on_line

    def stage(self, name, status, started, output='', **extra):
        entry = {'name': name, 'status': status, 'seconds': round(time.monotonic() - started, 1), **extra}
        self.timeline.append({'name': name, 'status': status, 'start': round(started - self.backend.log.started, 2), 'end': round(time.monotonic() - self.backend.log.started, 2)})
        if output and status != 'passed':
            entry['output'] = tail(output)
        self.stages.append(entry)
        self.progress({'stage': name, 'status': status, 'seconds': entry['seconds']})
        return status == 'passed'

    def step(self, name, *arguments, ok=(0,)):
        self.progress({'stage': name, 'status': 'running'})
        started = time.monotonic()
        result = self.command(*arguments)
        self.stage(name, 'passed' if result.returncode in ok else 'failed', started, result.stdout + '\n' + result.stderr)
        return result


def resource_events(stream, offset):
    """Per-resource start/finish times from Terraform's machine-readable stream."""
    import datetime
    events, first = [], None
    for line in stream.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if '@timestamp' not in event:
            continue
        moment = datetime.datetime.fromisoformat(event['@timestamp']).timestamp()
        first = moment if first is None else first
        if event.get('type') in ('apply_start', 'apply_complete', 'apply_errored'):
            events.append({'t': round(offset + moment - first, 2), 'event': event['type'], 'address': event['hook']['resource']['addr'], 'action': event['hook'].get('action')})
    return events


def diagnostics(stream):
    """Errors from Terraform's machine-readable stream, with resource addresses."""
    errors, completed = [], []
    for line in stream.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('type') == 'diagnostic' and event['diagnostic'].get('severity') == 'error':
            diagnostic = event['diagnostic']
            errors.append({'address': diagnostic.get('address'), 'summary': diagnostic.get('summary', '')[:500], 'detail': diagnostic.get('detail', '')[:1500]})
        elif event.get('type') == 'apply_complete':
            completed.append((event['hook']['resource']['addr'], event['hook']['action']))
    return errors, completed


def is_emulator_gap(error):
    text = (error.get('summary', '') + ' ' + error.get('detail', ''))
    return bool(re.search(r'EmulatorNotImplemented|EmulatorInternalError|not been implemented', text))


def state_resources(run):
    shown = run.command('show', '-json')
    if shown.returncode:
        return []
    found = []

    def walk(module):
        for resource in module.get('resources', []):
            if resource.get('mode') == 'managed':
                found.append({'address': resource['address'], 'type': resource['type'], 'values': resource.get('values') or {}})
        for child in module.get('child_modules', []):
            walk(child)
    walk(json.loads(shown.stdout).get('values', {}).get('root_module', {}))
    return found


def emulate_directory(source, terraform, provider_cache=None, inputs=None, progress=lambda event: None, workspace=None, trace=None, timeout=COMMAND_TIMEOUT):
    """Run the lifecycle on a private copy of `source`. Returns the report."""
    source = Path(source)
    started = time.monotonic()
    report = {'version': REPORT_VERSION, 'kind': 'terraform-apply-emulation', 'cloudOperations': False, 'terraformApply': 'not_run', 'stages': [], 'resources': [], 'boundaries': BOUNDARIES}
    digests = file_digests(source)
    report['fileDigests'] = digests
    report['artifactDigest'] = sha256(json.dumps(digests, sort_keys=True, separators=(',', ':')).encode())
    sources, variables, has_backend = read_configuration(source)
    families = sorted({PROVIDER_FAMILIES[s] for s in sources if s in PROVIDER_FAMILIES})
    unknown = sorted(s for s in sources if s not in PROVIDER_FAMILIES and s not in LOCAL_PROVIDERS)
    report['providers'] = sorted(sources)
    if not families:
        return {**report, 'status': 'unavailable', 'message': 'No supported cloud provider is declared in this Terraform directory.'}
    if len(families) > 1 or unknown:
        return {**report, 'status': 'unavailable', 'message': 'This configuration uses providers without an emulator backend: ' + ', '.join(unknown or families) + '.'}
    family = families[0]
    report['provider'] = family
    if family not in BACKENDS:
        return {**report, 'status': 'unavailable', 'message': PLANNED_FAMILIES[family]}
    missing = BACKENDS[family].availability()
    if missing:
        return {**report, 'status': 'unavailable', 'message': missing}
    backend = BACKENDS[family]()
    report['backend'] = backend.describe()

    # Provider plugins open Unix sockets under TMPDIR; keep the path short.
    short = os.getenv('ATMEM_EMULATOR_SCRATCH_ROOT') or ('/tmp' if os.name == 'posix' and Path('/tmp').is_dir() else None)
    folder = Path(workspace or tempfile.mkdtemp(prefix='tfe-', dir=short))
    target = folder / 'w'
    shutil.copytree(source, target, ignore=shutil.ignore_patterns('.terraform', '*.tfstate', '*.tfstate.backup', '.git'))
    # Immutable inputs may be root-owned/read-only in the sandbox. Only this
    # disposable copy needs writable directories; source bytes stay unchanged.
    for directory in [target,*(path for path in target.rglob('*') if path.is_dir())]:
        directory.chmod(0o700)
    declared = {name: value for name, value in read_test_variables(source).items() if name in variables and 'default' not in variables[name]}
    values = {**declared, **backend.synthetic_inputs(variables), **(inputs or {})}
    required = sorted(name for name, declaration in variables.items() if 'default' not in declaration and name not in values)
    if required:
        shutil.rmtree(folder, ignore_errors=True)
        return {**report, 'status': 'blocked', 'message': 'Supply values for required inputs before emulation.', 'missingInputs': required}
    (target / 'atmem-emulator.auto.tfvars.json').write_text(json.dumps({name: value for name, value in values.items() if name in variables}, indent=1))
    additions = ['atmem-emulator.auto.tfvars.json']
    if has_backend:
        # Remote state is replaced by local state inside the private workspace.
        (target / 'atmem_emulator_override.tf.json').write_text(json.dumps({'terraform': {'backend': {'local': {}}}}))
        additions.append('atmem_emulator_override.tf.json')
    report['workspaceAdditions'] = additions
    synthetic = backend.synthetic_inputs(variables)
    report['inputs'] = {name: 'supplied' if name in (inputs or {}) else 'synthetic' if name in synthetic else 'module-test' for name in values if name in variables}

    run = None
    try:
        backend.start()
        run = Run(target, terraform, provider_cache, backend, progress)
        run.timeout = timeout
        report['stages'] = run.stages
        version = json.loads(run.command('version', '-json').stdout)
        report['terraform'] = {'version': version.get('terraform_version'), 'providerSource': run.provider_source}
        outcome = lifecycle(run, backend, report, values)
        if trace is not None:
            trace.update(stages=run.timeline, resourceEvents=run.resource_events, apiCalls=backend.log.timeline())
    except subprocess.TimeoutExpired as error:
        outcome = ('failed', f'Terraform {error.cmd[2] if len(error.cmd) > 2 else ""} exceeded its time limit. No pass was recorded.')
    finally:
        if backend.log:
            report['apiCalls'] = backend.log.summary()
        backend.stop()
        shutil.rmtree(folder, ignore_errors=True)
    report['status'], report['message'] = outcome
    report['workspaceCleanup'] = 'passed' if not folder.exists() else 'failed'
    report['seconds'] = round(time.monotonic() - started, 1)
    return report


def lifecycle(run, backend, report, values):
    target = run.folder
    if (target / 'build-runtime.py').is_file():
        # Deterministic application archives referenced by the configuration.
        run.progress({'stage': 'Application build', 'status': 'running'})
        started = time.monotonic()
        build_env = {'PATH': os.getenv('PATH', ''), 'HOME': run.env['HOME'], 'TMPDIR': run.env['TMPDIR']}
        if os.getenv('ATMEM_EMULATOR_WHEELHOUSE'):
            build_env['ATMEM_BUILD_WHEELHOUSE']=os.environ['ATMEM_EMULATOR_WHEELHOUSE']
        built = subprocess.run([os.getenv('ATMEM_EMULATOR_BUILD_PYTHON') or sys.executable, '-I', 'build-runtime.py'], cwd=target, env=build_env, capture_output=True, text=True, timeout=COMMAND_TIMEOUT)
        if not run.stage('Application build', 'passed' if built.returncode == 0 else 'failed', started, built.stdout + '\n' + built.stderr):
            return 'failed', 'The application build failed before Terraform ran.'
        observed=file_digests(target)
        changed=[name for name,digest in report['fileDigests'].items() if observed.get(name)!=digest]
        changed+=sorted(set(observed)-set(report['fileDigests'])-set(report.get('workspaceAdditions',[])))
        if changed:
            run.stage('Artifact integrity','failed',time.monotonic(),'Build changed source inputs: '+', '.join(changed[:20]))
            return 'failed','The application build changed source inputs. No Terraform operation was run.'
    if run.step('Provider initialization', 'init', '-input=false', '-no-color').returncode:
        return 'failed', 'Terraform could not initialize the providers.'
    providers = json.loads(run.command('version', '-json').stdout).get('provider_selections', {})
    report['terraform']['providers'] = providers
    if run.step('Schema validation', 'validate', '-no-color').returncode:
        return 'failed', 'Terraform validation failed.'

    backend.seed(values)
    report['seededFixtures'] = list(backend.seeded)
    baseline = backend.remaining_resources()
    if baseline:
        return 'failed', 'The emulator did not start empty; no result was recorded.'

    planned = run.step('Plan', 'plan', '-input=false', '-no-color', '-out=emulator.tfplan')
    if planned.returncode:
        gaps = backend.log.summary()['notImplemented']
        if gaps and re.search(r'EmulatorNotImplemented|EmulatorInternalError', planned.stdout + planned.stderr):
            report['emulatorGaps'] = {'resourceTypes': [], 'operations': gaps}
            return 'unsupported', 'The emulator does not implement an API the provider needs while planning. This is not a pass.'
        return 'failed', 'Terraform could not plan against the emulator.'
    plan = json.loads(run.command('show', '-json', 'emulator.tfplan').stdout)
    resources = {}
    for change in plan.get('resource_changes', []):
        if change.get('mode') == 'managed' and change['change']['actions'] != ['no-op']:
            resources[change['address']] = {'address': change['address'], 'type': change['type'], 'planned': '/'.join(change['change']['actions']), 'applied': False}
            # A `Component` tag names the design block a resource belongs to.
            component = ((change['change'].get('after') or {}).get('tags') or {}).get('Component')
            if isinstance(component, str):
                resources[change['address']]['component'] = component
    report['resources'] = list(resources.values())
    if not resources:
        return 'failed', 'The plan contains no managed resources to emulate.'

    run.progress({'stage': 'Apply', 'status': 'running', 'resources': len(resources)})
    started = time.monotonic()
    components = {address: entry.get('component') for address, entry in resources.items()}
    run.progress({'planned': [{'resource': address, 'resourceType': entry['type'], **({'component': entry['component']} if entry.get('component') else {})} for address, entry in resources.items()]})
    applied = run.command('apply', '-input=false', '-json', 'emulator.tfplan', on_line=run.resource_progress(components))
    run.resource_events += resource_events(applied.stdout, started - backend.log.started)
    report['terraformApply'] = 'emulated'
    errors, _ = diagnostics(applied.stdout)
    state = state_resources(run)
    in_state = {resource['address'] for resource in state}
    for address, entry in resources.items():
        entry['applied'] = address in in_state
    for error in errors:
        entry = resources.get(error.get('address') or '')
        if entry:
            entry['error'] = error['summary'] + (': ' + error['detail'] if error['detail'] else '')
            entry['emulatorGap'] = is_emulator_gap(error)
    timed_out = applied.returncode == TIMED_OUT
    if timed_out:
        finished = {event['address'] for event in run.resource_events if event['event'] != 'apply_start'}
        for event in run.resource_events:
            entry = resources.get(event['address'])
            if entry and event['event'] == 'apply_start' and event['address'] not in finished:
                entry.update(error=f'Terraform was still creating at the {run.timeout}s execution deadline; provider waits and emulator readiness remain unproven.', emulatorGap=False, timedOut=True)
    apply_ok = applied.returncode == 0 and all(entry['applied'] for entry in resources.values())
    run.stage('Apply', 'passed' if apply_ok else 'failed', started, ('\n'.join(json.dumps(error) for error in errors) + '\n' + applied.stderr[-6000:]).strip(), applied=sum(entry['applied'] for entry in resources.values()), planned=len(resources))

    verified_ok = True
    if state:
        run.progress({'stage': 'Independent API read-back', 'status': 'running'})
        started = time.monotonic()
        counted = 0
        for resource in state:
            checks = backend.verify(resource)
            entry = resources.setdefault(resource['address'], {'address': resource['address'], 'type': resource['type'], 'planned': 'create', 'applied': True})
            if checks is None:
                entry['readBack'] = 'provider-refresh-only'
                continue
            counted += 1
            entry['readBack'] = 'sdk'
            entry['checks'] = checks
            run.progress({'resource': resource['address'], 'resourceType': resource['type'], 'state': 'verified' if all(check['passed'] for check in checks) else 'failed', **({'component': entry['component']} if entry.get('component') else {})})
            verified_ok = verified_ok and all(check['passed'] for check in checks)
        failed_checks = [f"{entry['address']}: {check['name']} ({check.get('detail', '')})" for entry in resources.values() for check in entry.get('checks', []) if not check['passed']]
        run.stage('Independent API read-back', 'passed' if verified_ok else 'failed', started, '\n'.join(failed_checks), sdkVerified=counted, providerRefreshOnly=len(state) - counted)

    converged = False
    if apply_ok:
        # Exit code 0 means a full provider refresh found nothing to change.
        result = run.step('Convergence plan', 'plan', '-input=false', '-no-color', '-detailed-exitcode')
        converged = result.returncode == 0
        if result.returncode == 2:
            run.stages[-1]['drift'] = re.findall(r'(?m)^\s*# (\S+) (?:will be|must be) .*$', result.stdout)[:50]

    protected = lift_destroy_protection(run, report)
    if protected is None:
        return 'failed', 'Protected resources inside child modules cannot be torn down by the emulator.'
    run.progress({'stage': 'Destroy', 'status': 'running'})
    started = time.monotonic()
    destroyed = run.command('destroy', '-input=false', '-json', '-auto-approve', on_line=run.resource_progress(components))
    run.resource_events += resource_events(destroyed.stdout, started - backend.log.started)
    destroy_errors, _ = diagnostics(destroyed.stdout)
    run.stage('Destroy', 'passed' if destroyed.returncode == 0 else 'failed', started, '\n'.join(json.dumps(error) for error in destroy_errors) or destroyed.stderr)
    started = time.monotonic()
    remaining = backend.remaining_resources() if destroyed.returncode == 0 else []
    leak_ok = destroyed.returncode == 0 and not remaining
    run.stage('Leak check', 'passed' if leak_ok else 'failed', started, '\n'.join(remaining) or 'Destroy did not complete.', remaining=remaining[:50])
    report['resources'] = list(resources.values())

    types = collections.defaultdict(lambda: {'planned': 0, 'applied': 0, 'sdkVerified': 0})
    for entry in resources.values():
        bucket = types[entry['type']]
        bucket['planned'] += 1
        bucket['applied'] += bool(entry['applied'])
        bucket['sdkVerified'] += bool(entry.get('checks')) and all(check['passed'] for check in entry['checks'])
    report['resourceTypes'] = dict(sorted(types.items()))
    gaps = sorted({entry['type'] for entry in resources.values() if entry.get('emulatorGap')})
    api_gaps = backend.log.summary()['notImplemented']
    if not apply_ok:
        failing = [entry for entry in resources.values() if entry.get('error')]
        if (failing and all(entry.get('emulatorGap') for entry in failing)) or (not failing and api_gaps):
            report['emulatorGaps'] = {'resourceTypes': gaps, 'operations': api_gaps}
            if timed_out:
                return 'unsupported', 'Some resources never became ready on the emulator within the time limit. This is not a pass.'
            return 'unsupported', 'The emulator does not implement some required API operations. This is not a pass or a configuration failure.'
        if timed_out:
            return 'blocked', 'Execution deadline reached; provider wait versus emulator readiness is unproven. Teardown results remain separate.'
        return 'failed', 'Terraform apply failed against the emulator. Review the resource errors.'
    if not verified_ok:
        return 'failed', 'Applied resources do not match an independent API read-back.'
    if not converged:
        return 'failed', 'A second plan still proposes changes; the configuration does not converge on the emulator.'
    if not leak_ok:
        if destroyed.returncode and destroy_errors and all(is_emulator_gap(error) for error in destroy_errors):
            report['emulatorGaps'] = {'resourceTypes': sorted({(error.get('address') or '').split('.')[0] for error in destroy_errors} - {''}), 'operations': api_gaps}
            return 'unsupported', 'The emulator cannot delete some resources. Apply and convergence passed; teardown is unproven.'
        return 'failed', 'Destroy left resources behind in the emulator.'
    return 'passed', 'Apply, independent read-back, convergence and destroy passed on the local emulator. No cloud account was used.'


def lift_destroy_protection(run, report):
    """Prove lifecycle.prevent_destroy blocks a destroy, then lift it in the private copy only."""
    run.progress({'stage': 'Destroy protection', 'status': 'running'})
    started = time.monotonic()
    probe = run.command('plan', '-destroy', '-input=false', '-no-color', '-refresh=false')
    addresses = sorted(set(re.findall(r'Resource (\S+) has\s+lifecycle\.prevent_destroy', probe.stdout + probe.stderr)))
    if not addresses:
        return []
    overrides = {}
    for address in addresses:
        parts = address.split('.')
        if len(parts) != 2:
            run.stage('Destroy protection', 'failed', started, 'Protected resource in a child module: ' + address)
            return None
        overrides.setdefault(parts[0], {})[parts[1]] = {'lifecycle': {'prevent_destroy': False}}
    (run.folder / 'atmem_emulator_teardown_override.tf.json').write_text(json.dumps({'resource': overrides}))
    report['workspaceAdditions'].append('atmem_emulator_teardown_override.tf.json')
    run.stage('Destroy protection', 'passed', started, protectedResources=addresses)
    return addresses


def find_terraform(root):
    configured = os.getenv('ATMEM_ARCHITECT_TERRAFORM_BIN')
    return configured or shutil.which('terraform', path=str(root / '.venv' / 'bin') + os.pathsep + os.getenv('PATH', ''))


def main(argv=None):
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description='Run the Terraform lifecycle against a local cloud emulator.')
    parser.add_argument('--dir', required=True, help='Terraform root module directory')
    parser.add_argument('--var-file', help='JSON file with input variable values')
    parser.add_argument('--report', help='Write the JSON report to this file instead of stdout')
    parser.add_argument('--provider-cache', default=os.getenv('ATMEM_ARCHITECT_PROVIDER_CACHE') or str(root / '.local/provider-cache'))
    parser.add_argument('--progress', action='store_true', help='Print stage progress as JSON lines on stderr')
    parser.add_argument('--trace', help='Write a timeline of stages, resource events and API calls to this file')
    parser.add_argument('--timeout', type=int, default=COMMAND_TIMEOUT, help='Time limit in seconds for each Terraform command')
    options = parser.parse_args(argv)
    terraform = find_terraform(root)
    if not terraform:
        report = {'version': REPORT_VERSION, 'status': 'unavailable', 'stages': [], 'message': 'Terraform is not installed. Install Terraform 1.7+ or set ATMEM_ARCHITECT_TERRAFORM_BIN.'}
    else:
        inputs = json.loads(Path(options.var_file).read_text()) if options.var_file else None
        progress = (lambda event: print(json.dumps(event), file=sys.stderr, flush=True)) if options.progress else (lambda event: None)
        trace = {} if options.trace else None
        report = emulate_directory(options.dir, terraform, options.provider_cache, inputs, progress, trace=trace, timeout=options.timeout)
        if options.trace:
            Path(options.trace).write_text(json.dumps({'report': report, **trace}) + '\n')
    text = json.dumps(report, indent=1) + '\n'
    if options.report:
        Path(options.report).write_text(text)
    else:
        sys.stdout.write(text)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
