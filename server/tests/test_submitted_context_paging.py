import hashlib
import json
import sqlite3
import unittest
from unittest.mock import Mock

from server.engineering_contexts import context_input
from server.engineering_tools import EngineeringTools
from server.engineering_sessions import SessionError


class SubmittedContextPagingTests(unittest.IsolatedAsyncioTestCase):
    async def test_large_utf8_context_is_referenced_and_losslessly_paged_with_digest_and_session_binding(self):
        content=json.dumps({'format':'atmem.ai-architect.project','meta':{'id':'clinic-project'},
                            'extensions':{'notes':'患者の診療 '*150000}},ensure_ascii=False)
        self.assertGreater(len(content.encode()),2_000_000)
        sha=hashlib.sha256(content.encode()).hexdigest()
        context={'id':'context-1','revision':2,'sha256':sha,'projectId':'clinic-project','content':content}
        rendered=context_input(context)
        self.assertLess(len(rendered['text']),2000)
        self.assertIn('submitted-context',rendered['text'])
        db=sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        db.execute('CREATE TABLE engineering_contexts (id,content,sha256)')
        db.execute('CREATE TABLE engineering_context_submissions (session,request,context)')
        db.execute('INSERT INTO engineering_contexts VALUES (?,?,?)',('context-1',content.encode(),sha))
        db.execute('INSERT INTO engineering_context_submissions VALUES (?,?,?)',('session-1','run-1','context-1'))
        tools=EngineeringTools.__new__(EngineeringTools)
        tools.db=db
        tools.store=Mock()
        tools.store.get.return_value={'run':'run-1'}
        offset=0
        parts=[]
        while True:
            page=await tools._execute(None,None,'session-1','atmem_reference_read',
                                      {'id':'submitted-context','offset':offset,'sha256':sha})
            parts.append(page['text'])
            self.assertLess(len(json.dumps(page,ensure_ascii=False).encode()),48000)
            self.assertEqual(page['sha256'],sha)
            if page['nextOffset'] is None:
                break
            offset=page['nextOffset']
        self.assertEqual(''.join(parts),content)
        for session,arguments in [('session-2',{'id':'submitted-context'}),
                                  ('session-1',{'id':'submitted-context','offset':24000}),
                                  ('session-1',{'id':'submitted-context','sha256':'wrong'})]:
            with self.assertRaises((SessionError,ValueError)):
                await tools._execute(None,None,session,'atmem_reference_read',arguments)
