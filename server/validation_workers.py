"""Operator-owned local executor registrations, never request-selected endpoints.

Definitions are snapshots. Missing sockets/policies can become available later;
instantiation never pulls images, changes contexts or discovers another executor.
"""
from dataclasses import dataclass
import json
from pathlib import Path
import re
from .local_validation import DockerValidationWorker


def worker_id(value):
    if type(value) is not str or not re.fullmatch(r'[a-z][a-z0-9_-]{2,79}',value):
        raise ValueError('Use an explicit operator worker ID')
    return value


@dataclass(frozen=True)
class WorkerRegistration:
    endpoint: str
    profiles: bytes

    def create(self):
        return DockerValidationWorker(self.endpoint,isolation_profiles=json.loads(self.profiles))


def registered_workers(entries):
    if type(entries) is not dict or len(entries)>16:
        raise ValueError('Register a bounded operator worker mapping')
    result={}
    for name,entry in entries.items():
        worker_id(name)
        if type(entry) is not dict or not {'endpoint'}<=set(entry)<={'endpoint','isolationProfiles'}:
            raise ValueError('Unrecognized operator worker registration')
        endpoint=entry['endpoint']
        if type(endpoint) is not str or len(endpoint)>1024 or '\0' in endpoint or not endpoint.startswith('unix:///') or not Path(endpoint[7:]).is_absolute():
            raise ValueError('Register an explicit local Docker Unix socket')
        profiles=entry.get('isolationProfiles',{})
        if type(profiles) is not dict or set(profiles)-set(DockerValidationWorker.REVIEWED_PROFILES):
            raise ValueError('Register reviewed worker-specific isolation profiles only')
        for profile,pin in profiles.items():
            if (type(pin) is not dict or set(pin)!={'path','sha256'} or
                pin['sha256']!=DockerValidationWorker.REVIEWED_PROFILES[profile] or
                type(pin['path']) is not str or not Path(pin['path']).is_absolute()):
                raise ValueError('Use exact reviewed isolation policy references')
        result[name]=WorkerRegistration(endpoint,json.dumps(profiles,sort_keys=True).encode())
    return result
