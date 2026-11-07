"""Local-only, session-authenticated dictation. The app boundary owns HTTP auth."""
import asyncio, base64, io, json, os, shutil, wave
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from .settings import setting

router=APIRouter()
ROOT=Path(__file__).resolve().parent

def configuration():
    binary=shutil.which('whisper')
    model=Path(setting('WHISPER_MODEL') or Path.home()/'.cache'/'whisper'/'tiny.en.pt')
    if not binary or not model.is_file():return None
    try: python=Path(binary).read_text().splitlines()[0].removeprefix('#!').strip()
    except (OSError,IndexError,UnicodeError):return None
    if not python.startswith('/') or not Path(python).is_file():return None
    return python,model

class LocalSpeech:
    def __init__(self):self.process=None;self.lock=asyncio.Lock()
    async def close(self):
        p=self.process;self.process=None
        if p and p.returncode is None:
            p.terminate()
            try:await asyncio.wait_for(p.wait(),3)
            except asyncio.TimeoutError:p.kill();await p.wait()
    async def ready(self):
        config=configuration()
        if not config:raise HTTPException(503,'Local voice is not prepared. Run python3 scripts/setup-voice.py, then try again.')
        if self.process and self.process.returncode is None:return
        python,model=config
        self.process=await asyncio.create_subprocess_exec(python,str(ROOT/'voice_worker.py'),str(model),
            stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL,
            limit=100000)
        try:
            hello=json.loads(await asyncio.wait_for(self.process.stdout.readline(),30))
            if hello.get('ready') is not True:raise ValueError('worker startup')
        except BaseException:
            await self.close();raise
    async def prepare(self):
        async with self.lock:await self.ready()
    async def transcribe(self,pcm):
        # A first partial can arrive while the page is warming the model. Wait for
        # that preparation instead of turning an ordinary warmup into a mic failure.
        try:await asyncio.wait_for(self.lock.acquire(),35)
        except asyncio.TimeoutError:raise HTTPException(503,'Local transcription is busy. Finish or stop another recording, then try again.')
        try:
            try:
                await self.ready()
                self.process.stdin.write((json.dumps({'pcm':base64.b64encode(pcm).decode()})+'\n').encode())
                await self.process.stdin.drain()
                result=json.loads(await asyncio.wait_for(self.process.stdout.readline(),25))
                if not isinstance(result.get('text'),str):raise ValueError('worker reply')
                return result['text']
            except HTTPException:raise
            except BaseException:
                await self.close();raise
        finally:self.lock.release()

engine=LocalSpeech()

@router.get('/api/voice/status')
async def status():
    return {'available':configuration() is not None,'engine':'local-whisper','audioStored':False,'maxSeconds':60}

@router.post('/api/voice/prepare')
async def prepare():
    try:await engine.prepare();return {'ready':True}
    except HTTPException:raise
    except Exception:raise HTTPException(503,'Local speech recognition could not start. Check the Whisper installation.')

@router.post('/api/voice/transcribe')
async def transcribe(request:Request):
    if request.headers.get('content-type','').split(';')[0]!='audio/wav':
        raise HTTPException(415,'Send mono 16 kHz PCM WAV audio.')
    body=await request.body()
    if len(body)>1_920_100:raise HTTPException(413,'Voice clips are limited to 60 seconds.')
    try:
        with wave.open(io.BytesIO(body),'rb') as audio:
            if (audio.getnchannels(),audio.getsampwidth(),audio.getframerate(),audio.getcomptype())!=(1,2,16000,'NONE'):
                raise ValueError('format')
            frames=audio.getnframes()
            if not 1600<=frames<=960000:raise ValueError('duration')
            pcm=audio.readframes(frames)
            if len(pcm)!=frames*2:raise ValueError('truncated')
    except (ValueError,EOFError,wave.Error):raise HTTPException(422,'Invalid audio. Use a mono 16 kHz PCM WAV clip of up to 60 seconds.')
    try:
        text=await engine.transcribe(pcm)
        return {'text':text,'engine':'local-whisper','audioStored':False}
    except HTTPException:raise
    except Exception:raise HTTPException(503,'Local transcription was interrupted. Your message has not been sent.')
