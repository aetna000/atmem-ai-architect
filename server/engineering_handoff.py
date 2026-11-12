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


def same_design(submitted, current, session, events):
    """Ignore only exact acknowledged conversation mirrors, never new intent.

    The UI records accepted requests after submission. Those entries already
    belong to the native conversation; all source snapshots stay unmodified.
    Preserve missing history, unresolved/forged entries, mappings and revisions.
    """
    if submitted == current:
        return True
    accepted = {e.get('requestId') for e in events if e.get('kind') == 'steering_accepted'}
    trusted = {}
    for event in events:
        if ((event.get('kind') == 'accepted' and event.get('origin') != 'automatic_repair')
                or (event.get('kind') == 'steering_submitted' and event.get('requestId') in accepted)):
            if type(event.get('sequence')) is int and isinstance(event.get('text'), str):
                ident = f'{session}:{event["sequence"]}'
                trusted[ident] = {'id': ident, 'sessionId': session, 'sequence': event['sequence'],
                                  'text': event['text'], 'status': 'accepted'}
    def intents(value):
        extensions = value.get('extensions', {})
        work = extensions.get('architectureWork', {}) if isinstance(extensions, dict) else {}
        return work.get('intents', []) if isinstance(work, dict) else None
    before, after = intents(submitted), intents(current)
    if not isinstance(before, list) or not isinstance(after, list) or len(before)>1000 or len(after)>1000:
        return False
    by_id = {}
    for row in after:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or row['id'] in by_id:
            return False
        by_id[row['id']] = row
    if any(not isinstance(row, dict) or not isinstance(row.get('id'), str) or by_id.get(row['id']) != row for row in before):
        return False
    def projection(value):
        value = json.loads(json.dumps(value))
        extensions = value.get('extensions')
        work = extensions.get('architectureWork') if isinstance(extensions, dict) else None
        if isinstance(work, dict) and isinstance(work.get('intents'), list):
            work['intents'] = [row for row in work['intents'] if trusted.get(row['id']) != row]
            empty = {'version': 2, 'records': [], 'intents': [], 'snapshots': [],
                     'bindings': [], 'history': [], 'artifactMappings': []}
            if work == empty:
                del extensions['architectureWork']
        if extensions == {}:
            del value['extensions']
        return value
    return projection(submitted) == projection(current)


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
        events = []
        current_run = (job['state'] == 'idle' and job['last_status'] == 'completed'
                       and job['run'] == manifest['runId'] and manifest.get('turnStatus') == 'completed'
                       and manifest.get('kind') == 'delivery')
        if current_run:
            try:
                context, events = worker.reconciliation.submitted_context(scope, row['session'])
            except SessionError:
                pass
        relation = 'earlier_turn' if not current_run else 'unknown'
        if context:
            relation = 'matches_saved_design' if same_design(design_value(context['content'].encode(), scope.project), current, row['session'], events) else 'design_changed'
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
