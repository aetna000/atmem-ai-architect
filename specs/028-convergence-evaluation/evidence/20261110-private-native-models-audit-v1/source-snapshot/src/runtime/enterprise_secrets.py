"""Startup secret injections for the owned read-only private assistant.

Native platforms resolve pinned secret references. This adapter never downloads
cloud secrets, generates a replacement encryption key or writes into an export.
All replicas must use the same reviewed encryption-key version; coordinated key
migration/backup is separate operator work, not automatic hot rotation.
"""
import atexit
import os
from pathlib import Path
import shutil
import tempfile
from cryptography.fernet import Fernet
from enterprise_sources import SourceUnavailable

FIELDS = {
    'encryption': ('ENTERPRISE_ENCRYPTION_KEY', 'ENTERPRISE_ENCRYPTION_KEY_FILE', 44),
    'graph': ('SHAREPOINT_CLIENT_SECRET', 'SHAREPOINT_CLIENT_SECRET_FILE', 16000),
    'confluence': ('CONFLUENCE_CLIENT_SECRET', 'CONFLUENCE_CLIENT_SECRET_FILE', 16000),
    'database_password': ('DATABASE_PASSWORD', 'DATABASE_PASSWORD_FILE', 500),
    'database_ca': ('DATABASE_CA_PEM', 'DATABASE_CA_FILE', 256000),
}


def decode(name, raw):
    if not raw or len(raw) > FIELDS[name][2] or b'\0' in raw:
        raise ValueError('Invalid owned secret value')
    value = raw.decode('utf-8')
    if name == 'encryption':
        if len(raw) != 44:
            raise ValueError('Use the existing exact Fernet key')
        Fernet(raw)
    if name == 'database_ca' and '-----BEGIN CERTIFICATE-----' not in value:
        raise ValueError('Use the native database CA certificate')
    return value


class SecretFiles:
    def __init__(self, provider, environment, role):
        if provider not in {'aws', 'azure', 'gcp', 'ibm'} or role not in {'api', 'worker'}:
            raise ValueError('Supply the owned private workload provider and role')
        # Read-only assistants have no action credentials. Native workload
        # identities must not silently fall back to inherited developer keys.
        forbidden = ['DESTINATION_TOKEN', 'DESTINATION_TOKEN_FILE', 'PARSER_SHARED_TOKEN', 'PARSER_SHARED_TOKEN_FILE',
                     'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 'AZURE_CLIENT_SECRET',
                     'GOOGLE_APPLICATION_CREDENTIALS', 'IBMCLOUD_API_KEY', 'OPENAI_API_KEY']
        if provider != 'ibm': forbidden += ['DATABASE_PASSWORD', 'DATABASE_PASSWORD_FILE']
        if any(key in environment for key in forbidden):
            raise ValueError('Unexpected static cloud, parser or action authority in the private workload')
        self.env, self.directory, self.closed = dict(environment), None, False
        required = ['encryption', 'graph', 'confluence']
        if provider != 'gcp': required.append('database_ca')
        if provider == 'ibm': required.append('database_password')
        selected = []
        for name, (direct, pointer, maximum) in FIELDS.items():
            if direct in environment and pointer in environment:
                raise ValueError('Conflicting native secret injection and mounted file')
            if direct in environment:
                value = environment[direct]
                if not isinstance(value, str): raise ValueError('Invalid native secret injection')
                decode(name, value.encode('utf-8'))
                selected.append((name, direct, pointer, value))
            elif pointer in environment:
                path = environment[pointer]
                if not isinstance(path, str) or not Path(path).is_absolute():
                    raise ValueError('Use the owned mounted secret path')
            elif name in required:
                raise ValueError('Missing required native secret reference')
        try:
            if selected:
                self.directory = Path(tempfile.mkdtemp(prefix='atmem-enterprise-secrets-'))
                self.directory.chmod(0o700)
                for name, direct, pointer, value in selected:
                    path = self.directory / name
                    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(descriptor, 'wb') as stream: stream.write(value.encode('utf-8'))
                    self.env[pointer] = str(path); self.env.pop(direct, None)
            # Fail startup for unreadable/invalid required files; do not generate
            # new keys, invent credentials or defer broken setup to a basic user.
            for name in required: self.read(name)
            if environment is os.environ:
                for _, direct, _, _ in selected: os.environ.pop(direct, None)
            atexit.register(self.close)
        except BaseException:
            self.close(); raise

    def __repr__(self): return '<Owned private-assistant secret files>'

    def read(self, name):
        if name not in FIELDS: raise ValueError('Unknown owned secret purpose')
        try:
            if self.closed: raise ValueError()
            _, pointer, maximum = FIELDS[name]
            path = self.env[pointer]
            with Path(path).open('rb') as stream: raw = stream.read(maximum + 1)
            return decode(name, raw)
        except Exception:
            raise SourceUnavailable('enterprise_secret_unavailable') from None

    def reader(self, name):
        if name not in FIELDS: raise ValueError('Unknown owned secret purpose')
        return lambda: self.read(name)

    def close(self):
        if self.directory is not None: shutil.rmtree(self.directory, ignore_errors=True)
        self.closed = True

    def __enter__(self): return self
    def __exit__(self, *args): self.close()
