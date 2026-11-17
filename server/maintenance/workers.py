"""Explicitly registered, qualified immutable tools; fail closed without local Docker."""
import hashlib
import io
import json
import platform
import sys
from pathlib import Path
import zipfile
from uuid import uuid4
from dataclasses import replace

from server.local_validation import DockerValidationWorker, ValidationSpec
from .inventory import safe_path, SECRET
from .store import digest

PROFILE = 'terraform-maintenance-v1'


def archive_files(files):
    if len(files) > 1000 or sum(len(t.encode()) for t in files.values()) > 8_000_000:
        raise ValueError('Validation source exceeds reviewed bounds')
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as archive:
        for path, text in sorted(files.items()):
            safe_path(path)
            # Deterministic archives: timestamps are not evidence of source changes.
            entry = zipfile.ZipInfo(path, date_time=(2020, 1, 1, 0, 0, 0))
            entry.external_attr = 0o100444 << 16
            archive.writestr(entry, text.encode('utf-8'))
    return data.getvalue()


def sanitize(text):
    return SECRET.sub('[REDACTED]', text)


class MaintenanceWorker:
    def __init__(self, config, qualification):
        if set(config) != {'schemaVersion', 'imageId', 'platform', 'endpoint', 'qualificationDigest', 'runnerDigest'} or config['schemaVersion'] != 1:
            raise ValueError('Invalid operator maintenance configuration')
        if config['platform'] != 'linux/arm64':
            raise ValueError('This maintenance image/platform is not qualified')
        if (sys.platform, platform.machine()) != ('darwin', 'arm64'):
            raise ValueError('This maintenance host OS is not qualified; inventory and export remain available')
        if config['runnerDigest'] != hashlib.sha256(Path(__file__).with_name('check_runner.py').read_bytes()).hexdigest():
            raise ValueError('Maintenance runner changed; rebuild and qualify the image')
        self.config = dict(config)
        self.controller = DockerValidationWorker(config['endpoint'], max_output_bytes=500_000)
        if (config['qualificationDigest'] != digest(qualification) or qualification.get('status') != 'passed'
            or qualification.get('imageId') != config['imageId'] or qualification.get('platform') != config['platform']
            or qualification.get('runnerDigest') != config['runnerDigest']
            or qualification.get('controllerPolicyDigest') != self.controller.policy_digest):
            raise ValueError('Independent maintenance isolation evidence is missing or stale')
        self.spec = ValidationSpec('terraform-maintenance', config['imageId'],
                                   ('/usr/local/bin/python3', '-I', '/opt/maintenance_check.py'),
                                   platform=config['platform'], timeout_seconds=240, isolation_profile=PROFILE)
        self.identity = digest({'config': config, 'controllerPolicy': self.controller.policy_digest,
                                'adapter': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})

    @classmethod
    def from_file(cls, path):
        path = Path(path)
        if path.is_symlink() or path.with_suffix('.qualification.json').is_symlink():
            raise ValueError('Linked operator registration denied')
        return cls(json.loads(path.read_text()), json.loads(path.with_suffix('.qualification.json').read_text()))

    def check(self, files, *, kind='baseline', cancel_event=None, execution_id=None):
        if kind not in {'baseline', 'control', 'candidate'}:
            raise ValueError('Unreviewed validation mode')
        archive = archive_files(files)
        artifact = hashlib.sha256(archive).hexdigest()
        if cancel_event is not None and cancel_event.is_set():
            return {'status': 'failed', 'reason': 'cancelled', 'output': '', 'artifactSha256': artifact,
                    'durationSeconds': 0.0, 'exitCode': None, 'report': None}
        spec = replace(self.spec, command=(*self.spec.command, '--baseline' if kind == 'baseline' else '--upgrade'))
        execution_id = execution_id or str(uuid4())
        result = self.controller.run(archive, artifact, spec, execution_id=execution_id, cancel_event=cancel_event)
        try:
            self.controller.recover(execution_id)
            result['cleanupConfirmed'] = True
        except (RuntimeError, OSError):
            result['cleanupConfirmed'] = False
            result['status'], result['reason'] = 'failed', 'container_cleanup_unconfirmed'
        # Never persist unsanitized provider diagnostics or feed them to a model.
        result['output'] = sanitize(result['output'])
        result['report'] = None
        if result['reason'] is None and not result['outputTruncated']:
            try:
                report = json.loads(result['output'])
                if report.get('schemaVersion') == 1 and isinstance(report.get('steps'), list):
                    result['report'] = report
            except (ValueError, AttributeError):
                pass
        if result['status'] == 'passed':
            report = result['report']
            if not report or report.get('schemaError') or len(report['steps']) != 2:
                result['status'] = 'failed'
                result['reason'] = 'independent_report_missing'
            else:
                try:
                    check = json.loads(report['steps'][1]['stdout'])
                    valid = check['valid'] is True and check['error_count'] == 0 and report.get('queueSchema')
                except (ValueError, KeyError, TypeError):
                    valid = False
                if not valid:
                    result['status'] = 'failed'
                    result['reason'] = 'schema_check_incomplete'
        return result
