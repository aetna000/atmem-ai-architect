"""Isolated SDK-backed dashboard read benchmark; synthetic rows, not semantic SDK write qualification."""
import importlib.util
import json
from pathlib import Path
import statistics
import tempfile
import time
import tracemalloc
from atmem import Memory

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('memory_worker',root/'server/memory_worker.py')
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
output=root/'.local/external-artifacts/memory-dashboard';output.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='atmem-million-')as directory:
 database=str(Path(directory)/'memories.db');memory=Memory(database,auto_vectors=False);db=memory.store._conn
 started=time.perf_counter();created='2026-11-13T00:00:00+00:00';total=1_000_000
 sql="INSERT INTO records(id,subject_id,content,source_type,trust_tier,created_at,scope,status,fact_key,raw,content_normalized)VALUES(?,?,?,'user_message','user',?,'subject','active',?,'{}',?)"
 for begin in range(0,total,5000):
  rows=[('rec_'+format(i,'032x'),'benchmark-owner',('needle 'if i in {7,77,777}else '')+'Synthetic memory '+str(i),created,'fixture.'+str(i))for i in range(begin,min(begin+5000,total))]
  db.execute('BEGIN');db.executemany(sql,[(*row,row[2].lower())for row in rows])
  db.executemany('INSERT INTO records_fts(record_id,subject_id,content)VALUES(?,?,?)',[(row[0],row[1],row[2])for row in rows])
  # Required SDK map: preserves the FTS migration contract on reopening.
  db.executemany('INSERT INTO records_fts_map(record_id,subject_id,fts_rowid)VALUES(?,?,?)',[(row[0],row[1],begin+index+1)for index,row in enumerate(rows)])
  db.commit()
  if begin%100000==0:print(json.dumps({'inserted':begin+len(rows)}),flush=True)
 db.execute(sql,('rec_'+'f'*32,'other-owner','Private other owner',created,'other','private other owner'))
 db.commit();build=time.perf_counter()-started
 tracemalloc.start();latencies=[]
 for index in range(5):
  started=time.perf_counter();page=worker.page_records(memory,'benchmark-owner',{'limit':50,'status':'active'});latencies.append((time.perf_counter()-started)*1000)
 assert len(page['records'])==50 and page['total']==total and page['hasMore']
 second=worker.page_records(memory,'benchmark-owner',{'limit':50,'cursor':page['nextCursor']})
 assert not set(row['id']for row in page['records'])&set(row['id']for row in second['records'])
 import base64
 deep=base64.urlsafe_b64encode(json.dumps([created,'rec_'+format(3,'032x')]).encode()).decode()
 started=time.perf_counter();last=worker.page_records(memory,'benchmark-owner',{'limit':50,'cursor':deep});deep_ms=(time.perf_counter()-started)*1000
 assert len(last['records'])==3 and not last['hasMore']
 started=time.perf_counter();search=worker.page_records(memory,'benchmark-owner',{'limit':50,'query':'needle'});search_ms=(time.perf_counter()-started)*1000
 assert search['total']==3 and len(search['records'])==3
 assert all(row['governance']['userId']is None for row in page['records'])
 plan=[tuple(row)for row in db.execute('EXPLAIN QUERY PLAN SELECT * FROM records WHERE subject_id=? AND status=? AND (created_at,id)<(?,?) ORDER BY created_at DESC,id DESC LIMIT 51',('benchmark-owner','active',created,'rec_'+format(3,'032x')))]
 _,peak=tracemalloc.get_traced_memory();tracemalloc.stop();memory.close()
 started=time.perf_counter();reopened=worker.run({'database':database,'operations':[{'action':'page','subject':'benchmark-owner','limit':50,'status':'active'}]});reopen_ms=(time.perf_counter()-started)*1000
 assert reopened['results'][0]['total']==total
 result={'records':total,'fixtureBuildSeconds':round(build,2),'page50MedianMs':round(statistics.median(latencies),2),'page50SamplesMs':[round(value,2)for value in latencies],'deepPageMs':round(deep_ms,2),'searchMs':round(search_ms,2),'workerReopenAndPageMs':round(reopen_ms,2),'pythonReadPeakBytes':peak,'scopeIsolation':True,'noPageOverlap':True,'legacyCreatorUnknown':True,'queryPlan':plan,'boundary':'Synthetic dashboard read benchmark through pinned AtMem SDK connection. Not semantic million-write, recall, concurrent-user or hosted qualification.'}
 (output/'million-records.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
