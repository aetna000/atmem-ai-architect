import io, wave, unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from server.app import app,TOKEN

def audio(rate=16000,channels=1,frames=3200):
    out=io.BytesIO()
    with wave.open(out,'wb') as w:
        w.setnchannels(channels);w.setsampwidth(2);w.setframerate(rate);w.writeframes(b'\x00\x01'*frames*channels)
    return out.getvalue()

class VoiceBoundaryTests(unittest.TestCase):
    def setUp(self):self.client=TestClient(app);self.headers={'Authorization':'Bearer '+TOKEN,'Content-Type':'audio/wav'}
    def test_requires_local_session_token(self):
        self.assertEqual(self.client.post('/api/voice/transcribe',content=audio()).status_code,401)
    def test_rejects_foreign_origin(self):
        self.assertEqual(self.client.post('/api/voice/transcribe',content=audio(),headers={**self.headers,'Origin':'https://evil.example'}).status_code,403)
    def test_rejects_wrong_type_and_invalid_wav(self):
        self.assertEqual(self.client.post('/api/voice/transcribe',content=audio(),headers={**self.headers,'Content-Type':'application/json'}).status_code,415)
        self.assertEqual(self.client.post('/api/voice/transcribe',content=b'not audio',headers=self.headers).status_code,422)
    def test_rejects_stereo_wrong_rate_and_oversize(self):
        for data in [audio(channels=2),audio(rate=44100),audio(frames=960001)]:
            self.assertIn(self.client.post('/api/voice/transcribe',content=data,headers=self.headers).status_code,[413,422])
    def test_real_route_returns_engine_text_without_saving_audio(self):
        with patch('server.voice_routes.engine.transcribe',new=AsyncMock(return_value='Use Azure.')) as call:
            response=self.client.post('/api/voice/transcribe',content=audio(),headers=self.headers)
            self.assertEqual(response.status_code,200);self.assertEqual(response.json()['text'],'Use Azure.')
            self.assertFalse(response.json()['audioStored']);self.assertEqual(len(call.call_args.args[0]),6400)
    def test_failure_is_sanitised(self):
        with patch('server.voice_routes.engine.transcribe',new=AsyncMock(side_effect=RuntimeError('private detail'))):
            response=self.client.post('/api/voice/transcribe',content=audio(),headers=self.headers)
            self.assertEqual(response.status_code,503);self.assertNotIn('private detail',response.text)
    def test_status_reports_missing_setup_and_prepare_requires_auth(self):
        with patch('server.voice_routes.configuration',return_value=None):
            self.assertFalse(self.client.get('/api/voice/status').json()['available'])
        self.assertEqual(self.client.post('/api/voice/prepare').status_code,401)


class VoiceWarmupTests(unittest.IsolatedAsyncioTestCase):
    async def test_first_partial_waits_for_warmup_instead_of_stopping_capture(self):
        import asyncio
        from types import SimpleNamespace
        from unittest.mock import Mock
        from server.voice_routes import LocalSpeech
        engine=LocalSpeech();release=asyncio.Event();entered=asyncio.Event();calls=0
        async def ready():
            nonlocal calls
            calls+=1
            if calls==1:entered.set();await release.wait()
        engine.ready=ready
        engine.process=SimpleNamespace(stdin=SimpleNamespace(write=Mock(),drain=AsyncMock()),stdout=SimpleNamespace(readline=AsyncMock(return_value=b'{"text":"hello"}\n')))
        preparation=asyncio.create_task(engine.prepare());await entered.wait()
        partial=asyncio.create_task(engine.transcribe(b'\x01\x00'*1600));await asyncio.sleep(.01)
        self.assertFalse(partial.done());release.set();await preparation
        self.assertEqual(await partial,'hello')
