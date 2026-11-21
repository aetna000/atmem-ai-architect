"""Bind proposed work records to actual immutable files and delivered context.

No generated code executes here. Binding records provenance and file existence,
not semantic correctness, business agreement or successful execution.
"""
import hashlib
import io
import json
from pathlib import Path
import re
import uuid
import zipfile
from jsonschema import Draft202012Validator, ValidationError
from .engineering_contexts import _object
from .engineering_sessions import SessionError
from .memory_service import safe

PROPOSAL_PATH = 'architecture-work-proposal.json'
MAX_PROPOSAL_BYTES = 1_500_000
BOUNDARY = 'artifact_file_binding_only'


def _sha(content):
    return hashlib.sha256(content).hexdigest()


def _path(value):
    if not isinstance(value,str) or not value.strip() or len(value)>500 or value.startswith('/') or re.match(r'^[A-Za-z]:',value) or '\\' in value or any(ord(c)<32 for c in value) or any(p in {'','.','..'} for p in value.split('/')):
        raise SessionError('Mapping files must be explicit relative artifact paths')
    return value


def _json(content):
    def constant(value):
        raise ValueError('Nonfinite proposal JSON')
    value=json.loads(content.decode('utf-8'),object_pairs_hook=_object,parse_constant=constant)
    json.dumps(value,allow_nan=False,ensure_ascii=False).encode('utf-8')
    def depth(item,level=0):
        if level>40:raise ValueError('Proposal exceeds its explicit nesting bound')
        if isinstance(item,dict):
            for child in item.values():depth(child,level+1)
        elif isinstance(item,list):
            for child in item:depth(child,level+1)
    depth(value)
    return value


