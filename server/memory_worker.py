"""Isolated pinned AtMem SDK process. JSON over stdio; no model/cloud tools."""
import json
import sys
import sqlite3
import base64
import re
from importlib.metadata import version
from pathlib import Path
EXPECTED_ATMEM_VERSION = re.search(r"^atmem==(\d+\.\d+\.\d+)$", (Path(__file__).parent / "memory-requirements.txt").read_text(), re.M).group(1)
from atmem import Memory


def public_record(record, owner=None, memory=None):
    episode=memory.store.get_episode(record['subject_id'],record['episode_id'])if memory and record.get('episode_id')else None
    raw=(episode or {}).get('raw') or record.get('raw') or {}
    return {**{key:record.get(key)for key in ('id','content','status','fact_key','created_at','updated_at','supersedes_id','source_type')},
            'governance':{'userId':raw.get('user_id'), 'actor':raw.get('actor'), 'actorType':raw.get('actor_type'),
                          'source':raw.get('source_url') or raw.get('interpreter'), 'ownerUserId':owner}}


def page_records(memory,subject,op):
    # Pinned SDK adapter: use its policy-aware connection, never reopen the database.
    from atmem.store.sqlite import _record_from_row
    db=memory.store._conn
    limit=max(1,min(int(op.get('limit',50)),100));query=str(op.get('query','')).strip()[:200]
    status=op.get('status','active')
    statuses=('active','superseded','quarantined') if status=='all' else (status,)
    if any(value not in {'active','superseded','quarantined'}for value in statuses):raise ValueError('Invalid memory status')
    before=None
    if op.get('cursor'):
        before=json.loads(base64.urlsafe_b64decode(op['cursor']).decode())
        if not isinstance(before,list)or len(before)!=2 or any(not isinstance(v,str)or len(v)>100 for v in before):raise ValueError('Invalid page cursor')
    candidates=[];total=0
    for selected in statuses:
        clauses=['subject_id=?','status=?'];args=[subject,selected]
        if query:
            if query.startswith('rec_'):
                clauses.append('id=?');args.append(query)
            else:
                terms=re.findall(r'[^\W_]+',query,flags=re.UNICODE)[:12]
                if not terms:raise ValueError('Enter a search word or record ID')
                if not memory.store._fts_enabled:raise ValueError('Indexed search is unavailable for this store')
                expression=' AND '.join('"'+word.replace('"','')+'"'for word in terms)
                clauses.append('id IN (SELECT record_id FROM records_fts WHERE records_fts MATCH ? AND subject_id=?)')
                args.extend([expression,subject])
        where=' AND '.join(clauses)
        total+=db.execute('SELECT COUNT(*) FROM records WHERE '+where,args).fetchone()[0]
        if before:where+=' AND (created_at,id)<(?,?)';args.extend(before)
        rows=db.execute('SELECT * FROM records WHERE '+where+' ORDER BY created_at DESC,id DESC LIMIT ?',(*args,limit+1)).fetchall()
        candidates.extend(_record_from_row(row)for row in rows)
    candidates.sort(key=lambda row:(row['created_at'],row['id']),reverse=True)
    more=len(candidates)>limit;rows=candidates[:limit]
    cursor=base64.urlsafe_b64encode(json.dumps([rows[-1]['created_at'],rows[-1]['id']]).encode()).decode()if more and rows else None
    return {'records':[public_record(row,op.get('owner'),memory)for row in rows],'total':total,'hasMore':more,'nextCursor':cursor,'limit':limit}


def keyed_records(memory,subject,record_id,limit=10001):
    record=memory.store.get_record(subject,record_id)
    if not record or record['status']=='tombstoned':raise ValueError('Memory is unavailable in this scope')
    if not record.get('fact_key'):return record,[record]
    from atmem.store.sqlite import _record_from_row
    rows=memory.store._conn.execute("SELECT * FROM records WHERE subject_id=? AND fact_key IS ? AND status IN ('active','superseded','quarantined') ORDER BY created_at DESC,id DESC LIMIT ?",(subject,record.get('fact_key'),limit)).fetchall()
    return record,[_record_from_row(row)for row in rows]


