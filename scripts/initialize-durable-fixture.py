"""Fresh local database from exact schema; never migrate/adopt a client database.

Run with .local/durable-runtime/bin/python after starting the owned local fixture.
Old synthetic databases/configuration remain available as failure evidence.
"""
import json
import os
from pathlib import Path
import re
import sys
import uuid
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/runtime'))
from workflow_database import initialize_database

if __name__=='__main__':
    path=ROOT/'.local/durable-postgres/fixture.json';config=json.loads(path.read_text())
    if config['name']!='atmem-durable-qualification'or not re.fullmatch(r'architect_qualification(?:_[a-z0-9]{1,32})?',config['database']):raise ValueError('Use the task-owned local database fixture')
    dsn=make_conninfo(host='127.0.0.1',port=config['port'],dbname=config['database'],user=config['user'],password=config['password'],sslmode='disable')
    with psycopg.connect(dsn,autocommit=True)as conn:
        if conn.execute('SELECT marker FROM workflow.qualification_guard').fetchone()[0]!=config['marker']:raise ValueError('Local fixture ownership marker mismatch')
        database='architect_qualification_'+uuid.uuid4().hex[:12]
        conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
    new={**config,'database':database,'marker':uuid.uuid4().hex+uuid.uuid4().hex}
    target=make_conninfo(host='127.0.0.1',port=new['port'],dbname=database,user=new['user'],password=new['password'],sslmode='disable')
    with psycopg.connect(target)as conn:
        initialize_database(conn);conn.execute('CREATE TABLE workflow.qualification_guard(marker text PRIMARY KEY)');conn.execute('INSERT INTO workflow.qualification_guard(marker) VALUES(%s)',(new['marker'],))
    old=path.with_name('fixture-before-'+database+'.json');old.write_bytes(path.read_bytes());old.chmod(0o600);path.write_text(json.dumps(new,indent=2)+'\n');path.chmod(0o600)
    print(json.dumps({'freshLocalSchema':'initialized','database':database,'queueVersion':'3.10.0','cloudOperations':False,'destructiveChanges':False}))
