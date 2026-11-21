"""Opt-in smoke check. Uses an existing account and incurs provider usage."""
import asyncio, json, sys, urllib.request
provider=sys.argv[1] if len(sys.argv)>1 else 'claude-code'
model=sys.argv[2] if len(sys.argv)>2 else 'default'
session=json.load(urllib.request.urlopen('http://127.0.0.1:5174/api/session'))
payload={'message':'Connection smoke test only. Reply with one short sentence identifying the architecture task. Do not propose changes. Do not use tools. Set proposal to null and phase to Discovery.','provider':provider,'model':model,'project':{'version':1,'revision':1,'name':'AI architecture test','provider':'gcp','requirements':'A cloud-neutral AI architecture workbench.','nodes':[],'edges':[]},'history':[]}
request=urllib.request.Request('http://127.0.0.1:5174/api/architect',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+session['token']})
try:
 with urllib.request.urlopen(request,timeout=160) as response:
  result=json.load(response)
  print(json.dumps({'provider':provider,'status':response.status,'phase':result.get('phase'),'message':result.get('message'),'proposal':result.get('proposal')},indent=2))
except urllib.error.HTTPError as error:
 print(json.dumps({'provider':provider,'status':error.code,'error':json.load(error)},indent=2));sys.exit(1)
