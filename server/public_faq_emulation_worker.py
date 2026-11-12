"""Execute emitted public catalog/HTTP checks with outbound network denied.

No real model, cloud IAM, workload token or deployment evidence is claimed.
"""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from emulation_worker import deny_network


def run(folder):
    root=Path(folder).resolve()
    plan=json.loads((root/'resource-schedule.json').read_text())
    entries=plan.get('publicFaqPlan',{}).get('entries',[])
    checks=[]
    with deny_network():
        for entry in entries:
            address=entry['row']['address'];provider=entry['provider']
            if not re.fullmatch(r'block_[0-9a-f]+',address) or provider not in {'aws','azure','gcp','ibm'}:raise ValueError('Invalid compiler component')
            app=root/'applications'/address;old=list(sys.path)
            try:
                sys.path.insert(0,str(app))
                for name in ['public_faq','public_faq_app','public_catalog_store','public_catalog_admin','structured_http','structured_output','faq_core_acceptance','faq_http_acceptance','faq_catalog_admin_acceptance','faq_catalog_store_acceptance','faq_lambda_acceptance']:sys.modules.pop(name,None)
                spec=importlib.util.spec_from_file_location('acceptance_'+address,app/'faq_acceptance.py')
                module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
                log=io.StringIO()
                result=unittest.TextTestRunner(stream=log,verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(module))
                checks.append({'name':'Generated public FAQ catalog, conditional editing, citations, freshness and HTTP boundaries','passed':result.wasSuccessful() and result.testsRun>0,'testsRun':result.testsRun,'componentId':entry['row']['id'],'sourceSha256':hashlib.sha256((app/'public_faq.py').read_bytes()).hexdigest(),'evidence':'host-asgi-scripted-public-catalog-'+provider,'output':log.getvalue()[-6000:]})
            finally:sys.path[:]=old
    return {'version':1,'kind':'local-public-faq-tests','backend':'host-asgi-scripted-public-catalog','status':'passed' if checks and all(c['passed'] for c in checks) else 'failed','checks':checks,'modelMode':'scripted-fixture','cloudOperations':False,'terraformApply':'not_run','limitations':['Emitted Python source executes on this host, not a Linux/provider image.','Local ASGI, retrieval, output validation, source lifecycle and conditional-edit fixtures run with outbound network denied.','The model and cloud object-store transports are scripted. Native workload authentication, effective IAM, real conditional API behavior, model factual/citation quality and latency remain unverified.','Image build/startup/security scan, destination capacity/cost/abuse controls, account plan and deployment require separate evidence.']}


if __name__=='__main__':
    sys.dont_write_bytecode=True
    try:report=run(sys.argv[1])
    except Exception as error:report={'version':1,'status':'failed','checks':[],'message':'Generated public FAQ checks failed: '+type(error).__name__,'cloudOperations':False}
    print(json.dumps(report));raise SystemExit(0 if report['status']=='passed' else 1)
