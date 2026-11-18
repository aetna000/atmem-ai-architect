#!/usr/bin/env python3
"""Interactive local broker setup. No account token may be supplied in arguments."""
import argparse
from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.maintenance.github_adapter import GitHubBroker
from server.maintenance.store import Store


def main():
    parser = argparse.ArgumentParser(description='Manage scoped maintenance GitHub connections in the OS keychain.')
    parser.add_argument('--home', type=Path, required=True)
    args = parser.parse_args()
    if not sys.stdin.isatty():
        raise ValueError('Use an interactive terminal; credentials cannot be piped or passed as arguments')
    broker = GitHubBroker(Store(args.home / 'maintenance.sqlite'))
    action = input('Action (connect / revoke / materialize): ').strip()
    tenant = 'local-owner'
    project = input('Architect project ID: ').strip()
    if action == 'connect':
        owner = input('GitHub resource owner (one account or organization): ').strip()
        repositories = [r.strip() for r in input('Selected owner/repository names, comma-separated: ').split(',') if r.strip()]
        expiry = input('Token expiry (YYYY-MM-DD, UTC): ').strip()
        stamp = int(datetime.strptime(expiry, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp())
        print('Use a fine-grained token for these repositories only: metadata read, contents read/write, pull requests read/write.')
        print('No workflow, organization administration, merge or release permission is requested.')
        print('This action performs identity and selected-repository reads. It grants no publication authorization.')
        if input('Connect this project and repository selection? Type connect: ').strip() != 'connect':
            return
        token = getpass.getpass('Fine-grained token (stored only in OS keychain): ')
        try:
            connected = broker.register(tenant, [project], owner, repositories, token, stamp)
        finally:
            token = None
        print(json.dumps(connected.model_dump(), indent=2))
    elif action == 'revoke':
        connection = input('Connection ID: ').strip()
        print(json.dumps(broker.revoke(tenant, project, connection), indent=2))
    elif action == 'materialize':
        connection = input('Connection ID: ').strip()
        repository = input('Selected owner/repository: ').strip()
        commit = input('Exact immutable commit: ').strip()
        paths = [p.strip() for p in input('Complete selected-root configuration and automation paths, comma-separated: ').split(',') if p.strip()]
        destination = Path(input('New snapshot JSON destination: ').strip()).expanduser()
        if destination.exists():
            raise ValueError('Use a new destination; existing files are never overwritten')
        if input('Fetch this exact selected source? Type fetch: ').strip() != 'fetch':
            return
        value = broker.materialize(tenant, project, connection, repository, commit, paths)
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        with os.fdopen(fd, 'w') as output:
            output.write(value.model_dump_json(indent=2) + '\n')
        print('Private source snapshot saved. This is not model-egress or publication approval.')
    else:
        raise ValueError('Choose connect, revoke or materialize')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, PermissionError, RuntimeError, OSError) as error:
        print('Maintenance broker: ' + str(error), file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        sys.exit(130)
