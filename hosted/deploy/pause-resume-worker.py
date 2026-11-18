#!/usr/bin/env python3
"""Pause/resume the retained Architect VM; never provision or delete resources.

Read-only status is the default. `start` is an explicit paid-compute action and
resumes existing queued work. Readiness checks do not submit any model job.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = Path(__file__).with_name('worker-pause-config.json')
CREDENTIAL = re.compile(r'github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}')


def now():
    return datetime.now(timezone.utc).isoformat()


def run(parts, *, timeout=180):
    result = subprocess.run(parts, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or 'Google Cloud command failed').strip()[-3000:])
    return result.stdout


def cloud(config, *parts, timeout=180):
    return run(['gcloud', *parts, '--project=' + config['project'], '--quiet'], timeout=timeout)


def describe(config):
    return json.loads(cloud(config, 'compute', 'instances', 'describe', config['instance'],
                            '--zone=' + config['zone'], '--format=json', timeout=45))


def identity(config, row):
    if row.get('name') != config['instance'] or str(row.get('id')) != config['instanceId'] or row.get('zone', '').rsplit('/', 1)[-1] != config['zone']:
        raise RuntimeError('The retained VM identity changed. Review the saved binding; no VM was started or stopped.')


def summarize(row):
    metadata = {item['key']: item.get('value', '') for item in row.get('metadata', {}).get('items', [])}
    script = metadata.get('startup-script', '')
    return {
        'instanceId': str(row['id']), 'name': row['name'], 'zone': row['zone'].rsplit('/', 1)[-1],
        'machineType': row['machineType'].rsplit('/', 1)[-1], 'deletionProtection': row.get('deletionProtection'),
        'labels': row.get('labels', {}), 'tags': row.get('tags', {}).get('items', []),
        'scheduling': row.get('scheduling', {}),
        'serviceAccounts': [{'email': s['email'], 'scopes': sorted(s.get('scopes', []))} for s in row.get('serviceAccounts', [])],
        'disks': sorted([{'source': d['source'], 'boot': d.get('boot', False), 'autoDelete': d.get('autoDelete', False),
                          'deviceName': d['deviceName'], 'sizeGb': int(d.get('diskSizeGb', 0)), 'mode': d.get('mode'),
                          'interface': d.get('interface')} for d in row.get('disks', [])], key=lambda d: d['source']),
        'networks': [{'name': n.get('name'), 'network': n['network'], 'subnetwork': n.get('subnetwork'), 'networkIP': n.get('networkIP'),
                      'accessConfigs': [{k: a.get(k) for k in ['name', 'type', 'networkTier']} for a in n.get('accessConfigs', [])]}
                     for n in row.get('networkInterfaces', [])],
        'metadata': {k: metadata[k] for k in ['block-project-ssh-keys', 'serial-port-enable'] if k in metadata},
        'startupScriptSha256': hashlib.sha256(script.encode()).hexdigest(),
        'shieldedInstanceConfig': row.get('shieldedInstanceConfig', {}),
    }


def tracked_matches(config, row):
    summary = summarize(row)
    disks = sorted([{'name': d['source'].rsplit('/', 1)[-1], 'boot': d['boot'], 'deviceName': d['deviceName'],
                     'autoDelete': d['autoDelete'], 'sizeGb': d['sizeGb']} for d in summary['disks']], key=lambda d: d['name'])
    expected = sorted(config['disks'], key=lambda d: d['name'])
    network = row.get('networkInterfaces', [])
    return (summary['machineType'] == config['machineType'] and disks == expected and
            summary['startupScriptSha256'] == config['startupScriptSha256'] and
            [s['email'] for s in summary['serviceAccounts']] == [config['serviceAccount']] and
            len(network) == 1 and network[0]['network'].rsplit('/', 1)[-1] == config['network'] and
            network[0].get('subnetwork', '').rsplit('/', 1)[-1] == config['subnet'] and
            network[0].get('networkIP') == config['internalIp'])


def public_ips(row):
    return [a['natIP'] for n in row.get('networkInterfaces', []) for a in n.get('accessConfigs', []) if a.get('natIP')]


def write_private(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise RuntimeError('Private pause state cannot be a symlink')
    data = json.dumps(value, indent=2, ensure_ascii=False) + '\n'
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(descriptor, 'w') as file:
        file.write(data)
    os.chmod(path, 0o600)


def capture(config, row, state_dir):
    snapshot = {'schemaVersion': 1, 'capturedAt': now(), 'project': config['project'], 'configuration': summarize(row),
                'status': row['status'], 'publicIPs': public_ips(row), 'sanitizedReportIncludesCredentials': False}
    write_private(state_dir / 'latest-pause.json', snapshot)
    metadata = {item['key']: item.get('value', '') for item in row.get('metadata', {}).get('items', [])}
    script = metadata.get('startup-script', '')
    # Raw startup metadata remains private and untracked. Pattern scanning is
    # limited; never treat this optional backup as publishable or secret-free.
    if script and not CREDENTIAL.search(script):
        target = state_dir / 'startup-script-preserved.sh'
        if target.is_symlink():
            raise RuntimeError('Private startup copy cannot be a symlink')
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        with os.fdopen(descriptor, 'w') as file:
            file.write(script)
        os.chmod(target, 0o600)
    return snapshot


def readiness(config, *, timeout):
    probe = '''import fcntl,json,os,socket,stat
from pathlib import Path
root=Path('/var/lib/architect/runtime')
sock=root/'broker.sock'
checks={'brokerSocket':sock.exists() and stat.S_ISSOCK(sock.stat().st_mode),'singletonLockHeld':False,'brokerAccepting':False}
if checks['brokerSocket']:
 connection=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);connection.settimeout(5)
 try:connection.connect(str(sock));checks['brokerAccepting']=True
 finally:connection.close()
if (root/'worker.lock').exists():
 with (root/'worker.lock').open('r') as file:
  try:fcntl.flock(file,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(file,fcntl.LOCK_UN)
  except BlockingIOError:checks['singletonLockHeld']=True
print(json.dumps(checks))
raise SystemExit(0 if all(checks.values()) else 1)
'''
    command = '\n'.join([
        'set -eu',
        'test "$(sudo systemctl is-active architect-native-worker.service)" = active',
        'test "$(sudo docker inspect -f ' + shlex.quote('{{.State.Running}}') + ' architect-native-worker)" = true',
        'mountpoint -q /mnt/disks/architect-state',
        'sudo docker exec architect-native-worker python -c ' + shlex.quote(probe),
    ])
    deadline, error = time.monotonic() + timeout, None
    while time.monotonic() < deadline:
        try:
            output = cloud(config, 'compute', 'ssh', config['instance'], '--zone=' + config['zone'], '--tunnel-through-iap',
                           '--command=' + command, timeout=min(60, max(5, int(deadline - time.monotonic()))))
            lines = [line for line in output.splitlines() if line.startswith('{')]
            checks = json.loads(lines[-1])
            if all(checks.values()):
                return {'ready': True, 'systemd': 'active', 'containerRunning': True, 'stateMounted': True, **checks,
                        'modelJobsSubmitted': 0, 'idleHeartbeat': 'not implemented; no synthetic heartbeat claimed'}
        except (RuntimeError, subprocess.TimeoutExpired, ValueError, IndexError) as failure:
            error = str(failure)[-1000:]
        if deadline - time.monotonic() > 5:
            time.sleep(5)
    return {'ready': False, 'detail': error or 'Worker readiness did not confirm before timeout', 'modelJobsSubmitted': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['status', 'stop', 'start'], default='status', nargs='?')
    parser.add_argument('--state-dir', type=Path, default=ROOT / '.local/worker-pause-resume')
    parser.add_argument('--dry-run', action='store_true', help='Read current state and show commands without changing compute')
    parser.add_argument('--check-ready', action='store_true', help='IAP readiness check on an already running VM')
    parser.add_argument('--ready-timeout', type=int, default=300)
    args = parser.parse_args()
    if not 30 <= args.ready_timeout <= 600:
        parser.error('Readiness timeout must be 30–600 seconds')
    config = json.loads(CONFIG_PATH.read_text())
    state_dir = args.state_dir.expanduser().resolve()
    row = describe(config);identity(config, row)
    snapshot_path = state_dir / 'latest-pause.json'
    baseline = json.loads(snapshot_path.read_text()) if snapshot_path.exists() else None
    changed = baseline is not None and baseline['configuration'] != summarize(row)
    report = {'action': args.action, 'project': config['project'], 'instance': config['instance'], 'zone': config['zone'],
              'status': row['status'], 'verifiedServiceAccounts': [s['email'] for s in row.get('serviceAccounts', [])], 'machineType': row['machineType'].rsplit('/', 1)[-1], 'trackedBindingMatches': tracked_matches(config, row),
              'publicIPs': public_ips(row), 'configurationMatchesPaused': not changed if baseline else None,
              'preservedDisks': [d['source'].rsplit('/', 1)[-1] for d in row.get('disks', [])], 'stateDir': str(state_dir),
              'deletionPerformed': False, 'provisioningPerformed': False, 'modelJobsSubmitted': 0}
    action = ['gcloud', 'compute', 'instances', args.action, config['instance'], '--project=' + config['project'], '--zone=' + config['zone'], '--quiet']
    if args.dry_run:
        report.update(dryRun=True, command=action if args.action != 'status' else None, readinessAfterStart=True)
        print(json.dumps(report, indent=2));return 0
    if args.action == 'stop':
        if row['status'] not in {'TERMINATED', 'RUNNING'}:
            raise RuntimeError('VM is in a transitional state; inspect status before repeating stop')
        if row['status'] == 'TERMINATED' and baseline is not None:
            if changed:
                report.update(alreadyStopped=True, storageChargesContinue=True, detail='Paused configuration drift detected; original pause baseline and startup backup were preserved.')
                print(json.dumps(report, indent=2));return 1
            before = baseline
        elif row['status'] == 'TERMINATED' and not tracked_matches(config, row):
            report.update(alreadyStopped=True, storageChargesContinue=True, detail='No pause baseline; changed tracked configuration was not adopted. Review before starting.')
            print(json.dumps(report, indent=2));return 1
        else:
            before = capture(config, row, state_dir)
        if row['status'] != 'TERMINATED':
            print('Stopping the retained Architect VM; preserving disks and deployment metadata.', file=sys.stderr)
            run(action, timeout=300)
        row = describe(config);identity(config, row)
        if row['status'] != 'TERMINATED' or public_ips(row):
            raise RuntimeError('Stopped state and ephemeral IP release have not both been confirmed')
        if before['configuration'] != summarize(row):
            raise RuntimeError('VM configuration changed during stop; review private snapshots before restarting')
        addresses = json.loads(cloud(config, 'compute', 'addresses', 'list', '--format=json'))
        retained = [a['name'] for a in addresses if a.get('address') in before['publicIPs'] or any('/instances/' + config['instance'] in u for u in a.get('users', []))]
        report.update(status=row['status'], publicIPs=public_ips(row), configurationMatchesPaused=True,
                      retainedReservedAddresses=retained, vmComputeChargesWhileStopped=False,
                      storageChargesContinue=True, stoppedAt=now())
        write_private(state_dir / 'last-operation.json', report)
    elif args.action == 'start':
        if changed:
            raise RuntimeError('The paused configuration changed. Review the private snapshot; nothing was started.')
        if baseline is None:
            if not tracked_matches(config, row):
                raise RuntimeError('No pause record and live deployment differs from the tracked binding. Capture/review before starting.')
            baseline = capture(config, row, state_dir)
        if row['status'] not in {'TERMINATED', 'RUNNING'}:
            raise RuntimeError('VM is in a transitional state; inspect before starting')
        if row['status'] == 'TERMINATED':
            print('Starting the retained VM. Existing queued work may resume; no new model test is submitted.', file=sys.stderr)
            run(action, timeout=300)
        row = describe(config);identity(config, row)
        if row['status'] != 'RUNNING':
            raise RuntimeError('VM is not RUNNING after the start operation')
        if baseline and baseline['configuration'] != summarize(row):
            raise RuntimeError('VM is running, but the saved configuration no longer matches; verify before declaring readiness')
        report.update(status=row['status'], publicIPs=public_ips(row), readiness=readiness(config, timeout=args.ready_timeout),
                      ephemeralIpMayHaveChanged=True, dnsChangeRequiredForQueueDeployment=False)
        write_private(state_dir / 'last-operation.json', report)
    elif args.check_ready:
        report['readiness'] = readiness(config, timeout=args.ready_timeout) if row['status'] == 'RUNNING' else {'ready': False, 'detail': 'VM is stopped'}
    print(json.dumps(report, indent=2))
    return 1 if args.action == 'start' and not report['readiness']['ready'] else 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        print('Architect worker: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
