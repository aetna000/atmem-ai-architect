"""Private local worker: bounded PCM requests via stdin, text via stdout. No audio files."""
import base64, json, os, sys
import numpy as np
import torch
import whisper

torch.set_num_threads(4)
model = whisper.load_model(sys.argv[1], device='cpu')  # Exact existing checkpoint; never downloads.
print(json.dumps({'ready': True}), flush=True)
for line in sys.stdin:
    try:
        payload=json.loads(line)
        raw=base64.b64decode(payload['pcm'], validate=True)
        if not 3200 <= len(raw) <= 1_920_000 or len(raw)%2:
            raise ValueError('audio size')
        samples=np.frombuffer(raw,dtype='<i2').astype(np.float32)/32768
        if np.sqrt(np.mean(samples*samples)) < .003:
            text=''
        else:
            result=model.transcribe(samples,language='en',fp16=False,temperature=0,
                condition_on_previous_text=False,verbose=None)
            text=' '.join(s['text'].strip() for s in result.get('segments',[])
                if s.get('no_speech_prob',0)<.8).strip()
        print(json.dumps({'text':text[:12000]}),flush=True)
    except Exception:
        print(json.dumps({'error':'Local transcription failed.'}),flush=True)
