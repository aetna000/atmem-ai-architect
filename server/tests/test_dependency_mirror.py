import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from server.dependency_mirror import inspect_mirror


class DependencyMirrorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve();self.payload=b'public synthetic dependency bytes';(self.root/'library.whl').write_bytes(self.payload)
        self.artifact={'file':'library.whl','sha256':hashlib.sha256(self.payload).hexdigest(),'bytes':len(self.payload),'name':'example-library','version':'1.2.3','kind':'python-wheel','license':'MIT','requiresPython':'>=3.10','requiresDist':[],'source':{'url':'https://example.invalid/library.whl','metadataUrl':'https://example.invalid/library.json','metadataSha256':'a'*64,'retrievedAt':'2026-11-11T00:00:00+00:00'}}
        self.index={'format':'atmem.public-dependency-mirror','version':1,'artifacts':[self.artifact]};self.write()
    def tearDown(self):self.temp.cleanup()
    def write(self): (self.root/'index.json').write_text(json.dumps(self.index))

    def test_exact_catalog_and_different_language_artifacts_are_data_without_execution(self):
        result=inspect_mirror(self.root);self.assertEqual(result['bytes'],len(self.payload));self.assertEqual(result['artifacts'],1)
        self.assertEqual(result['sha256'],hashlib.sha256((self.root/'index.json').read_bytes()).hexdigest())
        self.artifact.update(kind='node-package',name='different-domain-library',requiresPython=None);self.write();self.assertEqual(inspect_mirror(self.root)['artifacts'],1)

    def test_changed_bytes_and_extra_entries_are_not_exposed_to_a_worker(self):
        (self.root/'library.whl').write_bytes(b'changed')
        with self.assertRaises(ValueError):inspect_mirror(self.root)
        (self.root/'library.whl').write_bytes(self.payload);(self.root/'private.env').write_text('SYNTHETIC SECRET CANARY')
        with self.assertRaisesRegex(ValueError,'undeclared'):inspect_mirror(self.root)

    def test_links_and_traversal_are_rejected_without_importing_or_following_files(self):
        original=copy.deepcopy(self.artifact)
        for name in ['../outside','/outside','a/b','index.json']:
            self.artifact['file']=name;self.write()
            with self.subTest(name=name),self.assertRaises(ValueError):inspect_mirror(self.root)
        self.index['artifacts']=[original];self.write();(self.root/'library.whl').unlink();(self.root/'library.whl').symlink_to(self.root/'index.json')
        with self.assertRaises(OSError):inspect_mirror(self.root)

    def test_credential_urls_duplicates_missing_provenance_and_limits_remain_explicit(self):
        original=copy.deepcopy(self.index)
        changes=[{'bytes':True},{'bytes':32000001},{'sha256':'not-a-digest'},{'source':{**self.artifact['source'],'url':'https://user:password@example.invalid/file'}},{'source':{**self.artifact['source'],'url':'https://example.invalid/file?token=secret'}},{'source':{**self.artifact['source'],'retrievedAt':'2026-11-11'}},{'requiresDist':['x'*501]}]
        for change in changes:
            self.index=copy.deepcopy(original);self.index['artifacts'][0].update(change);self.write()
            with self.subTest(change=change),self.assertRaises(ValueError):inspect_mirror(self.root)
        self.index=copy.deepcopy(original);self.index['artifacts']*=2;self.write()
        with self.assertRaises(ValueError):inspect_mirror(self.root)
