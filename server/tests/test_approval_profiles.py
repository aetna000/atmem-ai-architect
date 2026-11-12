"""Declaration validation through the actual structured proposal boundary."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from server.contracts import Project

ROOT=Path(__file__).resolve().parents[2]


def project(template=False):
    fixture="approvalTemplateProject().project" if template else "approvalProject()"
    result=subprocess.run(['node','--input-type=module','-e',"import {approvalProject,approvalTemplateProject}from'./tests/fixtures/approval-project.mjs';process.stdout.write(JSON.stringify("+fixture+"));"],cwd=ROOT,capture_output=True,text=True,check=True)
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

    def test_template_survives_structured_producer_without_runtime_dependencies(self):
        raw=project(template=True);parsed=Project.model_validate(raw)
        self.assertEqual(parsed.nodes[0].data.approvalProfile,raw['nodes'][0]['data']['approvalProfile'])
        self.assertIsInstance(parsed.nodes[0].data.approvalProfile['publicOrigin'],dict)
    def test_template_output_owner_provider_environment_and_sensitive_names_are_checked(self):
        for mutation in ['missing','provider','environment','sensitive','note']:
            raw=project(template=True);ref=raw['nodes'][0]['data']['approvalProfile']['identitySettings']['POOL_ID']['nativeOutput']
            if mutation=='missing':ref['componentId']='absent'
            elif mutation=='provider':raw['nodes'][1]['data']['provider']='azure'
            elif mutation=='environment':ref['environment']='production'
            elif mutation=='sensitive':ref['name']='client_secret'
            else:raw['nodes'][1]['data']['kind']='note'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):Project.model_validate(raw)


if __name__=='__main__':unittest.main()
