"""Actual public runtime delivery, isolated CLI and fail-before-write boundaries."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from server.engineering_delivery import seed_delivery
from server.engineering_assets.materialize_runtime import materialize

ROOT=Path(__file__).resolve().parents[2]


class ApplicationRuntimeDeliveryTests(unittest.TestCase):
    def test_actual_isolated_helper_materializes_all_four_exact_provider_locks(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);pins=seed_delivery(root);catalog=json.loads((root/'atmem-tools/application-runtime.json').read_text())
            for provider in ['aws','azure','gcp','ibm']:
                result=subprocess.run([sys.executable,'-I',str(root/'atmem-tools/materialize-runtime.py'),'--provider',provider,'--out','applications/'+provider],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr);app=root/'applications'/provider;manifest=json.loads((app/'runtime-manifest.json').read_text())
                self.assertEqual(manifest['provider'],provider);self.assertEqual((app/'requirements.lock').read_text(),catalog['providers'][provider]['requirements'])
                self.assertEqual(manifest['catalogSha256'],pins['atmem-tools/application-runtime.json'])
                for name,digest in manifest['files'].items():self.assertEqual(hashlib.sha256((app/name).read_bytes()).hexdigest(),digest)
                self.assertTrue((app/'workflow_process_stage.py').exists());self.assertFalse(list(app.glob('invoice*')));self.assertFalse((app/'tests').exists())
                for name,digest in pins.items():self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest)
    def test_materialized_pure_contract_runs_without_host_repo_or_runtime_sdks(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);seed_delivery(root);materialize(root,'ibm','service')
            code="""import sys
sys.path.insert(0,sys.argv[1])
from workflow_bindings import application_declaration
from workflow_payload import PayloadContract
from workflow_review import ReviewPolicy
shape={'type':'object','properties':{'value':{'type':'string','minBytes':0,'maxBytes':4}},'required':['value']}
payload=PayloadContract({'version':1,'id':'received-contract','source':shape,'result':shape})
review=ReviewPolicy(payload,id='received-review',editable_fields=['value'])
assert review.validate_edit({'value':'a'},{'value':'a'},{'value':'🙂'})=={'value':'🙂'}
assert not ({'psycopg','jwt','boto3','fastapi'}&set(sys.modules))
print('PURE_RUNTIME_AVAILABLE')"""
            result=subprocess.run([sys.executable,'-I','-c',code,str(root/'service')],cwd=root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr);self.assertIn('PURE_RUNTIME_AVAILABLE',result.stdout)
    def test_unavailable_provider_unknown_paths_and_reserved_roots_create_nothing(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);seed_delivery(root)
            for provider,dest in [('other','service'),('aws','../foreign'),('aws','/absolute'),('aws','.tools/runtime'),('aws','atmem-tools/runtime'),('aws','a//b'),('aws','a/./b'),('aws','a\\b')]:
                with self.subTest(provider=provider,dest=dest),self.assertRaises(ValueError):materialize(root,provider,dest)
            self.assertEqual({p.name for p in root.iterdir()},{'ATMEM_DELIVERY.md','atmem-tools'})
    def test_existing_files_and_symlinked_ancestors_are_never_adopted(self):
        with tempfile.TemporaryDirectory()as tmp,tempfile.TemporaryDirectory()as outside:
            root=Path(tmp);seed_delivery(root);(root/'application').mkdir();(root/'application/keep.txt').write_text('KEEP');(root/'linked').symlink_to(outside,target_is_directory=True)
            for dest in ['application','linked/application']:
                with self.subTest(dest=dest),self.assertRaises(ValueError):materialize(root,'aws',dest)
            self.assertEqual((root/'application/keep.txt').read_text(),'KEEP');self.assertEqual(list(Path(outside).iterdir()),[])
    def test_tampered_source_and_path_in_catalog_fail_before_output_creation(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);seed_delivery(root);path=root/'atmem-tools/application-runtime.json';raw=path.read_bytes()
            for mutation in ['digest','path','version','duplicate']:
                catalog=json.loads(raw)
                if mutation=='digest':catalog['files']['workflow_application.py']['content']+='\n# changed'
                elif mutation=='path':catalog['files']['../foreign.py']=catalog['files'].pop('workflow_application.py')
                elif mutation=='version':catalog['version']=True
                else:
                    path.write_text('{"version":1,"version":1}')
                if mutation!='duplicate':path.write_text(json.dumps(catalog))
                with self.subTest(mutation=mutation),self.assertRaises(ValueError):materialize(root,'aws','service')
                self.assertFalse((root/'service').exists())
    def test_generated_catalog_bytes_equal_authoritative_runtime_sources(self):
        data=json.loads((ROOT/'server/engineering_assets/application-runtime.json').read_text())
        for name,entry in data['files'].items():self.assertEqual(entry['content'].encode(),(ROOT/'src/runtime'/name).read_bytes())
        self.assertIn('No domain implementation',data['boundary'])
    def test_seed_checks_new_asset_conflicts_before_any_input_write(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);(root/'atmem-tools').mkdir();(root/'atmem-tools/application-runtime.json').write_text('KEEP')
            with self.assertRaises(ValueError):seed_delivery(root)
            self.assertFalse((root/'ATMEM_DELIVERY.md').exists());self.assertEqual((root/'atmem-tools/application-runtime.json').read_text(),'KEEP')


if __name__=='__main__':unittest.main()
