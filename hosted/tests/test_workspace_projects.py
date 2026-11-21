import json
import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from hosted.sqlite_store import SQLiteTransactions
from hosted.projects import Profiles,Projects,ProjectUnavailable
from hosted.workspace_projects import WorkspaceProjects
from hosted.x_access import XIdentity
from hosted.credits import Conflict

class WorkspaceCreationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.store=SQLiteTransactions(Path(self.temp.name)/'workspace.sqlite')
  self.profiles=Profiles(self.store)
  for subject in ['1','2']:self.profiles.register(XIdentity(subject,subject,'User'))
  self.projects=Projects(self.store,self.profiles);self.workspace=WorkspaceProjects(self.store,self.profiles,self.projects)
 def tearDown(self):self.temp.cleanup()
 def test_new_project_is_a_saved_architect_document_without_upload(self):
  saved=self.workspace.create('1','request','Customer portal')
  row,raw=self.projects.download('1',saved['id']);file=json.loads(raw)
  self.assertEqual(file['format'],'atmem.ai-architect.project')
  self.assertEqual(file['meta']['id'],saved['id']);self.assertEqual(file['meta']['name'],'Customer portal')
  self.assertEqual(file['design'],{'provider':'tools','nodes':[],'edges':[]})
  with self.assertRaises(ProjectUnavailable):self.projects.download('2',saved['id'])
 def test_concurrent_creation_retry_does_not_create_duplicate_projects(self):
  with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(lambda _:self.workspace.create('1','same-request','Project'),range(8)))
  self.assertEqual(len({row['id'] for row in results}),1);self.assertEqual(len(self.projects.list('1')['projects']),1)
  with self.assertRaises(Conflict):self.workspace.create('1','same-request','Different title')

 def test_trash_and_restore_preserve_content_and_require_current_owned_revision(self):
  saved=self.workspace.create('1','new','Preserved project');original=self.projects.download('1',saved['id'])[1]
  trashed=self.workspace.move('1',saved['id'],1,True)
  self.assertEqual(self.projects.list('1')['projects'],[]);self.assertEqual(self.projects.list('1')['bin'][0]['id'],saved['id'])
  with self.assertRaises(ProjectUnavailable):self.workspace.move('2',saved['id'],trashed['revision'],False)
  with self.assertRaises(Conflict):self.workspace.move('1',saved['id'],1,False)
  restored=self.workspace.move('1',saved['id'],trashed['revision'],False)
  self.assertEqual(restored['revision'],3);self.assertEqual(self.projects.download('1',saved['id'])[1],original)
