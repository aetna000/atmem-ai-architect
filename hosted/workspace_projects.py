"""Create actual Architect project documents, independent of a browser upload."""
import base64
import hashlib
import json
import uuid
from datetime import datetime,timezone
from .credits import CreditError,Conflict,digest,identifier
from .projects import MAX_PROJECTS,USER_BYTES


class WorkspaceProjects:
    def __init__(self,store,profiles,projects):self.store,self.profiles,self.projects=store,profiles,projects

    def create(self,uid,request_id,title):
        identifier(request_id)
        if type(title) is not str or not 1<=len(title.strip())<=120 or any(ord(c)<32 for c in title):
            raise CreditError('Use a project name between 1 and 120 characters')
        title=title.strip();key=hashlib.sha256((uid+'\0'+request_id).encode()).hexdigest()
        proposed={'uid':uid,'id':uuid.uuid4().hex,'title':title,'createdAt':datetime.now(timezone.utc).isoformat()}
        def capture(tx):
            index=self.projects._index(tx,uid)
            previous=tx.get('workspace_creations',key)
            if previous:
                if previous['uid']!=uid or previous['title']!=title:raise Conflict('Creation request already belongs to a different project')
                return previous
            if len(index['ids'])+len(index['uploads'])>=MAX_PROJECTS:raise CreditError('Project limit reached')
            if index['bytes']+index['reservedBytes']+4096>USER_BYTES:raise CreditError('Project storage is full')
            tx.create('workspace_creations',key,proposed);return proposed
        creation=self.store.transaction(capture)
        file={'format':'atmem.ai-architect.project','formatVersion':'2.3.0',
              'meta':{'id':creation['id'],'name':title,'revision':1,'createdAt':creation['createdAt'],
                      'updatedAt':creation['createdAt'],'generator':'atmem-ai-architect hosted'},
              'design':{'provider':'tools','nodes':[],'edges':[]},'discovery':{'problem':''},
              'requirements':[],'assumptions':[],'openQuestions':[],'decisions':[],'extensions':{}}
        raw=json.dumps(file,separators=(',',':'),ensure_ascii=False).encode()
        sha=hashlib.sha256(raw).hexdigest()
        upload=self.projects.begin(uid,'create-'+key,title=title,size=len(raw),sha256=sha,pid=creation['id'],allow_new=True)
        if upload['state']!='completed':self.projects.put_chunk(uid,upload['id'],0,base64.b64encode(raw).decode(),sha)
        return self.projects.complete(uid,upload['id'])

    def move(self,uid,pid,revision,trashed):
        from .projects import ProjectUnavailable
        if type(revision) is not int or revision<1:raise CreditError('Use the current project revision')
        def apply(tx):
            self.profiles._account(tx,uid)
            key=self.projects._project_key(uid,pid);row=tx.get('projects',key)
            if not row:raise ProjectUnavailable('Project is unavailable')
            if row['revision']!=revision:raise Conflict('Project changed. Reload before moving it')
            row.update(trashed=trashed,revision=revision+1,updatedAt=datetime.now(timezone.utc).isoformat())
            tx.set('projects',key,row);return row
        return self.store.transaction(apply)
