"""Active check evidence must never become delivery/acceptance implicitly."""
import hashlib,io,json,os,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from server.engineering_artifacts import EngineeringArtifacts,WorkingCheckpoints,CheckSources
from server.engineering_sessions import ModelSelection,ProjectScope,SessionError,SqliteSessionStore

class WorkingCheckpointTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.source=self.root/'work';self.source.mkdir();self.store=SqliteSessionStore(self.root/'control.sqlite');self.scope=ProjectScope('local-owner','project-one');self.session=self.store.create(self.scope,'workspace-one','backend','private-handle',ModelSelection('exact-model','high'))['id'];self.store.reserve(self.scope,self.session,'run-one','Implement');self.store.attach_turn(self.scope,self.session,'run-one','turn-one');self.delivery=EngineeringArtifacts(self.store);self.checkpoints=WorkingCheckpoints(self.store);self.sources=CheckSources(self.delivery,self.checkpoints)
  (self.source/'context.json').write_text('Pinned requirements');self.pins={'context.json':hashlib.sha256((self.source/'context.json').read_bytes()).hexdigest()}
 def tearDown(self):self.store.close();self.temp.cleanup()
 def capture(self):return self.checkpoints.capture(self.scope,self.session,self.source,expected_inputs=self.pins)
 def test_same_bytes_reuse_checkpoint_and_changed_files_do_not_rewrite_evidence(self):
  (self.source/'nested').mkdir();(self.source/'nested/library.py').write_text('original')
  first=self.capture();self.assertEqual(first,self.capture());self.assertEqual(first['kind'],'working_checkpoint');self.assertEqual(first['turnStatus'],'in_progress')
  self.assertEqual(self.delivery.manifests(self.scope,self.session),[])
  with self.assertRaises(SessionError):self.delivery.capture(self.scope,self.session,self.source)
  with self.assertRaises(SessionError):self.delivery.get(self.scope,self.session,first['id'])
  (self.source/'nested/library.py').write_text('changed');second=self.capture();self.assertNotEqual(first['sha256'],second['sha256']);self.assertNotEqual(first['id'],second['id'])
  saved,data=self.sources.get(self.scope,self.session,first['id'])
  with zipfile.ZipFile(io.BytesIO(data)) as z:self.assertEqual(z.read('nested/library.py'),b'original')
  self.assertEqual(saved,first)
  self.store.terminal(self.scope,self.session,'run-one','turn-one','completed')
  with self.assertRaises(SessionError):self.capture()
  delivered=self.delivery.capture(self.scope,self.session,self.source);self.assertEqual(delivered['kind'],'delivery');self.assertNotEqual(delivered['id'],second['id']);self.assertTrue(self.sources.contains(self.scope,self.session,first['id']))
 def test_original_pins_ownership_links_and_checkpoint_boundaries_fail_closed(self):
  with self.assertRaises(SessionError):self.checkpoints.capture(self.scope,self.session,self.source)
  (self.source/'context.json').write_text('changed')
  with self.assertRaises(SessionError):self.capture()
  (self.source/'context.json').write_text('Pinned requirements');(self.source/'unsafe').symlink_to(self.root)
  with self.assertRaises(SessionError):self.capture()
  (self.source/'unsafe').unlink();first=self.capture()
  for scope in [ProjectScope('other-owner','project-one'),ProjectScope('local-owner','other-project')]:
   with self.assertRaises(SessionError):self.sources.get(scope,self.session,first['id'])
  self.assertEqual(self.store.db.execute('select count(*) from engineering_artifacts').fetchone()[0],0)
 def test_later_mutation_of_an_earlier_file_is_rejected_before_any_persist(self):
  (self.source/'a.py').write_text('original');(self.source/'z.py').write_text('later')
  original=zipfile.ZipFile.writestr
  def mutate(archive,name,data,*args,**kwargs):
   result=original(archive,name,data,*args,**kwargs)
   if getattr(name,'filename',name)=='z.py':(self.source/'a.py').write_text('changed after its read')
   return result
  with patch.object(zipfile.ZipFile,'writestr',mutate),self.assertRaisesRegex(SessionError,'changed'):self.capture()
  self.assertEqual(self.store.db.execute('select count(*) from engineering_checkpoints').fetchone()[0],0)
 def test_run_storage_count_is_bounded_but_reuse_still_works(self):
  for i in range(16):(self.source/'library.py').write_text(str(i));last=self.capture()
  self.assertEqual(self.capture(),last)
  (self.source/'library.py').write_text('new')
  with self.assertRaisesRegex(SessionError,'limit'):self.capture()
  self.assertEqual(self.store.db.execute('select count(*) from engineering_checkpoints').fetchone()[0],16)
