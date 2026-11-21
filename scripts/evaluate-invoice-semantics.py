"""Actual PDF/OCR -> signed-in local model -> independent invoice decoder probe.

Synthetic corpus, one sample per case. No cloud model, accounting API, identity,
payment, deployment or universal accuracy claim follows from this probe.
"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src/runtime')]
from invoice_document import PdfDocument
from invoice_extraction import extract_invoice
from server.local_providers import call_cli

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true',required=True);parser.add_argument('--out',required=True);parser.add_argument('--model',default='default');parser.add_argument('--effort',default='low');args=parser.parse_args()
    out=Path(args.out).resolve()
    if not out.is_relative_to(ROOT/'.local')or out.exists():raise ValueError('Use a fresh local evidence directory')
    out.mkdir(parents=True);folder=ROOT/'benchmarks/convergence/fixtures/invoices';corpus=json.loads((folder/'manifest.json').read_text())
    paths=[Path(__file__).resolve(),ROOT/'src/runtime/invoice_document.py',ROOT/'src/runtime/invoice_extraction.py',ROOT/'server/local_providers.py',folder/'manifest.json',*folder.glob('*.pdf')]
    hashes={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()for path in paths}
    (out/'manifest.json').write_text(json.dumps({'kind':'local-invoice-semantic-probe','model':'codex','requestedModel':args.model,'effort':args.effort,'sources':hashes,'cloudOperations':False,'boundary':'Authored visually inspected invoices, actual local Poppler/Tesseract, one signed-in local model sample per case, independent field/evidence validation. Not a cloud-model or full-project qualification.'},indent=2)+'\n')
    pdf=PdfDocument(tools={name:shutil.which(name)for name in ['pdfinfo','pdftotext','pdftoppm','tesseract']});results=[]
    for name in ['invoice-text.pdf','invoice-scan.pdf','invoice-mixed.pdf','invoice-ambiguous.pdf','invoice-injected.pdf']:
        calls=[];start=time.monotonic();result=None;error=None;document=None
        def generate(payload,schema,instruction):
            async def connected():return False
            call={'request':json.loads(payload),'schema':schema,'instruction':instruction};calls.append(call)
            response=asyncio.run(call_cli('codex',args.model,payload,instruction,schema,connected,effort=args.effort,timeout=180));call['response']=response
            return json.dumps(response,ensure_ascii=False)
        try:
            raw=(folder/name).read_bytes();document=pdf.extract(raw,hashlib.sha256(raw).hexdigest());result=extract_invoice(document,generate)
        except Exception as exc:error={'kind':type(exc).__name__,'message':str(exc)[:500]}
        checks={'completed':error is None,'oneModelCall':len(calls)==1,'mandatoryHumanReview':result is not None and result['requiresHumanReview']is True}
        if result:
            for key,expected in corpus['expected'].items():checks[key]=result[key]==expected
            checks['sourceDigest']=result['documentSha256']==corpus['fixtures'][name]['sha256']
        record={'case':name,'passed':all(checks.values()),'checks':checks,'seconds':round(time.monotonic()-start,3),'result':result,'error':error}
        (out/(name+'.json')).write_text(json.dumps({'result':record,'documentEvidence':document,'modelOperations':calls},indent=2,ensure_ascii=False)+'\n');results.append(record);print(json.dumps({'case':name,'passed':record['passed'],'seconds':record['seconds']}),flush=True)
    receipt={'kind':'local-invoice-semantic-probe','passed':all(row['passed']for row in results),'results':results,'sourcesUnchanged':all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest for path,digest in hashes.items()),'cloudOperations':False,'fullProjectQualification':False,'limitations':['Five authored English invoices; not representative production quality or a cloud model assessment.','Quote/value checks do not prove semantic correctness of every extracted field. Human review remains mandatory.','Native authenticated upload, cloud database/storage/worker resources, retention, accounting vendor semantics and operations remain separate.']}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');raise SystemExit(0 if receipt['passed']and receipt['sourcesUnchanged']else 1)
