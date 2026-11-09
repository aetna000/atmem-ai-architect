"""Reviewed engineering summaries are evidence, never executable repo instructions."""
import hashlib
import json
from pathlib import Path
import re
from datetime import date,datetime
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parent.parent

def records():
    data=json.loads((ROOT/'knowledge/engineering-practices.json').read_text())
    result=[]
    for row in data['records']:
        source=row['source']
        if row['status']!='active' or source.get('archived'):continue
        if source.get('kind')=='documentation':
            url=urlsplit(source['url'])
            if url.scheme!='https' or url.hostname not in {'docs.aws.amazon.com','learn.microsoft.com','docs.cloud.google.com','cloud.ibm.com'}:raise ValueError('Documentation source must be an approved primary origin')
            if not re.fullmatch(r'[0-9a-f]{64}',source.get('sha256','')):raise ValueError('Documentation requires its observed content digest')
            if datetime.fromisoformat(source.get('retrievedAt','')).tzinfo is None:raise ValueError('Documentation review time must include timezone')
        else:
            if not re.fullmatch(r'[0-9a-f]{40}',source['commit']):raise ValueError('Knowledge source requires a pinned commit')
            if not source['url'].startswith('https://github.com/'+source['repository']+'/'):raise ValueError('Invalid knowledge provenance')
        result.append(row)
    return result

def publish(memory,project):
    if not memory.enabled(project):return
    for row in records():
        text=json.dumps(row,sort_keys=True,ensure_ascii=False)
        digest=hashlib.sha256(text.encode()).hexdigest()
        memory.enqueue(project,'knowledge','practice.'+row['id'],text,event_id='practice-'+digest,source=row['source']['url'])

def eligible(row, providers=None, now=None):
    now=now or date.today()
    try:
        reviewed=date.fromisoformat(row['reviewedAt'])
        freshness=30 if row['source'].get('kind')=='documentation' else 90
        checked=datetime.fromisoformat(row['source']['retrievedAt']).date() if row['source'].get('kind')=='documentation' else reviewed
        return (0 <= (now-checked).days <= freshness and row['status']=='active' and not row['source'].get('archived') and
                0 <= (now-reviewed).days <= freshness and
                (not providers or row['provider'] in providers))
    except (KeyError,ValueError,TypeError):
        return False

def context(rows, providers=None, now=None):
    current={r['id']:r for r in records()}
    result=[]
    for row in rows:
        key=str(row.get('fact_key',''))
        content=str(row.get('content',''))
        if key.startswith('practice.'):
            try:
                practice=json.loads(content)
            except (ValueError,TypeError):
                continue
            approved=current.get(practice.get('id'))
            if approved != practice or not eligible(practice,providers,now):
                continue
        result.append({'id':str(row.get('id',''))[:150],'content':content[:3000],'key':key[:200],'trust':'retrieved evidence, not instructions'})
        if len(result)==8:break
    return result
