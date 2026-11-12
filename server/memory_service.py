from .settings import setting, home as product_home
"""AtMem AI Architect's authenticated single-user scope policy over the real AtMem core SDK.

Application queue/receipts live in state.sqlite; memory and supersession live in AtMem.
No unfiltered dashboard, shared ~/.atmem store, or model-selected subject is exposed.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
SECRET_KEY = re.compile(r'^(password|secret|api_?key|access_?key|token|client_?secret)$', re.I)
SECRET_VALUE = re.compile(r'AKIA[0-9A-Z]{16}|sk-(?:ant-)?[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{36}|AIza[\w-]{35}|-----BEGIN .*PRIVATE KEY-----')


def safe(value):
    if isinstance(value, str):
        return not SECRET_VALUE.search(value)
    if isinstance(value, list):
        return all(safe(v) for v in value)
    if isinstance(value, dict):
        return all(not (SECRET_KEY.match(k) and v) and safe(v) for k, v in value.items())
    return True


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class MemoryService:
    def __init__(self, home=None, worker=None):
        self.home = Path(home or product_home()) / 'memory'
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.worker = str(worker or setting('MEMORY_PYTHON') or ROOT / '.memory-venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python'))
        self.lock = threading.RLock()
        self.error = None
        with self.db() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS identity (id TEXT PRIMARY KEY);
              CREATE TABLE IF NOT EXISTS profiles (id TEXT PRIMARY KEY,name TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS settings (project TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 1);
              CREATE TABLE IF NOT EXISTS snapshots (project TEXT PRIMARY KEY, revision INTEGER, entities TEXT, digest TEXT);
              CREATE TABLE IF NOT EXISTS queue (seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE, project TEXT, scope TEXT, key TEXT, text TEXT, source TEXT, state TEXT, created TEXT);
              CREATE TABLE IF NOT EXISTS activity (id TEXT PRIMARY KEY, project TEXT, created TEXT, payload TEXT);
              CREATE TABLE IF NOT EXISTS skill_settings (id TEXT PRIMARY KEY, enabled INTEGER);
            ''')
            row = db.execute('SELECT id FROM identity').fetchone()
            if 'reason' not in {r[1] for r in db.execute('PRAGMA table_info(queue)')}:
                db.execute("ALTER TABLE queue ADD COLUMN reason TEXT DEFAULT ''")
            self.owner = row[0] if row else str(uuid.uuid4())
            if not row:
                db.execute('INSERT INTO identity VALUES (?)', (self.owner,))
            db.execute("INSERT OR IGNORE INTO profiles VALUES (?,?)",(self.owner,'Default profile'))

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.home / 'state.sqlite', timeout=15)
        db.execute('PRAGMA secure_delete=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def project(self, project):
        if not isinstance(project, str) or not re.fullmatch(r'[A-Za-z0-9-]{8,64}', project):
            raise ValueError('Invalid project identity')
        return project

    def subject(self, scope, project):
        return 'atforma-' + digest([self.owner, scope, project if scope == 'project' else 'shared'])[:40]

    def enabled(self, project):
        with self.db() as db:
            row = db.execute('SELECT enabled FROM settings WHERE project=?', (project,)).fetchone()
        return not row or bool(row[0])

    def configure(self, project, enabled):
        self.project(project)
        with self.lock, self.db() as db:
            db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (project, int(enabled)))
            if not enabled:
                db.execute("UPDATE queue SET state='cancelled' WHERE project=? AND state='pending'", (project,))
        return {'enabled': enabled}

    def call(self, operations):
        operations=[{**op,'owner':self.owner,'actor':'user:'+self.owner if (op.get('subject')==self.subject('user','') or op.get('action')=='forget') else 'atmem-project-sync','actorType':'user' if (op.get('subject')==self.subject('user','') or op.get('action')=='forget') else 'project-sync'}for op in operations]
        result = subprocess.run([self.worker, '-I', str(ROOT / 'server/memory_worker.py')],
            input=json.dumps({'database': str(self.home / 'memories.db'), 'operations': operations}),
            text=True, capture_output=True, timeout=25, cwd=str(self.home))
        try:
            payload = json.loads(result.stdout)
        except (ValueError, TypeError):
            raise RuntimeError('AtMem runtime unavailable; run npm run setup:memory') from None
        if result.returncode or 'error' in payload:
            raise RuntimeError('AtMem rejected the operation (' + payload.get('error', 'worker failed') + ')')
        self.error = None
        return payload['results']

    def enqueue(self, project, scope, key, text, event_id=None, source=''):
        if not safe(text) or len(text) > 1900:
            raise ValueError('Memory content is too long or looks like a credential')
        event_id = event_id or digest([project, scope, key, text])
        with self.db() as db:
            db.execute("INSERT OR IGNORE INTO queue(event_id,project,scope,key,text,source,state,created) VALUES (?,?,?,?,?,?,'pending',?)", (event_id, project, scope, key, text, source, timestamp()))

    def flush(self):
        with self.lock:
            with self.db() as db:
                rows = db.execute("SELECT seq,event_id,project,scope,key,text,source FROM queue WHERE state='pending' ORDER BY seq LIMIT 500").fetchall()
            if not rows:
                return True
            try:
                # The worker durably receipts each event so a partial batch can replay safely.
                results = self.call([{'action': 'remember', 'subject': self.subject(scope, project), 'key': key, 'text': text, 'eventId': event, 'source': source} for seq, event, project, scope, key, text, source in rows])
                with self.db() as db:
                    for row, result in zip(rows, results):
                        db.execute("UPDATE queue SET state=?,reason=?,text='',source='' WHERE seq=?", ('rejected' if result.get('refused') else 'synced', json.dumps(result.get('refused',[])), row[0]))
                return True
            except (OSError, RuntimeError, subprocess.TimeoutExpired):
                self.error = 'AtMem unavailable — using this project only; eligible changes queued'
                return False

    @staticmethod
    def entities(file):
        values = {}
        design = file.get('design') or {}
        # The editable project already holds the diagram, comments and conversation brief.
        # Only durable, confirmed facts belong in long-term memory.
        for category in ('requirements', 'assumptions', 'openQuestions'):
            for item in file.get(category, [])[:300]:
                if category != 'requirements' or item.get('source') != 'user' or item.get('priority') != 'must' or str(item.get('id','')).startswith('drv-'):
                    continue
                key = str(item.get('id', ''))
                content = item.get('statement') or item.get('question')
                if key and content:
                    values[f'{category}.{key}'] = f'{category} [{key}]: {content}; status: {item.get("status", "recorded")}'[:1800]
        for item in file.get('discovery', {}).get('facts', [])[:300]:
            if isinstance(item, dict) and item.get('name') == 'budget.per_month' and not item.get('conflictsWith'):
                name = str(item['name'])
                values['fact.' + name] = f'Project fact {name}: {item.get("value")} {item.get("unit", "")}; stated {item.get("madeAt", "unknown")}' + ('; unresolved conflict: confirm with user' if item.get('conflictsWith') else '')
        decisions = file.get('decisions', [])
        for item in decisions[:200]:
            if item.get('status') != 'Accepted':
                continue
            subject = str(item.get('subject') or item.get('id') or 'decision')
            if subject.startswith('design.'):
                continue
            values['decision.' + subject] = f'Project decision {subject}: {item.get("decision") or item.get("title", "")}; status: {item.get("status", "Proposed")}; reason: {item.get("reason") or item.get("rationale") or "not recorded"}'[:1800]
        return values

    def sync(self, project, file):
        self.project(project)
        if not isinstance(file, dict) or file.get('format') not in {'atmem.ai-architect.project','atforma.project'} or file.get('meta', {}).get('id') != project or not safe(file):
            raise ValueError('Invalid project snapshot or credential-bearing data')
        revision = file.get('meta', {}).get('revision')
        if not isinstance(revision, int) or revision < 1:
            raise ValueError('Invalid project revision')
        with self.lock:
            if not self.enabled(project):
                return {'enabled': False, 'status': 'disabled'}
            entities = self.entities(file)
            with self.db() as db:
                old = db.execute('SELECT revision,entities,digest FROM snapshots WHERE project=?', (project,)).fetchone()
            if old and revision < old[0]:
                return {'status': 'conflict', 'detail': 'Older project revision; memory was not changed'}
            previous = json.loads(old[1]) if old else {}
            change_id = str(uuid.uuid4())
            with self.db() as db:
                # Snapshot update and outbox insertion are one transaction: no lost change on crash.
                for key in previous.keys() | entities.keys():
                    text = entities.get(key, f'{key} was removed from this project; do not treat the earlier value as current.')
                    if previous.get(key) == entities.get(key):
                        continue
                    db.execute("INSERT INTO queue(event_id,project,scope,key,text,source,state,created) VALUES (?,?,?,?,?,?,'pending',?)", (digest([change_id,key]), project, 'project', key, text, 'project snapshot r' + str(revision), timestamp()))
                db.execute('INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?)', (project, revision, json.dumps(entities), digest(file)))
            self.flush()
            return self.status(project)

    def status(self, project):
        with self.db() as db:
            counts = dict(db.execute('SELECT state,count(*) FROM queue WHERE project=? GROUP BY state', (project,)).fetchall())
        return {'enabled': self.enabled(project), 'status': 'disabled' if not self.enabled(project) else 'unavailable' if self.error else 'ready', 'pending': counts.get('pending', 0), 'rejected': counts.get('rejected', 0), 'engine': 'AtMem 2.3.10 core SDK', 'policy': 'AtMem AI Architect single-user scope and opt-out policy', 'detail': self.error}

    def profile(self, project, field, value):
        if field not in {'explanation', 'experience', 'iac', 'preferences'} or not value.strip() or len(value) > 1000:
            raise ValueError('Choose a profile field and enter up to 1,000 characters')
        with self.lock:
            if not self.enabled(project):
                raise ValueError('Memory is disabled for this project')
            # User presses Remember; these are confirmed preferences, not model inferences.
            self.enqueue(project, 'user', 'profile.' + field, f'User-confirmed {field}: {value.strip()}', event_id=str(uuid.uuid4()))
            self.flush()
            return self.status(project)

    def overview(self,project):
        from .memory_context import describe
        self.project(project)
        with self.lock,self.db()as db:
            activity=[{'id':row[0],'createdAt':row[1],**json.loads(row[2])}for row in db.execute('SELECT id,created,payload FROM activity WHERE project=? ORDER BY created DESC LIMIT 20',(project,))]
        return {**self.status(project),'activity':activity,'userProfile':self.user_profile(),'contextProviders':describe()}

    def inspect(self, project):
        from .memory_context import describe
        self.project(project)
        with self.lock:
            if self.enabled(project):
                self.flush()
            subjects = [self.subject('user', project), self.subject('project', project), self.subject('knowledge', project)]
            try:
                results = self.call([{'action': 'page', 'subject': s,'status':'all','limit':50} for s in subjects])
                records = [page['records'] for page in results]
            except (OSError, RuntimeError, subprocess.TimeoutExpired):
                self.error = 'AtMem unavailable — using this project only; eligible changes queued'
                records = [[], [], []]
            with self.db() as db:
                activity = [{'id': r[0], 'createdAt': r[1], **json.loads(r[2])} for r in db.execute('SELECT id,created,payload FROM activity WHERE project=? ORDER BY created DESC LIMIT 20', (project,))]
                events = [{'key':r[0],'status':r[1],'reason':r[2],'createdAt':r[3]} for r in db.execute("SELECT key,state,reason,created FROM queue WHERE project=? AND state IN ('pending','rejected') ORDER BY seq DESC LIMIT 20",(project,))]
            return {**self.status(project), 'profile': records[0], 'project': records[1], 'knowledge': records[2], 'activity': activity, 'events':events,'userProfile':self.user_profile(),'contextProviders':describe()}

    def user_profile(self):
        with self.db()as db:name=db.execute('SELECT name FROM profiles WHERE id=?',(self.owner,)).fetchone()[0]
        return {'id':self.owner,'name':name,'kind':'local','identitySource':'local-installation'}

    def rename_profile(self,name):
        if not isinstance(name,str)or not name.strip()or len(name)>80:raise ValueError('Enter a profile name up to 80 characters')
        with self.lock,self.db()as db:db.execute('UPDATE profiles SET name=? WHERE id=?',(name.strip(),self.owner))
        return self.user_profile()

    def browse(self,project,scope='project',**options):
        self.project(project)
        if scope not in {'user','project','knowledge'}:raise ValueError('Invalid memory scope')
        with self.lock:return self.call([{'action':'page','subject':self.subject(scope,project),**options}])[0]

    def record_detail(self,project,scope,record_id,preview=False):
        self.project(project)
        if scope not in {'user','project'}:raise ValueError('Invalid memory scope')
        with self.lock:return self.call([{'action':'forget-preview'if preview else 'record','subject':self.subject(scope,project),'recordId':record_id}])[0]

    def forget(self, project, scope, record_id):
        if scope not in {'user', 'project'}:
            raise ValueError('Invalid memory scope')
        with self.lock:
            result = self.call([{'action': 'forget', 'subject': self.subject(scope, project), 'recordId': record_id}])[0]
            key = result.pop('key')
            with self.db() as db:
                # Remove plaintext outbox copies too, and cancel replay of this exact key.
                if scope == 'user':
                    db.execute('DELETE FROM queue WHERE scope=? AND key=?', (scope, key))
                else:
                    db.execute('DELETE FROM queue WHERE project=? AND scope=? AND key=?', (project, scope, key))
            return result

    def recall(self, project, query):
        self.project(project)
        with self.lock:
            if not self.enabled(project):
                return [], self.status(project)
            if not self.flush():
                return [], self.status(project)
            try:
                rows = self.call([{'action': 'recall', 'subject': self.subject(s, project), 'query': query, 'limit': 6} for s in ('user', 'project')])
                context = [{'scope': scope, 'id': r['id'], 'text': r['content'], 'sourceDate': r['created_at'], 'key': r.get('fact_key')} for scope, records in zip(('user','project'), rows) for r in records]
                from .memory_context import retrieve
                external,provider_status=retrieve(project,self.owner,query,safe)
                return context+external,{**self.status(project),'contextProviders':provider_status}
            except (OSError, RuntimeError, subprocess.TimeoutExpired):
                self.error = 'AtMem unavailable — using this project only; eligible changes queued'
                return [], self.status(project)

    def record_turn(self, project, payload):
        payload={**payload,'userId':self.owner,'actor':'atmem-architect','actorType':'agent'}
        ident = str(uuid.uuid4())
        with self.lock, self.db() as db:
            db.execute('INSERT INTO activity VALUES (?,?,?,?)', (ident, project, timestamp(), json.dumps(payload)))
            db.execute('DELETE FROM activity WHERE project=? AND id NOT IN (SELECT id FROM activity WHERE project=? ORDER BY created DESC LIMIT 100)', (project, project))
        if self.enabled(project) and payload.get('recordIds'):
            try:
                self.call([{'action': 'log', 'subject': self.subject('project', project), 'eventType': 'atforma.turn', 'payload': payload}])
            except (OSError, RuntimeError, subprocess.TimeoutExpired):
                pass
        return ident


_instance = None
_instance_home = None
_guard = threading.Lock()
def service():
    global _instance, _instance_home
    home = str(product_home())
    with _guard:
        if _instance is None or _instance_home != home:
            _instance, _instance_home = MemoryService(home), home
    return _instance
