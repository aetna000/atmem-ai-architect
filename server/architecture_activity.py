"""Project-scoped public activity, never model reasoning or raw protocol output."""
from datetime import datetime,timezone
import json
import re
import sqlite3
import uuid

KINDS={'context_started','context_ready','pass_started','model_started','model_message','model_checked','response_repair','tool_started','tool_finished','tool_cached','response_ready','failed','cancelled'}
DETAILS={'round','attempt','provider','model','effort','skillIds','recordCount','knowledgeCount','tool','success','cached','encoding','proposal','requirementCount','decisionCount'}

def now():return datetime.now(timezone.utc).isoformat()


class ArchitectureActivity:
    def __init__(self,path):
        self.db=sqlite3.connect(path);self.db.row_factory=sqlite3.Row
        self.db.execute('''CREATE TABLE IF NOT EXISTS architecture_turns (
            id TEXT PRIMARY KEY, project TEXT NOT NULL, metadata TEXT NOT NULL,
            state TEXT NOT NULL, started TEXT NOT NULL)''')
        self.db.execute('''CREATE TABLE IF NOT EXISTS architecture_events (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT, turn TEXT NOT NULL,
            payload TEXT NOT NULL)''')
        with self.db:self.db.execute("UPDATE architecture_turns SET state='recovery_required' WHERE state='running'")

    def close(self):self.db.close()

    def owned(self,project,turn):
        row=self.db.execute('SELECT * FROM architecture_turns WHERE id=? AND project=?',(turn,project)).fetchone()
        if row is None:raise LookupError('Architecture activity is unavailable for this project')
        return row

    def start(self,project,turn,metadata):
        if not isinstance(project,str) or not re.fullmatch(r'[A-Za-z0-9-]{8,64}',project) or not isinstance(turn,str) or str(uuid.UUID(turn))!=turn:
            raise ValueError('Use an exact project and canonical activity UUID')
        if set(metadata)-{'provider','model','effort','origin','revision'}:raise ValueError('Unsupported public turn metadata')
        if self.db.execute('SELECT 1 FROM architecture_turns WHERE id=?',(turn,)).fetchone():
            raise ValueError('This architecture request is already recorded; it was not replayed')
        if self.db.execute('SELECT COUNT(*) FROM architecture_turns WHERE project=?',(project,)).fetchone()[0]>=1000:
            raise ValueError('Architecture activity reached its history bound; no earlier turn was removed')
        with self.db:self.db.execute('INSERT INTO architecture_turns VALUES (?,?,?,?,?)',(turn,project,json.dumps(metadata,allow_nan=False),'running',now()))

    def append(self,project,turn,event):
        row=self.owned(project,turn)
        if row['state']!='running':raise ValueError('Activity is already settled; no work was replayed')
        if set(event)-{'kind','text','details'} or event.get('kind') not in KINDS or not isinstance(event.get('text'),str) or len(event['text'])>16000:
            raise ValueError('Unsupported public activity event')
        details=event.get('details',{})
        if not isinstance(details,dict) or set(details)-DETAILS:raise ValueError('Private or unsupported activity details are forbidden')
        for value in details.values():
            if value is not None and type(value) not in {str,int,bool,list}:raise ValueError('Unsupported activity detail')
            if isinstance(value,list) and (len(value)>100 or any(not isinstance(v,str) or len(v)>200 for v in value)):raise ValueError('Invalid public activity references')
        if self.db.execute('SELECT COUNT(*) FROM architecture_events WHERE turn=?',(turn,)).fetchone()[0]>=500:raise ValueError('Activity event bound reached; no events were discarded')
        encoded=json.dumps({**event,'at':now()},ensure_ascii=False,allow_nan=False)
        if len(encoded.encode())>80000:raise ValueError('Activity event is oversized; no text was clipped')
        with self.db:self.db.execute('INSERT INTO architecture_events(turn,payload) VALUES (?,?)',(turn,encoded))

    def finish(self,project,turn,state):
        if state not in {'response_ready','failed','cancelled','details_unavailable'}:raise ValueError('Unsupported activity state')
        self.owned(project,turn)
        with self.db:self.db.execute("UPDATE architecture_turns SET state=? WHERE id=? AND project=? AND state='running'",(state,turn,project))

    def read(self,project,turn,after=0):
        row=self.owned(project,turn)
        if type(after) is not int or after<0:raise ValueError('Invalid activity cursor')
        events=[{'sequence':r['sequence'],**json.loads(r['payload'])} for r in self.db.execute('SELECT sequence,payload FROM architecture_events WHERE turn=? AND sequence>? ORDER BY sequence LIMIT 200',(turn,after))]
        return {'id':turn,'projectId':project,'state':row['state'],'startedAt':row['started'],'selection':json.loads(row['metadata']),'events':events,
                'boundary':'Recorded public model messages and observed host actions. No private reasoning, raw prompts, credentials or provider protocol dumps. Response readiness is not design/application acceptance.'}
