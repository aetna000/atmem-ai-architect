"""Administrator-only, bounded activity summaries. Never store project contents."""
from datetime import datetime, timedelta, timezone
import uuid
import hashlib
from .credits import CreditError
from .projects import project_id
from .auth import Forbidden

KINDS=frozenset({'account_opened','project_created','project_saved','project_deleted',
    'project_opened','project_downloaded','signed_out','template_opened',
    'chat_requested','generation_requested','validation_requested','handoff_requested'})
JOB_KINDS={'/api/architect':'chat_requested','/api/engineering/start':'generation_requested',
    '/api/engineering/validation/start':'validation_requested','/api/terraform/validate':'validation_requested',
    '/api/terraform/emulate':'validation_requested',
    '/api/engineering/handoff':'handoff_requested'}

class Activity:
    def __init__(self,store,access,*,clock=lambda:datetime.now(timezone.utc)):
        self.store,self.access,self.clock=store,access,clock

    def record(self,actor,kind,*,project=None,event_id=None):
        if kind not in KINDS:raise CreditError('Unsupported activity')
        if project is not None:project_id(project)
        now=self.clock();day=now.date().isoformat();stamp=now.isoformat()
        event_id=hashlib.sha256((actor.x_id+'\0'+kind+'\0'+(event_id or uuid.uuid4().hex)).encode()).hexdigest()
        def apply(tx):
            # Recheck admission inside the transaction; client identities never select another user.
            entry=self.access._entry(tx,actor.x_id)
            if not entry['allowed']:return False
            index=tx.get('activity_index','days') or {'days':[]}
            bucket=tx.get('activity_days',day) or {'day':day,'counts':{},'users':{},'events':[],'seen':[]}
            if event_id in bucket['seen']:return True
            user=bucket['users'].get(actor.x_id) or {'xId':actor.x_id,'displayName':actor.display_name,'counts':{},'firstAt':stamp}
            user.update(lastAt=stamp,displayName=actor.display_name)
            bucket['counts'][kind]=bucket['counts'].get(kind,0)+1
            user['counts'][kind]=user['counts'].get(kind,0)+1
            bucket['users'][actor.x_id]=user
            bucket['events']=(bucket['events']+[{'kind':kind,'xId':actor.x_id,'at':stamp,**({'projectId':project} if project else {})}])[-200:]
            bucket['seen']=(bucket['seen']+[event_id])[-2048:]
            cutoff=(now.date()-timedelta(days=29)).isoformat()
            expired=[key for key in index['days'] if key<cutoff]
            index['days']=sorted(({key for key in index['days'] if key>=cutoff})|{day})
            for key in expired:tx.delete('activity_days',key)
            tx.set('activity_days',day,bucket);tx.set('activity_index','days',index)
            return True
        return self.store.transaction(apply)

    def report(self,actor,days=7):
        self.access.authorize(actor).require_admin()
        if type(days) is not int or not 1<=days<=30:raise CreditError('Choose 1–30 days')
        today=self.clock().date()
        def read(tx):
            own=self.access._entry(tx,actor.x_id)
            if not own['allowed'] or own['role']!='admin':raise Forbidden('Administrator access required')
            return [tx.get('activity_days',(today-timedelta(days=offset)).isoformat()) for offset in range(days)]
        buckets=[row for row in self.store.transaction(read) if row]
        counts={};users={};events=[]
        for row in buckets:
            for key,count in row['counts'].items():counts[key]=counts.get(key,0)+count
            events+=row['events']
            for uid,user in row['users'].items():
                if uid not in users:users[uid]={**user,'counts':dict(user['counts'])}
                else:
                    target=users[uid];target['firstAt']=min(target['firstAt'],user['firstAt'])
                    if user['lastAt']>target['lastAt']:target.update(lastAt=user['lastAt'],displayName=user['displayName'])
                    for kind,count in user['counts'].items():target['counts'][kind]=target['counts'].get(kind,0)+count
        return {'days':days,'activeUsers':len(users),'counts':counts,'users':sorted(users.values(),key=lambda r:r['lastAt'],reverse=True),
            'events':sorted(events,key=lambda r:r['at'],reverse=True)[:200],
            'eventWindow':'Latest 200 events; aggregate counts include all recorded actions.',
            'source':'Authenticated server activity; requested AI actions are not completion claims.'}
