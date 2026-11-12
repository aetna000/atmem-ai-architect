"""Read-only delivery projection and lossless handoff packaging; no model or tools."""
import hashlib
import io
import json
from pathlib import PurePosixPath
import zipfile
from .engineering_contexts import validate_context
from .engineering_sessions import SessionError


def digest(content):
    return hashlib.sha256(content).hexdigest()


def design_value(content, project):
    value = validate_context(content, project)
    # Export time changes on every autosave; every other field remains evidence.
    value.get('meta', {}).pop('updatedAt', None)
    return value


def design_digest(content, project):
    return digest(json.dumps(design_value(content, project), sort_keys=True, ensure_ascii=False,
                             separators=(',', ':'), allow_nan=False).encode())


class EngineeringHandoff:
    def __init__(self, worker):
        self.worker = worker

    def inspect(self, scope, saved):
        worker = self.worker
        current = design_value(saved, scope.project)
        row = worker.store.db.execute('''SELECT a.session,a.id FROM engineering_artifacts a
            JOIN engineering_sessions s ON s.id=a.session
            WHERE s.tenant=? AND s.project=? ORDER BY a.rowid DESC LIMIT 1''',
            (scope.tenant, scope.project)).fetchone()
        if row is None:
            return {'artifact': None, 'savedDesignSha256': design_digest(saved, scope.project), 'relation': 'not_implemented'}
        # Metadata only: do not load the archive or recover/execute a native job.
        manifests = worker.artifacts.manifests(scope, row['session'])
        manifest = next((item for item in manifests if item['id'] == row['id']), None)
        if manifest is None:
            raise SessionError('The captured package receipt is unavailable. Refresh Delivery.')
        job = worker.jobs.state(scope, row['session'])
        context = None
        current_run = (job['state'] == 'idle' and job['last_status'] == 'completed'
                       and job['run'] == manifest['runId'] and manifest.get('turnStatus') == 'completed'
                       and manifest.get('kind') == 'delivery')
        if current_run:
            try:
                context, _ = worker.reconciliation.submitted_context(scope, row['session'])
            except SessionError:
                pass
        relation = 'earlier_turn' if not current_run else 'unknown'
        if context:
            relation = 'matches_saved_design' if design_value(context['content'].encode(), scope.project) == current else 'design_changed'
        checks = worker.checks.list(scope, row['session'], manifest['id'])
        if any(check.get('artifactSha256') != manifest['sha256'] for check in checks):
            raise SessionError('A check receipt does not match this package. No combined handoff was prepared.')
        return {'session': job, 'artifact': manifest, 'checks': checks,
                'context': context, 'relation': relation, 'canPackage': bool(context and current_run),
                'savedDesignSha256': design_digest(saved, scope.project), 'savedFileSha256': digest(saved), 'acceptance': 'not_established_by_capture_or_local_checks'}

    def package(self, scope, saved, session, artifact, saved_sha):
        report = self.inspect(scope, saved)
        manifest = report.get('artifact')
        if report['savedDesignSha256'] != saved_sha:
            raise SessionError('Your saved design changed. Refresh Delivery before downloading its handoff.')
        if not manifest or manifest['id'] != artifact or manifest['sessionId'] != session or not report['canPackage']:
            raise SessionError('This implementation changed or lacks its submitted design receipt. Refresh Delivery; the original package remains available.')
        original, archive = self.worker.artifacts.get(scope, session, artifact)
        if original != manifest or digest(archive) != manifest['sha256']:
            raise SessionError('The captured package integrity check failed. No handoff was downloaded.')
        # Keep the exact original archive as well as a browsable receiving tree.
        # The archive digest remains independently verifiable after unpacking.
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as target:
            with zipfile.ZipFile(io.BytesIO(archive)) as source:
                entries = source.infolist()
                expected = {entry['path']: entry for entry in manifest['files']}
                if len(entries) != len(expected) or len({entry.filename for entry in entries}) != len(entries):
                    raise SessionError('The captured package directory disagrees with its receipt.')
                for entry in entries:
                    name = entry.filename
                    path = PurePosixPath(name)
                    if name not in expected or path.is_absolute() or '\\' in name or any(part in {'', '.', '..'} for part in name.rstrip('/').split('/')):
                        raise SessionError('The captured package has an unsafe or unrecorded file.')
                    record = expected[name]
                    content = source.read(entry)
                    if record['kind'] == 'file' and (len(content) != record['bytes'] or digest(content) != record['sha256']):
                        raise SessionError('A captured file disagrees with its receipt.')
                    copied = zipfile.ZipInfo('implementation/' + name, entry.date_time)
                    copied.external_attr = entry.external_attr
                    copied.compress_type = zipfile.ZIP_DEFLATED
                    target.writestr(copied, content)
            target.writestr('evidence/original-implementation.zip', archive)
            target.writestr('evidence/artifact-receipt.json', json.dumps(manifest, indent=2, ensure_ascii=False))
            target.writestr('evidence/local-checks.json', json.dumps(report['checks'], indent=2, ensure_ascii=False))
            target.writestr('design/submitted-project.json', report['context']['content'])
            target.writestr('design/latest-saved-project.json', saved)
            target.writestr('evidence/delivery.json', json.dumps({key: report[key] for key in
                ('relation', 'savedDesignSha256', 'savedFileSha256', 'acceptance')}, indent=2))
            target.writestr('START_HERE.md', '# Architect handoff\n\n'
                'Open implementation/ for the captured implementation, its Spec Kit (for example spec-kit/ or specs/<feature>/) and supplied run instructions. '
                'Missing files remain implementation work; this wrapper does not invent them.\n\n'
                f'Design relationship: {report["relation"]}. '
                'Compare design/submitted-project.json with design/latest-saved-project.json before continuing. '
                'New requirements in the latter are not proven implemented by an earlier package.\n\n'
                'Evidence is under evidence/. Local checks apply only to the captured artifact. '
                'Capture, model completion and local checks do not establish full project acceptance or cloud deployment.\n\n'
                f'Original implementation ZIP SHA-256: {manifest["sha256"]}. '
                'The exact original archive is retained in evidence/original-implementation.zip.\n')
        return output.getvalue(), manifest
