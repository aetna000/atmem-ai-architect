import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from server import terraform_emulator as emulator
from server.app import app, TOKEN
from server.terraform_emulation_routes import TerraformEmulationRequest, emulate_terraform, runtime_python

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / 'tests/terraform-emulator/aws'
TERRAFORM = emulator.find_terraform(ROOT)
CACHE = os.getenv('ATMEM_ARCHITECT_PROVIDER_CACHE') or str(ROOT / '.local/provider-cache')
READY = runtime_python().is_file() and bool(TERRAFORM)


def write(folder, name, text):
    path = Path(folder) / name
    path.write_text(text)
    return path


class ConfigurationTests(unittest.TestCase):
    def test_reads_hcl_and_json_providers_variables_and_backend(self):
        with tempfile.TemporaryDirectory() as folder:
            write(folder, 'main.tf', 'terraform {\n  backend "s3" {}\n  required_providers {\n    aws = {\n      source = "hashicorp/aws"\n    }\n  }\n}\nvariable "name" {\n  type = string\n}\nvariable "size" {\n  default = 1\n}\n# variable "commented" {}\n')
            write(folder, 'extra.tf.json', json.dumps({'variable': {'aws_account_id': {'type': 'string'}}}))
            sources, variables, backend = emulator.read_configuration(folder)
        self.assertEqual(sources, {'hashicorp/aws'})
        self.assertTrue(backend)
        self.assertNotIn('default', variables['name'])
        self.assertIn('default', variables['size'])
        self.assertNotIn('commented', variables)
        self.assertIn('aws_account_id', variables)

    def test_synthetic_inputs_open_the_review_gate_but_keep_other_defaults(self):
        values = emulator.MotoAwsBackend().synthetic_inputs({
            'review_approved': {'default': False}, 'aws_account_id': {}, 'aws_region': {},
            'principal_block_ab_arn': {}, 'memory_mb': {'default': 256}, 'customer_name': {},
        })
        self.assertIs(values['review_approved'], True)
        self.assertEqual(values['aws_account_id'], emulator.ACCOUNT_ID)
        self.assertRegex(values['principal_block_ab_arn'], r'^arn:aws:iam::123456789012:role/emulated/')
        self.assertNotIn('memory_mb', values)
        self.assertNotIn('customer_name', values)

    def test_module_test_variables_supply_literals_only(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'tests').mkdir()
            write(Path(folder) / 'tests', 'a.tftest.hcl', '# mock only\nmock_provider "aws" {}\nvariables {\n  model_id = "amazon.nova-micro-v1:0"\n  topics = ["a"]\n  count = 2\n  derived = var.other\n}\nrun "x" {\n  command = plan\n  variables { model_id = "ignored" }\n}\n')
            self.assertEqual(emulator.read_test_variables(folder), {'model_id': 'amazon.nova-micro-v1:0', 'topics': ['a'], 'count': 2})

    def test_unknown_required_input_blocks_instead_of_guessing(self):
        with tempfile.TemporaryDirectory() as folder:
            write(folder, 'main.tf', 'terraform {\n  required_providers {\n    aws = {\n      source = "hashicorp/aws"\n    }\n  }\n}\nvariable "customer_name" {\n  type = string\n}\n')
            with patch.object(emulator.MotoAwsBackend, 'availability', staticmethod(lambda: None)), patch.object(emulator.MotoAwsBackend, 'describe', lambda self: {}):
                report = emulator.emulate_directory(folder, 'terraform-not-run')
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(report['missingInputs'], ['customer_name'])
        self.assertEqual(report['terraformApply'], 'not_run')

    def test_other_clouds_are_unavailable_never_passed(self):
        for source, family in [('hashicorp/azurerm', 'azure'), ('hashicorp/google', 'gcp'), ('IBM-Cloud/ibm', 'ibm')]:
            with tempfile.TemporaryDirectory() as folder:
                write(folder, 'main.tf', 'terraform {\n  required_providers {\n    cloud = {\n      source = "%s"\n    }\n  }\n}\n' % source)
                report = emulator.emulate_directory(folder, 'terraform-not-run')
            self.assertEqual((report['status'], report['provider']), ('unavailable', family))
            self.assertEqual(report['terraformApply'], 'not_run')
        with tempfile.TemporaryDirectory() as folder:
            write(folder, 'main.tf', 'resource "terraform_data" "x" {}\n')
            self.assertEqual(emulator.emulate_directory(folder, 'terraform-not-run')['status'], 'unavailable')

    def test_mixed_or_unknown_providers_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            write(folder, 'main.tf', 'terraform {\n  required_providers {\n    aws = {\n      source = "hashicorp/aws"\n    }\n    dog = {\n      source = "datadog/datadog"\n    }\n  }\n}\n')
            report = emulator.emulate_directory(folder, 'terraform-not-run')
        self.assertEqual(report['status'], 'unavailable')
        self.assertIn('datadog/datadog', report['message'])

    def test_digests_ignore_state_and_plugin_directories(self):
        with tempfile.TemporaryDirectory() as folder:
            write(folder, 'main.tf', 'x')
            write(folder, 'terraform.tfstate', '{}')
            (Path(folder) / '.terraform').mkdir()
            write(Path(folder) / '.terraform', 'plugin', 'binary')
            self.assertEqual(list(emulator.file_digests(folder)), ['main.tf'])


