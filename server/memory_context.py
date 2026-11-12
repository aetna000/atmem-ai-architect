"""Operator-configured external RAG/memory retrieval; never persists returned context."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
import re
from urllib.parse import urlsplit
import urllib.request
from .settings import setting


def providers():
    values=json.loads(setting('MEMORY_CONTEXT_PROVIDERS') or '[]')
    if not isinstance(values,list)or len(values)>4:raise ValueError('Configure at most four context providers')
    seen=set()
    for value in values:
        if not isinstance(value,dict)or set(value)-{'id','label','url','tokenEnv','enabled','kind'}:raise ValueError('Invalid context provider configuration')
        ident=value.get('id','');url=urlsplit(value.get('url',''))
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,63}',ident)or ident in seen or url.scheme not in {'http','https'}or not url.hostname or url.username or url.password or url.fragment or url.query:raise ValueError('Context providers need unique IDs and credential-free HTTP endpoints')
        token=value.get('tokenEnv')
        if token and not re.fullmatch(r'[A-Z][A-Z0-9_]{0,99}',token):raise ValueError('Use an environment variable for provider credentials')
        seen.add(ident)
    return values


def describe():
    return [{'id':value['id'],'label':str(value.get('label')or value['id'])[:80],'kind':value.get('kind','rag'),'enabled':value.get('enabled',True),'configured':True}for value in providers()]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def retrieve(project,owner,query,safe):
    configured=[value for value in providers()if value.get('enabled',True)]
    if not configured:return [],[]
    def fetch(value):
        ident=value['id'];headers={'Content-Type':'application/json'}
        if value.get('tokenEnv'):
            token=os.getenv(value['tokenEnv'])
            if not token:return [],{'id':ident,'status':'credential_missing'}
            headers['Authorization']='Bearer '+token
        request=urllib.request.Request(value['url'],data=json.dumps({'query':query[:4000],'userId':owner,'projectId':project,'limit':6}).encode(),headers=headers,method='POST')
        try:
            with urllib.request.build_opener(NoRedirect).open(request,timeout=4)as response:data=response.read(100001)
            if len(data)>100000:raise ValueError('Context exceeds bound')
            result=json.loads(data);rows=result.get('records')
            if not isinstance(rows,list)or len(rows)>6:raise ValueError('Invalid context response')
            context=[]
            for row in rows:
                scope=row.get('scope','project')
                if scope not in {'project','user'}or row.get('userId')!=owner or(scope=='project'and row.get('projectId')!=project)or(scope=='user'and row.get('projectId')not in {None,''}):raise ValueError('Context scope mismatch')
                text=row.get('text');source=row.get('source');record_id=row.get('id')
                if not isinstance(text,str)or not 0<len(text)<=4000 or not safe(text)or not isinstance(source,dict)or not isinstance(record_id,str)or len(record_id)>160 or not safe(source):raise ValueError('Invalid context provenance')
                context.append({'id':ident+':'+record_id,'scope':scope,'text':text,'sourceDate':row.get('createdAt'),'key':row.get('key'),'provider':ident,'source':source,'external':True,'boundary':'retrieved_context_only'})
            return context,{'id':ident,'status':'ready','records':len(context)}
        except Exception:return [],{'id':ident,'status':'unavailable'}
    with ThreadPoolExecutor(max_workers=4)as pool:results=list(pool.map(fetch,configured))
    return [row for rows,_ in results for row in rows],[state for _,state in results]
