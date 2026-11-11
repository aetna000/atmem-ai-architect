"""Declaration validation through the actual structured proposal boundary."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from server.contracts import Project

ROOT=Path(__file__).resolve().parents[2]


def project():
    result=subprocess.run(['node','--input-type=module','-e',"import {approvalProject}from'./tests/fixtures/approval-project.mjs';process.stdout.write(JSON.stringify(approvalProject()));"],cwd=ROOT,capture_output=True,text=True,check=True)
    raw=json.loads(result.stdout)
    return {key:raw[key]for key in ['version','revision','name','provider','requirements','nodes','edges']}


class ApprovalProposalTests(unittest.TestCase):
    def test_producer_profile_is_preserved_and_uses_pure_validation(self):
        raw=project();parsed=Project.model_validate(raw)
        self.assertEqual(parsed.nodes[0].data.approvalProfile,raw['nodes'][0]['data']['approvalProfile'])
        code="import sys;sys.path.insert(0,sys.argv[1]);from server.contracts import Project;import json;Project.model_validate(json.load(sys.stdin));assert not ({'psycopg','jwt','workflow_connection'}&set(sys.modules))"
        result=subprocess.run([sys.executable,'-I','-c',code,str(ROOT)],input=json.dumps(raw),capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
    def test_wrong_owner_provider_role_or_code_selector_fails_at_producer_boundary(self):
        for mutation in ['owner','provider','origin','kind','code','coercion','payloadHash']:
            raw=project();data=raw['nodes'][0]['data'];profile=data['approvalProfile']
            if mutation=='owner':profile['componentId']='another'
            elif mutation=='provider':profile['provider']='azure'
            elif mutation=='origin':data['origin']='existing'
            elif mutation=='kind':data['kind']='note'
            elif mutation=='code':profile['processor']='unsafe:run'
            elif mutation=='coercion':profile['payloadContract']['version']=True
            else:profile['destinationContract']['payloadContractSha256']='f'*64
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):Project.model_validate(raw)


if __name__=='__main__':unittest.main()
