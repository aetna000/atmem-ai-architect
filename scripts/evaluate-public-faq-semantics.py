"""Authorized local-model probe of real FAQ retrieval/prompt/output validation.

Frozen synthetic expectations are separate from the implementation. No cloud call,
provider substitution or model-quality certification is implied by this probe.
"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src/runtime')]
from public_faq import PublicFaq,parse_catalog
from server.local_providers import call_cli

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true',required=True);parser.add_argument('--output',required=True);parser.add_argument('--model',default='default');parser.add_argument('--effort',default='low');args=parser.parse_args()
    corpus_path=ROOT/'benchmarks/convergence/public-faq-semantics.json';corpus=json.loads(corpus_path.read_text());out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=False)
    artifacts={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [corpus_path,Path(__file__).resolve(),ROOT/'src/runtime/public_faq.py',ROOT/'src/runtime/faq-output-contract.json',ROOT/'server/local_providers.py']}
    (out/'manifest.json').write_text(json.dumps({'kind':'local-model-public-faq-semantic-probe','modelProvider':'codex','requestedModel':args.model,'effort':args.effort,'sourceHashes':artifacts,'cloudOperations':False,'boundary':corpus['boundary']},indent=2)+'\n')
    articles=[]
    for row in corpus['articles']:
        padding=('Archive index entry. '*(row.get('paddingBytes',0)//21))
        articles.append({k:row[k] for k in ['id','title']}|{'text':padding+row['text'],'revision':'initial','url':'https://public.example.test/'+row['id'],'visibility':'public'})
    for index in range(len(articles),20):articles.append({'id':'unrelated-'+str(index),'title':'Unrelated catalog item '+str(index),'text':'This public catalog item describes a separate retired accessory number '+str(index)+'.','revision':'initial','url':'','visibility':'public'})
    results=[]
    for index,case in enumerate(corpus['cases']):
        if case.get('update'):
            for row in articles:
                if row['id']==case['update']['id']:row.update(text=case['update']['text'],revision='updated')
        if case.get('delete'):articles=[a for a in articles if a['id']!=case['delete']]
        raw=json.dumps({'format':'atmem-public-faq-v1','revision':'catalog-'+str(index),'articles':articles},ensure_ascii=False).encode();snapshot=parse_catalog(raw,'generation-'+str(index));calls=[]
        def generate(payload,schema,instruction):
            async def disconnected():return False
            calls.append({'request':json.loads(payload),'instruction':instruction,'schema':schema})
            result=asyncio.run(call_cli('codex',args.model,payload,instruction,schema,disconnected,effort=args.effort,timeout=180))
            calls[-1]['response']=result
            return json.dumps(result,ensure_ascii=False)
        start=time.monotonic();reply=None;error=None
        try:reply=PublicFaq(lambda:snapshot,generate)(case['question'])
        except Exception as exc:error={'kind':type(exc).__name__,'message':str(exc)[:500]}
        checks={'completed':error is None,'abstention':reply is not None and reply['abstained']==case['abstained']}
        if reply:
            checks['sources']=set(c['id'] for c in reply['citations'])==set(case['sources'])
            if case.get('answerPattern'):checks['expectedFact']=bool(re.search(case['answerPattern'],reply['answer'],re.I))
            if case.get('forbiddenPattern'):checks['noContradiction']=not re.search(case['forbiddenPattern'],reply['answer'],re.I)
        result={'case':case['id'],'passed':all(checks.values()),'checks':checks,'durationSeconds':round(time.monotonic()-start,2),'modelCalls':len(calls),'response':reply,'error':error,'catalogSha256':hashlib.sha256(raw).hexdigest()}
        (out/(case['id']+'.json')).write_text(json.dumps({'result':result,'modelOperations':calls},indent=2)+'\n');results.append(result);print(case['id'],result['passed'],result['durationSeconds'],flush=True)
    receipt={'kind':'local-model-public-faq-semantic-probe','passed':all(r['passed'] for r in results),'results':results,'cloudOperations':False,'boundary':corpus['boundary'],'limitations':['One local signed-in model sample per case, not a cloud model or regional latency check.','Deterministic fact/source expectations cover this small synthetic corpus, not universal factual entailment or linguistic quality.','Provider native IAM, model policy and actual deployment remain separate.']};(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    raise SystemExit(0 if receipt['passed'] else 1)

if __name__=='__main__':main()
