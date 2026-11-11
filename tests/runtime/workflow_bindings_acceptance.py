"""Pure template/output-ledger qualification; no cloud or database operations."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src/runtime'),str(Path(__file__).resolve().parent)]
from workflow_bindings import ApplicationTemplate,resolve_template,write_binding,load_bound_profile
from workflow_profile import ApplicationProfile
from workflow_application_acceptance import configuration

def fixture(provider='aws'):
    raw=configuration(provider=provider);raw['format']='approval-application-template-v1';outputs=[]
    def ref(owner,name,value):
        data={'componentId':owner,'provider':provider,'environment':raw['environment'],'name':name}
        outputs.append({**data,'value':value,'sensitive':False,'sourceSha256':'a'*64});return {'nativeOutput':data}
    raw['publicOrigin']=ref(raw['componentId'],'public_origin',raw['publicOrigin'])
    for key in raw['identitySettings']:
        if key not in {'REGION','AUTH_SCOPE'}:raw['identitySettings'][key]=ref('native-identity',key.lower(),raw['identitySettings'][key])
    return raw,{'version':1,'outputs':outputs}

class BindingTests(unittest.TestCase):
    def test_four_provider_templates_resolve_exact_public_outputs_and_keep_fixed_policy(self):
        for provider in ['aws','azure','gcp','ibm']:
            raw,ledger=fixture(provider);before=copy.deepcopy(raw);template=ApplicationTemplate(raw);profile,receipt=resolve_template(template,ledger)
            self.assertEqual(profile.data['provider'],provider);self.assertEqual(profile.data['accountId'],raw['accountId']);self.assertEqual(profile.data['payloadContract'],raw['payloadContract'])
            for ref in template.references:
                expected=next(row['value']for row in ledger['outputs']if all(row[k]==ref[k]for k in ['componentId','provider','environment','name']))
                value=profile.data
                for key in ref['path'].split('/'):value=value[key]
                self.assertEqual(value,expected)
            self.assertFalse(receipt['cloudVerified']);self.assertEqual(receipt['status'],'structurally_resolved');self.assertEqual(raw,before)
    def test_missing_wrong_provider_or_wrong_environment_never_selects_a_default(self):
        raw,ledger=fixture();template=ApplicationTemplate(raw)
        for mutation in ['missing','provider','environment','owner']:
            inputs=copy.deepcopy(ledger)
            if mutation=='missing':inputs['outputs'].pop()
            elif mutation=='owner':inputs['outputs'][0]['componentId']='foreign'
            elif mutation=='provider':inputs['outputs'][0]['provider']='azure'
            else:inputs['outputs'][0]['environment']='production'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):resolve_template(template,inputs)
    def test_sensitive_credential_like_duplicate_and_mixed_snapshot_records_are_rejected(self):
        raw,ledger=fixture();template=ApplicationTemplate(raw)
        for mutation in ['sensitive','credential','duplicate','snapshot','claim']:
            inputs=copy.deepcopy(ledger)
            if mutation=='sensitive':inputs['outputs'][0]['sensitive']=True
            elif mutation=='credential':inputs['outputs'][0]['value']='-----BEGIN PRIVATE KEY-----'
            elif mutation=='duplicate':inputs['outputs'].append(copy.deepcopy(inputs['outputs'][0]))
            elif mutation=='snapshot':inputs['outputs'][-1]['sourceSha256']='b'*64
            else:inputs['approved']=True
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):resolve_template(template,inputs)
    def test_ownership_and_operation_policy_cannot_be_deferred(self):
        raw,ledger=fixture();ref=raw['publicOrigin']
        for key in ['provider','componentId','accountId','environment','operationKind','payloadContract']:
            value=copy.deepcopy(raw);value[key]=copy.deepcopy(ref)
            with self.subTest(key=key),self.assertRaises(ValueError):ApplicationTemplate(value)
    def test_template_cannot_start_as_a_concrete_profile(self):
        raw,_=fixture()
        with self.assertRaises(ValueError):ApplicationProfile(raw)
    def test_binding_bundle_checks_marker_profile_and_template_without_overwriting(self):
        raw,ledger=fixture()
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);template=root/'template.json';inputs=root/'outputs.json';out=root/'binding'
            template.write_text(json.dumps(raw));inputs.write_text(json.dumps(ledger));receipt=write_binding(template,inputs,out)
            profile=load_bound_profile(template,out);self.assertEqual(profile.sha256,receipt['profileSha256'])
            with self.assertRaises(FileExistsError):write_binding(template,inputs,out)
            changed=profile.data;changed['operationKind']='account_change';(out/'application-profile.json').write_text(json.dumps(changed))
            with self.assertRaises(ValueError):load_bound_profile(template,out)
            changed_template=copy.deepcopy(raw);changed_template['operationKind']='account_change';template.write_text(json.dumps(changed_template))
            (out/'application-profile.json').write_text(json.dumps(profile.data))
            with self.assertRaises(ValueError):load_bound_profile(template,out)
            template.write_text(json.dumps(raw))
            (out/'application-profile.json').write_text(json.dumps(profile.data));marker=json.loads((out/'binding-receipt.json').read_text());marker['version']=True;(out/'binding-receipt.json').write_text(json.dumps(marker))
            with self.assertRaises(ValueError):load_bound_profile(template,out)
            (out/'binding-receipt.json').unlink()
            with self.assertRaises(FileNotFoundError):load_bound_profile(template,out)
    def test_invalid_ledger_does_not_create_a_partial_output_directory(self):
        raw,ledger=fixture();ledger['outputs'][0]['sensitive']=True
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);(root/'template.json').write_text(json.dumps(raw));(root/'outputs.json').write_text(json.dumps(ledger))
            with self.assertRaises(ValueError):write_binding(root/'template.json',root/'outputs.json',root/'out')
            self.assertFalse((root/'out').exists())

if __name__=='__main__':unittest.main(verbosity=2)