class RequestLogTests(unittest.TestCase):
    def call(self, app, **environ):
        log = emulator.RequestLog(app)
        body = environ.pop('body', b'')
        base = {'PATH_INFO': '/', 'REQUEST_METHOD': 'POST', 'QUERY_STRING': '', 'CONTENT_LENGTH': str(len(body)), 'wsgi.input': io.BytesIO(body),
                'HTTP_AUTHORIZATION': 'AWS4-HMAC-SHA256 Credential=testing/20261116/ap-southeast-2/sqs/aws4_request, SignedHeaders=host, Signature=0'}
        started = []
        output = b''.join(log({**base, **environ}, lambda status, headers, exc_info=None: started.append(status)))
        return log, started[0], output

    def test_records_service_operation_and_preserves_the_body(self):
        seen = []

        def app(environ, start_response):
            seen.append(environ['wsgi.input'].read())
            start_response('200 OK', [])
            return [b'ok']
        log, status, _ = self.call(app, body=b'Action=CreateQueue&QueueName=q')
        self.assertEqual(seen, [b'Action=CreateQueue&QueueName=q'])
        self.assertEqual(status, '200 OK')
        self.assertEqual([(call['service'], call['operation'], call['status']) for call in log.calls], [('sqs', 'CreateQueue', 200)])
        log, _, _ = self.call(app, HTTP_X_AMZ_TARGET='DynamoDB_20120810.CreateTable')
        self.assertEqual(log.calls[0]['operation'], 'CreateTable')
        self.assertEqual(log.timeline()[0][1:], ['sqs', 'CreateTable', 200])

    def test_unimplemented_operation_is_one_non_retryable_explicit_gap(self):
        def app(environ, start_response):
            raise NotImplementedError('The create_thing action has not been implemented')
        log, status, output = self.call(app, HTTP_X_AMZ_TARGET='Service.CreateThing')
        # 5xx would be retried by the AWS SDK for minutes; a gap is permanent.
        self.assertTrue(status.startswith('400'))
        self.assertEqual(json.loads(output)['__type'], 'EmulatorNotImplemented')
        self.assertEqual(log.summary()['notImplemented'], ['sqs:CreateThing'])
        self.assertTrue(emulator.is_emulator_gap({'summary': 'creating thing', 'detail': output.decode()}))

    def test_gap_errors_use_the_callers_wire_protocol(self):
        def app(environ, start_response):
            raise NotImplementedError('missing')
        _, _, query = self.call(app, body=b'Action=CreateThing&Version=1')
        self.assertTrue(query.startswith(b'<ErrorResponse><Error>'))
        self.assertIn(b'<Code>EmulatorNotImplemented</Code>', query)
        _, _, s3 = self.call(app, REQUEST_METHOD='PUT', PATH_INFO='/bucket', HTTP_AUTHORIZATION='AWS4-HMAC-SHA256 Credential=testing/20261116/ap-southeast-2/s3/aws4_request, SignedHeaders=host, Signature=0')
        self.assertIn(b'<Error><Code>EmulatorNotImplemented</Code>', s3)

    def test_routeless_framework_page_is_a_gap_but_an_api_404_is_not(self):
        def routeless(environ, start_response):
            start_response('404 NOT FOUND', [])
            return [b'<!doctype html>\n<title>404 Not Found</title>']
        log, status, output = self.call(routeless, REQUEST_METHOD='POST', PATH_INFO='/2020-05-31/cache-policy')
        self.assertTrue(status.startswith('400'))
        self.assertEqual(len(log.summary()['notImplemented']), 1)

        def missing(environ, start_response):
            start_response('404 Not Found', [])
            return [b'<Error><Code>NoSuchBucketPolicy</Code></Error>']
        log, status, output = self.call(missing, REQUEST_METHOD='GET', PATH_INFO='/bucket')
        self.assertEqual(status, '404 Not Found')
        self.assertIn(b'NoSuchBucketPolicy', output)
        self.assertEqual(log.summary()['notImplemented'], [])

    def test_emulator_crash_is_reported_as_an_emulator_error_not_a_pass(self):
        def app(environ, start_response):
            start_response('500 INTERNAL SERVER ERROR', [])
            return [b'Traceback: KeyError']
        log, status, output = self.call(app, HTTP_X_AMZ_TARGET='Service.CreateThing')
        self.assertTrue(status.startswith('400'))
        self.assertEqual(json.loads(output)['__type'], 'EmulatorInternalError')
        self.assertEqual([error['operation'] for error in log.summary()['serverErrors']], ['CreateThing'])
        self.assertTrue(emulator.is_emulator_gap({'summary': '', 'detail': output.decode()}))

    def test_ordinary_client_error_is_not_an_emulator_gap(self):
        def app(environ, start_response):
            start_response('400 Bad Request', [])
            return [b'<Error><Code>ValidationError</Code></Error>']
        log, status, output = self.call(app)
        self.assertEqual(status, '400 Bad Request')
        self.assertIn(b'ValidationError', output)
        self.assertEqual(log.summary()['notImplemented'], [])
        self.assertFalse(emulator.is_emulator_gap({'summary': 'ValidationError: bad name', 'detail': 'StatusCode: 400'}))

    def test_create_bucket_tags_adapter_ignores_unrelated_requests(self):
        # Only a successful bodyless-query PUT of a bucket with <Tags> is in scope.
        for environ, body, path in [({'REQUEST_METHOD': 'GET', 'QUERY_STRING': ''}, b'<Tags>', '/b'), ({'REQUEST_METHOD': 'PUT', 'QUERY_STRING': 'versioning='}, b'<Tags>', '/b'), ({'REQUEST_METHOD': 'PUT', 'QUERY_STRING': ''}, b'<x/>', '/b'), ({'REQUEST_METHOD': 'PUT', 'QUERY_STRING': ''}, b'<Tags>', '/b/key')]:
            self.assertIsNone(emulator.create_bucket_tags_adapter(environ, body, path))

    def test_own_sdk_checks_are_not_recorded_as_provider_calls(self):
        def app(environ, start_response):
            start_response('200 OK', [])
            return [b'']
        log = emulator.RequestLog(app)
        log.recording = False
        log({'PATH_INFO': '/', 'wsgi.input': io.BytesIO()}, lambda *a, **k: None)
        self.assertEqual(log.calls, [])


