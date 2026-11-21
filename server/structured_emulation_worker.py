"""Execute server-generated Azure source acceptance checks without Azure/network.

These are local source/cryptographic/ASGI checks with scripted key/model/policy
transport. Neither cloud authentication nor real inference is established.
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
    entries=[(entry,'azure') for entry in plan.get('azureStructuredPlan',{}).get('entries',[])]+[(entry,'gcp') for entry in plan.get('gcpStructuredPlan',{}).get('entries',[])]+[(entry,'ibm') for entry in plan.get('ibmStructuredPlan',{}).get('entries',[])]
    checks=[]
    with deny_network():
        for entry,provider in entries:
            address=entry['row']['address']
            if not re.fullmatch(r'block_[0-9a-f]+',address):raise ValueError('Invalid compiler component address')
            app=root/'applications'/address
            script=app/(provider+'_acceptance.py')
            old=list(sys.path)
            try:
                sys.path.insert(0,str(app))
                for name in ['azure_structured','gcp_structured','ibm_structured','policy_review','structured_output','structured_http','http_acceptance','export_contract_acceptance']:sys.modules.pop(name,None)
                spec=importlib.util.spec_from_file_location('acceptance_'+address,script)
                module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
                log=io.StringIO()
                result=unittest.TextTestRunner(stream=log,verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(module))
                checks.append({'name':'Generated '+provider+' application JWT, HTTP, output and account-policy boundaries','passed':result.wasSuccessful() and result.testsRun>0,'testsRun':result.testsRun,'componentId':entry['row']['id'],'sourceSha256':hashlib.sha256((app/(provider+'_structured.py')).read_bytes()).hexdigest(),'evidence':'host-runtime-cryptographic-jwt-scripted-'+provider+'-transport','output':log.getvalue()[-6000:]})
            finally:sys.path[:]=old
    providers=sorted({provider for _,provider in entries})
    return {'version':1,'kind':'local-structured-application-tests','backend':'host-asgi-scripted-'+('-'.join(providers)),'status':'passed' if checks and all(c['passed'] for c in checks) else 'failed','checks':checks,'modelMode':'scripted-fixture','cloudOperations':False,'terraformApply':'not_run','limitations':['Generated Python source executes on this host, not a provider container image.','Ephemeral RSA/ES256 JWT signatures and local ASGI requests are real; provider key retrieval, policy and model transports are scripted, with network denied.','Cloud sign-in, MFA, group assignment and token revocation, workload-identity exchange, model quality, regional capacity, container startup/scan, account plan and deployment remain unverified.','Token authorization is bounded by expiry/skew; these modules do not implement independent continuous group/user revocation.']}


if __name__=='__main__':
    sys.dont_write_bytecode=True
    try:report=run(sys.argv[1])
    except Exception as error:report={'version':1,'status':'failed','checks':[],'message':'Generated source checks failed: '+type(error).__name__,'cloudOperations':False}
    print(json.dumps(report));raise SystemExit(0 if report['status']=='passed' else 1)
