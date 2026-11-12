"""Fixed-destination native Azure Batch transport; no pool/node mutation authority.

Typed methods emit only this implementation's owned job/task contracts. A202
acknowledgement never proves termination/deletion. Controller, pool/agent checks,
SQL ownership and cleanup receipts remain separate required composition layers.
"""
from datetime import datetime, timezone
from email.utils import format_datetime
import json
import re
import time
from types import MappingProxyType
import requests
from enterprise_azure_jobs import API_VERSION, configuration, identity, job_spec, task_spec
from enterprise_document_job import unique
from enterprise_sources import SourceUnavailable


class AzureBatchApi:
    def __init__(self, config, *, session=None, credential=None):
        self.config = MappingProxyType(configuration(config))
        self.base = 'https://' + self.config['batchAccount'] + '.' + self.config['region'] + '.batch.azure.com'
        self.account_id = ('/subscriptions/' + self.config['subscriptionId'] + '/resourceGroups/' + self.config['resourceGroup'] +
                           '/providers/Microsoft.Batch/batchAccounts/' + self.config['batchAccount'])
        self.session = session or requests.Session()
        self.session.trust_env = False
        self.credential = credential

    def _credential(self):
        if self.credential is None:
            from azure.identity import ManagedIdentityCredential
            self.credential = ManagedIdentityCredential(client_id=self.config['workerClientId'], retry_total=0,
                                                       connection_timeout=1, read_timeout=2)
        return self.credential

    def _send(self, method, path, *, body=None, arm=False, missing=False):
        account_url = 'https://management.azure.com' + self.account_id
        if arm:
            if method != 'GET' or path != self.account_id or body is not None or missing:
                raise ValueError('Only the owned Batch account observation is permitted')
            url, version, scope, statuses = account_url, '2025-06-01', 'https://management.azure.com/.default', {200}
        else:
            pool = re.escape('/pools/' + self.config['poolId'])
            job = '/jobs/[0-9a-f]{64}'
            allowed = ((method == 'GET' and re.fullmatch(pool + '(?:/nodes)?', path)) or
                       (method in {'GET', 'DELETE'} and re.fullmatch(job, path)) or
                       (method == 'POST' and (path == '/jobs' or re.fullmatch(job + '/(?:tasks|terminate)', path))) or
                       (method == 'GET' and re.fullmatch(job + '/(?:tasks/document|jobpreparationandreleasetaskstatus)', path)))
            if not allowed or body is not None and method != 'POST':
                raise ValueError('Use only fixed owned Batch job/task observations and lifecycle operations')
            if missing and not (method == 'GET' and re.fullmatch(job + '(?:/tasks/document)?', path)):
                raise ValueError('Only a direct owned job/task lookup may be missing')
            url, version, scope = self.base + path, API_VERSION, 'https://batch.core.windows.net/.default'
            statuses = {200} if method == 'GET' else {202} if method == 'DELETE' or path.endswith('/terminate') else {201}
        encoded = None if body is None else json.dumps(body, allow_nan=False, separators=(',', ':')).encode()
        if encoded is not None and len(encoded) > 65536:
            raise ValueError('Owned Batch metadata exceeds the request bound')
        try:
            token = self._credential().get_token(scope).token
            if not isinstance(token, str) or not 8 <= len(token) <= 20000 or any(ord(c) < 33 or ord(c) > 126 for c in token):
                raise ValueError()
            headers = {'Authorization': 'Bearer ' + token, 'Accept-Encoding': 'identity',
                       'ocp-date': format_datetime(datetime.now(timezone.utc), usegmt=True)}
            if encoded is not None: headers['Content-Type'] = 'application/json; odata=minimalmetadata'
            started = time.monotonic()
            with self.session.request(method, url, params={'api-version': version}, headers=headers,
                    data=encoded, stream=True, allow_redirects=False, timeout=(2, 8)) as response:
                if missing and response.status_code == 404: return None
                if response.status_code not in statuses: raise ValueError()
                if response.headers.get('Content-Encoding') not in {None, 'identity'}: raise ValueError()
                raw = bytearray()
                for chunk in response.iter_content(16384):
                    raw.extend(chunk)
                    if len(raw) > 262144 or time.monotonic() - started > 15: raise ValueError()
                if not raw:
                    if method == 'GET': raise ValueError()
                    return {}
                value = json.loads(raw, object_pairs_hook=unique)
                if not isinstance(value, dict): raise ValueError()
                return value
        except Exception:
            raise SourceUnavailable('document_batch_api_unavailable') from None

    def account(self):
        value = self._send('GET', self.account_id, arm=True)
        try:
            properties = value['properties']
            if (not isinstance(value.get('id'), str) or value['id'].lower() != self.account_id.lower() or
                    value.get('location') != self.config['region'] or properties.get('provisioningState') != 'Succeeded' or
                    properties.get('accountEndpoint') != self.base.removeprefix('https://') or
                    properties.get('publicNetworkAccess') != 'Disabled' or properties.get('allowedAuthenticationModes') != ['AAD']):
                raise ValueError()
            return value
        except Exception:
            raise SourceUnavailable('document_batch_account_changed') from None

    def pool(self):
        return self._send('GET', '/pools/' + self.config['poolId'])

    def nodes(self):
        return self._send('GET', '/pools/' + self.config['poolId'] + '/nodes')

    def job(self, identifier, *, missing=False):
        return self._send('GET', '/jobs/' + identity(identifier), missing=missing)

    def task(self, identifier, *, missing=False):
        return self._send('GET', '/jobs/' + identity(identifier) + '/tasks/document', missing=missing)

    def create_job(self, metadata, etag):
        return self._send('POST', '/jobs', body=job_spec(dict(self.config), metadata, etag))

    def create_task(self, identifier):
        return self._send('POST', '/jobs/' + identity(identifier) + '/tasks', body=task_spec(dict(self.config), identifier))

    def terminate(self, identifier):
        # Never request force=true: nodes must be allowed to process release.
        return self._send('POST', '/jobs/' + identity(identifier) + '/terminate', body={'terminateReason': 'Owned document cleanup'})

    def delete(self, identifier):
        return self._send('DELETE', '/jobs/' + identity(identifier))

    def release_status(self, identifier):
        return self._send('GET', '/jobs/' + identity(identifier) + '/jobpreparationandreleasetaskstatus')

    def close(self):
        try: self.session.close()
        finally:
            if self.credential is not None: self.credential.close()
