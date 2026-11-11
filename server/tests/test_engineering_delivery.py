import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from server.engineering_delivery import seed_delivery
from server.engineering_assets.prepare_tools import prepare


class DeliveryContractTests(unittest.TestCase):
    def test_exported_helper_restores_offline_tools_for_infrastructure_and_plain_code(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);pinned=seed_delivery(root);mirror=root/'approved-provider-mirror';mirror.mkdir()
            report=prepare(root,{'python':sys.executable,'node':sys.executable,'terraform':sys.executable,'providerMirror':mirror},['python','terraform','providerMirror'])
            self.assertEqual(report['configured'],['python','node','terraform','providerMirror'])
            self.assertFalse(report['downloads']);self.assertFalse(report['cloudAccess'])
            config=(root/'.worker-tmp/terraform.rc').read_text();self.assertIn('filesystem_mirror',config);self.assertNotIn('direct',config)
            for name,digest in pinned.items():self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest)
            self.assertEqual(prepare(root,{'python':sys.executable,'node':sys.executable,'terraform':sys.executable,'providerMirror':mirror},['python'])['configured'],report['configured'])
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);seed_delivery(root)
            report=prepare(root,{'python':sys.executable},['python'])
            self.assertEqual(report['configured'],['python']);self.assertIn('terraform',report['missingOptional'])
            self.assertFalse((root/'.worker-tmp/terraform.rc').exists())

    def test_missing_required_tool_is_explicit_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);seed_delivery(root)
            with self.assertRaisesRegex(ValueError,'Required tools'):prepare(root,{'python':sys.executable},['terraform'])
            self.assertFalse((root/'.tools').exists());self.assertFalse((root/'.worker-tmp').exists())

    def test_existing_project_files_and_foreign_directory_links_are_preserved(self):
        for kind in ['tool-file','tool-directory-link','temporary-link','different-config']:
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as folder:
                root=Path(folder)/'project';root.mkdir();outside=Path(folder)/'foreign';outside.mkdir();seed_delivery(root)
                if kind=='tool-directory-link':(root/'.tools').symlink_to(outside,target_is_directory=True)
                elif kind=='temporary-link':(root/'.worker-tmp').symlink_to(outside,target_is_directory=True)
                else:
                    (root/'.tools').mkdir()
                    if kind=='tool-file':(root/'.tools/python').write_text('KEEP MY SOURCE')
                    else:(root/'.tools/toolchain.json').write_text('{"tools":{"python":"unexpected"}}')
                with self.assertRaises(ValueError):prepare(root,{'python':sys.executable},['python'])
                self.assertEqual(list(outside.iterdir()),[])
                if kind=='tool-file':self.assertEqual((root/'.tools/python').read_text(),'KEEP MY SOURCE')

    def test_seed_refuses_overwrite_and_linked_parent_before_writing_anything(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'project';root.mkdir();outside=Path(folder)/'foreign';outside.mkdir()
            (root/'atmem-tools').symlink_to(outside,target_is_directory=True)
            with self.assertRaises(ValueError):seed_delivery(root)
            self.assertFalse((root/'ATMEM_DELIVERY.md').exists());self.assertEqual(list(outside.iterdir()),[])
