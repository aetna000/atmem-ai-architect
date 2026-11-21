"""Shared HTTP load/failure checks; model and identity are explicit local fixtures."""
from concurrent.futures import ThreadPoolExecutor
import threading
import unittest
from fastapi.testclient import TestClient
from structured_http import create_app

class ConcurrencyTests(unittest.TestCase):
    def test_five_simultaneous_requests_complete_and_excess_is_bounded(self):
        lock=threading.Lock();ready=threading.Event();release=threading.Event();entered=[]
        def infer(text):
            with lock:
                entered.append(text)
                if len(entered)==5:ready.set()
            if not release.wait(5):raise RuntimeError('Fixture timed out')
            return {'synthetic':text}
        app=create_app({'max_input':64,'PUBLIC_ORIGIN':'https://fixture.test'},lambda token:'fixture-user',infer,lambda:{})
        def post(text):
            with TestClient(app) as client:return client.post('/api/ask',json={'text':text})
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures=[executor.submit(post,'request-'+str(i)) for i in range(5)]
            try:
                self.assertTrue(ready.wait(4),'Five simultaneous inference calls should be admitted')
                excess=post('excess');self.assertEqual(excess.status_code,429);self.assertEqual(excess.json(),{'error':'busy'})
                self.assertEqual(len(entered),5)
            finally:release.set()
            for i,future in enumerate(futures):
                reply=future.result(timeout=5);self.assertEqual(reply.status_code,200);self.assertEqual(reply.json()['result'],{'synthetic':'request-'+str(i)})
        self.assertEqual(post('after-release').status_code,200)
    def test_failed_model_request_releases_capacity_without_retry(self):
        calls=[]
        def infer(text):
            calls.append(text)
            if text=='fail':raise ValueError('synthetic failure')
            return {'synthetic':text}
        client=TestClient(create_app({'max_input':64,'PUBLIC_ORIGIN':'https://fixture.test'},lambda token:'fixture-user',infer,lambda:{}))
        for _ in range(6):self.assertEqual(client.post('/api/ask',json={'text':'fail'}).status_code,503)
        self.assertEqual(client.post('/api/ask',json={'text':'recovered'}).status_code,200)
        self.assertEqual(calls,['fail']*6+['recovered'])