try:
    import moto
    HAS_MOTO = moto.__version__ == '5.2.5'
except ImportError:
    HAS_MOTO = False


@unittest.skipUnless(HAS_MOTO, 'Moto 5.2.5 is not installed in the server environment')
class AdapterTests(unittest.TestCase):
    """Each repair changes only the observed emulator defect."""

    def client(self, service):
        import boto3
        return boto3.client(service, region_name='ap-southeast-2', aws_access_key_id='testing', aws_secret_access_key='testing')

    def test_queue_attributes_survive_unrelated_updates_and_read_back_as_supplied(self):
        from moto import mock_aws
        with mock_aws():
            emulator.install_redrive_allow_adapter()
            sqs = self.client('sqs')
            dead = sqs.create_queue(QueueName='dead')['QueueUrl']
            read = lambda url: sqs.get_queue_attributes(QueueUrl=url, AttributeNames=['All']).get('Attributes', {})
            self.assertNotIn('RedriveAllowPolicy', read(dead))
            policy = json.dumps({'Version': '2012-10-17', 'Statement': [{'Effect': 'Deny', 'Principal': '*', 'Action': 'sqs:*', 'Resource': '*'}]})
            sqs.set_queue_attributes(QueueUrl=dead, Attributes={'Policy': policy})
            allow = '{"redrivePermission":"byQueue","sourceQueueArns":["arn:aws:sqs:ap-southeast-2:123456789012:work"]}'
            sqs.set_queue_attributes(QueueUrl=dead, Attributes={'RedriveAllowPolicy': allow})
            attributes = read(dead)
            self.assertEqual(attributes['RedriveAllowPolicy'], allow)
            self.assertEqual(json.loads(attributes['Policy']), json.loads(policy))
            self.assertEqual(sqs.get_queue_attributes(QueueUrl=dead, AttributeNames=['RedriveAllowPolicy'])['Attributes'], {'RedriveAllowPolicy': allow})
            redrive = '{"deadLetterTargetArn":"%s","maxReceiveCount":5}' % attributes['QueueArn']
            work = sqs.create_queue(QueueName='work', Attributes={'RedrivePolicy': redrive})['QueueUrl']
            self.assertEqual(read(work)['RedrivePolicy'], redrive)
            # An explicit empty Policy still removes it.
            sqs.set_queue_attributes(QueueUrl=dead, Attributes={'Policy': ''})
            self.assertNotIn('Policy', read(dead))

    def test_conditional_bucket_statements_are_not_enforced_but_unconditional_ones_are(self):
        from botocore.exceptions import ClientError
        from moto import mock_aws
        with mock_aws():
            emulator.install_policy_condition_adapter()
            s3 = self.client('s3')
            for name in ('conditional', 'unconditional'):
                s3.create_bucket(Bucket=name, CreateBucketConfiguration={'LocationConstraint': 'ap-southeast-2'})
            deny = {'Effect': 'Deny', 'Principal': '*', 'Action': 's3:*', 'Resource': ['arn:aws:s3:::%s', 'arn:aws:s3:::%s/*']}
            conditional = {'Version': '2012-10-17', 'Statement': [{**deny, 'Resource': [r % 'conditional' for r in deny['Resource']], 'Condition': {'Bool': {'aws:SecureTransport': 'false'}}}]}
            s3.put_bucket_policy(Bucket='conditional', Policy=json.dumps(conditional))
            s3.put_object(Bucket='conditional', Key='a', Body=b'x')
            self.assertEqual(json.loads(s3.get_bucket_policy(Bucket='conditional')['Policy']), conditional)
            s3.put_bucket_policy(Bucket='unconditional', Policy=json.dumps({'Version': '2012-10-17', 'Statement': [{**deny, 'Resource': [r % 'unconditional' for r in deny['Resource']]}]}))
            with self.assertRaises(ClientError):
                s3.put_object(Bucket='unconditional', Key='a', Body=b'x')

    def test_alias_mapping_target_is_kept_and_other_targets_are_unchanged(self):
        emulator.install_alias_mapping_adapter()
        from moto.awslambda.models import EventSourceMapping
        spec = {'RegionName': 'ap-southeast-2', 'AccountId': '123456789012', 'EventSourceArn': 'arn:aws:sqs:ap-southeast-2:123456789012:q'}
        version = 'arn:aws:lambda:ap-southeast-2:123456789012:function:f:1'
        alias = 'arn:aws:lambda:ap-southeast-2:123456789012:function:f:live'
        self.assertEqual(EventSourceMapping({**spec, 'FunctionName': alias, 'FunctionArn': version}).function_arn, alias)
        self.assertEqual(EventSourceMapping({**spec, 'FunctionName': version, 'FunctionArn': version}).function_arn, version)
        self.assertEqual(EventSourceMapping({**spec, 'FunctionName': 'f', 'FunctionArn': version}).function_arn, version)

    def test_cbor_bridge_preserves_members_and_types_both_ways(self):
        import datetime
        import botocore.session
        from botocore import parsers, serialize
        model = botocore.session.get_session().get_service_model('cloudwatch')
        operation = model.operation_model('PutMetricAlarm')
        params = {'AlarmName': 'a', 'Namespace': 'AWS/SQS', 'MetricName': 'm', 'Statistic': 'Maximum', 'Period': 60, 'EvaluationPeriods': 1, 'Threshold': 0.5, 'ComparisonOperator': 'GreaterThanThreshold', 'Dimensions': [{'Name': 'QueueName', 'Value': 'q'}]}
        request = serialize.RpcV2CBORSerializer().serialize_to_request(params, operation)
        bridge = emulator.CborBridge('monitoring', request['url_path'])
        environ = {'HTTP_SMITHY_PROTOCOL': 'rpc-v2-cbor', 'PATH_INFO': request['url_path']}
        body = bridge.request(environ, request['body'])
        self.assertEqual(json.loads(body), params)
        self.assertEqual((environ['PATH_INFO'], environ['HTTP_X_AMZ_TARGET']), ('/', 'GraniteServiceVersion20100801.PutMetricAlarm'))
        self.assertNotIn('HTTP_SMITHY_PROTOCOL', environ)
        self.assertEqual(bridge.response(200, b''), ([('smithy-protocol', 'rpc-v2-cbor')], b''))

        describe = emulator.CborBridge('monitoring', '/service/GraniteServiceVersion20100801/operation/DescribeAlarms')
        answer = json.dumps({'MetricAlarms': [{'AlarmName': 'a', 'Threshold': 0.5, 'Period': 60, 'ActionsEnabled': True, 'AlarmConfigurationUpdatedTimestamp': 1794851575.0}]}).encode()
        headers, encoded = describe.response(200, answer)
        parsed = parsers.RpcV2CBORParser().parse({'body': encoded, 'headers': dict(headers), 'status_code': 200}, describe.operation.output_shape)
        alarm = parsed['MetricAlarms'][0]
        self.assertEqual((alarm['AlarmName'], alarm['Threshold'], alarm['Period'], alarm['ActionsEnabled']), ('a', 0.5, 60, True))
        self.assertIsInstance(alarm['AlarmConfigurationUpdatedTimestamp'], datetime.datetime)

        headers, encoded = describe.response(404, b'{"__type": "ResourceNotFound", "message": "missing"}')
        self.assertIn(('x-amzn-query-error', 'ResourceNotFound;Sender'), headers)
        error = parsers.RpcV2CBORParser().parse({'body': encoded, 'headers': {}, 'status_code': 404}, describe.operation.output_shape)
        self.assertEqual((error['Error']['Code'], error['Error']['Message']), ('ResourceNotFound', 'missing'))

    def test_cbor_bridge_refuses_services_without_a_known_json_form(self):
        with self.assertRaises(LookupError):
            emulator.CborBridge('monitoring', '/service/SomethingElse/operation/PutMetricAlarm')
        with self.assertRaises(Exception):
            emulator.CborBridge('no-such-service', '/service/X/operation/Y')


