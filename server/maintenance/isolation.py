"""Real local-container hostile qualification. No test source reaches a host shell."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import time

from server.local_validation import DockerValidationWorker, ValidationSpec
from .workers import archive_files, PROFILE


def qualify(endpoint, image, platform):
    controller = DockerValidationWorker(endpoint, max_output_bytes=4096)
    spec = ValidationSpec('maintenance-isolation', image, ('/usr/local/bin/python3', '-I', 'probe.py'),
                          platform=platform, timeout_seconds=10, isolation_profile=PROFILE)
    results = {}
    with tempfile.TemporaryDirectory(prefix='atmem-maintenance-host-canary-') as directory:
        sentinel = Path(directory) / 'private'
        sentinel.write_text('private-host-sentinel')
        probe = '''import os,pathlib,socket,json
findings={}
findings['uid_dropped']=os.getuid()==65532 and os.getgid()==65532
findings['credentials_absent']=not any(k in os.environ for k in ['OPENROUTER_API_KEY','GH_TOKEN','GOOGLE_APPLICATION_CREDENTIALS','AWS_ACCESS_KEY_ID','ATMEM_HOST_CANARY'])
for key,path in [('host_secret',HOST_PATH),('docker_socket','/var/run/docker.sock'),('host_home','/Users')]:
 try: pathlib.Path(path).open('rb').read(1); findings[key]=False
 except (OSError,PermissionError):findings[key]=True
for key,path in [('source_readonly','/work/source/probe.py'),('image_readonly','/opt/maintenance_check.py')]:
 try:pathlib.Path(path).write_text('changed');findings[key]=False
 except OSError:findings[key]=True
try:os.setuid(0);findings['privilege_denied']=False
except OSError:findings['privilege_denied']=True
try:
 s=socket.create_connection(('1.1.1.1',443),timeout=1);s.close();findings['network_denied']=False
except OSError:findings['network_denied']=True
link=pathlib.Path('/tmp/host-link');link.symlink_to(HOST_PATH)
try:link.read_bytes();findings['symlink_escape_denied']=False
except OSError:findings['symlink_escape_denied']=True
print(json.dumps(findings))
assert all(findings.values())
'''.replace('HOST_PATH', repr(str(sentinel)))
        archive = archive_files({'probe.py': probe})
        result = controller.run(archive, hashlib.sha256(archive).hexdigest(), spec)
        results['hostile'] = {'status': result['status'], 'findings': json.loads(result['output']) if result['status'] == 'passed' else {}, 'reason': result['reason']}
    for name, source, seconds, cancel in [
        ('timeout', 'import time; time.sleep(30)', 1, None),
        ('cancel', 'import time; time.sleep(30)', 10, threading.Event()),
        ('output_bound', 'print("x"*10000)', 10, None),
    ]:
        archive = archive_files({'probe.py': source})
        bounded = ValidationSpec('maintenance-isolation', image, spec.command, platform=platform,
                                 timeout_seconds=seconds, isolation_profile=PROFILE)
        timer = threading.Timer(.5, cancel.set) if cancel is not None else None
        if timer:
            timer.start()
        try:
            result = controller.run(archive, hashlib.sha256(archive).hexdigest(), bounded, cancel_event=cancel)
            expected = {'timeout': 'timeout', 'cancel': 'cancelled', 'output_bound': 'output_limit'}[name]
            okay = result['status'] == 'failed' and (result['reason'] == expected or name == 'output_bound' and result['outputTruncated'])
            results[name] = {'status': 'passed' if okay else 'failed', 'observedReason': result['reason']}
        finally:
            if timer:
                timer.cancel()
    return {'schemaVersion': 1, 'status': 'passed' if all(x['status'] == 'passed' for x in results.values()) else 'failed',
            'imageId': image, 'platform': platform, 'isolationProfile': PROFILE,
            'controllerPolicyDigest': controller.policy_digest,
            'runnerDigest': hashlib.sha256(Path(__file__).with_name('check_runner.py').read_bytes()).hexdigest(),
            'results': results, 'qualifiedAt': time.time(),
            'limits': ['Local Linux containers only; no cloud, deployment, hypervisor escape or Windows qualification.']}
