"""Actual isolated SQL checker transfer, denial, classification and cleanup checks.

Synthetic editorial/inventory schemas only. No model inference, host SQL or cloud.
"""
import argparse,hashlib,io,json,sys,uuid,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker,ValidationSpec
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--image',required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--endpoint',required=True);parser.add_argument('--platform',choices=['linux/arm64','linux/amd64'],default='linux/arm64');args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
worker=DockerValidationWorker(args.endpoint);driver=('/usr/local/bin/python3','-I','/opt/atmem/sql_validation.py','-m','unittest','discover','-v')
code=r'''
import errno,os,pathlib,socket,stat,unittest
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
class SqlFixture(unittest.TestCase):
 def test_editorial_transaction_and_readonly_role(self):
  dsn=os.environ['ATMEM_TEST_POSTGRES_DSN']
  with psycopg.connect(dsn)as c:
   self.assertTrue(170000<=int(c.execute('SHOW server_version_num').fetchone()[0])<180000)
   c.execute('CREATE TABLE editorial_drafts(id integer primary key, status text)');c.execute("INSERT INTO editorial_drafts VALUES(1,'review')")
   c.execute("CREATE ROLE editorial_reader LOGIN PASSWORD 'synthetic-fixture-reader'");c.execute('GRANT SELECT ON editorial_drafts TO editorial_reader')
  with psycopg.connect(make_conninfo(dsn,user='editorial_reader',password='synthetic-fixture-reader'))as c:
   self.assertEqual(c.execute('SELECT status FROM editorial_drafts').fetchone()[0],'review')
   with self.assertRaises(psycopg.errors.InsufficientPrivilege):c.execute("UPDATE editorial_drafts SET status='published'")
 def test_inventory_rollback(self):
  with psycopg.connect(os.environ['ATMEM_TEST_POSTGRES_DSN'])as c:
   c.execute('CREATE TABLE inventory(item text primary key, quantity integer check(quantity>=0))');c.execute("INSERT INTO inventory VALUES('camera',2)")
  with psycopg.connect(os.environ['ATMEM_TEST_POSTGRES_DSN'])as c:
   with self.assertRaises(psycopg.errors.CheckViolation):
    with c.transaction():c.execute("UPDATE inventory SET quantity=-1")
   self.assertEqual(c.execute('SELECT quantity FROM inventory').fetchone()[0],2)
 def test_wrong_credentials_fail(self):
  with self.assertRaises(psycopg.OperationalError):psycopg.connect(make_conninfo(os.environ['ATMEM_TEST_POSTGRES_DSN'],password='wrong-fixture-password'))
 def test_source_and_image_are_readonly_and_capabilities_dropped(self):
  self.assertEqual(os.getuid(),65532)
  with self.assertRaises(PermissionError):pathlib.Path(__file__).write_text('MUTATED')
  with self.assertRaises(OSError)as blocked:pathlib.Path('/opt/atmem/sql_validation.py').write_text('MUTATED')
  self.assertIn(blocked.exception.errno,{errno.EACCES,errno.EROFS})
  with self.assertRaises(PermissionError):os.setuid(0)
  status=pathlib.Path('/proc/self/status').read_text();self.assertIn('CapEff:\t0000000000000000',status);self.assertIn('NoNewPrivs:\t1',status)
  self.assertEqual(stat.S_IMODE(pathlib.Path(os.environ['ATMEM_TEST_POSTGRES_DATA']).stat().st_mode),0o700)
 def test_private_network_namespace(self):
  self.assertEqual({p.name for p in pathlib.Path('/sys/class/net').iterdir()},{'lo'})
  self.assertFalse(pathlib.Path('/var/run/docker.sock').exists())
  sock=socket.socket();sock.settimeout(.2)
  try:
   with self.assertRaises(OSError):sock.connect(('198.51.100.1',9))
  finally:sock.close()
'''
empty_fixture=r'''
import os,unittest,psycopg
class Fresh(unittest.TestCase):
 def test_new_database_has_no_previous_job_data(self):
  with psycopg.connect(os.environ['ATMEM_TEST_POSTGRES_DSN'])as c:
   self.assertIsNone(c.execute("SELECT to_regclass('public.editorial_drafts')").fetchone()[0]);self.assertIsNone(c.execute("SELECT to_regclass('public.inventory')").fetchone()[0])
'''

def archive(source):
 stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w')as z:z.writestr('test_sql.py',source)
 return stream.getvalue()

rows=[]
for name,source,expected,sql_fixture,budget in [('transfer_and_denials',code,'passed',True,60),('fresh_job',empty_fixture,'passed',True,60),('same_source_without_fixture',code,'failed',False,60),('skipped_tests','import unittest\nclass Skip(unittest.TestCase):\n def test_skip(self):self.skipTest("synthetic unexecuted prerequisite")\n','incomplete',True,60),('no_tests','VALUE=1\n','failed',True,60),('timeout','import time,unittest\nclass Slow(unittest.TestCase):\n def test_slow(self):time.sleep(30)\n','failed',True,3)]:
 data=archive(source);execution=str(uuid.uuid4());spec=ValidationSpec('sql-'+name.replace('_','-'),args.image,driver if sql_fixture else('/usr/local/bin/python3','-m','unittest','discover','-v'),platform=args.platform,timeout_seconds=budget,isolation_profile='postgresql-local-v1'if sql_fixture else'standard-v1')
 result=worker.run(data,hashlib.sha256(data).hexdigest(),spec,execution_id=execution);(out/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n');assert result['status']==expected,(name,result)
 cleanup=worker.recover(execution);assert cleanup['cleanupConfirmed']and not cleanup['workReplayed'];rows.append({'case':name,'status':result['status'],'tests':result['testsReported'],'skipped':result['skipped'],'reason':result['reason'],'cleanupConfirmed':True})
 if name=='skipped_tests':assert result['skipped']==1
 if name=='no_tests':assert result['reason']=='no_tests_reported'
 if name=='timeout':assert result['reason']=='timeout'
print(json.dumps({'passed':True,'cases':rows}));(out/'receipt.json').write_text(json.dumps({'passed':True,'imageId':args.image,'cases':rows,'cloudOperations':False,'boundary':'Actual isolated PostgreSQL/SDK checks across synthetic editorial/inventory schemas, role/auth/readonly/network denials, fresh state, skips/zero tests and timeout cleanup. No managed cloud, security acceptance or client system claim.'},indent=2)+'\n')
