"""Private publication ledger. Portable campaign data never restores authority."""
import json
import time
from uuid import uuid4

from .store import Conflict, digest


class PublicationStore:
    def __init__(self, store):
        self.store = store
        with store.transaction() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS publication_installation (id TEXT PRIMARY KEY, nonce TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS publication_previews (
                id TEXT PRIMARY KEY, tenant TEXT NOT NULL, project TEXT NOT NULL, campaign TEXT NOT NULL,
                digest TEXT NOT NULL, payload TEXT NOT NULL, created REAL NOT NULL);
              CREATE TABLE IF NOT EXISTS publication_authorizations (
                id TEXT PRIMARY KEY, tenant TEXT NOT NULL, project TEXT NOT NULL, preview TEXT NOT NULL,
                digest TEXT NOT NULL, expires REAL NOT NULL, state TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS publication_operations (
                id TEXT PRIMARY KEY, preview TEXT NOT NULL, action INTEGER NOT NULL,
                body_digest TEXT NOT NULL, payload TEXT NOT NULL, state TEXT NOT NULL, result TEXT,
                UNIQUE(preview,action));
              CREATE TABLE IF NOT EXISTS publication_leases (
                preview TEXT PRIMARY KEY, epoch INTEGER NOT NULL, owner TEXT NOT NULL, expires REAL NOT NULL);
              CREATE TABLE IF NOT EXISTS publication_claims (
                repository INTEGER NOT NULL, branch TEXT NOT NULL, tenant TEXT NOT NULL,
                project TEXT NOT NULL, campaign TEXT NOT NULL, nonce TEXT NOT NULL, head TEXT NOT NULL, manifest TEXT,
                PRIMARY KEY(repository,branch));
              CREATE TABLE IF NOT EXISTS publication_pr_observations (
                tenant TEXT NOT NULL, project TEXT NOT NULL, campaign TEXT NOT NULL, repository INTEGER NOT NULL,
                number INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(tenant,project,campaign,repository,number));
              CREATE TABLE IF NOT EXISTS publication_merge_observations (
                tenant TEXT NOT NULL, project TEXT NOT NULL, campaign TEXT NOT NULL, graph TEXT NOT NULL,
                root TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(tenant,project,campaign,root));
              CREATE TABLE IF NOT EXISTS publication_poll_cursors (
                tenant TEXT NOT NULL, project TEXT NOT NULL, campaign TEXT NOT NULL, next REAL NOT NULL,
                PRIMARY KEY(tenant,project,campaign));
              CREATE TABLE IF NOT EXISTS publication_release_observations (
                id TEXT PRIMARY KEY, tenant TEXT NOT NULL, project TEXT NOT NULL, campaign TEXT NOT NULL,
                digest TEXT NOT NULL, payload TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS publication_events (
                sequence INTEGER PRIMARY KEY, preview TEXT NOT NULL, operation TEXT,
                kind TEXT NOT NULL, at REAL NOT NULL);
            ''')
            if 'manifest' not in {row['name'] for row in db.execute('PRAGMA table_info(publication_claims)')} :
                db.execute('ALTER TABLE publication_claims ADD COLUMN manifest TEXT')
            row = db.execute("SELECT nonce FROM publication_installation WHERE id='local'").fetchone()
            if row is None:
                self.installation = str(uuid4())
                db.execute("INSERT INTO publication_installation VALUES('local',?)", (self.installation,))
            else:
                self.installation = row['nonce']

    @staticmethod
    def _event(db, preview, kind, operation=None):
        db.execute('INSERT INTO publication_events(preview,operation,kind,at) VALUES(?,?,?,?)',
                   (preview, operation, kind, time.time()))

    def preview(self, tenant, project, ident):
        with self.store.transaction() as db:
            row = db.execute('SELECT * FROM publication_previews WHERE id=? AND tenant=? AND project=?',
                             (ident, tenant, project)).fetchone()
        if row is None:
            raise PermissionError('Publication preview unavailable')
        value = json.loads(row['payload'])
        if digest(value) != row['digest']:
            raise ValueError('Private publication preview integrity mismatch')
        return {**value, 'digest': row['digest']}

    def save_preview(self, tenant, project, campaign, payload):
        encoded = json.dumps(payload, allow_nan=False, separators=(',', ':'), ensure_ascii=False)
        if len(encoded.encode()) > 64_000_000 or payload.get('tenant') != tenant or payload.get('project') != project:
            raise ValueError('Publication preview exceeds its scope or size bound')
        with self.store.transaction() as db:
            if db.execute('SELECT COUNT(*) FROM publication_previews WHERE tenant=? AND project=?', (tenant, project)).fetchone()[0] >= 100:
                raise ValueError('Publication preview retention bound reached; preserve audit before starting fresh')
            db.execute('INSERT INTO publication_previews VALUES(?,?,?,?,?,?,?)',
                       (payload['id'], tenant, project, campaign, digest(payload), encoded, time.time()))
            self._event(db, payload['id'], 'preview_created')
        return self.preview(tenant, project, payload['id'])

    def campaign_previews(self, tenant, project, campaign):
        with self.store.transaction() as db:
            rows = db.execute('SELECT id FROM publication_previews WHERE tenant=? AND project=? AND campaign=? ORDER BY created',
                              (tenant, project, campaign)).fetchall()
        return [self.preview(tenant, project, row['id']) for row in rows]

    def poll_due(self, tenant, project, campaign):
        with self.store.transaction() as db:
            row = db.execute('SELECT next FROM publication_poll_cursors WHERE tenant=? AND project=? AND campaign=?', (tenant, project, campaign)).fetchone()
            if row is not None and row['next'] > time.time():
                return False
            db.execute('INSERT OR REPLACE INTO publication_poll_cursors VALUES(?,?,?,?)', (tenant, project, campaign, time.time() + 30))
            return True

    def retain_pr(self, tenant, project, campaign, graph, root, payload, *, consumer=False):
        encoded = json.dumps(payload, allow_nan=False, separators=(',', ':'))
        if len(encoded) > 10000:
            raise ValueError('PR observation exceeds its bound')
        with self.store.transaction() as db:
            db.execute('INSERT OR REPLACE INTO publication_pr_observations VALUES(?,?,?,?,?,?)',
                       (tenant, project, campaign, payload['repositoryId'], payload['number'], encoded))
            if consumer and payload['merged']:
                previous = db.execute('SELECT payload FROM publication_merge_observations WHERE tenant=? AND project=? AND campaign=? AND root=?',
                                      (tenant, project, campaign, root)).fetchone()
                if previous is not None:
                    old = json.loads(previous['payload'])
                    if (old['repositoryId'], old['number'], old['head']) != (payload['repositoryId'], payload['number'], payload['head']):
                        raise Conflict('Merged consumer observation cannot be replaced by a different proposal')
                else:
                    db.execute('INSERT INTO publication_merge_observations VALUES(?,?,?,?,?,?)', (tenant, project, campaign, graph, root, encoded))

    def merged_consumers(self, tenant, project, campaign, graph):
        with self.store.transaction() as db:
            rows = db.execute('SELECT root,payload FROM publication_merge_observations WHERE tenant=? AND project=? AND campaign=? AND graph=? ORDER BY root',
                              (tenant, project, campaign, graph)).fetchall()
        return {row['root']: json.loads(row['payload']) for row in rows}

    def pr_observations(self, tenant, project, campaign):
        with self.store.transaction() as db:
            rows = db.execute('SELECT payload FROM publication_pr_observations WHERE tenant=? AND project=? AND campaign=?', (tenant, project, campaign)).fetchall()
        return [json.loads(row['payload']) for row in rows]

    def save_release_observation(self, tenant, project, campaign, payload):
        ident = str(uuid4())
        encoded = json.dumps(payload, allow_nan=False, separators=(',', ':'), ensure_ascii=False)
        if len(encoded.encode()) > 64000:
            raise ValueError('Release observation exceeds its explicit bound')
        with self.store.transaction() as db:
            count = db.execute('SELECT COUNT(*) FROM publication_release_observations WHERE tenant=? AND project=?', (tenant, project)).fetchone()[0]
            if count >= 1000:
                raise ValueError('Release observation retention bound reached')
            db.execute('INSERT INTO publication_release_observations VALUES(?,?,?,?,?,?)',
                       (ident, tenant, project, campaign, digest(payload), encoded))
        return ident

    def release_observation(self, tenant, project, campaign, ident):
        with self.store.transaction() as db:
            row = db.execute('SELECT * FROM publication_release_observations WHERE id=? AND tenant=? AND project=? AND campaign=?',
                             (ident, tenant, project, campaign)).fetchone()
        if row is None:
            raise PermissionError('Authenticated module release observation is unavailable')
        value = json.loads(row['payload'])
        if digest(value) != row['digest']:
            raise ValueError('Private release observation integrity mismatch')
        return value

    def authorize(self, tenant, project, preview, expected_digest, *, automation_accepted):
        current = self.preview(tenant, project, preview)
        if current['digest'] != expected_digest or automation_accepted is not True or time.time() > current['createdAt'] + 900:
            raise Conflict('Review the current exact preview and accept repository automation before confirming')
        ident, expiry = str(uuid4()), time.time() + 900
        with self.store.transaction() as db:
            # Reconfirmation never extends another in-flight authority silently.
            db.execute("UPDATE publication_authorizations SET state='revoked' WHERE preview=? AND state='active'", (preview,))
            db.execute('INSERT INTO publication_authorizations VALUES(?,?,?,?,?,?,?)',
                       (ident, tenant, project, preview, expected_digest, expiry, 'active'))
            self._event(db, preview, 'exact_wave_authorized')
        return {'id': ident, 'previewId': preview, 'previewDigest': expected_digest, 'expiresAt': expiry}

    def acquire(self, tenant, project, preview, authorization, expected_digest, seconds=900):
        if type(seconds) is not int or not 1 <= seconds <= 900:
            raise ValueError('Publication lease exceeds its bound')
        self.preview(tenant, project, preview)
        with self.store.transaction() as db:
            self._authorization(db, tenant, project, preview, authorization, expected_digest)
            current = db.execute('SELECT campaign FROM publication_previews WHERE id=?', (preview,)).fetchone()
            competing = db.execute('''SELECT 1 FROM publication_leases l JOIN publication_previews p ON p.id=l.preview
                WHERE p.tenant=? AND p.project=? AND p.campaign=? AND l.preview<>? AND l.expires>?''',
                (tenant, project, current['campaign'], preview, time.time())).fetchone()
            if competing is not None:
                raise Conflict('Another exact wave owns this campaign')
            row = db.execute('SELECT * FROM publication_leases WHERE preview=?', (preview,)).fetchone()
            if row is not None and row['expires'] > time.time():
                raise Conflict('Another coordinator owns this publication wave')
            db.execute("UPDATE publication_operations SET state='uncertain' WHERE preview=? AND state='in_flight'", (preview,))
            owner = str(uuid4())
            epoch = 1 if row is None else row['epoch'] + 1
            db.execute('INSERT OR REPLACE INTO publication_leases VALUES(?,?,?,?)', (preview, epoch, owner, time.time() + seconds))
            return owner, epoch

    @staticmethod
    def _authorization(db, tenant, project, preview, authorization, expected_digest):
        row = db.execute('SELECT * FROM publication_authorizations WHERE id=? AND tenant=? AND project=?',
                         (authorization, tenant, project)).fetchone()
        if row is None or row['preview'] != preview or row['digest'] != expected_digest or row['state'] != 'active' or row['expires'] <= time.time():
            raise PermissionError('Exact publication authorization expired, revoked or changed')

    def operation(self, tenant, project, preview, index):
        value = self.preview(tenant, project, preview)
        if type(index) is not int or not 0 <= index < len(value['actions']):
            raise ValueError('Unknown exact publication action')
        action = value['actions'][index]
        ident = digest({'preview': preview, 'action': index, 'body': action})
        encoded = json.dumps(action, allow_nan=False, separators=(',', ':'), ensure_ascii=False)
        with self.store.transaction() as db:
            row = db.execute('SELECT * FROM publication_operations WHERE preview=? AND action=?', (preview, index)).fetchone()
            if row is None:
                db.execute('INSERT INTO publication_operations VALUES(?,?,?,?,?,?,?)',
                           (ident, preview, index, digest(action), encoded, 'pending', None))
                row = db.execute('SELECT * FROM publication_operations WHERE id=?', (ident,)).fetchone()
            if row['id'] != ident or row['body_digest'] != digest(action) or json.loads(row['payload']) != action:
                raise Conflict('Publication action differs from the retained exact intent')
            return {**dict(row), 'payload': action, 'result': json.loads(row['result']) if row['result'] else None}

    def before_write(self, tenant, project, preview, authorization, expected_digest, lease, operation):
        """Durably record intent while authority/fence are live, immediately before I/O."""
        with self.store.transaction() as db:
            self._authorization(db, tenant, project, preview, authorization, expected_digest)
            current = db.execute('SELECT campaign FROM publication_previews WHERE id=?', (preview,)).fetchone()
            competing = db.execute('''SELECT 1 FROM publication_leases l JOIN publication_previews p ON p.id=l.preview
                WHERE p.tenant=? AND p.project=? AND p.campaign=? AND l.preview<>? AND l.expires>?''',
                (tenant, project, current['campaign'], preview, time.time())).fetchone()
            if competing is not None:
                raise Conflict('Another exact wave owns this campaign')
            row = db.execute('SELECT * FROM publication_leases WHERE preview=?', (preview,)).fetchone()
            if row is None or (row['owner'], row['epoch']) != lease or row['expires'] <= time.time():
                raise Conflict('Publication executor was fenced or expired')
            saved = db.execute('SELECT * FROM publication_operations WHERE id=? AND preview=?', (operation['id'], preview)).fetchone()
            if saved is None or saved['body_digest'] != operation['body_digest'] or saved['state'] not in {'pending', 'uncertain'}:
                raise Conflict('Publication intent is not available for this write')
            if saved['state'] == 'uncertain' and operation['payload']['kind'] == 'pull':
                raise Conflict('Reconcile the uncertain PR; absence is not permission to repeat it')
            db.execute("UPDATE publication_operations SET state='in_flight' WHERE id=?", (operation['id'],))
            self._event(db, preview, 'write_intent_committed', operation['id'])

    def result(self, preview, operation, state, result=None):
        if state not in {'confirmed', 'uncertain', 'blocked'}:
            raise ValueError('Unknown operation outcome')
        encoded = None if result is None else json.dumps(result, allow_nan=False, separators=(',', ':'))
        if encoded is not None and len(encoded) > 10000:
            raise ValueError('Publication receipt exceeds its bound')
        # Recording a late, immutable observed outcome does not permit any new write.
        with self.store.transaction() as db:
            saved = db.execute('SELECT * FROM publication_operations WHERE id=? AND preview=?', (operation['id'], preview)).fetchone()
            if saved is None or saved['body_digest'] != operation['body_digest']:
                raise Conflict('Operation identity changed')
            if saved['state'] == 'confirmed':
                if state != 'confirmed' or json.loads(saved['result']) != result:
                    raise Conflict('Confirmed operation cannot be rewritten')
                return
            db.execute('UPDATE publication_operations SET state=?,result=? WHERE id=?', (state, encoded, operation['id']))
            self._event(db, preview, 'operation_' + state, operation['id'])

    def claim(self, tenant, project, campaign, repository, branch, nonce, head, *, manifest=None, expected_head=None):
        with self.store.transaction() as db:
            row = db.execute('SELECT * FROM publication_claims WHERE repository=? AND branch=?', (repository, branch)).fetchone()
            if row is not None and (row['tenant'], row['project'], row['campaign'], row['nonce']) != (tenant, project, campaign, nonce):
                raise Conflict('Proposal branch belongs to a different campaign or installation')
            if row is not None and row['head'] != head and (expected_head is None or row['head'] != expected_head):
                raise Conflict('Proposal ownership head advanced; late outcomes cannot roll it back')
            encoded = json.dumps(manifest, allow_nan=False, separators=(',', ':')) if manifest is not None else (row['manifest'] if row else None)
            if encoded is not None and len(encoded) > 64000:
                raise ValueError('Proposal ownership manifest exceeds its bound')
            db.execute('INSERT OR REPLACE INTO publication_claims VALUES(?,?,?,?,?,?,?,?)',
                       (repository, branch, tenant, project, campaign, nonce, head, encoded))

    def owned(self, tenant, project, campaign, repository, branch):
        with self.store.transaction() as db:
            row = db.execute('SELECT * FROM publication_claims WHERE repository=? AND branch=?', (repository, branch)).fetchone()
        if row is None or (row['tenant'], row['project'], row['campaign']) != (tenant, project, campaign):
            return None
        return {**dict(row), 'manifest': json.loads(row['manifest']) if row['manifest'] else None}

    def cancel(self, tenant, project, preview):
        self.preview(tenant, project, preview)
        with self.store.transaction() as db:
            db.execute("UPDATE publication_authorizations SET state='revoked' WHERE preview=?", (preview,))
            db.execute('UPDATE publication_leases SET epoch=epoch+1,expires=0 WHERE preview=?', (preview,))
            self._event(db, preview, 'publication_canceled')

    def release(self, preview, lease):
        with self.store.transaction() as db:
            db.execute('UPDATE publication_leases SET expires=0 WHERE preview=? AND owner=? AND epoch=?', (preview, *lease))

    def status(self, tenant, project, preview):
        with self.store.transaction() as db:
            if db.execute('SELECT 1 FROM publication_previews WHERE id=? AND tenant=? AND project=?', (preview, tenant, project)).fetchone() is None:
                raise PermissionError('Publication preview unavailable')
            rows = db.execute('SELECT id,action,state,result FROM publication_operations WHERE preview=? ORDER BY action', (preview,)).fetchall()
        # Crash between intent and acknowledgement is uncertain until reconciliation.
        return {'previewId': preview, 'operations': [{**dict(row), 'state': 'uncertain' if row['state'] == 'in_flight' else row['state'],
                'result': json.loads(row['result']) if row['result'] else None} for row in rows]}
