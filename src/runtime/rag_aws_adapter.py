"""AWS IAM HTTP API identity and strongly consistent bounded document adapters.

The infrastructure contract must grant invocation only to the exact API route,
not to end-user IAM identities. This adapter cannot authenticate a forged direct
Lambda invocation by itself; the generated IAM boundary is part of the contract.
"""
import json
import re
from bounded_rag import Principal, RetrievalDenied, MAX_DOCUMENTS


def authenticated_principal(event, directory, expected_account, expected_api, expected_issuer=None, expected_client=None):
    if not isinstance(event, dict) or event.get('version') != '2.0':
        raise RetrievalDenied('Invalid authenticated request')
    context = event.get('requestContext') or {}
    if context.get('accountId') != expected_account or context.get('apiId') != expected_api:
        raise RetrievalDenied('Unexpected authenticated route')
    if context.get('routeKey') == 'POST /api/ask' and expected_issuer and expected_client:
        claims=((context.get('authorizer') or {}).get('jwt') or {}).get('claims') or {}
        subject=claims.get('sub');scope=claims.get('scope')
        if claims.get('iss')!=expected_issuer or claims.get('client_id')!=expected_client or claims.get('token_use')!='access' or not isinstance(subject,str) or not re.fullmatch(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',subject) or not isinstance(scope,str) or 'atmem/ask' not in scope.split():
            raise RetrievalDenied('Unknown identity')
        return mapped_principal(directory,'COGNITO#'+subject)
    if context.get('routeKey')!='POST /ask':raise RetrievalDenied('Unexpected authenticated route')
    iam = (context.get('authorizer') or {}).get('iam') or {}
    caller, arn = iam.get('callerId'), iam.get('userArn')
    if iam.get('accountId') != expected_account or not isinstance(caller, str) or not isinstance(arn, str):
        raise RetrievalDenied('Unknown identity')
    if not re.fullmatch(r'(AIDA|AROA)[A-Z0-9]{12,32}(?::[A-Za-z0-9_+=,.@-]{2,64})?', caller):
        raise RetrievalDenied('Unknown identity')
    role = caller.startswith('AROA')
    pattern = rf'arn:aws:sts::{expected_account}:assumed-role/[A-Za-z0-9_+=,.@-]+/[A-Za-z0-9_+=,.@-]+' if role else rf'arn:aws:iam::{expected_account}:user/[A-Za-z0-9_+=,.@/-]+'
    if not re.fullmatch(pattern, arn):
        raise RetrievalDenied('Unknown identity')
    # IAM's stable unique principal ID survives session-name changes but not
    # deletion/recreation of a role. No ARN-path guessing or body claims.
    return mapped_principal(directory,caller.split(':',1)[0])


def mapped_principal(directory,principal_id):
    record = directory.get_identity(principal_id)
    if not isinstance(record, dict) or record.get('enabled') is not True:
        raise RetrievalDenied('Unknown or disabled identity')
    subject, region = record.get('subject'), record.get('employeeRegion')
    if not isinstance(subject, str) or not subject or not isinstance(region, str) or not re.fullmatch(r'[A-Z]{2}', region):
        raise RetrievalDenied('Identity mapping is incomplete')
    return Principal(subject, region)


def question_body(event):
    if event.get('isBase64Encoded') is True:
        raise ValueError('Send an ordinary JSON request body')
    body = event.get('body')
    if not isinstance(body, str) or len(body.encode('utf-8')) > 8_000:
        raise ValueError('Invalid request size')
    payload = json.loads(body)
    if not isinstance(payload, dict) or set(payload) != {'question'} or not isinstance(payload['question'], str):
        raise ValueError('Expected exactly one question string')
    return payload['question']


class DynamoRepository:
    """Small-table qualification adapter; rejects overflow rather than partial scans."""
    def __init__(self, client, table, deserialize):
        self.client, self.table, self.deserialize = client, table, deserialize

    def _read(self, key):
        response = self.client.get_item(TableName=self.table, Key={'recordId': {'S': key}}, ConsistentRead=True)
        return self.deserialize(response['Item']) if 'Item' in response else None

    def get_identity(self, principal_id):
        return self._read('IDENTITY#' + principal_id)

    def get_current(self, document_id):
        return self._read('DOCUMENT#' + document_id)

    def list_bounded(self):
        documents, key, scanned = [], None, 0
        # All records, including identity mappings, count against a hard bounded
        # read budget. A filter must not hide unbounded scan consumption.
        for _ in range(5):
            args = {'TableName': self.table, 'ConsistentRead': True, 'Limit': 100}
            if key: args['ExclusiveStartKey'] = key
            response = self.client.scan(**args)
            scanned += response.get('ScannedCount', len(response.get('Items', [])))
            if scanned > 500:
                raise ValueError('Collection read budget exceeded')
            for item in response.get('Items', []):
                value = self.deserialize(item)
                if value.get('kind') == 'DOCUMENT': documents.append(value)
            if len(documents) > MAX_DOCUMENTS:
                raise ValueError('Document collection limit exceeded')
            key = response.get('LastEvaluatedKey')
            if not key: return documents
        raise ValueError('Collection read budget exceeded')
