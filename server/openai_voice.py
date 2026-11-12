"""OpenAI audio transport credentials; never substitutes the selected Architect."""
import os
import time
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter()
MODEL = 'gpt-realtime-2.1-mini'
TRANSCRIPTION_MODEL = 'gpt-transcribe'
VOICE = 'marin'
TOKEN_URL = 'https://api.openai.com/v1/realtime/client_secrets'
_voice_key = None


def api_key():
    # Dedicated voice credential first, then the existing server OpenAI key.
    # Never a native-login token, project file or extracted CLI credential.
    from .app import ARCHITECT
    return _voice_key or ARCHITECT.keys.get('openai') or os.getenv('OPENAI_API_KEY')


def configuration():
    return {'model': MODEL, 'type': 'realtime', 'output_modalities': ['audio'],
            'instructions': 'You are the audio interface for a separate Architect. Read only the supplied written reply aloud naturally. Do not answer architecture questions yourself, add decisions, use tools or claim to have performed work.',
            'tools': [],
            'audio': {'input': {'transcription': {'model': TRANSCRIPTION_MODEL},
                                'turn_detection': {'type': 'server_vad', 'create_response': False,
                                                   'interrupt_response': False}},
                      'output': {'voice': VOICE}}}


class VoiceRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')


class VoiceCredentialRequest(VoiceRequest):
    key: str = Field(max_length=5000, strict=True)


@router.post('/api/voice/openai/credentials')
async def configure_key(payload: VoiceCredentialRequest):
    global _voice_key
    _voice_key = payload.key.strip() or None
    return {'configuredInMemory': bool(_voice_key)}


@router.get('/api/voice/openai/status')
async def status():
    return {'available': bool(api_key()), 'engine': 'openai-realtime', 'model': MODEL,
            'voice': VOICE, 'audioDestination': 'OpenAI', 'audioStoredByArchitect': False}


@router.post('/api/voice/openai/session')
async def create_session(payload: VoiceRequest):
    key = api_key()
    if not key:
        raise HTTPException(503, 'OpenAI voice needs an OpenAI API key on the Architect server. Configure it in the voice panel; your selected Architect model stays unchanged.')
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            response = await client.post(TOKEN_URL, headers={'Authorization': 'Bearer '+key},
                json={'expires_after': {'anchor': 'created_at', 'seconds': 60}, 'session': configuration()})
        if response.status_code == 429:
            raise HTTPException(429, 'OpenAI voice is rate limited. Retry after a short wait.')
        if response.status_code in {401, 403}:
            raise HTTPException(503, 'The OpenAI API key could not start voice. Check its permissions and account access.')
        if response.status_code != 200:
            raise HTTPException(502, 'OpenAI voice could not start. Check API access and retry; no local voice fallback was selected.')
        value = response.json()
        if (not isinstance(value, dict) or not isinstance(value.get('value'), str)
                or not value['value'].startswith('ek_') or len(value['value']) > 4096
                or type(value.get('expires_at')) not in {int, float}
                or not time.time() < value['expires_at'] <= time.time()+120):
            raise ValueError('Invalid ephemeral credential response')
        return {'value': value['value'], 'expires_at': value['expires_at'], 'model': MODEL, 'voice': VOICE}
    except HTTPException:
        raise
    except Exception:
        # Never expose upstream bodies, credentials or HTTP transport diagnostics.
        raise HTTPException(502, 'OpenAI voice connection failed. Check API access and retry.') from None
