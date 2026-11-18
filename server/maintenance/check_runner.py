"""Trusted fixed image command. Never executes repository tests, plans or hooks."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def run():
    if sys.argv[1:] not in [['--baseline'], ['--upgrade']]:
        raise ValueError('Select a fixed reviewed validation mode')
    upgrade = sys.argv[1] == '--upgrade'
    work = Path('/tmp/maintenance-check')
    work.mkdir(mode=0o700)
    shutil.copytree('/work/source', work, dirs_exist_ok=True)
    for path in [work, *work.rglob('*')]:
        path.chmod(0o700 if path.is_dir() else 0o600)
    env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/tmp', 'TMPDIR': '/tmp',
           'TF_CLI_CONFIG_FILE': '/opt/terraform.rc', 'CHECKPOINT_DISABLE': '1',
           'TF_IN_AUTOMATION': '1', 'AWS_EC2_METADATA_DISABLED': 'true'}
    steps = []
    for command in [
        ['/usr/local/bin/terraform', 'init', '-backend=false', '-input=false', *(['-upgrade'] if upgrade else []), '-no-color'],
        ['/usr/local/bin/terraform', 'validate', '-json'],
    ]:
        result = subprocess.run(command, cwd=work, env=env, capture_output=True, text=True, timeout=120)
        steps.append({'command': command[1:], 'exitCode': result.returncode,
                      'stdout': result.stdout, 'stderr': result.stderr})
        if result.returncode:
            break
    lock = work / '.terraform.lock.hcl'
    report = {'schemaVersion': 1, 'steps': steps, 'lock': lock.read_text() if lock.exists() else None}
    if steps[-1]['exitCode'] == 0:
        schema = subprocess.run(['/usr/local/bin/terraform', 'providers', 'schema', '-json'],
                                cwd=work, env=env, capture_output=True, text=True, timeout=120)
        if schema.returncode:
            report['schemaError'] = True
            print(json.dumps(report))
            return 1
        queue = json.loads(schema.stdout)['provider_schemas']['registry.terraform.io/hashicorp/aws']['resource_schemas']['aws_batch_job_queue']
        report['queueSchema'] = queue
    print(json.dumps(report))
    return steps[-1]['exitCode']


if __name__ == '__main__':
    sys.exit(run())