class EngineeringReconciliation:
    def __init__(self,store,artifacts,contexts):
        self.store,self.db,self.artifacts,self.contexts=store,store.db,artifacts,contexts
        self.schema_path=Path(__file__).parent/'engineering_assets/architecture_work.schema.json'
        schema=self.schema_path.read_bytes()
        self.validator=Draft202012Validator(json.loads(schema))
        self.definition=_sha(Path(__file__).read_bytes()+schema)
        self.db.execute('''CREATE TABLE IF NOT EXISTS engineering_reconciliations (
            id TEXT PRIMARY KEY, session TEXT NOT NULL, artifact TEXT NOT NULL,
            sha256 TEXT NOT NULL, payload TEXT NOT NULL, UNIQUE(session,artifact,sha256))''')
        self.db.commit()

    def submitted_context(self,scope,session):
        # Only durable client identity events are needed. Do not page or truncate
        # thousands of unrelated token/tool deltas into a supposed complete brief.
        rows=self.db.execute('''SELECT sequence,payload FROM engineering_events
            WHERE session=? AND json_extract(payload,'$.kind') IN
            ('accepted','steering_submitted','steering_accepted','steering_delivery_uncertain')
            ORDER BY sequence''',(session,)).fetchall()
        if len(rows)>4000:raise SessionError('Intent history exceeds the reconciliation bound; nothing was discarded')
        events=[{'sequence':r['sequence'],**json.loads(r['payload'])} for r in rows]
        for event in events:
            if event['kind']=='accepted' and 'text' not in event:
                saved=self.db.execute('SELECT intent FROM engineering_runs WHERE id=? AND session=?',(event.get('runId'),session)).fetchone()
                if saved and isinstance(saved['intent'],str):event['text']=saved['intent']
        accepted={e.get('requestId') for e in events if e['kind']=='steering_accepted'}
        uncertain={e.get('requestId') for e in events if e['kind']=='steering_delivery_uncertain'}
        intents=[]
        for e in events:
            if e['kind']=='accepted' and e.get('origin')!='automatic_repair':
                request=e.get('runId');status='accepted'
            elif e['kind']=='steering_submitted':
                request=e.get('requestId');status='accepted' if request in accepted else 'uncertain' if request in uncertain else 'pending'
            else:continue
            if not isinstance(e.get('text'),str) or not e['text'].strip():
                raise SessionError('Exact client intent is unavailable; reconcile the durable history first')
            intents.append({'requestId':request,'sequence':e['sequence'],'text':e['text'],'status':status})
        if not intents or any(i['status']!='accepted' for i in intents):
            raise SessionError('Client intent delivery is unresolved; no mapping was reconciled')
        latest=self.contexts.for_request(scope,session,intents[-1]['requestId'])
        if latest is None:raise SessionError('This legacy submission has no immutable current-context receipt')
        return latest,[e for e in events if not (e['kind']=='accepted' and e.get('origin')=='automatic_repair')]

    def _current(self,scope,session,manifest):
        row=self.store.get(scope,session)
        if row['state']!='idle' or row['last_status']!='completed' or row['run']!=manifest['runId'] or manifest.get('turnStatus')!='completed' or manifest.get('kind')!='delivery':
            raise SessionError('Mapping reconciliation requires the current completed delivery artifact')

    def prepare(self,scope,session,artifact):
        manifest,archive=self.artifacts.get(scope,session,artifact)
        self._current(scope,session,manifest)
        if manifest.get('sessionId')!=session or manifest.get('id')!=artifact or _sha(archive)!=manifest.get('sha256'):
            raise SessionError('Artifact integrity check failed; no mappings were imported')
        context,events=self.submitted_context(scope,session)
        files={}
        for entry in manifest['files']:
            if entry['kind']!='file':continue
            name=_path(entry['path'])
            if name in files:raise SessionError('Artifact manifest repeats a file path')
            files[name]=entry
        if PROPOSAL_PATH not in files:
            return {'status':'proposal_missing','artifactId':artifact,
                'boundary':BOUNDARY,'message':'This package has no proposed work mappings. Ask engineering to produce architecture-work-proposal.json; the artifact remains unchanged.'}
        if files[PROPOSAL_PATH]['bytes']>MAX_PROPOSAL_BYTES:raise SessionError('Work proposal exceeds its explicit byte bound')
        with zipfile.ZipFile(io.BytesIO(archive)) as package:
            entries=package.infolist()
            if len(entries)>2000 or len({e.filename for e in entries})!=len(entries):raise SessionError('Artifact archive has inconsistent entries')
            content=package.read(PROPOSAL_PATH)
            if len(content)>MAX_PROPOSAL_BYTES or len(content)!=files[PROPOSAL_PATH]['bytes'] or _sha(content)!=files[PROPOSAL_PATH]['sha256']:
                raise SessionError('Proposed mapping bytes differ from the captured manifest')
            try:
                proposal=_json(content)
                self.validator.validate(proposal)
            except (ValueError,UnicodeError,RecursionError,ValidationError):
                raise SessionError('The proposed mapping file is malformed or uses an unsupported schema; the artifact is retained') from None
            if not safe(proposal):raise SessionError('Proposed mapping data looks like a credential')
            if not proposal['records']:raise SessionError('The work proposal contains no records')
            ids=set();bindings={}
            for record in proposal['records']:
                if not record['id'].strip() or not record['title'].strip() or record['id'] in ids or any(not r.strip() for r in record['dependsOn']):
                    raise SessionError('Work proposals require unique explicit identities and references')
                ids.add(record['id'])
                paths=record['data'].get('files',[])
                if not isinstance(paths,list) or len(paths)>200 or len(set(p for p in paths if isinstance(p,str)))!=len(paths):
                    raise SessionError('Mapping file lists must be bounded unique paths')
                if record['kind']=='implementation' and not paths:
                    raise SessionError('An implementation mapping must name actual artifact files')
                for path in paths:
                    _path(path)
                    if path not in files or path in manifest.get('pinnedInputs',{}) or path==PROPOSAL_PATH:
                        raise SessionError('An implementation/evidence mapping names a missing or supplied input file')
                    actual=package.read(path)
                    if len(actual)!=files[path]['bytes'] or _sha(actual)!=files[path]['sha256']:
                        raise SessionError('Mapped file bytes differ from the captured manifest')
                    bindings[path]={'path':path,'bytes':len(actual),'sha256':_sha(actual)}
        payload={'format':'atmem.architecture-proposal','version':1,'projectId':scope.project,
            'sessionId':session,'runId':manifest['runId'],'artifactId':artifact,'artifactSha256':manifest['sha256'],
            'proposalSha256':_sha(content),'context':context,'events':events,'proposal':proposal,
            'files':sorted(bindings.values(),key=lambda f:f['path']),'definitionSha256':self.definition,'boundary':BOUNDARY}
        encoded=json.dumps(payload,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':'))
        if len(encoded.encode())>6_000_000:raise SessionError('Mapping receipt exceeds its explicit byte bound; nothing was discarded')
        digest=_sha(encoded.encode())
        self._current(scope,session,manifest)
        prior=self.db.execute('SELECT id,payload FROM engineering_reconciliations WHERE session=? AND artifact=? AND sha256=?',(session,artifact,digest)).fetchone()
        if prior:
            if prior['payload']!=encoded:raise SessionError('Stored mapping receipt integrity check failed')
            ident=prior['id']
        else:
            ident=str(uuid.uuid4())
            with self.db:self.db.execute('INSERT INTO engineering_reconciliations VALUES (?,?,?,?,?)',(ident,session,artifact,digest,encoded))
        # Exact encoded bytes avoid cross-runtime number/key serialization differences.
        return {'status':'prepared','id':ident,'sha256':digest,'content':encoded}
