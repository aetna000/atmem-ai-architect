"""Idle cache eviction must preserve accepted work and never close an active turn."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from server.engineering_routes import LocalEngineeringService,WorkerCapacityError
from server.engineering_sessions import ModelSelection,ProjectScope

class Client:
    def __init__(self):self.closed=False
    async def close(self):self.closed=True

class CapacityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.home=patch('server.engineering_routes.home',return_value=Path(self.folder.name));self.home.start();self.addCleanup(self.home.stop)
        self.settings=patch('server.engineering_routes.setting',return_value=None);self.settings.start();self.addCleanup(self.settings.stop)
        self.worker=LocalEngineeringService();self.rows=[]
        for i in range(4):
            scope=ProjectScope('local-owner','project-'+str(i));handle='native-'+str(i);client=Client()
            state=self.worker.store.create(scope,'workspace-'+str(i),self.worker.backend.name,handle,ModelSelection('model','low'))
            self.worker.backend.clients[scope,handle]=(client,Path(self.folder.name),ModelSelection('model','low'))
            self.rows.append((scope,handle,client,state))
    async def asyncTearDown(self):await self.worker.close()
    def state(self,i,value):
        with self.worker.store.db:self.worker.store.db.execute('UPDATE engineering_sessions SET state=? WHERE id=?',(value,self.rows[i][3]['id']))
    async def test_idle_transport_closes_but_durable_identity_and_other_sessions_survive(self):
        self.state(0,'running');self.state(1,'starting')
        await self.worker.ensure_worker_capacity()
        self.assertFalse(self.rows[0][2].closed);self.assertFalse(self.rows[1][2].closed);self.assertTrue(self.rows[2][2].closed)
        scope,handle,_,saved=self.rows[2]
        self.assertEqual(self.worker.store.get(scope,saved['id'])['handle'],handle)
        self.assertEqual(self.worker.backend.session_count,3)
        self.assertFalse(self.rows[3][2].closed)
    async def test_capacity_refuses_when_every_session_is_active_or_uncertain(self):
        for i in range(4):self.state(i,'running' if i%2 else 'starting')
        with self.assertRaises(WorkerCapacityError):await self.worker.ensure_worker_capacity()
        self.assertFalse(any(row[2].closed for row in self.rows))
    async def test_pending_finalization_is_not_evicted(self):
        for i in range(1,4):self.state(i,'running')
        with self.worker.store.db:self.worker.store.db.execute('INSERT INTO engineering_finalizations VALUES (?,?,?,?,?)',('finalizing',self.rows[0][3]['id'],'run','checking','{}'))
        with self.assertRaises(WorkerCapacityError):await self.worker.ensure_worker_capacity()
        self.assertFalse(self.rows[0][2].closed)
    async def test_idle_collector_is_protected_until_it_settles(self):
        import asyncio
        gate=asyncio.Event();task=asyncio.create_task(gate.wait());self.worker.jobs.tasks[self.rows[0][0],self.rows[0][3]['id']]=task
        for i in range(1,4):self.state(i,'running')
        try:
            with self.assertRaises(WorkerCapacityError):await self.worker.ensure_worker_capacity()
            self.assertFalse(self.rows[0][2].closed)
        finally:gate.set();await task