class DiagnosticsTests(unittest.TestCase):
    def test_apply_stream_errors_keep_resource_addresses(self):
        stream = '\n'.join([
            'not json',
            json.dumps({'type': 'apply_complete', 'hook': {'resource': {'addr': 'aws_s3_bucket.a'}, 'action': 'create'}}),
            json.dumps({'type': 'diagnostic', 'diagnostic': {'severity': 'warning', 'summary': 'ignored'}}),
            json.dumps({'type': 'diagnostic', 'diagnostic': {'severity': 'error', 'summary': 'creating X', 'detail': 'StatusCode: 501', 'address': 'aws_x.y'}}),
        ])
        errors, completed = emulator.diagnostics(stream)
        self.assertEqual(completed, [('aws_s3_bucket.a', 'create')])
        self.assertEqual(errors, [{'address': 'aws_x.y', 'summary': 'creating X', 'detail': 'StatusCode: 501'}])


class RouteBoundaryTests(unittest.TestCase):
    def test_token_and_server_owned_files_boundary(self):
        client = TestClient(app)
        headers = {'Authorization': f'Bearer {TOKEN}'}
        self.assertEqual(client.post('/api/terraform/emulate', json={'project': {}}).status_code, 401)
        self.assertEqual(client.post('/api/terraform/emulate', headers=headers, json={'project': {}, 'files': {'main.tf': 'x'}}).status_code, 422)
        self.assertEqual(client.post('/api/terraform/emulate', headers=headers, json={'project': {}, 'endpoint': 'https://aws.example'}).status_code, 422)
        self.assertEqual(client.get('/api/terraform/emulate/unknown', headers=headers).status_code, 404)

    def test_disabled_or_missing_runtime_never_passes(self):
        with patch.dict(os.environ, {'ATMEM_ARCHITECT_EMULATION_ENABLED': '0'}):
            self.assertEqual(emulate_terraform(TerraformEmulationRequest(project={}))['status'], 'unavailable')
        with patch.dict(os.environ, {'ATMEM_ARCHITECT_TERRAFORM_EMULATOR_PYTHON': '/nonexistent/python'}):
            report = emulate_terraform(TerraformEmulationRequest(project={}))
        self.assertEqual((report['status'], report['terraformApply']), ('unavailable', 'not_run'))

    def test_busy_server_refuses_a_second_job(self):
        client = TestClient(app)
        with patch('server.terraform_emulation_routes.LOCK.locked', return_value=True):
            self.assertEqual(client.post('/api/terraform/emulate', headers={'Authorization': f'Bearer {TOKEN}'}, json={'project': {}}).status_code, 409)


