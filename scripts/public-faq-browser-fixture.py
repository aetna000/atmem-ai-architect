"""Loopback-only synthetic fixture. Never shipped in a client application."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json
import socket
import threading

app_dir=Path(sys.argv[1]).resolve();sdk=Path(sys.argv[2]).resolve();sys.path[:0]=[str(sdk),str(app_dir)]
import uvicorn
from public_faq_app import create_app
from public_faq import parse_catalog

sock=socket.socket();sock.bind(('127.0.0.1',0));origin='http://127.0.0.1:'+str(sock.getsockname()[1])
release=threading.Event();release.set();lock=threading.Lock()
state={'version':1,'text':'Refunds are accepted within thirty days after purchase.','hold':False,'malicious':False,'deleted':False,'calls':0,'active':0}

class Catalog:
    def load(self):
        with lock:
            rows=[] if state['deleted'] else [{'id':'refund','revision':'r'+str(state['version']),'title':'<svg onload=alert(1)> Refund policy' if state['malicious'] else 'Refund policy','text':state['text'],'url':'https://help.example.test/refund','visibility':'public'}]
            return parse_catalog(json.dumps({'format':'atmem-public-faq-v1','revision':'catalog-'+str(state['version']),'articles':rows}).encode(),'generation-'+str(state['version']))
class Model:
    def generate(self,payload,schema,instruction):
        with lock:state['calls']+=1;state['active']+=1;hold=state['hold'];malicious=state['malicious']
        try:
            if hold and not release.wait(8):raise RuntimeError('Synthetic fixture release timed out')
            article=json.loads(payload)['articles'][0]
            return json.dumps({'answer':'<img src=x onerror=alert(1)> Synthetic answer' if malicious else article['text'],'citations':[{'id':article['id'],'quote':article['text']}],'abstained':False})
        finally:
            with lock:state['active']-=1

app=create_app({'PUBLIC_ORIGIN':origin},Catalog(),Model(),static_root=app_dir/'web')
@app.post('/_fixture')
async def control(request:__import__('fastapi').Request):
    change=await request.json()
    with lock:
        action=change.get('action')
        if action=='hold':state['hold']=True;release.clear()
        elif action=='release':state['hold']=False;release.set()
        elif action=='malicious':state['malicious']=True;state['version']+=1
        elif action=='normal':state['malicious']=False;state['version']+=1
        elif action=='update':state['text']='Refunds are accepted within fourteen days after purchase.';state['version']+=1
        elif action=='delete':state['deleted']=True;state['version']+=1
        elif action!='inspect':raise ValueError('Unknown synthetic fixture control')
        return dict(state)

print(json.dumps({'origin':origin,'boundary':'Synthetic loopback catalog/model fixture over emitted application source; no cloud IAM or model proof.'}),flush=True)
uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=sock.getsockname()[1],log_level='warning',access_log=False)).run(sockets=[sock])
