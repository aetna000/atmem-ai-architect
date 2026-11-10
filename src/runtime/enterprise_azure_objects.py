"""Bounded, native-MI Azure temporary blobs; never a source URL connector.

ARM preflight is observational, not an administrative lock. Provisioning must
restrict changes to this dedicated no-history account/container. Lost nodes and
cloud erasure require separate controller/recovery evidence.
"""
import base64
from datetime import datetime, timezone
from email.utils import format_datetime
import hashlib
import json
import re
import time
from urllib.parse import quote
import requests
from enterprise_document_contract import MAX_INPUT
from enterprise_document_job import MAX_ENVELOPE, unique
from enterprise_sources import SourceUnavailable

ARM_VERSION = '2025-06-01'
BLOB_VERSION = '2025-05-05'
_UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'


def object_key(identifier, side, node_id=None):
    if not isinstance(identifier, str) or not re.fullmatch('[0-9a-f]{64}', identifier) or side not in {'input', 'result', 'cleanup'}:
        raise ValueError('Use the owned per-file object identity')
    if side == 'cleanup':
        if not isinstance(node_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', node_id):
            raise ValueError('Use the exact native cleanup node identity')
        return 'document-jobs/' + identifier + '/cleanup/' + node_id
    if node_id is not None: raise ValueError('Only cleanup receipts have a node identity')
    return 'document-jobs/' + identifier + '/' + side


def etag(value):
    if not isinstance(value, str) or not re.fullmatch(r'"0x[0-9A-Fa-f]{1,32}"', value):
        raise SourceUnavailable('document_object_unavailable')
    return value


class AzureDocumentObjects:
    def __init__(self, *, subscription, resource_group, region, account, container,
                 client_id, session=None, credential=None):
        for value, pattern in [(subscription, _UUID), (client_id, _UUID),
                (resource_group, r'[A-Za-z0-9_()-](?:[A-Za-z0-9_().-]{0,88}[A-Za-z0-9_()-])?'),
                (region, r'[a-z][a-z0-9]{1,30}'), (account, r'[a-z0-9]{3,24}'),
                (container, r'[a-z0-9]+(?:-[a-z0-9]+)*')]:
            if not isinstance(value, str) or not re.fullmatch(pattern, value):
                raise ValueError('Use the owned Azure temporary object destination')
        if not 3 <= len(container) <= 63:
            raise ValueError('Use the owned Azure temporary container')
        self.region, self.account, self.container, self.client_id = region, account, container, client_id
        self.account_id = ('/subscriptions/' + subscription + '/resourceGroups/' + resource_group +
                           '/providers/Microsoft.Storage/storageAccounts/' + account)
        self.service_id = self.account_id + '/blobServices/default'
        self.container_id = self.service_id + '/containers/' + container
        self.base = 'https://' + account + '.blob.core.windows.net/' + container + '/'
        self.session = session or requests.Session()
        self.session.trust_env = False
        self.credential = credential

    def _credential(self):
        if self.credential is None:
            from azure.identity import ManagedIdentityCredential
            self.credential = ManagedIdentityCredential(client_id=self.client_id, retry_total=0,
                                                       connection_timeout=1, read_timeout=2)
        return self.credential

    def _send(self, method, url, *, arm=False, headers=None, raw=None, limit=32768, missing=False):
        # The private entry point still enforces destination ownership. Never
        # follow redirects or use developer proxy/netrc credentials.
        if method not in {'GET', 'PUT', 'DELETE'}:
            raise ValueError('Use the fixed owned object operations')
        if arm:
            if method != 'GET' or url not in {'https://management.azure.com' + value for value in
                                            [self.account_id, self.service_id, self.container_id]}:
                raise ValueError('Use only the fixed owned ARM observations')
        elif not url.startswith(self.base + 'document-jobs/') or not re.fullmatch(
                re.escape(self.base) + r'document-jobs/[0-9a-f]{64}/(?:input|result|cleanup/[A-Za-z0-9_-]{1,128})', url):
            raise ValueError('Use only the fixed owned blob object')
        try:
            scope = 'https://management.azure.com/.default' if arm else 'https://storage.azure.com/.default'
            token = self._credential().get_token(scope).token
            if not isinstance(token, str) or not 8 <= len(token) <= 20000 or any(ord(c) < 33 or ord(c) > 126 for c in token):
                raise ValueError()
            request_headers = {'Authorization': 'Bearer ' + token, 'Accept-Encoding': 'identity'}
            if not arm:
                request_headers.update({'x-ms-version': BLOB_VERSION,
                    'x-ms-date': format_datetime(datetime.now(timezone.utc), usegmt=True)})
            request_headers.update(headers or {})
            started = time.monotonic()
            with self.session.request(method, url, headers=request_headers, data=raw,
                    params={'api-version': ARM_VERSION} if arm else None,
                    stream=True, allow_redirects=False, timeout=(2, 8)) as response:
                if missing and response.status_code == 404:
                    return None
                expected = {'GET': {200}, 'PUT': {201}, 'DELETE': {202}}
                if response.status_code not in expected[method]:
                    raise ValueError()
                received = {key.lower(): value for key, value in response.headers.items()}
                if received.get('content-encoding') not in {None, 'identity'}:
                    raise ValueError()
                data = bytearray()
                for chunk in response.iter_content(16384):
                    data.extend(chunk)
                    if len(data) > limit or time.monotonic() - started > 15:
                        raise ValueError()
                return bytes(data), received
        except Exception:
            raise SourceUnavailable('document_object_unavailable') from None

    def _arm(self, identifier):
        raw, _ = self._send('GET', 'https://management.azure.com' + identifier, arm=True, limit=262144)
        try:
            value = json.loads(raw, object_pairs_hook=unique)
            if not isinstance(value, dict) or not isinstance(value.get('id'), str) or value['id'].lower() != identifier.lower():
                raise ValueError()
            return value
        except Exception:
            raise SourceUnavailable('document_object_policy_unavailable') from None

    def preflight(self):
        """Before any data operation, observe placement and no retained history."""
        try:
            account = self._arm(self.account_id)
            properties = account['properties']
            if (account.get('location') != self.region or account.get('kind') != 'StorageV2' or
                    account.get('sku', {}).get('name') not in {'Standard_LRS', 'Standard_ZRS'} or
                    properties.get('primaryLocation') != self.region or properties.get('secondaryLocation') is not None or
                    properties.get('supportsHttpsTrafficOnly') is not True or properties.get('minimumTlsVersion') != 'TLS1_2' or
                    properties.get('allowSharedKeyAccess') is not False or properties.get('allowBlobPublicAccess') is not False or
                    properties.get('publicNetworkAccess') != 'Disabled' or
                    properties.get('encryption', {}).get('services', {}).get('blob', {}).get('enabled') is not True or
                    properties.get('immutableStorageWithVersioning', {}).get('enabled') is True):
                raise ValueError()
            service = self._arm(self.service_id)['properties']
            if service.get('isVersioningEnabled') is not False:
                raise ValueError()
            for name in ['deleteRetentionPolicy', 'containerDeleteRetentionPolicy', 'restorePolicy', 'changeFeed']:
                if service.get(name, {}).get('enabled') is not False:
                    raise ValueError()
            container = self._arm(self.container_id)['properties']
            if (container.get('publicAccess') != 'None' or container.get('hasImmutabilityPolicy') is not False or
                    container.get('hasLegalHold') is not False or
                    container.get('immutableStorageWithVersioning', {}).get('enabled') is True):
                raise ValueError()
        except Exception:
            raise SourceUnavailable('document_object_policy_unavailable') from None

    def url(self, identifier, side, node_id=None):
        return self.base + quote(object_key(identifier, side, node_id), safe='/')

    def put(self, identifier, side, raw):
        if side == 'cleanup': raise ValueError('Only the root publisher creates cleanup acknowledgements')
        url = self.url(identifier, side)
        maximum = MAX_INPUT if side == 'input' else MAX_ENVELOPE
        if not isinstance(raw, bytes) or not 0 < len(raw) <= maximum:
            raise ValueError('Use bounded owned document bytes')
        self.preflight()
        _, headers = self._send('PUT', url, raw=raw, headers={'If-None-Match': '*',
            'Content-Type': 'application/octet-stream', 'Content-Length': str(len(raw)),
            'Content-MD5': base64.b64encode(hashlib.md5(raw, usedforsecurity=False).digest()).decode(),
            'x-ms-blob-type': 'BlockBlob'}, limit=4096)
        if headers.get('x-ms-request-server-encrypted') != 'true' or headers.get('x-ms-version-id') is not None:
            raise SourceUnavailable('document_object_unavailable')
        return etag(headers.get('etag'))

    def load(self, identifier, side, condition=None, *, allow_missing=False, node_id=None):
        if allow_missing and side != 'cleanup': raise ValueError('Only cleanup receipt lookup is optional')
        url = self.url(identifier, side, node_id)
        headers = {} if condition is None else {'If-Match': etag(condition)}
        self.preflight()
        maximum = MAX_INPUT if side == 'input' else 1024 if side == 'cleanup' else MAX_ENVELOPE
        value = self._send('GET', url, headers=headers, limit=maximum, missing=allow_missing)
        if value is None: return None
        raw, observed = value
        try:
            if (observed.get('x-ms-server-encrypted') != 'true' or observed.get('x-ms-version-id') is not None or
                    observed.get('x-ms-blob-type') != 'BlockBlob' or
                    not isinstance(observed.get('content-length'), str) or
                    not re.fullmatch('[1-9][0-9]{0,9}', observed['content-length']) or
                    int(observed['content-length']) != len(raw) or (condition is not None and observed.get('etag') != condition)):
                raise ValueError()
            etag(observed.get('etag'))
            return raw
        except Exception:
            raise SourceUnavailable('document_object_unavailable') from None

    def delete(self, identifier, side):
        if side == 'cleanup': raise ValueError('Cleanup metadata is retired by its dedicated lifecycle policy')
        url = self.url(identifier, side)
        self.preflight()
        try:
            value = self._send('DELETE', url, headers={'x-ms-delete-snapshots': 'include'}, missing=True, limit=4096)
            if value is not None and value[1].get('x-ms-version-id') is not None:
                raise ValueError()
        except Exception:
            raise SourceUnavailable('document_cleanup_unavailable') from None

    def cleanup_acknowledged(self, identifier, owner, node_id):
        if not isinstance(owner, str) or not re.fullmatch('[0-9a-f]{64}', owner):
            raise ValueError('Use the exact owned cleanup destination fingerprint')
        raw = self.load(identifier, 'cleanup', allow_missing=True, node_id=node_id)
        if raw is None: return False
        try:
            value = json.loads(raw, object_pairs_hook=unique)
            if (not isinstance(value, dict) or value.get('cleaned') is not True or value != {
                    'format': 'enterprise-azure-document-cleanup-v2', 'requestId': identifier,
                    'owner': owner, 'nodeId': node_id, 'cleaned': True}):
                raise ValueError()
            return True
        except Exception:
            raise SourceUnavailable('document_cleanup_receipt_unavailable') from None

    def cleanup_acknowledged_all(self, identifier, owner, node_ids):
        """Caller must obtain this complete closed set from terminal native work.

        A partial/preflight node list is not a settlement proof. Empty/duplicate
        sets cannot accidentally certify cleanup; unscheduled jobs require a
        separate verified no-writer lifecycle in the controller.
        """
        if (not isinstance(node_ids, (set, frozenset, list, tuple)) or not 1 <= len(node_ids) <= 100 or
                any(not isinstance(node, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', node) for node in node_ids) or
                len(set(node_ids)) != len(node_ids)):
            raise ValueError('Use the complete unique native writer-node set')
        return all(self.cleanup_acknowledged(identifier, owner, node) for node in sorted(node_ids))

    def close(self):
        try:
            self.session.close()
        finally:
            if self.credential is not None:
                self.credential.close()