@unittest.skipUnless(READY, 'Terraform emulator runtime or Terraform is not installed')
class LifecycleTests(unittest.TestCase):
    """Real Terraform CLI and provider against the loopback emulator."""

    def run_directory(self, folder):
        with tempfile.TemporaryDirectory() as output:
            report = Path(output) / 'report.json'
            environment = {'PATH': os.getenv('PATH', ''), 'HOME': output, 'ATMEM_ARCHITECT_TERRAFORM_BIN': TERRAFORM}
            subprocess.run([str(runtime_python()), '-I', str(ROOT / 'server/terraform_emulator.py'), '--dir', str(folder), '--provider-cache', CACHE, '--report', str(report)], env=environment, capture_output=True, timeout=900)
            return json.loads(report.read_text())

    def test_identity_fixture_passes_every_stage_and_leaves_nothing(self):
        report = self.run_directory(CORPUS / 'identity')
        self.assertEqual(report['status'], 'passed', report.get('message'))
        self.assertEqual([stage['status'] for stage in report['stages']], ['passed'] * len(report['stages']))
        self.assertTrue({'Apply', 'Independent API read-back', 'Convergence plan', 'Destroy', 'Leak check'} <= {stage['name'] for stage in report['stages']})
        self.assertTrue(all(resource['applied'] for resource in report['resources']))
        self.assertGreater(report['resourceTypes']['aws_iam_role']['sdkVerified'], 0)
        self.assertIs(report['cloudOperations'], False)
        self.assertEqual(report['apiCalls']['notImplemented'], [])
        self.assertEqual(report['workspaceCleanup'], 'passed')
        # The source fixture is never modified.
        self.assertEqual(sorted(path.name for path in (CORPUS / 'identity').iterdir()), ['main.tf'])

    def test_broken_configuration_fails_and_is_not_called_an_emulator_gap(self):
        with tempfile.TemporaryDirectory() as folder:
            shutil.copy(CORPUS / 'identity/main.tf', folder)
            # A dangling policy attachment: valid schema, rejected by the API at apply.
            with open(Path(folder) / 'main.tf', 'a') as handle:
                handle.write('\nresource "aws_iam_role_policy_attachment" "dangling" {\n  role       = aws_iam_role.worker.name\n  policy_arn = "arn:aws:iam::123456789012:policy/does-not-exist"\n}\n')
            report = self.run_directory(folder)
        self.assertEqual(report['status'], 'failed')
        failing = [resource for resource in report['resources'] if resource.get('error')]
        self.assertEqual([resource['address'] for resource in failing], ['aws_iam_role_policy_attachment.dangling'])
        self.assertFalse(failing[0]['emulatorGap'])
        # Teardown still ran, so nothing is left behind.
        self.assertEqual({stage['name']: stage['status'] for stage in report['stages']}['Leak check'], 'passed')


if __name__ == '__main__':
    unittest.main()
