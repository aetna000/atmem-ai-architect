import asyncio
import sys
import tempfile
import unittest
from server.codex_app_server import CodexAppServer, ProtocolError

FAKE = r'''
import json,sys,os
for line in sys.stdin:
 m=json.loads(line)
 if 'method' not in m:
  print(json.dumps({'method':'handler-result','params':m}),flush=True);continue
 if m['method']=='initialized':continue
 if m['method']=='exit':sys.exit(0)
 if m['method']=='wait':continue
 if m['method']=='events':
  for i in range(3):print(json.dumps({'method':'item/progress','params':{'index':i}}),flush=True)
 if m['method']=='tool':print(json.dumps({'id':'server-tool','method':'item/tool/call','params':{'threadId':'owned-thread','turnId':'owned-turn','callId':'call-one','tool':'registered','arguments':{}}}),flush=True)
 if m['method']=='approval':print(json.dumps({'id':'server-approval','method':'item/commandExecution/requestApproval','params':{}}),flush=True)
 if m['method']=='reject':
  print(json.dumps({'id':m['id'],'error':{'code':-32602,'message':'private diagnostic'}}),flush=True);continue
 if m['method']=='missing-thread':
  print(json.dumps({'id':m['id'],'error':{'code':-32600,'message':'no rollout found for thread id private-id'}}),flush=True);continue
 if m['method']=='environment':result={k:os.environ.get(k) for k in ['AWS_PROFILE','AZURE_CLIENT_SECRET','TF_VAR_secret','DOCKER_HOST']}
 else:result={'method':m['method'],'params':m['params']}
 print(json.dumps({'id':m['id'],'result':result}),flush=True)
'''

class CodexTransportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.client = CodexAppServer(self.temp.name, command=[sys.executable, '-u', '-c', FAKE])
        await self.client.start()

    async def asyncTearDown(self):
        await self.client.close()
        self.temp.cleanup()

    async def test_handshake_and_concurrent_requests_do_not_mix_results(self):
        results = await asyncio.gather(*(self.client.request('probe', {'value':i}) for i in range(8)))
        self.assertEqual([r['params']['value'] for r in results], list(range(8)))
        with self.assertRaises(ProtocolError): await self.client.start()

    async def test_progress_is_separate_from_result_and_order_is_preserved(self):
        await self.client.request('events')
        values=[await asyncio.wait_for(self.client.events.get(),1) for _ in range(3)]
        self.assertEqual([m['params']['index'] for m in values],[0,1,2])

    async def test_notification_timeout_does_not_consume_the_next_event(self):
        with self.assertRaises(asyncio.TimeoutError):
            await self.client.notification(timeout=.01)
        await self.client.request('events')
        event=await self.client.notification(timeout=1)
        self.assertEqual(event['params']['index'],0)

    async def test_notification_waiter_wakes_when_transport_closes(self):
        waiter=asyncio.create_task(self.client.notification(timeout=10))
        await asyncio.sleep(0)
        await self.client.close()
        with self.assertRaises(ProtocolError):
            await asyncio.wait_for(waiter,1)

    async def test_cancelled_notification_wait_does_not_steal_later_progress(self):
        waiter=asyncio.create_task(self.client.notification(timeout=10))
        await asyncio.sleep(0)
        waiter.cancel()
        with self.assertRaises(asyncio.CancelledError):await waiter
        await self.client.request('events')
        event=await self.client.notification(timeout=1)
        self.assertEqual(event['params']['index'],0)

    async def test_server_approval_is_not_automatically_granted(self):
        await self.client.request('approval')
        event=await asyncio.wait_for(self.client.events.get(),1)
        self.assertEqual(event['params']['id'],'server-approval')
        self.assertEqual(event['params']['error']['code'],-32601)
        self.assertNotIn('result',event['params'])

    async def test_registered_tool_does_not_block_protocol_and_approvals_remain_denied(self):
        entered,release=asyncio.Event(),asyncio.Event()
        async def handler(params):
            self.assertEqual(params['callId'],'call-one');entered.set();await release.wait()
            return {'success':True,'contentItems':[{'type':'inputText','text':'Scoped evidence'}]}
        self.client.dynamic_tool_handler=handler
        await self.client.request('tool');await asyncio.wait_for(entered.wait(),1)
        self.assertEqual((await self.client.request('probe'))['method'],'probe')
        await self.client.request('approval');denied=await self.client.notification(timeout=1)
        self.assertEqual(denied['params']['error']['code'],-32601)
        release.set();result=await self.client.notification(timeout=1)
        self.assertEqual(result['params']['id'],'server-tool');self.assertTrue(result['params']['result']['success'])

    async def test_tool_errors_and_oversize_responses_never_expose_raw_diagnostics(self):
        for mode in ['error','oversize']:
            async def handler(params):
                if mode=='error':raise RuntimeError('PRIVATE-WORKER-DIAGNOSTIC')
                return {'success':True,'contentItems':[{'type':'inputText','text':'x'*65000}]}
            self.client.dynamic_tool_handler=handler;await self.client.request('tool')
            result=await self.client.notification(timeout=1)
            self.assertFalse(result['params']['result']['success']);self.assertNotIn('PRIVATE-WORKER',str(result))

    async def test_provider_error_is_not_exposed_as_success_or_raw_diagnostics(self):
        with self.assertRaises(ProtocolError) as caught:await self.client.request('reject')
        self.assertIn('-32602',str(caught.exception));self.assertNotIn('private diagnostic',str(caught.exception))

    async def test_missing_history_has_narrow_category_without_raw_diagnostics(self):
        with self.assertRaises(ProtocolError) as caught:await self.client.request('missing-thread')
        self.assertEqual(caught.exception.category,'missing_thread')
        self.assertEqual(caught.exception.code,-32600)
        self.assertNotIn('private-id',str(caught.exception))

    async def test_timeout_does_not_claim_turn_cancelled_and_next_request_works(self):
        with self.assertRaises(asyncio.TimeoutError):await self.client.request('wait',timeout=.02)
        self.assertEqual((await self.client.request('probe'))['method'],'probe')
        self.assertFalse(self.client.pending)

    async def test_exit_is_not_a_successful_pending_request(self):
        with self.assertRaises(ProtocolError):await self.client.request('exit')

    async def test_event_overflow_fails_instead_of_losing_progress_silently(self):
        self.client.events=asyncio.Queue(maxsize=1)
        try:await self.client.request('events')
        except ProtocolError:pass
        await asyncio.sleep(.02)
        self.assertIn('capacity',self.client.failure)
        with self.assertRaises(ProtocolError):await self.client.request('probe')

    async def test_deployment_environment_not_forwarded(self):
        async with self._environment_client() as client:
            result=await client.request('environment')
        self.assertEqual(result,dict.fromkeys(['AWS_PROFILE','AZURE_CLIENT_SECRET','TF_VAR_secret','DOCKER_HOST']))

    def _environment_client(self):
        from contextlib import asynccontextmanager
        from unittest.mock import patch
        @asynccontextmanager
        async def scoped():
            client=CodexAppServer(self.temp.name,command=[sys.executable,'-u','-c',FAKE])
            with patch.dict('os.environ',{'AWS_PROFILE':'private','AZURE_CLIENT_SECRET':'private','TF_VAR_secret':'private','DOCKER_HOST':'private'}):await client.start()
            try:yield client
            finally:await client.close()
        return scoped()
