"""Private evaluator RPC via docker exec only; no exposed control HTTP endpoint."""
import http.client,json,pathlib,sys
ROOT=pathlib.Path('/runtime');data=json.loads(sys.stdin.buffer.read(1000000));fixture=json.loads((ROOT/'fixture.json').read_bytes())
if data['action']=='http':
 host=data.get('host','api');assert host in {'api','worker'};connection=http.client.HTTPConnection(host,8080,timeout=30)
 try:
  body=data.get('raw');body=body.encode()if body is not None else None
  if 'body'in data:body=json.dumps(data['body'],ensure_ascii=True,allow_nan=False).encode()
  connection.request(data['method'],data['path'],body=body,headers=data.get('headers',{}));response=connection.getresponse();raw=response.read(1000000)
  result={'status':response.status,'headers':dict(response.getheaders()),'body':(json.loads(raw)if 'application/json'in(response.getheader('Content-Type')or'')else raw.decode('utf-8'))if raw else None}
 finally:connection.close()
elif data['action']=='roles':
 import psycopg
 from psycopg import sql
 with psycopg.connect(fixture['dsns']['admin'])as connection:
  for role in ['api','worker']:
   connection.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT').format(sql.Identifier(fixture['roles'][role]),sql.Literal(fixture['passwords'][role])))
 result={'created':True}
elif data['action']=='sql':
 import psycopg
 from psycopg.rows import dict_row
 with psycopg.connect(fixture['dsns'][data.get('role','admin')],row_factory=dict_row)as connection:
  try:
   cursor=connection.execute(data['query'],data.get('params',[]));result={'rows':cursor.fetchall()if cursor.description else[],'rowcount':cursor.rowcount}
   if data.get('rollback'):connection.rollback()
  except psycopg.Error as error:result={'sqlstate':error.sqlstate,'errorType':type(error).__name__};connection.rollback()
elif data['action']in {'extraction-fence','dispatch-fence'}:
 import psycopg
 sys.path.insert(0,'/app')
 from workflow_worker import producer_store
 from durable_workflow import LostLease
 from sample_configuration import destination_contract,payload_contract
 config=json.loads((ROOT/'application-config.json').read_bytes());store=producer_store(fixture['dsns']['worker'],destination_contract=destination_contract(config),payload_contract=payload_contract(),namespace='sample',operation_kind='draft',lease_seconds=30)
 operation=data['operationId'];dispatch=data['action']=='dispatch-fence'
 old=store.claim_dispatch(operation)if dispatch else store.claim_extract(operation);assert old is not None
 with psycopg.connect(fixture['dsns']['admin'])as connection:connection.execute("UPDATE workflow.operations SET lease_until=clock_timestamp()-interval '1 second' WHERE id=%s",(operation,))
 if dispatch:
  assert store.claim_dispatch(operation)is None
  repaired=store.recover_expired();assert operation in repaired
 else:
  new=store.claim_extract(operation);assert new is not None and str(new['lease_token'])!=str(old['lease_token'])
 try:
  if dispatch:store.record_sent(operation,str(old['lease_token']),{'operationId':operation,'payloadSha256':old['approved_hash'],'externalId':'synthetic/stale'})
  else:store.record_result(operation,str(old['lease_token']),data['expectedResult'])
 except LostLease:pass
 else:raise AssertionError('Expired worker settled a current operation')
 with store.connect()as connection:
  row=connection.execute('SELECT state,lease_token,result FROM workflow.operations WHERE id=%s',(operation,)).fetchone()
  assert row['state']==('unknown'if dispatch else'processing')
 if not dispatch:store.record_result(operation,str(new['lease_token']),data['expectedResult'])
 result={'oldLeaseRejected':True,'role':'worker','realSql':True,'dispatchNoReplay':dispatch}
elif data['action']=='events':
 path=ROOT/'events.jsonl';result={'events':[json.loads(line)for line in path.read_text().splitlines()]if path.exists()else[]}
elif data['action']=='mode':
 assert data['value']in {'success','ambiguous','hold'};(ROOT/'mode').write_text(data['value']);result={'saved':True}
else:raise ValueError('Unsupported private fixture action')
print(json.dumps(result,default=str,ensure_ascii=True,allow_nan=False))
