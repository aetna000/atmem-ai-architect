import hashlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from server.windows_snapshot import snapshot
from server.engineering_sessions import SessionError

@unittest.skipUnless(os.name=='nt','Requires real Windows file handles')
class WindowsSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'workspace';self.root.mkdir()
    def tearDown(self):self.temp.cleanup()
    def capture(self,**options):return snapshot(self.root,excluded={'.git'},max_bytes=options.get('max_bytes',1000000),max_files=options.get('max_files',30))
    def test_exact_unicode_bytes_and_inventory(self):
        (self.root/'spec-kit').mkdir();content='Library — café\n'.encode();(self.root/'spec-kit'/'requirements.md').write_bytes(content)
        data,files,_=self.capture()
        with zipfile.ZipFile(io.BytesIO(data))as z:self.assertEqual(z.read('spec-kit/requirements.md'),content)
        self.assertEqual(files[-1]['sha256'],hashlib.sha256(content).hexdigest())
    def test_hard_link_refused_and_failure_closes_handles(self):
        p=self.root/'source';p.write_text('private');os.link(p,self.root/'alias')
        with self.assertRaises(SessionError):self.capture()
        p.unlink();(self.root/'alias').unlink()
    def test_directory_junction_refused(self):
        outside=Path(self.temp.name)/'outside';outside.mkdir();(outside/'private').write_text('outside')
        subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(self.root/'linked'),str(outside)],check=True,capture_output=True)
        with self.assertRaises(SessionError):self.capture()
        (self.root/'linked').rmdir()
    def test_root_junction_refused(self):
        alias=Path(self.temp.name)/'alias';subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(alias),str(self.root)],check=True,capture_output=True)
        try:
            with self.assertRaises(SessionError):snapshot(alias,excluded=set(),max_bytes=1000,max_files=10)
        finally:alias.rmdir()
    def test_byte_and_entry_bounds(self):
        (self.root/'a').write_bytes(b'12345')
        with self.assertRaises(SessionError):self.capture(max_bytes=4)
        (self.root/'b').write_bytes(b'1')
        with self.assertRaises(SessionError):self.capture(max_files=1)
    def test_empty_directories_count_toward_entry_bound(self):
        (self.root/'a').mkdir();(self.root/'b').mkdir()
        with self.assertRaises(SessionError):self.capture(max_files=1)
    def test_excluded_content_is_absent(self):
        (self.root/'.git').mkdir();(self.root/'.git'/'private').write_text('excluded')
        data,files,excluded=self.capture();self.assertEqual(files,[]);self.assertEqual(excluded,['.git'])
        with zipfile.ZipFile(io.BytesIO(data))as z:self.assertEqual(z.namelist(),[])
    def test_capture_denies_concurrent_write_and_keeps_original_bytes(self):
        source=self.root/'a.txt';source.write_bytes(b'original');original=zipfile.ZipFile.writestr;denied=[]
        def write(archive,item,content,*args,**kwargs):
            if item.filename=='a.txt':
                try:source.write_bytes(b'changed')
                except PermissionError:denied.append(True)
            return original(archive,item,content,*args,**kwargs)
        with patch.object(zipfile.ZipFile,'writestr',write):data,_,_=self.capture()
        self.assertEqual(denied,[True]);self.assertEqual(source.read_bytes(),b'original')
        with zipfile.ZipFile(io.BytesIO(data))as z:self.assertEqual(z.read('a.txt'),b'original')
    def test_added_entry_during_capture_is_rejected(self):
        (self.root/'a.txt').write_bytes(b'original');original=zipfile.ZipFile.writestr
        def write(archive,item,content,*args,**kwargs):
            if item.filename=='a.txt':(self.root/'late.txt').write_bytes(b'new')
            return original(archive,item,content,*args,**kwargs)
        with patch.object(zipfile.ZipFile,'writestr',write):
            with self.assertRaises(SessionError):self.capture()
    def test_existing_writer_fails_closed(self):
        source=self.root/'a';source.write_bytes(b'original')
        with source.open('ab')as writer:
            with self.assertRaises(SessionError):self.capture()