def run(payload):
    if version('atmem') != EXPECTED_ATMEM_VERSION:
        raise RuntimeError(f'AtMem AI Architect requires the tested AtMem {EXPECTED_ATMEM_VERSION} runtime')
    memory = Memory(payload['database'], auto_vectors=False)
    receipts = sqlite3.connect(payload['database'] + '.receipts.sqlite')
    receipts.execute('CREATE TABLE IF NOT EXISTS receipts (id TEXT PRIMARY KEY, result TEXT)')
    results = []
    try:
        for op in payload['operations']:
            subject = op['subject']
            action = op['action']
            if action == 'remember':
                previous = receipts.execute('SELECT result FROM receipts WHERE id=?', (op['eventId'],)).fetchone()
                if previous:
                    results.append(json.loads(previous[0]))
                    continue
                value = memory.remember(subject, message=op['text'], source_type='user_message',
                    interpreted_fact=op['text'], interpreted_fact_key=op['key'], actor=op.get('actor','atforma'),
                    raw={'interpreter': 'atforma-project-event-v1', 'event_id': op['eventId'], 'source_url': op.get('source', ''), 'user_id':op.get('owner'), 'actor':op.get('actor'), 'actor_type':op.get('actorType')})
                receipt = {'refused': value.get('refused', []), 'ids': [r['id'] for r in value.get('records', [])] + value.get('duplicate_ids', [])}
                receipts.execute('INSERT INTO receipts VALUES (?,?)', (op['eventId'], json.dumps(receipt)))
                receipts.commit()
                results.append(receipt)
            elif action == 'recall':
                results.append(memory.recall(subject, op['query'], limit=op.get('limit', 6)))
            elif action == 'page':
                results.append(page_records(memory,subject,op))
            elif action == 'record':
                record=memory.store.get_record(subject,op['recordId'])
                if not record or record['status']=='tombstoned':raise ValueError('Record unavailable in this scope')
                audit=memory.store._conn.execute('SELECT actor,event_type,created_at FROM audit_log WHERE subject_id=? AND record_id=? ORDER BY created_at DESC,sequence DESC LIMIT 50',(subject,op['recordId'])).fetchall()
                results.append({'record':public_record(record,op.get('owner'),memory),'audit':[dict(row)for row in audit]})
            elif action == 'forget-preview':
                record,rows=keyed_records(memory,subject,op['recordId'],101)
                total=memory.store._conn.execute("SELECT COUNT(*) FROM records WHERE subject_id=? AND fact_key IS ? AND status!='tombstoned'",(subject,record.get('fact_key'))).fetchone()[0]if record.get('fact_key')else 1
                results.append({'records':[public_record(row,op.get('owner'),memory)for row in rows[:100]],'total':total})
            elif action == 'list':
                results.append(memory.list(subject, include_inactive=True))
            elif action == 'forget':
                # Forget the entire keyed preference history so old values cannot resurface.
                record,records=keyed_records(memory,subject,op['recordId'])
                if len(records)>10000:raise ValueError('History exceeds the synchronous removal limit; no records were removed')
                deletion_receipts = []
                for r in records:
                    deletion_receipts.append(memory.forget_record(subject,r['id'],actor=op.get('actor','user'))['receipt'])
                results.append({'deleted': True, 'receipts': deletion_receipts, 'key': record.get('fact_key')})
            elif action == 'audit':
                report = memory.audit(subject)
                results.append({'valid': report['audit_chain_valid'], 'events': report['audit_log'][-40:]})
            elif action == 'log':
                results.append(memory.log_action(subject, op['eventType'], op['payload'], actor='atmem-architect:'+op.get('owner','unknown')))
            else:
                raise ValueError('Unknown memory operation')
        return {'version': version('atmem'), 'results': results}
    finally:
        memory.close()
        receipts.close()


if __name__ == '__main__':
    try:
        print(json.dumps(run(json.load(sys.stdin))))
    except Exception as exc:
        # No text/credentials from an exception cross this process boundary.
        print(json.dumps({'error': type(exc).__name__}))
        sys.exit(1)
